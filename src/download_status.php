<?php
header('Content-Type: application/json');

require 'vendor/autoload.php';
use PhpAmqpLib\Connection\AMQPStreamConnection;

try {
    $connection = new AMQPStreamConnection('localhost', 5672, 'gautard', 'gautard');
    $channel = $connection->channel();

    $queue = 'spotdl_status_queue';
    $channel->queue_declare($queue, false, true, false, false);

    $messages = [];
    $callback = function ($msg) use (&$messages) {
        $messages[] = json_decode($msg->body, true);
        $msg->ack();  // Accuse réception pour supprimer le message de la queue
    };

    $channel->basic_consume($queue, '', false, true, false, false, $callback);

    $start_time = time();
    while (count($messages) == 0 && (time() - $start_time) < 30) {  // Attendre jusqu'à 30 secondes
        $channel->wait(null, false, 30);
    }

    $channel->close();
    $connection->close();

    echo json_encode($messages);
} catch (Exception $e) {
    echo json_encode(['error' => 'Erreur lors de la récupération des statuts : ' . $e->getMessage()]);
}
?>
