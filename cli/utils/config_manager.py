# utils.py
import os
import json
from typing import Dict, Any

class ConfigManager:
    """Classe pour gérer le chargement et l'accès aux fichiers de configuration JSON avec chemins en dur."""

    # Chemins en dur relatifs au répertoire du script appelant
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', 'etc', 'config.json'))
    TAG_CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', 'etc', 'tag_config.json'))

    def __init__(self):
        """Initialise le gestionnaire de configuration avec les chemins en dur."""
        self.config: Dict[str, Any] = {}
        self.tag_config: Dict[str, Any] = {}
        self._load_configs()

    def _load_json_file(self, file_path: str) -> Dict[str, Any]:
        """
        Charge un fichier JSON et gère les erreurs.

        Args:
            file_path (str): Chemin du fichier JSON.

        Returns:
            Dict[str, Any]: Contenu du fichier JSON.

        Raises:
            FileNotFoundError: Si le fichier est introuvable.
            ValueError: Si le fichier JSON est invalide.
            Exception: Pour d'autres erreurs inattendues.
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Le fichier de configuration {file_path} est introuvable")
        except json.JSONDecodeError:
            raise ValueError(f"Le fichier {file_path} n'est pas un JSON valide")
        except Exception as e:
            raise Exception(f"Erreur lors du chargement de {file_path} : {str(e)}")

    def _load_configs(self) -> None:
        """Charge les fichiers de configuration principaux et optionnels."""
        self.config = self._load_json_file(self.CONFIG_PATH)
        try:
            self.tag_config = self._load_json_file(self.TAG_CONFIG_PATH)
        except Exception as e:
            print(f"Erreur lors du chargement de tag_config.json : {str(e)}. Utilisation de configuration vide.")
            self.tag_config = {}

    def get_rabbitmq_config(self) -> Dict[str, Any]:
        """Retourne la configuration RabbitMQ avec des valeurs par défaut."""
        rabbitmq_config = self.config.get('rabbitmq', {})
        return {
            'host': rabbitmq_config.get('host', 'localhost'),
            'port': rabbitmq_config.get('port', 5672),
            'username': rabbitmq_config.get('username', 'gautard'),
            'password': rabbitmq_config.get('password', 'gautard'),
            'virtual_host': rabbitmq_config.get('virtual_host', '/')
        }

    def get_download_config(self) -> Dict[str, Any]:
        """Retourne la configuration de téléchargement avec des valeurs par défaut."""
        download_config = self.config.get('playlist_download', {})
        spotify_config = self.config.get('spotify', {})
        paths_config = self.config.get('paths', {})
        return {
            'provider': download_config.get('provider', 'spotdl'),
            'download_lyrics': download_config.get('download-lyrics', True),
            'download_format': download_config.get('download-format', 'mp3'),
            'download_quality': download_config.get('download-quality', 'very_high'),
            'credentials_location': download_config.get('credentials-location', ''),
            'song_archive': download_config.get('song-archive', '/archive.txt'),
            'skip_previously_downloaded': download_config.get('skip-previously-downloaded', True),
            'print_download_progress': download_config.get('print-download-progress', True),
            'print_progress_info': download_config.get('print-progress-info', True),
            'print_downloads': download_config.get('print-downloads', True),
            'retry_attempts': download_config.get('retry-attempts', 3),
            'download_real_time': download_config.get('download-real-time', True),
            'root_path': paths_config.get('downloads', ''),
            'client_id': spotify_config.get('client_id'),
            'client_secret': spotify_config.get('client_secret'),
            'output': download_config.get('output', ''),
            'username': spotify_config.get('username'),
            'password': spotify_config.get('password')
        }

    def get_paths_config(self) -> Dict[str, str]:
        """Retourne la configuration des chemins."""
        paths_config = self.config.get('paths', {})
        return {
            'downloads': paths_config.get('downloads', '/downloads/'),
            'music': paths_config.get('music', '/music/downloads/')
        }

    def get_tag_config(self) -> Dict[str, str]:
        """Retourne les règles de mapping des genres depuis tag_config.json."""
        return self.tag_config.get('genre_patterns', {})

    def get_grok_api_config(self) -> Dict[str, str]:
        """Retourne la configuration de l'API Grok."""
        grok_config = self.config.get('grok_api', {})
        return {
            'api_key': grok_config.get('api_key', ''),
            'endpoint': grok_config.get('endpoint', ''),
            'model': grok_config.get('model', '')
        }

    def get_tagging_config(self) -> Dict[str, Any]:
        """Retourne la configuration des tags."""
        return self.config.get('tag', {})

    def get_config(self, section: str, default: Any = None) -> Any:
        """
        Retourne une section spécifique de la configuration.

        Args:
            section (str): Nom de la section (ex: 'rabbitmq', 'spotify').
            default (Any): Valeur par défaut si la section n'existe pas.

        Returns:
            Any: Contenu de la section ou valeur par défaut.
        """
        return self.config.get(section, default)

    def reload(self) -> None:
        """Recharge les configurations depuis les fichiers."""
        self._load_configs()