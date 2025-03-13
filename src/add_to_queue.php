<?php
require __DIR__ . '/vendor/autoload.php';

use Model\ConfigReader;
use Model\Amqp\Handler;
use Model\Logger;

$handler = new Handler();
$config = new ConfigReader();
$logger = new Logger(); // Initialiser le logger

// Définir le type de contenu comme JSON
header('Content-Type: application/json');

// Vérifier si des URLs sont fournies
if (!isset($_POST['urls'])) {
    $errorMessage = 'Aucune URL fournie';
    $logger->log('queue', 'error', 'add', $errorMessage);
    echo json_encode(['error' => $errorMessage]);
    exit;
}

// Découper les URLs en un tableau
$urls = explode("\n", trim($_POST['urls']));
$sync = isset($_POST['sync']) && $_POST['sync'] == 1;

// Charger les identifiants Spotify depuis le fichier de configuration
$spotifyConfig = $config->getSpotifyConfig();
if (!isset($spotifyConfig['client_id']) || !isset($spotifyConfig['client_secret'])) {
    $errorMessage = 'Identifiants Spotify invalides dans le fichier de configuration';
    $logger->log('queue', 'error', 'add', $errorMessage);
    echo json_encode(['error' => $errorMessage]);
    exit;
}
$client_id = $spotifyConfig['client_id'];
$client_secret = $spotifyConfig['client_secret'];

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

            // Journaliser l'ajout avec Logger
            $logger->log('queue', 'info', 'add', "Ajouté à la file : $url");
        }
    }

    echo json_encode([
        'success' => true,
        'message' => 'URL(s) ajoutée(s) à la file avec succès'
    ]);
} catch (Exception $e) {
    $errorMessage = 'Erreur lors de l’ajout à la file : ' . $e->getMessage();
    $logger->log('queue', 'error', 'add', $errorMessage);
    echo json_encode([
        'success' => false,
        'error' => $errorMessage
    ]);
}