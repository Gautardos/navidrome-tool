<?php
// Définir le type de contenu comme HTML
header('Content-Type: text/html');

// Charger l'autoloader de Composer depuis src/vendor/
require __DIR__ . '/vendor/autoload.php';

// Importer les classes nécessaires
use Model\Amqp\Handler;

/** @var Handler $handler */
$handler = new Handler();

try {
    // Récupérer les informations de la file spotdl_queue via Handler
    $queue = 'spotdl_queue';
    $queueInfo = $handler->getQueueInfo($queue); // Nouvelle méthode à ajouter dans Handler
    $messageCount = $queueInfo['message_count'];
    $consumerCount = $queueInfo['consumer_count'];

    // Afficher les informations de la file
    echo "<p>Messages en attente : $messageCount</p>";
    echo "<p>Consommateurs actifs : $consumerCount</p>";
    echo "<p>Derniers messages (limité à 5) :</p>";
    echo "<ul>";

    // Lire les 5 derniers messages du fichier history.txt
    $historyFile = '/music/downloads/history.txt';
    $history = file_exists($historyFile) ? file($historyFile, FILE_SKIP_EMPTY_LINES) : [];
    $lastMessages = array_slice($history, -5);
    foreach ($lastMessages as $line) {
        echo "<li>" . htmlspecialchars($line) . "</li>";
    }
    echo "</ul>";
} catch (Exception $e) {
    echo "<p>Erreur lors de la récupération de l’état : " . htmlspecialchars($e->getMessage()) . "</p>";
}