<?php
// Définir le type de contenu comme JSON
header('Content-Type: application/json');

// Vérifier si des URLs sont fournies
if (!isset($_POST['urls'])) {
    echo json_encode(['error' => 'Aucune URL fournie']);
    exit;
}

// Découper les URLs en un tableau
$urls = explode("\n", trim($_POST['urls']));
$sync = isset($_POST['sync']) && $_POST['sync'] == 1;

// Charger les identifiants Spotify depuis le fichier de configuration
$config_path = '/home/gautard/spotdl-config/spotify_config.json';
if (!file_exists($config_path)) {
    echo json_encode(['error' => 'Fichier de configuration Spotify manquant']);
    exit;
}
$config = json_decode(file_get_contents($config_path), true);
if (!$config || !isset($config['client_id']) || !isset($config['client_secret'])) {
    echo json_encode(['error' => 'Identifiants Spotify invalides dans le fichier de configuration']);
    exit;
}
$client_id = $config['client_id'];
$client_secret = $config['client_secret'];

// Charger l'autoloader de Composer depuis src/vendor/
require __DIR__ . '/vendor/autoload.php';

// Importer les classes nécessaires
use Model\Amqp\Handler;

/** @var Handler $handler */
$handler = new Handler();

try {
    // Envoyer chaque URL à la file spotdl_queue via Handler
    $queue = 'spotdl_queue';
    foreach ($urls as $url) {
        $url = trim($url);
        if (!empty($url)) {
            $messageData = [
                'url' => $url,
                'sync' => $sync,
                'client_id' => $client_id,
                'client_secret' => $client_secret
            ];
            $handler->sendMessage($queue, $messageData);

            // Journaliser l'ajout dans history.txt avec gestion des permissions
            $log_file = '../log/history.txt';
            $log_dir = dirname($log_file);
            if (!is_dir($log_dir) && !mkdir($log_dir, 0755, true)) {
                throw new Exception("Impossible de créer le dossier $log_dir");
            }
            if (is_writable($log_dir)) {
                file_put_contents($log_file, date('Y-m-d H:i:s') . " - Ajouté à la file : $url\n", FILE_APPEND | LOCK_EX);
            } else {
                throw new Exception("Pas de permissions d'écriture dans $log_dir");
            }
        }
    }

    echo json_encode([
        'success' => true,
        'message' => 'URL(s) ajoutée(s) à la file avec succès'
    ]);
} catch (Exception $e) {
    echo json_encode([
        'success' => false,
        'error' => 'Erreur lors de l’ajout à la file : ' . $e->getMessage()
    ]);
}