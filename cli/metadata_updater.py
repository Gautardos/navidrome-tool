#!/usr/bin/env python3

import sqlite3
import os
import argparse
import json
import subprocess
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
import colorama
from colorama import Fore, Style
from tabulate import tabulate

colorama.init()

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'db', 'database.db'))
POPULATE_DB_SCRIPT = os.path.join(SCRIPT_DIR, 'populate_db.py')

def parse_criteria(criteria_str):
    """Parse les critères de recherche en une liste de conditions SQL avec opérateurs."""
    conditions = []
    or_parts = criteria_str.split('/')
    for or_part in or_parts:
        and_parts = or_part.split(';')
        and_conditions = []
        for part in and_parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip().lower()
                value = value.strip()
                db_key_map = {'album artist': 'album_artist', 'artist': 'artist', 'album': 'album', 'genre': 'genre', 'year': 'year', 'title': 'title'}
                display_key = key
                key = db_key_map.get(display_key, display_key)
                if key in ['artist', 'album_artist', 'album', 'genre', 'year', 'title']:
                    and_conditions.append((key, value))
        if and_conditions:
            conditions.append(('AND', and_conditions))
    return conditions

def build_sql_query(conditions, case_sensitive=False):
    """Construit une requête SQL à partir des conditions avec AND et OR, avec option case-sensitive."""
    where_clauses = []
    params = []
    for op, and_conditions in conditions:
        and_clauses = []
        for key, value in and_conditions:
            # Si case_sensitive est True, on n'utilise pas LOWER()
            if case_sensitive:
                and_clauses.append(f"{key} = ?")
            else:
                and_clauses.append(f"LOWER({key}) = LOWER(?)")
            params.append(value)
        if and_clauses:
            where_clauses.append(f"({' AND '.join(and_clauses)})")
    where_clause = ' OR '.join(where_clauses) if where_clauses else "1=1"
    query = f"""
        SELECT path, title, artist, album_artist, album, genre, year
        FROM tracks
        WHERE {where_clause}
    """
    return query, params

def fetch_tracks(criteria_str, case_sensitive=False):
    """Récupère les morceaux correspondant aux critères depuis la base de données."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    conditions = parse_criteria(criteria_str)
    query, params = build_sql_query(conditions, case_sensitive)
    cursor.execute(query, params)
    tracks = cursor.fetchall()
    conn.close()
    return [{'path': row[0], 'title': row[1], 'artist': row[2], 'album_artist': row[3], 
             'album': row[4], 'genre': row[5], 'year': row[6]} for row in tracks]

def display_tracks(tracks, as_json=False, updates=None):
    """Affiche les morceaux sous forme de tableau ou JSON, avec mises à jour si fournies, et un récapitulatif."""
    headers = ['Path', 'Title', 'Artist', 'Album Artist', 'Album', 'Genre', 'Year']
    table_data = []
    
    for t in tracks:
        row = [t['path'], t['title'], t['artist'], t['album_artist'], t['album'], t['genre'], t['year']]
        if updates:
            for metadata_key, new_value in updates.items():
                display_key = metadata_key.replace('albumartist', 'album artist')
                idx = headers.index(display_key.replace('_', ' ').title())
                row[idx] = f"{Fore.GREEN}{new_value}{Style.RESET_ALL}"
        table_data.append(row)
    
    if as_json:
        result = [dict(zip(headers, [t['path'], t['title'], t['artist'], t['album_artist'], t['album'], t['genre'], t['year']])) for t in tracks]
        if updates:
            for r in result:
                for k, v in updates.items():
                    display_k = k.replace('albumartist', 'album artist')
                    r[display_k.replace('_', ' ').title()] = v
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        # Récapitulatif du nombre de morceaux
        num_tracks = len(tracks)
        print(f"\n{Fore.YELLOW}Récapitulatif : {num_tracks} morceau(s) vont être modifié(s).{Style.RESET_ALL}")

def prompt_metadata_choice(used_options):
    """Affiche un prompt pour choisir la métadonnée à modifier, excluant les déjà utilisées."""
    options = ['artist', 'albumartist', 'album', 'genre', 'year']
    available_options = [opt for opt in options if opt not in used_options]
    if not available_options:
        print("Toutes les métadonnées disponibles ont été modifiées.")
        return None
    print("\nQuelle métadonnée souhaitez-vous modifier ?")
    for i, opt in enumerate(available_options, 1):
        print(f"{i}. {opt.replace('albumartist', 'album artist')}")
    while True:
        choice = input("Entrez le numéro de votre choix (ou 'q' pour quitter) : ").strip().lower()
        if choice == 'q':
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(available_options):
            return available_options[int(choice) - 1]
        print("Choix invalide. Veuillez réessayer.")

def prompt_new_value(metadata_key):
    """Demande la nouvelle valeur pour la métadonnée choisie."""
    display_key = metadata_key.replace('albumartist', 'album artist')
    return input(f"Entrez la nouvelle valeur pour '{display_key}' : ").strip()

def update_metadata(tracks, updates):
    """Applique les modifications aux fichiers audio."""
    for track in tracks:
        file_path = track['path']
        try:
            if file_path.lower().endswith('.mp3'):
                audio = EasyID3(file_path)
                for metadata_key, new_value in updates.items():
                    if metadata_key == 'year':
                        audio['date'] = new_value
                    else:
                        audio[metadata_key] = new_value
                audio.save()
            elif file_path.lower().endswith('.m4a'):
                audio = MP4(file_path)
                tag_map = {'artist': '\xa9ART', 'albumartist': 'aART', 'album': '\xa9alb', 'genre': '\xa9gen', 'year': '\xa9day'}
                for metadata_key, new_value in updates.items():
                    audio[tag_map[metadata_key]] = new_value
                audio.save()
            print(f"{Fore.GREEN}Métadonnées mises à jour pour {file_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Erreur lors de la mise à jour de {file_path} : {e}{Style.RESET_ALL}")

def reindex_directories(tracks):
    """Lance populate_db.py pour réindexer les dossiers modifiés."""
    directories = {os.path.dirname(track['path']) for track in tracks}
    successful_reindex = 0
    for directory in directories:
        cmd = ["python3", POPULATE_DB_SCRIPT, directory]
        print(f"Lancement de la réindexation pour {directory} : {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"{Fore.RED}Erreurs lors de la réindexation : {result.stderr}{Style.RESET_ALL}")
            successful_reindex += 1
        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}Échec de la réindexation pour {directory} : {e}{Style.RESET_ALL}")
            if e.stdout:
                print(f"Sortie standard : {e.stdout}")
            if e.stderr:
                print(f"Sortie d'erreur : {e.stderr}")
    print(f"{Fore.GREEN}Réindexation terminée pour {successful_reindex} dossier(s) sur {len(directories)}.{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description='Met à jour les métadonnées des fichiers audio basé sur des critères.')
    parser.add_argument('criteria', help="Critères de recherche (ex: 'artist=Dr Dre;album=2001' pour AND, 'artist=Dr Dre/album=Eminem' pour OR)")
    parser.add_argument('--json', action='store_true', help='Affiche les résultats au format JSON')
    parser.add_argument('--case-sensitive', action='store_true', help='Rend la recherche sensible à la casse')
    args = parser.parse_args()

    # Récupérer les morceaux
    tracks = fetch_tracks(args.criteria, case_sensitive=args.case_sensitive)
    if not tracks:
        print("Aucun morceau trouvé correspondant aux critères.")
        return

    # Afficher les morceaux initiaux
    display_tracks(tracks, args.json)
    if args.json:
        return  # Sortir si JSON demandé

    # Boucle pour collecter plusieurs modifications
    updates = {}
    used_options = set()
    while True:
        metadata_key = prompt_metadata_choice(used_options)
        if metadata_key is None:
            break
        new_value = prompt_new_value(metadata_key)
        updates[metadata_key.replace('album artist', 'albumartist')] = new_value
        used_options.add(metadata_key)
        print("\nAperçu actuel des modifications :")
        display_tracks(tracks, updates=updates)
        print(f"\n{Fore.GREEN}Voulez-vous modifier une autre métadonnée ? (Oui/Non) : {Style.RESET_ALL}", end='')
        continue_choice = input().lower().strip()
        if continue_choice not in ['oui', 'o', 'yes', 'y']:
            print(f"Débogage : Réponse capturée = '{continue_choice}' (sortie de la boucle)")
            break
        print(f"Débogage : Réponse capturée = '{continue_choice}' (continuation)")

    if not updates:
        print("Aucune modification spécifiée.")
        return

    # Afficher l'aperçu final et le récapitulatif
    print("\nAperçu final des modifications proposées :")
    display_tracks(tracks, updates=updates)

    # Demander confirmation finale
    print(f"\n{Fore.GREEN}Appliquer toutes les modifications ? (Oui/Non) : {Style.RESET_ALL}", end='')
    confirmation = input().lower().strip()
    if confirmation not in ['oui', 'o', 'yes', 'y']:
        print("Modifications annulées.")
        return

    # Appliquer toutes les modifications
    update_metadata(tracks, updates)
    print(f"{Fore.GREEN}Modifications appliquées avec succès !{Style.RESET_ALL}")

    # Demander réindexation
    print(f"\n{Fore.GREEN}Souhaitez-vous réindexer les dossiers modifiés ? (Oui/Non) : {Style.RESET_ALL}", end='')
    reindex = input().lower().strip()
    if reindex in ['oui', 'o', 'yes', 'y']:
        reindex_directories(tracks)

if __name__ == "__main__":
    main()