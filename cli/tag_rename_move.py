import os
import mutagen.easyid3
from mutagen.easyid3 import EasyID3
import shutil
import time
import re
import requests
import json
from datetime import datetime
from mutagen.id3 import ID3, TDRC  # Ajout pour gérer la date

# Répertoires
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'etc', 'config.json'))
TAG_CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'etc', 'tag_config.json'))
STATUS_HISTORY_FILE = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'log', 'status_history.txt'))
COMMAND_HISTORY_FILE = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'log', 'command_history.txt'))

def load_tag_config():
    """Charge les règles de mapping des genres depuis tag_config.json."""
    try:
        with open(TAG_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return config.get('genre_patterns', {})
    except FileNotFoundError:
        log_action("Erreur : Fichier de configuration des tags manquant", TAG_CONFIG_PATH, "")
        return {}
    except json.JSONDecodeError:
        log_action("Erreur : Fichier tag_config.json invalide", TAG_CONFIG_PATH, "Utilisation de règles par défaut")
        return {}
    except Exception as e:
        log_action("Erreur lors du chargement de tag_config.json", TAG_CONFIG_PATH, f"Exception : {str(e)}")
        return {}

def ensure_directory(path):
    """Assure que le répertoire existe avec les permissions correctes, avec gestion non bloquante de [Errno 1]."""
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            os.chmod(path, 0o775)  # Utilise les permissions courantes
            log_action("Dossier créé et permissions ajustées avec succès", path, "")
        except PermissionError as e:
            if e.errno == 1:  # Operation not permitted
                log_action("Erreur de permission non bloquante pour le dossier - Ignorée", path, f"Exception : [Errno 1] Operation not permitted")
            else:
                log_action("Erreur de permission bloquante pour le dossier", path, f"Exception : {str(e)}")
                raise
    except Exception as e:
        log_action("Erreur lors de la création du dossier", path, f"Exception : {str(e)}")
        raise

def log_action(action, file_path, message=""):
    """Journalise les actions dans status_history.txt via spotdl-consumer.py."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(STATUS_HISTORY_FILE, 'a') as f:
        f.write(f"[{timestamp}] Fichier: {file_path} - {action} - {message}\n")
    try:
        os.chown(STATUS_HISTORY_FILE, os.getuid(), os.getgid())  # Utilise UID/GID courant
        os.chmod(STATUS_HISTORY_FILE, 0o664)
    except PermissionError as e:
        if e.errno == 1:
            log_action("Erreur de permission non bloquante pour log - Ignorée", STATUS_HISTORY_FILE, f"Exception : [Errno 1] Operation not permitted")
        else:
            log_action("Erreur de permission bloquante pour log", STATUS_HISTORY_FILE, f"Exception : {str(e)}")

def sanitize_name(name):
    """Remplace les '/' par des ',' dans un nom pour éviter les erreurs de chemin, normalise les espaces, et supprime un '.' uniquement s'il est à la fin."""
    if not name:
        return ""
    name = " ".join(name.split()).strip()
    if name.endswith('.'):
        name = name.rstrip('.')  # Supprime le point uniquement s'il est à la fin
    return name.replace("/", ",").replace('"', "").replace(":", "").replace("?", "").replace("¿", "") if name else ""

def map_genre(genre, genre_patterns):
    """Mappe un genre vers une valeur standardisée en utilisant des expressions régulières configurables, avec journalisation pour débogage."""
    if not genre:
        #log_action("Genre manquant (débogage)", "", "Genre vide")
        return "Unknown"
    genre_str = str(genre) if not isinstance(genre, str) else genre
    genre_encoded = genre_str.encode('utf-8', errors='replace').decode('utf-8')
    genre_bytes = genre_str.encode('utf-8', errors='replace') if isinstance(genre_str, str) else b''
    genre_lower = genre_str.lower()
    #log_action("Genre analysé (débogage)", "", f"Genre type : {type(genre_str)}, Genre original : {genre_str!r}, Genre encoded : {genre_encoded!r}, Genre bytes : {genre_bytes!r}, Genre lowercase : {genre_lower!r}")
    for pattern, mapped_genre in genre_patterns.items():
        try:
            if re.search(pattern, genre_lower):
                #log_action("Genre mappé avec regex (débogage)", "", f"Pattern matché : {pattern}, Nouveau genre : {mapped_genre}")
                return mapped_genre
        except re.error as e:
            #log_action("Erreur dans le pattern regex (débogage)", "", f"Pattern invalide : {pattern}, Exception : {str(e)}")
            continue
    #log_action("Genre non mappé (débogage)", "", f"Genre non mappé : {genre_lower!r}")
    return genre

def get_processed_dir(main_artist, music_path):
    """Retourne le chemin du dossier processed basé sur l’artiste principal (albumartist) sous /music/downloads/."""
    artist_folder = sanitize_name(main_artist) or "Unknown"
    return os.path.join(music_path, artist_folder)

def process_mp3_file(file_path, music_dir, genre_patterns, config):
    """Traite un fichier MP3 : modifie les tags ID3, renomme avec tracknum sur 2 digits, utilise albumartist comme artiste principal, et ajuste le titre avec featuring basé sur artist, avec journalisation."""
    try:
        log_action("Début du traitement", file_path)

        # Charge les tags ID3 avec mutagen
        try:
            audio = EasyID3(file_path)
            # Charge aussi les tags complets pour gérer la date
            audio_full = ID3(file_path)
        except Exception as e:
            log_action("Erreur de chargement des tags", file_path, f"Exception : {str(e)}")
            return

        # Récupérer la date si elle existe
        date = audio.get("originaldate", audio_full.get('TDRC', ['0000'])[0])
        if isinstance(date, list):
            date = date[0]  # Prendre la première valeur si c'est une liste
        log_action("Date récupérée", file_path, f"Date: {date}")

        # Règle 2 : Utiliser albumartist comme artiste principal, et générer featuring à partir de artist
        if "albumartist" in audio:
            main_artist = sanitize_name(audio["albumartist"][0])
        else:
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
            all_artists = [a.strip() for a in artist_str.split(",") if a.strip()]
            all_artists = list(dict.fromkeys(all_artists))  # Supprime les doublons
            for artist in all_artists:
                if artist and artist != main_artist:
                    featuring_artists.append(artist)
            log_action("Artistes extraits (débogage)", file_path, f"Artistes : {all_artists}, Artiste principal : {main_artist}, Featuring : {featuring_artists}")
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
        tracknum = audio.get("tracknumber", ["1"])[0].split("/")[0]
        try:
            tracknum = str(int(tracknum)).zfill(2)
        except ValueError:
            tracknum = "01"
        artist = main_artist
        audio['artist'] = artist  # Remplace l'artiste par l'artiste de l'album
        album = sanitize_name(audio.get("album", ["Unknown"])[0])
        title = audio["title"][0]
        ext = os.path.splitext(file_path)[1].lower()

        # Assurer que la date est conservée
        audio["date"] = date

        # Règle : Mapper les genres musicaux avec des expressions régulières configurables
        tagging_config = config.get('tag', {})
        genre_tagging_mode = tagging_config.get('genre-tagging-mode', 'mapping')
        
        if "genre" in audio:
            original_genre = audio["genre"][0]
            new_genre = map_genre(original_genre, genre_patterns)
            if new_genre != original_genre:
                audio["genre"] = new_genre
                log_action("Genre mappé avec regex", file_path, f"Genre original : {original_genre}, Nouveau genre : {new_genre}")
            else:
                log_action("Genre non mappé, conservé", file_path, f"Genre : {original_genre}")
        else:
            audio["genre"] = ["Unknown"]
            log_action("Genre manquant", file_path, "Défini à 'Unknown'")

        # Vérifie si le nouveau nom existe déjà dans /music/downloads/<albumartist>/, et écrase l’ancien fichier
        processed_dir = get_processed_dir(main_artist, music_dir)
        new_filename = f"{artist} - {album} - {tracknum} - {title}{ext}"
        new_path = os.path.join(processed_dir, new_filename)
        if os.path.exists(new_path):
            log_action("Fichier existant détecté, écrasement", file_path, f"Nom existant : {new_filename}")
            try:
                OldAudio = EasyID3(new_path)
                audio["genre"] = OldAudio["genre"]
                os.remove(new_path)
                log_action("Ancien fichier supprimé avec succès & ancien genre conservé", new_path, "")
            except Exception as e:
                log_action("Erreur lors de la suppression de l’ancien fichier", new_path, f"Exception : {str(e)}")
                raise
        else:
            if genre_tagging_mode == "ai" and audio["genre"][0] == "Unknown":
                ai_genre = detect_genre_with_grok(artist, album, config)
                audio["genre"] = ai_genre
                log_action("Genre détecté par Grok", file_path, f"Genre : {ai_genre}")
        
        # Sauvegarde les nouveaux tags, y compris la date
        audio.save(file_path)
        # Vérification supplémentaire avec ID3 pour garantir la persistance de TDRC
        audio_full = ID3(file_path)
        audio_full['TDRC'] = TDRC(encoding=3, text=date)
        audio_full.save(file_path)
        log_action("Tags ID3 sauvegardés avec date", file_path, f"Date conservée: {date}")

        # Vérifier les permissions pour le répertoire source et destination
        source_dir = os.path.dirname(file_path)
        dest_dir = os.path.dirname(new_path)
        ensure_directory(dest_dir)

        if not os.access(source_dir, os.W_OK | os.R_OK):
            log_action(f"Erreur : Pas de permissions pour accéder au répertoire source {source_dir}", file_path, f"Nouvelle position : {new_path}")
            return
        if not os.access(dest_dir, os.W_OK | os.R_OK):
            log_action(f"Erreur : Pas de permissions pour écrire dans {dest_dir}", file_path, f"Nouvelle position : {new_path}")
            return

        # Déplacer le fichier
        new_path = new_path.replace(":", "")
        shutil.move(file_path, new_path)
        log_action("Fichier déplacé et renommé (ou écrasé)", file_path, f"Nouvelle position : {new_path}")

        # Ajuster les permissions avec l’utilisateur courant
        try:
            os.chmod(new_path, 0o664)  # rw-rw-r--
            log_action("Permissions ajustées avec succès avec permissions courantes", new_path, "")
        except PermissionError as e:
            if e.errno == 1:  # Operation not permitted
                log_action("Erreur de permission non bloquante ignorée", new_path, f"Exception : [Errno 1] Operation not permitted")
            else:
                log_action("Erreur de permission bloquante", new_path, f"Exception : {str(e)}")
                raise
        except Exception as e:
            log_action("Erreur générale lors de l’ajustement des permissions", new_path, f"Exception : {str(e)}")
            raise
    except Exception as e:
        log_action("Erreur générale lors du traitement", file_path, f"Exception : {str(e)}")

def detect_genre_with_grok(artist, album, config):
    grok_config = config.get('grok_api', {})
    api_key = grok_config.get('api_key', '')
    url = grok_config.get('endpoint', '')
    model = grok_config.get('model', '')

    """
    Détecte le genre musical d'une chanson via l'API xAI à https://api.x.ai/v1/chat/completions.
    
    Args:
        artist (str): Nom de l'artiste
        album (str): Nom de l'album
        config (dict): Configuration contenant les informations de l'API
    
    Returns:
        str: Le ou les genres détectés selon la catégorisation définie, séparés par '/'
    """
    # Créer une clé unique pour le cache basée sur artist et album
    cache_key = f"{artist.lower()}|{album.lower()}"

    # Vérifier si le résultat est déjà dans le cache
    if cache_key in genre_cache:
        return genre_cache[cache_key]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Structure des messages pour l'API
    messages = [
        {
            "role": "system",
            "content": """
            Tu es un expert en classification musicale. Ton objectif est de déterminer le genre musical d'une chanson à partir de son artiste et de son titre, en respectant strictement une catégorisation spécifique. 
            Les genres peuvent être cumulables : si un morceau appartient à plusieurs catégories, sépare les genres par le caractère ' / '. 
            Rap & Hip-Hop n'est cumulable qu'avec Latin sinon il est dominant
            
            Voici les règles précises que tu dois suivre :
            - "Rap & Hip-Hop" : Pour tous les morceaux de rap et hip-hop avec des paroles dans une langue autre que le français.
            - "Rap Français" : Pour tous les morceaux de rap avec des paroles en français.
            - "Electro" : Pour tous les morceaux de musique électronique (techno, trance, EDM, etc.), sauf la house.
            - "House" : Pour tous les types de house (deep house, progressive house, tech house, etc.).
            - "Reggaeton" : Pour tous les morceaux de reggaeton.
            - "Variété Américaine" : Pour tous les morceaux de chanson (hors rap, hip-hop, electro, house, reggaeton, pop, rock) d'artistes américains ou avec des paroles en anglais américain.
            - "Variété Internationale" : Pour tous les morceaux de chanson (hors rap, hip-hop, electro, house, reggaeton, pop, rock) dans une langue autre que le français ou l'anglais américain.
            - "Variété Française" : Pour tous les morceaux de chanson (hors rap, hip-hop, electro, house, reggaeton, pop, rock) avec des paroles en français.
            - "Pop" : Pour tous les morceaux de pop, quelle que soit la langue.
            - "Rock" : Pour tous les morceaux de rock ou apparentés (rock alternatif, punk, metal, grunge, etc.).
            - "Latin" : Pour tous les morceaux de musique latine (salsa, bachata, cumbia, etc.), hors reggaeton.
            - "Instrumental / Trip-Hop" : Pour tous les morceaux sans paroles d'abstract hip-hop, trip-hop ou instrumentaux dans ce style.
            - "Ambiance" : Pour tous les morceaux d'ambiance (chill, downtempo, lounge, etc.).
            - "Classical" : Pour tous les morceaux orchestraux ou de musique classique.
            - "Funk" : Pour tous les morceaux de funk ou genres apparentés
            - "Jazz" : Pour tous les morceaux de jazz ou genres apparentés
            - "Soul" : Pour tous les morceaux de soul ou genres apparentés

            Instructions :
            - Si tu as un doute sur la langue ou le style, base-toi sur les informations typiquement associées à l'artiste ou à l'album.
            - Réponds UNIQUEMENT par le nom du ou des genres, sans aucun autre texte, commentaire ou explication (exemple : "Pop / Rock").
            """
        },
        {
            "role": "user",
            "content": f"Analyse l'artiste '{artist}' et l'album '{album}'. Quelle est ta réponse ?"
        }
    ]
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 50,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        genre = result.get("choices", [{}])[0].get("message", {}).get("content", "Unknown").strip()
        
        # Stocker le résultat dans le cache avant de le retourner
        genre_cache[cache_key] = genre
        return genre
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            log_action("Erreur 401 Unauthorized lors de l'appel à l'API xAI", "", f"Détails : {str(e)} - Vérifiez la clé API dans config.json")
        else:
            log_action("Erreur HTTP lors de l'appel à l'API xAI", "", f"Détails : {str(e)}")
        return "Unknown"
    except requests.exceptions.RequestException as e:
        log_action("Erreur réseau ou autre lors de l'appel à l'API xAI", "", f"Détails : {str(e)}")
        return "Unknown"

def main():
    """Scanne et traite tous les fichiers MP3 dans /downloads/, sans supprimer les fichiers restants sauf en cas de succès."""
    # Charger les règles de mapping des genres
    genre_patterns = load_tag_config()
    global genre_cache
    genre_cache = {}

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    path_config = config.get('paths', {})
    downloads_dir = path_config.get('downloads', '/downloads/')
    music_dir = path_config.get('music', '/music/downloads/')

    # Crée le dossier de base /music/downloads/ s’il n’existe pas
    ensure_directory(music_dir)

    # Liste tous les fichiers dans /downloads/
    processed_files = []
    for filename in os.listdir(downloads_dir):
        if filename.lower().endswith('.mp3'):
            file_path = os.path.join(downloads_dir, filename)
            process_mp3_file(file_path, music_dir, genre_patterns, config)
            processed_files.append(filename)

    # Supprime uniquement les fichiers qui ont été traités avec succès
    for filename in processed_files:
        file_path = os.path.join(downloads_dir, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                log_action("Fichier supprimé de /downloads/", file_path, "Après traitement réussi")
            except Exception as e:
                log_action("Erreur lors de la suppression", file_path, f"Exception : {str(e)}")

if __name__ == "__main__":
    main()