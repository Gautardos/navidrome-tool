<?php
header('Content-Type: application/json');

session_start();
/*if (!isset($_SESSION['logged_in'])) {
    echo json_encode(['message' => 'Non autorisé. Veuillez vous connecter.', 'success' => false]);
    exit;
}*/

require_once 'vendor/autoload.php'; // Si tu utilises Composer pour php-amqplib
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Channel\AMQPChannel;

$action = $_POST['action'] ?? '';
$response = ['message' => 'Action non reconnue.', 'success' => false];

// Journalisation des actions dans status_history.txt, même en cas d’erreur
$log_file = "/home/gautard/spotdl-web/history/status_history.txt";
$log_message = "[" . date('Y-m-d H:i:s') . "] Gestion du service - Action demandée : " . $action . " - Données reçues : " . json_encode($_POST) . "\n";
file_put_contents($log_file, $log_message, FILE_APPEND | LOCK_EX);

if ($action === 'stop') {
    // Arrêter le service spotdl-consumer.service
    $command = "sudo systemctl stop spotdl-consumer.service 2>&1";
    exec($command, $output, $return_var);
    if ($return_var === 0) {
        $response = ['message' => 'Service arrêté avec succès.', 'success' => true];
        file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] Service arrêté avec succès.\n", FILE_APPEND | LOCK_EX);
    } else {
        $error = 'Erreur lors de l’arrêt du service : ' . implode("\n", $output);
        $response = ['message' => $error, 'success' => false];
        file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] " . $error . "\n", FILE_APPEND | LOCK_EX);
    }
} elseif ($action === 'purge') {
    // Retirer le premier message de la file spotdl_queue
    try {
        $connection = new AMQPStreamConnection('localhost', 5672, 'gautard', 'gautard');
        $channel = $connection->channel();
        $channel->queue_declare('spotdl_queue', false, true, false, false);
        $message = $channel->basic_get('spotdl_queue', true); // Retire et supprime le message
        if ($message) {
            $response = ['message' => 'Premier message retiré avec succès.', 'success' => true];
            file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] Premier message retiré avec succès.\n", FILE_APPEND | LOCK_EX);
        } else {
            $response = ['message' => 'Aucun message dans la file.', 'success' => false];
            file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] Aucun message dans la file.\n", FILE_APPEND | LOCK_EX);
        }
        $channel->close();
        $connection->close();
    } catch (Exception $e) {
        $error = 'Erreur lors du retrait du message : ' . $e->getMessage();
        $response = ['message' => $error, 'success' => false];
        file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] " . $error . "\n", FILE_APPEND | LOCK_EX);
    }
} elseif ($action === 'start') {
    // Relancer le service spotdl-consumer.service
    $command = "sudo systemctl start spotdl-consumer.service 2>&1";
    exec($command, $output, $return_var);
    if ($return_var === 0) {
        $response = ['message' => 'Service relancé avec succès.', 'success' => true];
        file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] Service relancé avec succès.\n", FILE_APPEND | LOCK_EX);
    } else {
        $error = 'Erreur lors du redémarrage du service : ' . implode("\n", $output);
        $response = ['message' => $error, 'success' => false];
        file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] " . $error . "\n", FILE_APPEND | LOCK_EX);
    }
} else {
    $response = ['message' => 'Action non reconnue : ' . $action, 'success' => false];
    file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] " . $response['message'] . "\n", FILE_APPEND | LOCK_EX);
}

echo json_encode($response);
