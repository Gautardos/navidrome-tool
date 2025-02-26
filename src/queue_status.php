<?php
header('Content-Type: text/html');

require 'vendor/autoload.php';
use PhpAmqpLib\Connection\AMQPStreamConnection;

try {
    $connection = new AMQPStreamConnection('localhost', 5672, 'gautard', 'gautard');
    $channel = $connection->channel();

    $queue = 'spotdl_queue';
    $queue_info = $channel->queue_declare($queue, false, true, false, false);
    $message_count = $queue_info[1]; // Nombre de messages dans la file
    $consumer_count = $queue_info[2]; // Nombre de consommateurs

    $channel->close();
    $connection->close();

    echo "<p>Messages en attente : $message_count</p>";
    echo "<p>Consommateurs actifs : $consumer_count</p>";
    echo "<p>Derniers messages (limité à 5) :</p>";
    echo "<ul>";
    $history = file_exists('/music/downloads/history.txt') ? file('/music/downloads/history.txt', FILE_SKIP_EMPTY_LINES) : [];
    $last_messages = array_slice($history, -5);
    foreach ($last_messages as $line) {
        echo "<li>" . htmlspecialchars($line) . "</li>";
    }
    echo "</ul>";
} catch (Exception $e) {
    echo "<p>Erreur lors de la récupération de l’état : " . htmlspecialchars($e->getMessage()) . "</p>";
}
?>
