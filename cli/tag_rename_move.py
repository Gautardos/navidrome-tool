import os
import mutagen.easyid3
from mutagen.easyid3 import EasyID3
import shutil
import time
import re
from datetime import datetime

# Répertoires
DOWNLOADS_DIR = "/downloads/"  # Source des téléchargements
BASE_PROCESSED_DIR = "/music/downloads/"  # Dossier de base pour les sous-dossiers nommés d’après l’artiste de l’album

# Règles de mapping des genres avec expressions régulières
GENRE_PATTERNS = {
    r"\s*rap\s*": "Rap & Hip-Hop",  # "rap" avec espaces avant/après
    r"\s*(hip[- ]?hop)\s*": "Rap & Hip-Hop",  # "hip hop" ou "hip-hop" avec espaces avant/après
    r"\s*[gG][- ]?[fF][uU][nN][kK]\s*": "Rap & Hip-Hop",  # "G-Funk", "g-funk", "G Funk", etc., avec espaces/tirets (pattern original de l’utilisateur)
    # Ajoute d'autres patterns ici selon tes besoins
}

def ensure_directory(path):
    """Assure que le répertoire existe avec les permissions correctes, avec gestion non bloquante de [Errno 1]."""
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            os.chown(path, 1000, 33)  # UID de gautard (1000), GID de www-data (33)
            os.chmod(path, 0o775)
            log_action("Dossier créé et permissions ajustées avec succès", path)
        except PermissionError as e:
            if e.errno == 1:  # Operation not permitted
                log_action("Erreur de permission non bloquante pour le dossier", path, f"Exception : [Errno 1] Operation not permitted - Ignorée")
            else:
                log_action("Erreur de permission bloquante pour le dossier", path, f"Exception : {str(e)}")
                raise  # Relève l’erreur si ce n’est pas [Errno 1]
    except Exception as e:
        log_action("Erreur lors de la création du dossier", path, f"Exception : {str(e)}")
        raise

def log_action(action, file_path, message=""):
    """Journalise les actions dans status_history.txt via spotdl-consumer.py."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open("/home/gautard/spotdl-web/log/status_history.txt", 'a') as f:
        f.write(f"[{timestamp}] Fichier: {file_path} - {action} - {message}\n")
    os.chown("/home/gautard/spotdl-web/log/status_history.txt", 1000, 33)
    os.chmod("/home/gautard/spotdl-web/log/status_history.txt", 0o664)

def sanitize_name(name):
    """Remplace les '/' par des ',' dans un nom pour éviter les erreurs de chemin, et normalise les espaces."""
    if not name:
        return ""
    # Normalise les espaces multiples et supprime les espaces en début/fin
    name = " ".join(name.split()).strip()
    return name.replace("/", ",") if name else ""

def map_genre(genre):
    """Mappe un genre vers une valeur standardisée en utilisant des expressions régulières, avec journalisation pour débogage."""
    if not genre:
        log_action("Genre manquant (débogage)", "", "Genre vide")
        return "Unknown"
    # Vérifie la valeur exacte, y compris les caractères invisibles, l’encodage, et les octets bruts
    genre_str = str(genre) if not isinstance(genre, str) else genre
    genre_encoded = genre_str.encode('utf-8', errors='replace').decode('utf-8')
    genre_bytes = genre_str.encode('utf-8', errors='replace') if isinstance(genre_str, str) else b''
    genre_lower = genre_str.lower()
    log_action("Genre analysé (débogage)", "", f"Genre type : {type(genre_str)}, Genre original : {genre_str!r}, Genre encoded : {genre_encoded!r}, Genre bytes : {genre_bytes!r}, Genre lowercase : {genre_lower!r}")
    for pattern, mapped_genre in GENRE_PATTERNS.items():
        if re.search(pattern, genre_lower):
            log_action("Genre mappé avec regex (débogage)", "", f"Pattern matché : {pattern}, Nouveau genre : {mapped_genre}")
            return mapped_genre
    log_action("Genre non mappé (débogage)", "", f"Genre non mappé : {genre_lower!r}")
    return genre  # Retourne le genre original si aucun mapping n'est trouvé

def get_processed_dir(main_artist):
    """Retourne le chemin du dossier processed basé sur l’artiste principal (albumartist) sous /music/downloads/."""
    artist_folder = sanitize_name(main_artist) or "Unknown"
    return os.path.join(BASE_PROCESSED_DIR, artist_folder)

def process_mp3_file(file_path):
    """Traite un fichier MP3 : modifie les tags ID3, renomme avec tracknum sur 2 digits, utilise albumartist comme artiste principal, et ajuste le titre avec featuring basé sur artist, avec journalisation."""
    try:
        log_action("Début du traitement", file_path)

        # Charge les tags ID3 avec mutagen
        try:
            audio = EasyID3(file_path)
        except Exception as e:
            log_action("Erreur de chargement des tags", file_path, f"Exception : {str(e)}")
            return  # Passe au fichier suivant si les tags sont inaccessibles

        # Règle 1 : Mapper les genres musicaux avec des expressions régulières
        if "genre" in audio:
            original_genre = audio["genre"][0]
            new_genre = map_genre(original_genre)
            if new_genre != original_genre:
                audio["genre"] = new_genre
                log_action("Genre mappé avec regex", file_path, f"Genre original : {original_genre}, Nouveau genre : {new_genre}")
            else:
                log_action("Genre non mappé, conservé", file_path, f"Genre : {original_genre}")
        else:
            audio["genre"] = ["Unknown"]
            log_action("Genre manquant", file_path, "Défini à 'Unknown'")

        # Règle 2 : Utiliser albumartist comme artiste principal, et générer featuring à partir de artist
        if "albumartist" in audio:
            main_artist = sanitize_name(audio["albumartist"][0])
        else:
            # Si albumartist n'existe pas, utilise le premier artiste de artist comme fallback
            if "artist" in audio:
                artists = [sanitize_name(a.strip()) for a in audio["artist"][0].split(",") if a.strip()]
                main_artist = artists[0] if artists else "Unknown"
            else:
                main_artist = "Unknown"
        log_action("Artiste principal défini", file_path, f"Artiste principal (albumartist) : {main_artist}")

        # Générer les featuring en comparant artist avec albumartist, en divisant uniquement sur ',' et supprimant l’albumartist
        featuring_artists = []
        if "artist" in audio:
            artist_str = sanitize_name(audio["artist"][0])
            log_action("Artistes analysés (débogage)", file_path, f"Artist original : {artist_str!r}")
            # Divise uniquement sur ',' et supprime les espaces
            all_artists = [a.strip() for a in artist_str.split(",") if a.strip()]
            all_artists = list(dict.fromkeys(all_artists))  # Supprime les doublons
            for artist in all_artists:
                if artist and artist != main_artist:
                    featuring_artists.append(artist)
            log_action("Artistes extraits (débogage)", file_path, f"Artistes : {all_artists}, Artiste principal : {main_artist}, Featuring : {featuring_artists}")
        # Après avoir déterminé featuring_artists et original_title
        if featuring_artists:
            original_title = sanitize_name(audio["title"][0])
            if "feat. " not in original_title.lower():
                audio["title"] = f"{original_title} (feat. {', '.join(featuring_artists)})"
                log_action("Featuring ajoutés au titre", file_path, f"Titre : {audio['title'][0]}")
            else:
                log_action("Titre conservé sans ajout de featuring", file_path, f"Titre existant : {original_title}")
        elif "title" in audio:
            audio["title"] = sanitize_name(audio["title"][0])
            log_action("Titre conservé sans featuring", file_path, f"Titre : {audio['title'][0]}")
        else:
            audio["title"] = "Untitled"
            log_action("Titre manquant, défini à 'Untitled'", file_path)

        # Obtient les tags nécessaires pour le renommage, avec tracknum sur 2 digits et remplacement des '/'
        tracknum = audio.get("tracknumber", ["1"])[0].split("/")[0]  # Prend le numéro de piste (si existe)
        try:
            tracknum = str(int(tracknum)).zfill(2)  # Formate sur 2 digits (par exemple, 6 -> 06)
        except ValueError:
            tracknum = "01"  # Valeur par défaut si le numéro de piste n'est pas un entier
        artist = main_artist  # Utilise l’artiste de l’album comme artiste principal
        audio['artist'] = artist; # Remplace l'artiste par l'artiste de l'album
        album = sanitize_name(audio.get("album", ["Unknown"])[0])
        title = audio["title"][0]
        ext = os.path.splitext(file_path)[1].lower()  # Extension (par exemple, .mp3)

        # Vérifie si le nouveau nom existe déjà dans /music/downloads/<albumartist>/, et écrase l’ancien fichier
        processed_dir = get_processed_dir(main_artist)
        new_filename = f"{artist} - {album} - {tracknum} - {title}{ext}"
        new_path = os.path.join(processed_dir, new_filename)
        if os.path.exists(new_path):
            log_action("Fichier existant détecté, écrasement", file_path, f"Nom existant : {new_filename}")
            try:
                os.remove(new_path)  # Supprime l’ancien fichier
                log_action("Ancien fichier supprimé avec succès", new_path)
            except Exception as e:
                log_action("Erreur lors de la suppression de l’ancien fichier", new_path, f"Exception : {str(e)}")
                raise  # Relève l’erreur si la suppression échoue

        # Sauvegarde les nouveaux tags (sans modifier les '/' dans les tags, sauf si nécessaire)
        audio.save(file_path)
        log_action("Tags ID3 sauvegardés", file_path)

        # Déplace et renomme le fichier dans le dossier /music/downloads/<albumartist>
        ensure_directory(processed_dir)
        new_path = new_path.replace(":", "")
        shutil.move(file_path, new_path)
        log_action("Fichier déplacé et renommé (ou écrasé)", file_path, f"Nouvelle position : {new_path}")

        # Tente de modifier la propriété et les permissions, avec gestion spécifique de [Errno 1]
        try:
            os.chown(new_path, 1000, 33)  # UID de gautard (1000), GID de www-data (33)
            os.chmod(new_path, 0o664)
            log_action("Permissions ajustées avec succès", new_path)
        except PermissionError as e:
            if e.errno == 1:  # Operation not permitted
                log_action("Erreur de permission non bloquante", new_path, f"Exception : [Errno 1] Operation not permitted - Ignorée")
            else:
                log_action("Erreur de permission bloquante", new_path, f"Exception : {str(e)}")
                raise  # Relève l’erreur si ce n’est pas [Errno 1]
    except Exception as e:
        log_action("Erreur générale lors du traitement", file_path, f"Exception : {str(e)}")

def main():
    """Scanne et traite tous les fichiers MP3 dans /downloads/, sans supprimer les fichiers restants sauf en cas de succès."""
    # Crée le dossier de base /music/downloads/ s’il n’existe pas
    ensure_directory(BASE_PROCESSED_DIR)

    # Liste tous les fichiers dans /downloads/
    processed_files = []
    for filename in os.listdir(DOWNLOADS_DIR):
        if filename.lower().endswith('.mp3'):
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            process_mp3_file(file_path)
            processed_files.append(filename)

    # Supprime uniquement les fichiers qui ont été traités avec succès
    for filename in processed_files:
        file_path = os.path.join(DOWNLOADS_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                log_action("Fichier supprimé de /downloads/", file_path, "Après traitement réussi")
            except Exception as e:
                log_action("Erreur lors de la suppression", file_path, f"Exception : {str(e)}")

if __name__ == "__main__":
    main()
