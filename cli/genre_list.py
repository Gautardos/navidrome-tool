import os
import mutagen.easyid3
from mutagen.easyid3 import EasyID3
import mutagen.id3
from mutagen.id3 import ID3
import json
import argparse
import re

# Répertoires
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'etc', 'tag_config.json'))

def sanitize_name(name):
    """Remplace les '/' par des ',' dans un nom, gère les encodages, et normalise les espaces."""
    if not name:
        return ""
    try:
        name = str(name, 'utf-8', errors='replace').strip()
    except (TypeError, UnicodeDecodeError):
        name = str(name).strip()
    name = " ".join(name.split())  # Normalise les espaces multiples
    return name.replace("/", ",") if name else ""

def load_mapping_config():
    """Charge les règles de mapping des genres depuis config.json."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return config.get('genre_patterns', {})
    except FileNotFoundError:
        print(f"Erreur : Le fichier de configuration {CONFIG_PATH} est introuvable. Mapping désactivé.")
        return {}
    except json.JSONDecodeError:
        print(f"Erreur : Le fichier {CONFIG_PATH} n'est pas un JSON valide. Mapping désactivé.")
        return {}
    except Exception as e:
        print(f"Erreur lors du chargement de {CONFIG_PATH} : {str(e)}. Mapping désactivé.")
        return {}

def map_genre(genre, mapping_patterns):
    """Mappe un genre vers une valeur standardisée en utilisant les patterns configurables, en convertissant en minuscules."""
    if not genre:
        return "Unknown"
    genre_lower = genre.lower().strip().replace("\u200b", "").replace("\u00a0", "")  # Nettoyage des caractères invisibles
    for pattern, mapped_genre in mapping_patterns.items():
        try:
            if re.search(pattern, genre_lower):
                return mapped_genre
        except re.error:
            continue
    return genre  # Retourne le genre original si aucun mapping n'est trouvé

def extract_genres_from_mp3(directory, recursive=False):
    """Extrait les genres uniques des fichiers MP3 dans le répertoire donné, avec option récursive."""
    genres = set()
    if recursive:
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(('.mp3', '.MP3')):
                    file_path = os.path.join(root, filename)
                    try:
                        # Essayer d'abord avec EasyID3
                        try:
                            audio = EasyID3(file_path)
                            if "genre" in audio:
                                raw_genre = audio["genre"][0].strip()
                                sanitized_genre = sanitize_name(raw_genre)
                                if sanitized_genre:
                                    genres.add(sanitized_genre)
                        except mutagen.easyid3.EasyID3KeyError:
                            pass

                        # Essayer ensuite avec ID3
                        try:
                            audio_id3 = ID3(file_path)
                            if 'TCON' in audio_id3:
                                raw_genre = audio_id3['TCON'].text[0].strip()
                                sanitized_genre = sanitize_name(raw_genre)
                                if sanitized_genre:
                                    genres.add(sanitized_genre)
                        except mutagen.id3.ID3NoHeaderError:
                            pass
                    except Exception as e:
                        print(f"Erreur pour {file_path} : {str(e)}")
                        continue
    else:
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.mp3', '.MP3')):
                file_path = os.path.join(directory, filename)
                try:
                    # Essayer d'abord avec EasyID3
                    try:
                        audio = EasyID3(file_path)
                        if "genre" in audio:
                            raw_genre = audio["genre"][0].strip()
                            sanitized_genre = sanitize_name(raw_genre)
                            if sanitized_genre:
                                genres.add(sanitized_genre)
                    except mutagen.easyid3.EasyID3KeyError:
                        pass

                    # Essayer ensuite avec ID3
                    try:
                        audio_id3 = ID3(file_path)
                        if 'TCON' in audio_id3:
                            raw_genre = audio_id3['TCON'].text[0].strip()
                            sanitized_genre = sanitize_name(raw_genre)
                            if sanitized_genre:
                                genres.add(sanitized_genre)
                    except mutagen.id3.ID3NoHeaderError:
                        pass
                except Exception as e:
                    print(f"Erreur pour {file_path} : {str(e)}")
                    continue
    return sorted(list(genres))

def print_genres_to_screen(genres, apply_mapping=False):
    """Affiche les genres au format JSON { "genre1": "", "genre2": "", ... } à l’écran, avec option de mapping."""
    mapping_patterns = load_mapping_config() if apply_mapping else {}
    if mapping_patterns:
        mapped_genres = {map_genre(genre, mapping_patterns): "" for genre in genres if genre != "Unknown"}
        if not mapped_genres:
            mapped_genres = {"Unknown": ""}
    else:
        mapped_genres = {genre: "" for genre in genres if genre != "Unknown"}
        if not mapped_genres:
            mapped_genres = {"Unknown": ""}
    print(json.dumps(mapped_genres, indent=2, ensure_ascii=False))

def main():
    # Parser des arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Liste les genres uniques des fichiers MP3 dans un dossier spécifié.")
    parser.add_argument("directory", help="Dossier à scanner pour les fichiers MP3.")
    parser.add_argument("--recursive", action="store_true", help="Activer un scan récursif des sous-dossiers.")
    parser.add_argument("--map", action="store_true", help="Appliquer le mapping des genres depuis config.json.")
    args = parser.parse_args()

    directory = os.path.abspath(args.directory)

    # Vérifier que le répertoire existe
    if not os.path.exists(directory):
        print(f"Erreur : Le répertoire {directory} n'existe pas.")
        exit(1)
    
    # Vérifier les permissions sur le répertoire
    if not os.access(directory, os.R_OK):
        print(f"Erreur : Pas de permissions pour lire {directory}.")
        exit(1)
    
    # Extraire les genres uniques
    genres = extract_genres_from_mp3(directory, args.recursive)
    
    if not genres:
        print("Aucun genre trouvé.")
    
    # Afficher les genres à l’écran au format JSON, avec option mapping
    print_genres_to_screen(genres, args.map)

if __name__ == "__main__":
    main()