import subprocess
import os
import json
import time
import pika
from utils.config_manager import ConfigManager

# Chemin du virtual environment et chemins relatifs des fichiers d’historique
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', 'spotdl-venv/venv/bin/activate'))
STATUS_HISTORY_FILE = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'log', 'status_history.txt'))
COMMAND_HISTORY_FILE = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'log', 'command_history.txt'))
QUEUE_NAME = "spotdl_queue"

# Initialisation du ConfigManager
config_manager = ConfigManager()

def ensure_directory(path):
    """Assure que le répertoire existe avec les permissions correctes."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def log_command(command, url):
    """Journalise la commande exécutée dans command_history.txt."""
    ensure_directory(COMMAND_HISTORY_FILE)
    with open(COMMAND_HISTORY_FILE, 'a') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] URL: {url} - Commande: {command}\n")

def log_status(url, message):
    """Journalise les statuts dans status_history.txt."""
    ensure_directory(STATUS_HISTORY_FILE)
    with open(STATUS_HISTORY_FILE, 'a') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {url} - {message}\n")

def callback(ch, method, properties, body):
    start_time = time.time()
    try:
        data = json.loads(body.decode())
        url = data.get("url")
        sync = data.get("sync", False)
        client_id = data.get("client_id", None)
        client_secret = data.get("client_secret", None)

        # Charger la configuration de téléchargement
        download_config = config_manager.get_download_config()
        if not client_id or not client_secret:
            client_id = download_config['client_id']
            client_secret = download_config['client_secret']
        if not client_id or not client_secret:
            raise ValueError("Identifiants Spotify invalides dans le fichier de configuration")

        print(f"Processing URL: {url} with provider: {download_config['provider']}")
        log_status(url, "Début du téléchargement...")
        ensure_directory(STATUS_HISTORY_FILE)

        # Construire la commande en fonction du provider
        escaped_client_id = client_id.replace("{", "{{").replace("}", "}}")
        escaped_client_secret = client_secret.replace("{", "{{").replace("}", "}}")
        cmd = ""

        if download_config['provider'].lower() == 'spotdl':
            cmd = (
                f"source {VENV_PATH} && spotdl '{url}' "
                f"{'--sync' if sync else ''} "
                f"--client-id '{escaped_client_id}' "
                f"--client-secret '{escaped_client_secret}' "
                f"--output {download_config['root_path']} "
                f"--config 2>&1"
            )
        elif download_config['provider'].lower() == 'zotify':
            cmd = (
                f"source {VENV_PATH} && zotify '{url}' "
                f"--output '{download_config['output']}' "
                f"--download-format '{download_config['download_format']}' "
                f"--root-path '{download_config['root_path']}' "
                f"--credentials-location '{download_config['credentials_location']}' "
                f"--song-archive '{download_config['song_archive']}' "
                f"--download-quality '{download_config['download_quality']}' "
                f"--skip-previously-downloaded '{download_config['skip_previously_downloaded']}' "
                f"--download-lyrics '{download_config['download_lyrics']}' "
                f"--print-download-progress '{download_config['print_download_progress']}' "
                f"--print-downloads '{download_config['print_downloads']}' "
                f"--print-progress-info '{download_config['print_progress_info']}' "
                f"--retry-attempts {download_config['retry_attempts']} 2>&1"
            )
        else:
            raise ValueError(f"Provider '{download_config['provider']}' non pris en charge")

        log_command(cmd, url)
        process = subprocess.Popen(['/bin/bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

        while True:
            output_line = process.stdout.readline()
            if output_line:
                log_status(url, output_line.strip())
            error_line = process.stderr.readline()
            if error_line:
                log_status(url, f"ERREUR: {error_line.strip()}")
            if process.poll() is not None:
                break

        return_code = process.returncode
        output, error = process.communicate()
        end_time = time.time()
        processing_time = end_time - start_time

        if return_code == 0:
            print(f"Download completed for {url} in {processing_time:.2f} seconds: {output}")
            log_status(url, f"Téléchargement terminé avec succès en {processing_time:.2f} secondes")
            tag_rename_path = os.path.join(SCRIPT_DIR, 'tag_rename_move.py')
            if not os.path.exists(tag_rename_path):
                print(f"Error: {tag_rename_path} not found")
                log_status(url, f"Erreur : {tag_rename_path} n'existe pas")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

            process_cmd = f"source {VENV_PATH} && python3 {tag_rename_path}"
            process_result = subprocess.run(['/bin/bash', '-c', process_cmd], capture_output=True, text=True)
            if process_result.returncode == 0:
                print(f"Processing completed for {url}")
                log_status(url, "Fichiers traités et déplacés avec succès")
            else:
                error_msg = process_result.stderr or "Erreur inconnue"
                print(f"Error processing files for {url}: {error_msg}")
                log_status(url, f"Erreur lors du traitement des fichiers : {error_msg}")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            print(f"Error downloading {url} in {processing_time:.2f} seconds: {error}")
            log_status(url, f"Échec du téléchargement en {processing_time:.2f} secondes : {error.strip()}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"Error processing message for {url} in {processing_time:.2f} seconds: {e}")
        log_status(url, f"Erreur de traitement en {processing_time:.2f} secondes : {str(e)}")
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

def main():
    # Charger les identifiants RabbitMQ
    rabbitmq_config = config_manager.get_rabbitmq_config()

    # Connexion à RabbitMQ
    max_attempts = 5
    delay = 10
    for attempt in range(max_attempts):
        try:
            credentials = pika.PlainCredentials(rabbitmq_config['username'], rabbitmq_config['password'])
            parameters = pika.ConnectionParameters(
                host=rabbitmq_config['host'],
                port=rabbitmq_config['port'],
                credentials=credentials,
                virtual_host=rabbitmq_config['virtual_host'],
                heartbeat=36000
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            break
        except pika.exceptions.AMQPConnectionError:
            print(f"Tentative {attempt + 1}/{max_attempts} : Attente de RabbitMQ... (délai de {delay} secondes)")
            time.sleep(delay)
    else:
        raise Exception("Impossible de se connecter à RabbitMQ après plusieurs tentatives")

    # Déclarer la file d'attente
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # Configurer le consommateur
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("Waiting for messages. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Consumer stopped by user")
    finally:
        connection.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Consumer error: {e}")