import subprocess
import os
import json
import time
import pika

# Configuration
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "gautard"
RABBITMQ_PASS = "gautard"
QUEUE_NAME = "spotdl_queue"  # Queue pour les URLs

# Chemin du virtual environment et du fichier d’historique
VENV_PATH = "/home/gautard/spotdl-venv/venv/bin/activate"
STATUS_HISTORY_FILE = "/home/gautard/spotdl-web/log/status_history.txt"
COMMAND_HISTORY_FILE = "/home/gautard/spotdl-web/log/command_history.txt"

def ensure_directory(path):
    """Assure que le répertoire existe avec les permissions correctes."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    os.chown(directory, 1000, 33)  # UID de gautard (1000), GID de www-data (33)
    os.chmod(directory, 0o775)

def log_command(command, url):
    """Journalise la commande exécutée dans command_history.txt."""
    ensure_directory(COMMAND_HISTORY_FILE)
    with open(COMMAND_HISTORY_FILE, 'a') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] URL: {url} - Commande: {command}\n")
    os.chown(COMMAND_HISTORY_FILE, 1000, 33)  # UID de gautard (1000), GID de www-data (33)
    os.chmod(COMMAND_HISTORY_FILE, 0o664)

def log_status(url, message):
    """Journalise les statuts dans status_history.txt."""
    ensure_directory(STATUS_HISTORY_FILE)
    with open(STATUS_HISTORY_FILE, 'a') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {url} - {message}\n")
    os.chown(STATUS_HISTORY_FILE, 1000, 33)  # UID de gautard (1000), GID de www-data (33)
    os.chmod(STATUS_HISTORY_FILE, 0o664)

def callback(ch, method, properties, body):
    try:
        # Décoder le message JSON
        data = json.loads(body.decode())
        url = data.get("url")
        sync = data.get("sync", False)
        client_id = data.get("client_id", None)
        client_secret = data.get("client_secret", None)

        # Charger les identifiants depuis le fichier de configuration si non fournis dans le message
        if not client_id or not client_secret:
            config_path = "/home/gautard/spotdl-config/spotify_config.json"
            if not os.path.exists(config_path):
                raise ValueError("Fichier de configuration Spotify manquant")
            with open(config_path, 'r') as f:
                config = json.load(f)
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")
            if not client_id or not client_secret:
                raise ValueError("Identifiants Spotify invalides dans le fichier de configuration")

        print(f"Processing URL: {url}")
        log_status(url, "Début du téléchargement...")
        ensure_directory(STATUS_HISTORY_FILE)

        # Mesurer le temps de traitement pour détecter les blocages
        start_time = time.time()

        # Exécuter spotdl dans le virtual environment
        try:
            # Échapper les accolades dans client_id et client_secret pour éviter les conflits
            escaped_client_id = client_id.replace("{", "{{").replace("}", "}}")
            escaped_client_secret = client_secret.replace("{", "{{").replace("}", "}}")
            cmd = f"source {VENV_PATH} && spotdl '{url}' {'--sync' if sync else ''} --client-id '{escaped_client_id}' --client-secret '{escaped_client_secret}' --output /downloads/ --config 2>&1"
            # Journalise la commande avant l'exécution
            log_command(cmd, url)
            process = subprocess.Popen(['/bin/bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

            # Lire l'output ligne par ligne et persister dans l’historique
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

                # Lancer process_downloaded_files.py après un téléchargement réussi
                script_dir = os.path.dirname(os.path.abspath(__file__))
                process_cmd = f"source {VENV_PATH} && python3 {os.path.join(script_dir, 'tag_rename_move.py')}"

                process_result = subprocess.run(['/bin/bash', '-c', process_cmd], capture_output=True, text=True)
                if process_result.returncode == 0:
                    log_status(url, "Fichiers traités et déplacés avec succès")
                else:
                    log_status(url, f"Erreur lors du traitement des fichiers : {process_result.stderr}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                print(f"Error downloading {url} in {processing_time:.2f} seconds: {error}")
                log_status(url, f"Échec du téléchargement en {processing_time:.2f} secondes : {error.strip()}")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)  # Ne pas réenfiler en cas d'échec
        except Exception as e:
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"Error executing spotdl for {url} in {processing_time:.2f} seconds: {e}")
            log_status(url, f"Erreur d’exécution de spotdl en {processing_time:.2f} secondes : {str(e)}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)  # Ne pas réenfiler en cas d'erreur
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time  # Utilise start_time pour une mesure cohérente
        print(f"Error processing message for {url} in {processing_time:.2f} seconds: {e}")
        log_status(url, f"Erreur de traitement en {processing_time:.2f} secondes : {str(e)}")
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

def main():
    # Connexion à RabbitMQ pour les URLs, avec un délai pour attendre RabbitMQ et un heartbeat personnalisé
    max_attempts = 5
    delay = 10  # Augmente le délai à 10 secondes pour éviter des connexions trop rapides
    for attempt in range(max_attempts):
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            # Augmente le heartbeat à 6000 secondes (1 heure et 40 minutes)
            parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials, heartbeat=36000)
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

    # Configurer le consommateur pour un traitement strictement séquentiel
    channel.basic_qos(prefetch_count=1)  # Limiter à un message à la fois
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
