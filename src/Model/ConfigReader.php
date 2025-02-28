<?php

namespace Model;

class ConfigReader {
    private $config = [];
    protected $filePath = __DIR__ . '/../../etc/config.json';

    /**
     * Constructeur - Initialise le chemin du fichier de configuration
     * @param string $filePath Chemin vers le fichier config.json
     */
    public function __construct() {
        $this->loadConfig();
    }

    /**
     * Charge le fichier de configuration JSON
     * @throws \Exception Si le fichier n'existe pas ou est invalide
     */
    private function loadConfig(): void {
        if (!file_exists($this->filePath)) {
            throw new \Exception("Le fichier de configuration '{$this->filePath}' n'existe pas.");
        }

        $jsonContent = file_get_contents($this->filePath);
        $config = json_decode($jsonContent, true);

        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new \Exception("Erreur de décodage JSON : " . json_last_error_msg());
        }

        if (!is_array($config)) {
            throw new \Exception("Le contenu du fichier n'est pas un tableau valide.");
        }

        $this->config = $config;
    }

    /**
     * Récupère toutes les configurations
     * @return array Les configurations complètes
     */
    public function getAllConfig(): array {
        return $this->config;
    }

    /**
     * Récupère les configurations RabbitMQ
     * @return array Les configurations RabbitMQ
     * @throws \Exception Si la section RabbitMQ n'existe pas
     */
    public function getRabbitMQConfig(): array {
        if (!isset($this->config['rabbitmq'])) {
            throw new \Exception("La section 'rabbitmq' n'existe pas dans la configuration.");
        }
        return $this->config['rabbitmq'];
    }

    /**
     * Récupère les configurations d'authentification utilisateur
     * @return array Les configurations user_auth
     * @throws \Exception Si la section user_auth n'existe pas
     */
    public function getUserAuthConfig(): array {
        if (!isset($this->config['user_auth'])) {
            throw new \Exception("La section 'user_auth' n'existe pas dans la configuration.");
        }
        return $this->config['user_auth'];
    }

    /**
     * Récupère les configurations de l'API Grok
     * @return array Les configurations grok_api
     * @throws \Exception Si la section grok_api n'existe pas
     */
    public function getGrokAPIConfig(): array {
        if (!isset($this->config['grok_api'])) {
            throw new \Exception("La section 'grok_api' n'existe pas dans la configuration.");
        }
        return $this->config['grok_api'];
    }

    /**
     * Récupère les configurations de Spotify
     * @return array Les configurations spotify
     * @throws \Exception Si la section spotify n'existe pas
     */
    public function getSpotifyConfig(): array {
        if (!isset($this->config['spotify'])) {
            throw new \Exception("La section 'spotify' n'existe pas dans la configuration.");
        }
        return $this->config['spotify'];
    }

    /**
     * Récupère une valeur spécifique de la configuration
     * @param string $section Section de la configuration (rabbitmq, user_auth, grok_api)
     * @param string $key Clé à récupérer dans la section
     * @return mixed La valeur demandée
     * @throws \Exception Si la section ou la clé n'existe pas
     */
    public function getValue(string $section, string $key) {
        if (!isset($this->config[$section])) {
            throw new \Exception("La section '{$section}' n'existe pas dans la configuration.");
        }
        if (!isset($this->config[$section][$key])) {
            throw new \Exception("La clé '{$key}' n'existe pas dans la section '{$section}'.");
        }
        return $this->config[$section][$key];
    }
}