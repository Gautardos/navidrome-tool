import os
import mutagen.easyid3
from mutagen.easyid3 import EasyID3
import mutagen.id3
from mutagen.id3 import ID3, TCON
import json
import argparse
import re
import sys
import colorama

# Initialisation de colorama pour les couleurs dans le terminal
colorama.init()

# Répertoires
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'etc', 'tag_config.json'))

def sanitize_name(name):
    """Gère les encodages et normalise les espaces, sans modifier les '/'."""
    if not name:
        return ""
    try:
        name = str(name, 'utf-8', errors='replace').strip()
    except (TypeError, UnicodeDecodeError):
        name = str(name).strip()
    name = " ".join(name.split())  # Normalise les espaces multiples
    return name  # Ne remplace pas "/" par ","

def load_mapping_config():
    """Charge les règles de mapping des genres depuis tag_config.json, avec débogage minimal sur stderr."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        patterns = config.get('genre_patterns', {})
        if not patterns:
            print(f"Avertissement : Aucun pattern de mapping trouvé dans {CONFIG_PATH}. Mapping désactivé.", file=sys.stderr)
        return patterns
    except FileNotFoundError:
        print(f"Erreur : Le fichier de configuration {CONFIG_PATH} est introuvable. Mapping désactivé.", file=sys.stderr)
        return {}
    except json.JSONDecodeError:
        print(f"Erreur : Le fichier {CONFIG_PATH} n'est pas un JSON valide. Mapping désactivé.", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Erreur lors du chargement de {CONFIG_PATH} : {str(e)}. Mapping désactivé.", file=sys.stderr)
        return {}

def map_genre(genre, mapping_patterns):
    """Mappe un genre vers une valeur standardisée en utilisant les patterns configurables, en convertissant en minuscules, avec débogage minimal sur stderr."""
    if not genre:
        print(f"Avertissement : Genre vide détecté, retour 'Unknown'.", file=sys.stderr)
        return "Unknown"
    genre_lower = genre.lower().strip().replace("\u200b", "").replace("\u00a0", "")  # Nettoyage des caractères invisibles
    if genre_lower == "west coast hip hop":
        print(f"Débogage - Tentative de mapping pour 'West Coast Hip Hop' ({genre_lower})", file=sys.stderr)
    for pattern, mapped_genre in mapping_patterns.items():
        try:
            if re.search(pattern, genre_lower):
                if genre_lower == "west coast hip hop":
                    print(f"Débogage - Match trouvé avec pattern {pattern!r} pour 'West Coast Hip Hop', résultat : {mapped_genre!r}", file=sys.stderr)
                return mapped_genre
        except re.error:
            print(f"Avertissement : Pattern regex invalide {pattern!r} ignoré.", file=sys.stderr)
            continue
    if genre_lower == "west coast hip hop":
        print(f"Débogage - Aucun match trouvé pour 'West Coast Hip Hop' ({genre_lower})", file=sys.stderr)
    return genre  # Retourne le genre original si aucun mapping n'est trouvé

def extract_genres_from_mp3(directory, recursive=False):
    """Extrait les genres uniques (ou inventaire) des fichiers MP3 dans le répertoire donné, avec option récursive, en évitant les doublons."""
    if recursive:
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(('.mp3', '.MP3')):
                    file_path = os.path.join(root, filename)
                    try:
                        genre_found = False
                        # Essayer d'abord avec EasyID3
                        try:
                            audio = EasyID3(file_path)
                            if "genre" in audio:
                                raw_genre = audio["genre"][0].strip()
                                sanitized_genre = sanitize_name(raw_genre)
                                if sanitized_genre:
                                    genre_found = True
                                    yield sanitized_genre, os.path.basename(file_path)
                        except mutagen.easyid3.EasyID3KeyError:
                            pass

                        # Essayer ensuite avec ID3 seulement si aucun genre n’a été trouvé avec EasyID3
                        if not genre_found:
                            try:
                                audio_id3 = ID3(file_path)
                                if 'TCON' in audio_id3:
                                    raw_genre = audio_id3['TCON'].text[0].strip()
                                    sanitized_genre = sanitize_name(raw_genre)
                                    if sanitized_genre:
                                        yield sanitized_genre, os.path.basename(file_path)
                            except mutagen.id3.ID3NoHeaderError:
                                pass
                    except Exception as e:
                        print(f"Erreur pour {file_path} : {str(e)}", file=sys.stderr)
                        continue
    else:
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.mp3', '.MP3')):
                file_path = os.path.join(directory, filename)
                try:
                    genre_found = False
                    # Essayer d'abord avec EasyID3
                    try:
                        audio = EasyID3(file_path)
                        if "genre" in audio:
                            raw_genre = audio["genre"][0].strip()
                            sanitized_genre = sanitize_name(raw_genre)
                            if sanitized_genre:
                                genre_found = True
                                yield sanitized_genre, os.path.basename(file_path)
                    except mutagen.easyid3.EasyID3KeyError:
                        pass

                    # Essayer ensuite avec ID3 seulement si aucun genre n’a été trouvé avec EasyID3
                    if not genre_found:
                        try:
                            audio_id3 = ID3(file_path)
                            if 'TCON' in audio_id3:
                                raw_genre = audio_id3['TCON'].text[0].strip()
                                sanitized_genre = sanitize_name(raw_genre)
                                if sanitized_genre:
                                    yield sanitized_genre, os.path.basename(file_path)
                        except mutagen.id3.ID3NoHeaderError:
                            pass
                except Exception as e:
                    print(f"Erreur pour {file_path} : {str(e)}", file=sys.stderr)
                    continue

def build_inventory(genres_with_titles, recursive=False):
    """Construit un inventaire à partir des genres et titres générés par extract_genres_from_mp3."""
    genre_inventory = {}  # Dictionnaire {genre: set(titres)} pour éviter les doublons
    for genre, title in genres_with_titles:
        if genre in genre_inventory:
            genre_inventory[genre].add(title)
        else:
            genre_inventory[genre] = {title}
    # Convertir les sets en listes triées et retourner une liste triée de tuples (genre, titres)
    return sorted([(genre, sorted(list(titres))) for genre, titres in genre_inventory.items()], key=lambda x: x[0])

def update_genre_in_file(file_path, old_genre, new_genre):
    """Met à jour le tag 'genre' (TCON) d'un fichier MP3."""
    try:
        # Essayer d'abord avec EasyID3 pour ID3v2
        try:
            audio = EasyID3(file_path)
            if "genre" in audio and audio["genre"][0].strip() == old_genre:
                audio["genre"] = new_genre
                audio.save()
                print(f"Mise à jour : {os.path.basename(file_path)} - Ancien genre : {old_genre}, Nouveau genre : {new_genre}")
        except mutagen.easyid3.EasyID3KeyError:
            pass

        # Essayer ensuite avec ID3 pour ID3v1/ID3v2 si nécessaire
        try:
            audio_id3 = ID3(file_path)
            if 'TCON' in audio_id3 and audio_id3['TCON'].text[0].strip() == old_genre:
                audio_id3['TCON'] = TCON(encoding=3, text=[new_genre])  # UTF-8 encoding
                audio_id3.save()
                print(f"Mise à jour : {os.path.basename(file_path)} - Ancien genre : {old_genre}, Nouveau genre : {new_genre}")
        except mutagen.id3.ID3NoHeaderError:
            pass
    except Exception as e:
        print(f"Erreur lors de la mise à jour de {file_path} : {str(e)}", file=sys.stderr)

def print_inventory_to_screen(inventory, apply_mapping=False, args=None):
    """Affiche l’inventaire des genres et leurs titres associés, avec option de mapping, en jaune et avec séparateurs, en regroupant par genre mappé, et colore les chansons modifiées en rouge avec l’ancien genre."""
    mapping_patterns = load_mapping_config() if apply_mapping else {}
    if inventory:
        # Regrouper les titres par genre mappé et suivre les changements
        mapped_inventory = {}  # Dictionnaire temporaire {genre_mappé: set(titres)}
        genre_changes = {}  # Suivre les changements de genre pour le prompt : {file_path: (old_genre, new_genre)}
        title_changes = {}  # Suivre les titres modifiés : {title: old_genre}
        for genre, titles in inventory:
            mapped_genre = map_genre(genre, mapping_patterns) if apply_mapping else genre
            for title in titles:
                file_path = None
                # Rechercher le fichier correspondant au titre dans le répertoire
                for root, _, files in os.walk(args.directory if not args.recursive else args.directory):
                    for f in files:
                        if os.path.basename(f) == title and f.lower().endswith(('.mp3', '.MP3')):
                            file_path = os.path.join(root, f)
                            break
                    if file_path:
                        break
                if file_path:
                    try:
                        # Vérifier le genre actuel dans le fichier
                        current_genre = None
                        try:
                            audio = EasyID3(file_path)
                            if "genre" in audio:
                                current_genre = audio["genre"][0].strip()
                        except mutagen.easyid3.EasyID3KeyError:
                            pass
                        if not current_genre:
                            try:
                                audio_id3 = ID3(file_path)
                                if 'TCON' in audio_id3:
                                    current_genre = audio_id3['TCON'].text[0].strip()
                            except mutagen.id3.ID3NoHeaderError:
                                pass
                        if current_genre and current_genre != mapped_genre:
                            genre_changes[file_path] = (current_genre, mapped_genre)
                            title_changes[title] = current_genre
                    except Exception as e:
                        print(f"Erreur lors de la vérification de {file_path} : {str(e)}", file=sys.stderr)
                        continue
                if mapped_genre in mapped_inventory:
                    mapped_inventory[mapped_genre].add(title)
                else:
                    mapped_inventory[mapped_genre] = {title}
        
        # Convertir en liste triée de tuples (genre, titres triés) pour une sortie claire
        sorted_inventory = sorted([(genre, sorted(list(titles))) for genre, titles in mapped_inventory.items()], key=lambda x: x[0])
        
        for i, (genre, titles) in enumerate(sorted_inventory, 1):
            # Utiliser colorama pour colorer le genre en jaune
            colored_genre = f"{colorama.Fore.YELLOW}{genre}{colorama.Style.RESET_ALL}"
            print(f"{colored_genre}:")
            for title in titles:
                if title in title_changes and apply_mapping:  # Si le titre a changé de genre et que --map est utilisé
                    # Colorer en rouge et ajouter l’ancien genre
                    colored_title = f"{colorama.Fore.RED}{title} (Ancien genre : {title_changes[title]}){colorama.Style.RESET_ALL}"
                    print(f"  - {colored_title}")
                else:
                    print(f"  - {title}")
            # Séparateur visuel entre les genres (ligne de tirets)
            if i < len(sorted_inventory):
                print("-" * 50)

        # Gérer le prompt si --map est présent, sauf si --dry ou pas de changement de genre
        if apply_mapping and not args.dry and genre_changes:  # Si au moins un genre a été modifié
            # Coloration du prompt en vert
            prompt = f"{colorama.Fore.GREEN}Voulez-vous appliquer le mapping de genre aux morceaux sélectionnés ? (oui/non) {colorama.Style.RESET_ALL}"
            response = input(prompt).lower().strip()
            if response == "oui":
                for file_path, (old_genre, new_genre) in genre_changes.items():
                    update_genre_in_file(file_path, old_genre, new_genre)
    else:
        print("Aucun genre ou titre trouvé.", file=sys.stderr)

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

def update_genre_in_file(file_path, old_genre, new_genre):
    """Met à jour le tag 'genre' (TCON) d'un fichier MP3."""
    try:
        # Essayer d'abord avec EasyID3 pour ID3v2
        try:
            audio = EasyID3(file_path)
            if "genre" in audio and audio["genre"][0].strip() == old_genre:
                audio["genre"] = new_genre
                audio.save()
                print(f"Mise à jour : {os.path.basename(file_path)} - Ancien genre : {old_genre}, Nouveau genre : {new_genre}")
        except mutagen.easyid3.EasyID3KeyError:
            pass

        # Essayer ensuite avec ID3 pour ID3v1/ID3v2 si nécessaire
        try:
            audio_id3 = ID3(file_path)
            if 'TCON' in audio_id3 and audio_id3['TCON'].text[0].strip() == old_genre:
                audio_id3['TCON'] = TCON(encoding=3, text=[new_genre])  # UTF-8 encoding
                audio_id3.save()
                print(f"Mise à jour : {os.path.basename(file_path)} - Ancien genre : {old_genre}, Nouveau genre : {new_genre}")
        except mutagen.id3.ID3NoHeaderError:
            pass
    except Exception as e:
        print(f"Erreur lors de la mise à jour de {file_path} : {str(e)}", file=sys.stderr)

def main():
    # Parser des arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Liste les genres uniques des fichiers MP3 dans un dossier spécifié.")
    parser.add_argument("directory", help="Dossier à scanner pour les fichiers MP3.")
    parser.add_argument("--recursive", action="store_true", help="Activer un scan récursif des sous-dossiers.")
    parser.add_argument("--map", action="store_true", help="Appliquer le mapping des genres depuis tag_config.json.")
    parser.add_argument("--inventory", action="store_true", help="Afficher un inventaire des genres et des titres associés au lieu du JSON.")
    parser.add_argument("--dry", action="store_true", help="Mode sec (ne pas appliquer de modifications, même avec --map).")
    args = parser.parse_args()

    directory = os.path.abspath(args.directory)

    # Vérifier que le répertoire existe
    if not os.path.exists(directory):
        print(f"Erreur : Le répertoire {directory} n'existe pas.", file=sys.stderr)
        exit(1)
    
    # Vérifier les permissions sur le répertoire
    if not os.access(directory, os.R_OK):
        print(f"Erreur : Pas de permissions pour lire {directory}.", file=sys.stderr)
        exit(1)
    
    # Extraire les genres uniques ou l’inventaire
    if args.inventory:
        inventory = build_inventory(extract_genres_from_mp3(directory, args.recursive), args.recursive)
        print_inventory_to_screen(inventory, args.map, args)
    else:
        genres = sorted({genre for genre, _ in extract_genres_from_mp3(directory, args.recursive)})
        if not genres:
            print("Aucun genre trouvé.", file=sys.stderr)
        print_genres_to_screen(genres, args.map)

if __name__ == "__main__":
    main()