<?php
header('Content-Type: application/json');

if (!isset($_POST['urls'])) {
    echo json_encode(['error' => 'Aucune URL fournie']);
    exit;
}

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

require 'vendor/autoload.php';
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

try {
    $connection = new AMQPStreamConnection('localhost', 5672, 'gautard', 'gautard');
    $channel = $connection->channel();

    $channel->queue_declare('spotdl_queue', false, true, false, false);

    foreach ($urls as $url) {
        $url = trim($url);
        if (!empty($url)) {
            $message = json_encode([
                'url' => $url,
                'sync' => $sync,
                'client_id' => $client_id,
                'client_secret' => $client_secret
            ]);
            $msg = new AMQPMessage($message, ['delivery_mode' => AMQPMessage::DELIVERY_MODE_PERSISTENT]);
            $channel->basic_publish($msg, '', 'spotdl_queue');
            file_put_contents('/home/gautard/spotdl-web/log/history.txt', date('Y-m-d H:i:s') . " - Ajouté à la file : $url\n", FILE_APPEND);
        }
    }

    $channel->close();
    $connection->close();

    echo json_encode(['success' => 'URL(s) ajoutée(s) à la file avec succès']);
} catch (Exception $e) {
    echo json_encode(['error' => 'Erreur lors de l’ajout à la file : ' . $e->getMessage()]);
}
?>
