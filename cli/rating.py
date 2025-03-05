import os
import requests
import json
from tqdm import tqdm
import xml.etree.ElementTree as ET
import colorama
from colorama import Fore, Style
import argparse

# Initialisation de colorama pour les couleurs en terminal
colorama.init()

# Chemin du script pour trouver le dossier etc sibling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, '..', 'etc', 'config.json')

# Chargement des credentials depuis config.json
try:
    with open(CONFIG_PATH, 'r') as config_file:
        config = json.load(config_file)
    NAVIDROME_USERNAME = config['navidrome_user_auth']['username']
    NAVIDROME_PASSWORD = config['navidrome_user_auth']['password']
except FileNotFoundError:
    print(f"Erreur : Le fichier de configuration {CONFIG_PATH} n'a pas été trouvé.")
    exit(1)
except KeyError as e:
    print(f"Erreur : Clé manquante dans config.json : {e}")
    exit(1)
except json.JSONDecodeError as e:
    print(f"Erreur : Le fichier config.json est invalide : {e}")
    exit(1)

# Configuration
ITUNES_LIBRARY_PATH = "/music/Itunes folder/iTunes Music Library.xml"
NAVIDROME_URL = "http://localhost:4533/rest"  # URL de base pour les appels Subsonic

def get_navidrome_session(debug=False):
    """Obtient les paramètres d'authentification pour Navidrome avec un mot de passe encodé en hexadécimal."""
    # Encoder le mot de passe en hexadécimal et préfixer avec "enc:"
    hex_password = NAVIDROME_PASSWORD.encode('utf-8').hex()
    encoded_password = f"enc:{hex_password}"
    
    params = {
        'u': NAVIDROME_USERNAME,
        'p': encoded_password,
        'v': '1.16.0',  # Version de l'API Subsonic
        'c': 'itunes-navidrome-script',
        'f': 'json'  # Format de réponse
    }
    if debug:
        print(f"Paramètres de session Navidrome : {params}")
    return params

def get_artists(session_params, debug=False):
    """Récupère la liste des artistes (dossiers racine) via /rest/getIndexes en parcourant les index par lettre."""
    url = f"{NAVIDROME_URL}/getIndexes"
    try:
        response = requests.get(url, params=session_params, timeout=10)
        if debug:
            print(f"Statut HTTP pour getIndexes : {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if debug:
                print(f"Réponse JSON brute (partiel) : {json.dumps(data)[:500]}...")
            
            # Vérifie si 'subsonic-response' existe et est un dictionnaire
            subsonic_response = data.get('subsonic-response')
            if subsonic_response is None or not isinstance(subsonic_response, dict):
                if debug:
                    print(f"Erreur : 'subsonic-response' invalide dans la réponse JSON : {data}")
                return None
            
            if subsonic_response.get('status') == 'failed':
                if debug:
                    print(f"Échec de getIndexes : {subsonic_response}")
                return None
            
            # Récupère les index
            indexes = subsonic_response.get('indexes')
            if indexes is None:
                if debug:
                    print(f"Erreur : 'indexes' est None dans subsonic-response : {subsonic_response}")
                return None
            
            if isinstance(indexes, dict):
                index_list = indexes.get('index', [])
                if not isinstance(index_list, list):
                    if debug:
                        print(f"Erreur : 'index' dans 'indexes' n'est pas une liste, mais un {type(index_list)} : {index_list}")
                    return None
            elif isinstance(indexes, list):
                index_list = indexes
            else:
                if debug:
                    print(f"Erreur : 'indexes' n'est ni un dictionnaire ni une liste, mais un {type(indexes)} : {indexes}")
                return None
            
            artists = {}
            for index in index_list:
                if isinstance(index, dict):
                    artists_list = index.get('artist', [])
                    if not isinstance(artists_list, list):
                        if debug:
                            print(f"Erreur : 'artist' n'est pas une liste, mais un {type(artists_list)} : {artists_list}")
                        continue
                    
                    for artist in artists_list:
                        if isinstance(artist, dict):
                            artist_name = artist.get('name', '').replace('&', '&')  # Remplacement de & par &
                            artist_id = artist.get('id')
                            if artist_name and artist_id:
                                try:
                                    artists[artist_name.lower()] = artist_id
                                except Exception as e:
                                    if debug:
                                        print(f"Erreur lors de l'ajout de l'artiste {artist_name} : {e}")
                            else:
                                if debug:
                                    print(f"Artiste ignoré : name vide ou None ({artist_name}) ou id vide ou None ({artist_id})")
                        else:
                            if debug:
                                print(f"Erreur : artiste n'est pas un dictionnaire, mais un {type(artist)} : {artist}")
                else:
                    if debug:
                        print(f"Erreur : index n'est pas un dictionnaire, mais un {type(index)} : {index}")
            if not artists:
                if debug:
                    print(f"Aucun artiste valide trouvé dans la réponse JSON : {subsonic_response}")
            if debug:
                print(f"Nombre total d'artistes trouvés dans la bibliothèque : {len(artists)}")
            return artists
        else:
            if debug:
                print(f"Erreur API Navidrome pour getIndexes : Statut {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        if debug:
            print(f"Erreur de connexion pour getIndexes : {e}")
        return None
    except json.JSONDecodeError as e:
        if debug:
            print(f"Erreur de décodage JSON pour getIndexes : {e}")
        return None

def get_albums_for_artist(session_params, artist_id, debug=False):
    """Récupère les albums (dossiers de niveau 2) pour un artiste donné via /rest/getMusicDirectory."""
    url = f"{NAVIDROME_URL}/getMusicDirectory"
    params = {**session_params, 'id': artist_id}
    try:
        response = requests.get(url, params=params, timeout=10)
        if debug:
            print(f"Statut HTTP pour artiste ID {artist_id} : {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('subsonic-response', {}).get('status') == 'failed':
                if debug:
                    print(f"Échec pour artiste ID {artist_id} : {data}")
                return None
            
            albums = {}
            for child in data.get('subsonic-response', {}).get('directory', {}).get('child', []):
                if child.get('isDir') and child.get('title'):
                    album_name = child.get('title', '').replace('&', '&')  # Remplacement de & par &
                    albums[album_name.lower()] = child.get('id')
            if debug:
                print(f"Albums trouvés pour artiste ID {artist_id} : {len(albums)} albums")
            return albums
        else:
            if debug:
                print(f"Erreur API Navidrome pour artiste ID {artist_id} : Statut {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        if debug:
            print(f"Erreur de connexion pour artiste ID {artist_id} : {e}")
        return None
    except json.JSONDecodeError as e:
        if debug:
            print(f"Erreur de décodage JSON pour artiste ID {artist_id} : {e}")
        return None

def find_song_in_navidrome(song, artists, session_params, debug=False):
    """Recherche une chanson dans Navidrome et retourne son ID ainsi que son rating actuel, si existant."""
    artist_name = (song.get('album_artist') or song.get('artist') or '').replace('&', '&').lower()
    album_name = (song.get('album') or '').replace('&', '&').lower()
    song_title = (song.get('name') or '').replace('&', '&').lower()

    if not (artist_name and album_name and song_title):
        if debug:
            print(f"Informations manquantes pour la chanson : Artist='{artist_name}', Album='{album_name}', Title='{song_title}' - {song}")
        return None, None  # Retourne aussi le rating actuel (None si non trouvé)

    artist_id = artists.get(artist_name)
    if not artist_id:
        if debug:
            print(f"Artiste non trouvé : {artist_name}")
        return None, None

    albums = get_albums_for_artist(session_params, artist_id, debug)
    if not albums:
        if debug:
            print(f"Impossible de récupérer les albums pour l'artiste ID {artist_id}")
        return None, None

    album_id = albums.get(album_name)
    if not album_id:
        if debug:
            print(f"Album non trouvé : {album_name} pour l'artiste {artist_name}")
        return None, None

    url = f"{NAVIDROME_URL}/getMusicDirectory"
    params = {**session_params, 'id': album_id}
    try:
        response = requests.get(url, params=params, timeout=10)
        if debug:
            print(f"Statut HTTP pour album ID {album_id} : {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('subsonic-response', {}).get('status') == 'failed':
                if debug:
                    print(f"Échec pour album ID {album_id} : {data}")
                return None, None
            
            for child in data.get('subsonic-response', {}).get('directory', {}).get('child', []):
                if not child.get('isDir') and child.get('title', '').replace('&', '&').lower() == song_title:
                    if debug:
                        print(f"Chanson trouvée : {child.get('title')} avec ID {child.get('id')}")
                    current_rating = child.get('userRating')  # Récupère le rating actuel dans Navidrome (0-5)
                    return child.get('id'), current_rating
                elif debug:
                    print(f"Mismatch titre : iTunes='{song_title}', Navidrome='{child.get('title', '').replace('&', '&').lower()}'")
        else:
            if debug:
                print(f"Erreur API Navidrome pour album ID {album_id} : Statut {response.status_code} - {response.text}")
            return None, None
    except requests.RequestException as e:
        if debug:
            print(f"Erreur de connexion pour album ID {album_id} : {e}")
        return None, None
    except json.JSONDecodeError as e:
        if debug:
            print(f"Erreur de décodage JSON pour album ID {album_id} : {e}")
        return None, None

    if debug:
        print(f"Chanson non trouvée : {song_title} dans l'album {album_name} de l'artiste {artist_name}")
    return None, None

def update_song_rating(navidrome_song_id, rating, session_params, debug=False):
    """Met à jour le rating d'une chanson dans Navidrome."""
    navidrome_rating = int(rating / 20) if rating > 0 else 0  # Convertit le rating iTunes (0-100) en Navidrome (0-5)
    url = f"{NAVIDROME_URL}/setRating"
    params = {**session_params, 'id': navidrome_song_id, 'rating': navidrome_rating}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            if debug:
                print(f"Rating mis à jour pour ID {navidrome_song_id} : {navidrome_rating} étoiles")
        else:
            if debug:
                print(f"Échec mise à jour rating : {response.status_code} - {response.text}")
    except requests.RequestException as e:
        if debug:
            print(f"Erreur lors de la mise à jour : {e}")

def parse_itunes_xml(limit=None, artist_filter=None, album_filter=None, debug=False):
    """Parse le fichier XML iTunes manuellement pour extraire les chansons avec rating manuel, en suivant la structure dict > dict > dict, avec filtres optionnels."""
    if not os.path.exists(ITUNES_LIBRARY_PATH):
        if debug:
            print(f"Le fichier {ITUNES_LIBRARY_PATH} n'existe pas.")
        return []

    try:
        tree = ET.parse(ITUNES_LIBRARY_PATH)
        root = tree.getroot()
    except ET.ParseError as e:
        if debug:
            print(f"Erreur lors du parsing du fichier XML iTunes : {e}")
        return []
    except Exception as e:
        if debug:
            print(f"Erreur lors de la lecture du fichier iTunes : {e}")
        return []

    rated_songs = []
    total_songs = 0
    valid_songs = 0

    # Trouver le noeud racine <dict> et son unique enfant <dict> (la bibliothèque)
    library_dict = root.find('dict/dict')
    if library_dict is None:
        if debug:
            print("Erreur : Noeud bibliothèque <dict> non trouvé dans le XML.")
        return []

    # Itérer sur les noeuds <dict> de 3ème niveau (les chansons)
    for song_dict in library_dict.findall('dict'):
        total_songs += 1
        # Extraire les champs pertinents (Rating, Rating Computed, Name, Artist, Album Artist, Album)
        artist = None
        album_artist = None
        album = None
        name = None
        rating = None
        rating_computed = None

        # Parcourir les éléments enfants de chaque chanson pour associer chaque <key> à sa valeur suivante
        i = 0
        while i < len(song_dict):
            elem = song_dict[i]
            if elem.tag == 'key':
                key = elem.text
                # Trouver la valeur suivante (non <key>)
                j = i + 1
                while j < len(song_dict) and song_dict[j].tag == 'key':
                    j += 1
                if j < len(song_dict) and song_dict[j].tag in ['string', 'integer']:
                    value = song_dict[j].text
                    if value is None or (value.strip() == '' and song_dict[j].tag == 'string'):
                        value = None  # Traite les chaînes vides comme None
                    if debug and value is None:
                        print(f"Debug: Valeur manquante ou vide pour clé '{key}' dans la chanson {total_songs}")
                    if key == "Artist":
                        artist = value
                    elif key in ["Album Artist", "AlbumArtist"]:  # Gère les deux formes possibles
                        album_artist = value
                    elif key == "Album":
                        album = value
                    elif key == "Name":
                        name = value
                    elif key == "Rating":
                        rating = int(value) if value and value.isdigit() else None
                    elif key == "Rating Computed":
                        rating_computed = int(value) if value and value.isdigit() else None
            i += 1

        # Appliquer les filtres si spécifiés (insensible à la casse)
        if artist_filter and (artist or '').lower() != artist_filter.lower():
            continue
        if album_filter and (album or '').lower() != album_filter.lower():
            continue

        # Vérifier si c'est une chanson avec rating manuel, avec gestion des valeurs par défaut
        if (rating is not None and rating > 0 and (rating_computed is None or rating_computed == 0) and
            (artist or '').strip() and (album or '').strip() and (name or '').strip()):
            valid_songs += 1
            rated_songs.append({
                'artist': artist or 'Unknown',
                'album_artist': album_artist or '',
                'album': album or 'Unknown',
                'name': name or 'Untitled',
                'rating': rating
            })
        elif debug:
            print(f"Debug: Chanson {total_songs} ignorée - Artist={artist}, Album={album}, Name={name}, "
                  f"Rating={rating}, Rating Computed={rating_computed}")

    if debug:
        print(f"Nombre total de chansons analysées : {total_songs}")
        print(f"Nombre total de chansons avec rating manuel trouvées : {valid_songs}")

    if limit is not None:
        try:
            limit = int(limit)
            if limit < 0:
                raise ValueError("La limite doit être un nombre positif ou zéro.")
            if debug:
                print(f"Limite appliquée : traitement de {min(limit, len(rated_songs))} chansons sur {len(rated_songs)} trouvées.")
            rated_songs = rated_songs[:limit]
        except ValueError as e:
            if debug:
                print(f"Erreur dans la limite spécifiée : {e}")
            return []

    if debug:
        print(f"Nombre total de chansons avec rating manuel valides (après limite et filtres) : {len(rated_songs)}")
    return rated_songs

def match_songs_with_navidrome(rated_songs, artists, session_params, force_update=False, debug=False):
    """Fait correspondre les chansons iTunes avec leurs IDs dans Navidrome, vérifie les ratings existants, et retourne les résultats, avec une barre de progression."""
    matched_songs = []
    with tqdm(total=len(rated_songs), desc="Matching des chansons avec Navidrome", unit="chanson") as pbar:
        for song in rated_songs:
            navidrome_song_id, current_rating = find_song_in_navidrome(song, artists, session_params, debug)
            # Par défaut, ignore les chansons avec un rating existant sauf si --force-update est spécifié
            if navidrome_song_id is not None:
                if current_rating is not None and current_rating > 0 and not force_update:
                    matched_songs.append({
                        'song': song,
                        'navidrome_id': navidrome_song_id,
                        'found': False,  # Marqué comme non trouvé pour affichage sans couleur
                        'ignored': True  # Indicateur pour les chansons ignorées
                    })
                else:
                    matched_songs.append({
                        'song': song,
                        'navidrome_id': navidrome_song_id,
                        'found': True,
                        'ignored': False
                    })
            else:
                matched_songs.append({
                    'song': song,
                    'navidrome_id': None,
                    'found': False,
                    'ignored': False
                })
            pbar.update(1)
    if debug:
        print(f"Matching terminé : {sum(1 for song in matched_songs if song['found'])} chansons trouvées sur {len(matched_songs)}.")
    return matched_songs

def display_matched_songs(matched_songs, output_errors_only=False, debug=False):
    """Affiche les chansons avec coloration (vert pour trouvées, rouge pour non trouvées, pas de couleur pour ignorées)."""
    total_songs = len(matched_songs)
    found_songs = sum(1 for song in matched_songs if song['found'] and not song['ignored'])
    not_found_songs = sum(1 for song in matched_songs if not song['found'] and not song['ignored'])
    ignored_songs = sum(1 for song in matched_songs if song['ignored'])

    print("\nDétail des morceaux :")

    for song in matched_songs:
        if output_errors_only and (song['found'] or song['ignored']):
            continue  # N’affiche que les chansons non trouvées (rouges) si --output-errors-only est activé
        color = None
        if song['found'] and not song['ignored']:
            color = Fore.GREEN  # Chansons trouvées (vert)
        elif not song['found'] and not song['ignored']:
            color = Fore.RED  # Chansons non trouvées (rouge)
        # Chansons ignorées (pas de couleur)
        print(f"{color if color else ''}{song['song']['name']} | Artist : {song['song'].get('artist', 'Unknown')} | "
              f"Album : {song['song']['album']} | Rating : {song['song']['rating']}/100{Style.RESET_ALL if color else ''}")

    print("\nRécapitulatif des chansons à importer :")
    print(f"Total des morceaux sélectionnés : {total_songs}")
    print(f"Morceaux trouvés dans Navidrome : {found_songs} (en vert)")
    print(f"Morceaux non trouvés dans Navidrome : {not_found_songs} (en rouge)")
    print(f"Morceaux ignorés (rating existant) : {ignored_songs} (pas de couleur)")

def confirm_send_to_navidrome(debug=False):
    """Demande une confirmation avant l'envoi."""
    return input("Voulez-vous envoyer ces ratings à Navidrome ? (y/n) : ").lower().strip() == 'y'

def send_ratings_to_navidrome(matched_songs, session_params, debug=False):
    """Envoie les ratings des chansons trouvées à Navidrome, en ignorant celles avec rating existant sauf si --force-update est spécifié."""
    with tqdm(total=sum(1 for song in matched_songs if song['found'] and not song['ignored']), desc="Envoi des ratings") as pbar:
        for song in matched_songs:
            if song['found'] and not song['ignored']:
                try:
                    update_song_rating(song['navidrome_id'], song['song']['rating'], session_params, debug)
                except Exception as e:
                    if debug:
                        print(f"Erreur mise à jour {song['song']['name']} : {e}")
            pbar.update(1)
    if debug:
        print(f"Envoi terminé : {sum(1 for song in matched_songs if song['found'] and not song['ignored'])} ratings envoyés.")

def main():
    parser = argparse.ArgumentParser(description="Script pour synchroniser ratings iTunes vers Navidrome.")
    parser.add_argument('--limit', type=int, help="Nombre maximum d'éléments à traiter (0 pour aucun limite).")
    parser.add_argument('--debug', action='store_true', help="Activer le mode debug pour afficher les informations techniques.")
    parser.add_argument('--artist', type=str, help="Filtrer les chansons par artiste (insensible à la casse).")
    parser.add_argument('--album', type=str, help="Filtrer les chansons par album (insensible à la casse).")
    parser.add_argument('--force-update', action='store_true', help="Forcer la mise à jour des ratings même s'ils existent déjà dans Navidrome.")
    parser.add_argument('--output-errors-only', action='store_true', help="N'afficher que les chansons non trouvées (lignes rouges) dans le récapitulatif.")
    args = parser.parse_args()

    print("Étape 1 : Préparation de l’authentification Subsonic...")
    session_params = get_navidrome_session(debug=args.debug)
    print("Authentification Subsonic prête.")

    print("Étape 2 : Récupération de la liste des artistes...")
    artists = get_artists(session_params, debug=args.debug)
    if not artists:
        print("Impossible de récupérer la liste des artistes. Arrêt du script.")
        return

    print("Étape 3 : Extraction des ratings...")
    rated_songs = parse_itunes_xml(limit=args.limit, artist_filter=args.artist, album_filter=args.album, debug=args.debug)

    if not rated_songs:
        print("Aucune chanson avec rating trouvée.")
        return

    print("Étape 4 : Matching des chansons avec Navidrome...")
    matched_songs = match_songs_with_navidrome(rated_songs, artists, session_params, force_update=args.force_update, debug=args.debug)

    print("Étape 5 : Confirmation...")
    display_matched_songs(matched_songs, output_errors_only=args.output_errors_only, debug=args.debug)
    if confirm_send_to_navidrome(debug=args.debug):
        print("Envoi des ratings à Navidrome...")
        send_ratings_to_navidrome(matched_songs, session_params, debug=args.debug)
        print("Envoi terminé.")
    else:
        print("Envoi annulé.")

if __name__ == "__main__":
    main()