import sqlite3
import os
import time
import datetime
import mutagen
from mutagen.id3 import ID3, USLT, SYLT
import psutil
import sys
from pathlib import Path
from utils.logger import Logger  # Importer la classe Logger depuis utils.logger
from utils.lyrics import Lyrics  # Importer la classe Lyrics depuis utils.lyrics

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'db')
DB_PATH = os.path.join(DB_DIR, 'database.db')

AUDIO_EXTENSIONS = (".mp3", ".flac", ".m4a")  # Extensions audio supportées

# Initialisation de la base de données (pour tracks)
def init_db(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE,
        updated_at TEXT,
        title TEXT,
        album TEXT,
        artist TEXT,
        album_artist TEXT,
        year INTEGER,
        genre TEXT,
        has_image INTEGER,
        lyrics_type TEXT,
        completeness REAL
    )''')
    conn.commit()

# Extraction des métadonnées et calcul de la complétude
def extract_metadata(file_path, file_mtime, logger):
    try:
        audio = mutagen.File(file_path, easy=True)
        if audio is None:
            return None

        tags = audio.tags if audio.tags else {}
        id3 = ID3(file_path) if file_path.endswith(".mp3") else None

        # Extraire les paroles
        lyrics = None
        if id3:
            # Priorité aux paroles synchronisées (SYLT)
            sylt = id3.getall("SYLT")
            if sylt and sylt[0].text:
                lyrics = sylt[0].text
            else:
                # Sinon, prendre les paroles non synchronisées (USLT)
                uslt = id3.getall("USLT")
                if uslt and uslt[0].text:
                    lyrics = uslt[0].text

        # Déterminer le type de paroles avec la classe Lyrics
        lyrics_type = Lyrics.get_lyrics_type(lyrics) if lyrics else None

        # Métadonnées de base
        metadata = {
            "path": file_path,
            "updated_at": datetime.datetime.fromtimestamp(file_mtime).isoformat(),
            "title": tags.get("title", [None])[0],
            "album": tags.get("album", [None])[0],
            "artist": tags.get("artist", [None])[0],
            "album_artist": tags.get("albumartist", [None])[0] or tags.get("artist", [None])[0],
            "year": int(tags.get("date", [None])[0].split("-")[0]) if tags.get("date") else None,
            "genre": tags.get("genre", [None])[0],
            "has_image": 1 if id3 and id3.getall("APIC") else 0 if id3 else (1 if audio.pictures else 0),
            "lyrics_type": lyrics_type,
            "completeness": 0.0
        }

        # Calcul de la complétude selon les nouvelles règles
        base_score = 0
        criteria = {
            "artist": metadata["artist"] is not None,
            "album": metadata["album"] is not None,
            "title": metadata["title"] is not None,
            "image": metadata["has_image"] == 1,
            "lyrics": metadata["lyrics_type"] is not None
        }

        if all(criteria.values()) and metadata["lyrics_type"] == "sync":
            base_score = 100
        elif all([criteria["artist"], criteria["album"], criteria["title"], criteria["image"]]) and metadata["lyrics_type"] == "unsync":
            base_score = 90
        else:
            base_score = 100  # Point de départ
            missing_count = sum(1 for value in criteria.values() if not value)
            base_score -= missing_count * 20
            base_score = max(0, base_score)  # Pas en dessous de 0

        metadata["completeness"] = base_score

        return metadata
    except Exception as e:
        logger.log("error", "warning", "metadata", f"Erreur extraction {file_path}: {str(e)}")
        return None

# Mise à jour ou insertion d'un fichier dans la base
def update_or_insert_track(conn, metadata):
    c = conn.cursor()
    c.execute("SELECT updated_at FROM tracks WHERE path = ?", (metadata["path"],))
    result = c.fetchone()
    
    if result:
        db_updated_at = result[0]
        if metadata["updated_at"] > db_updated_at:
            c.execute('''UPDATE tracks SET 
                updated_at = ?, title = ?, album = ?, artist = ?, album_artist = ?, 
                year = ?, genre = ?, has_image = ?, lyrics_type = ?, completeness = ?
                WHERE path = ?''', 
                (metadata["updated_at"], metadata["title"], metadata["album"], metadata["artist"],
                 metadata["album_artist"], metadata["year"], metadata["genre"], metadata["has_image"],
                 metadata["lyrics_type"], metadata["completeness"], metadata["path"]))
            return "updated"
    else:
        c.execute('''INSERT INTO tracks (path, updated_at, title, album, artist, album_artist, 
                year, genre, has_image, lyrics_type, completeness) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (metadata["path"], metadata["updated_at"], metadata["title"], metadata["album"],
                 metadata["artist"], metadata["album_artist"], metadata["year"], metadata["genre"],
                 metadata["has_image"], metadata["lyrics_type"], metadata["completeness"]))
        return "inserted"
    return None

# Détection des suppressions limitées au répertoire de scan
def detect_deletions(conn, current_files, logger, scan_directory):
    c = conn.cursor()
    c.execute("SELECT path FROM tracks")
    db_files = set(row[0] for row in c.fetchall())
    deleted_files = db_files - current_files
    
    scan_directory_normalized = os.path.normpath(scan_directory)
    delete_count = 0
    
    for file_path in deleted_files:
        file_path_normalized = os.path.normpath(file_path)
        # Vérifier si le fichier est un enfant du répertoire de scan
        if file_path_normalized.startswith(scan_directory_normalized + os.sep) or file_path_normalized == scan_directory_normalized:
            c.execute("DELETE FROM tracks WHERE path = ?", (file_path,))
            logger.log("scan", "info", "delete", f"Fichier supprimé: {file_path}")
            delete_count += 1
    
    return delete_count

# Scan du dossier
def scan_directory(directory, conn, logger):
    start_time = time.time()
    max_memory = 0
    adds, updates, deletes = 0, 0, 0
    
    logger.log("scan", "info", "start", f"Début du scan du répertoire {directory}")
    
    current_files = set()
    
    # Parcours récursif avec transaction
    with conn:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(AUDIO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    current_files.add(file_path)
                    file_mtime = os.path.getmtime(file_path)
                    
                    metadata = extract_metadata(file_path, file_mtime, logger)
                    if metadata:
                        action = update_or_insert_track(conn, metadata)
                        if action == "inserted":
                            adds += 1
                        elif action == "updated":
                            updates += 1
                    
                    # Suivi mémoire
                    memory = psutil.Process().memory_info().rss / 1024 / 1024  # Mo
                    max_memory = max(max_memory, memory)
    
        # Détection des suppressions limitées au répertoire de scan
        deletes = detect_deletions(conn, current_files, logger, directory)
    
    # Récapitulatif
    end_time = time.time()
    execution_time = end_time - start_time
    recap = (f"Scan terminé: {adds} ajouts, {updates} mises à jour, {deletes} suppressions, "
             f"temps: {execution_time:.2f}s, mémoire max: {max_memory:.2f} Mo")
    logger.log("scan", "info", "summary", recap)

# Point d'entrée
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print("Le chemin spécifié n'est pas un dossier valide.")
        sys.exit(1)
    
    # Créer une seule connexion SQLite partagée
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 5000")  # Attendre jusqu'à 5 secondes si la base est verrouillée
    
    try:
        init_db(conn)
        logger = Logger(conn)  # Passer la connexion au logger
        scan_directory(directory, conn, logger)
    finally:
        conn.close()  # Assurer la fermeture de la connexion