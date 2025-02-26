<?php
// Définir le type de contenu comme JSON
header('Content-Type: application/json');

// Démarrer la session
session_start();

/* 
 * Vérification de l'authentification (commentée pour l'instant)
 * if (!isset($_SESSION['logged_in'])) {
 *     echo json_encode(['message' => 'Non autorisé. Veuillez vous connecter.', 'success' => false]);
 *     exit;
 * }
 */

// Charger l'autoloader de Composer depuis src/vendor/
require __DIR__ . '/vendor/autoload.php';

// Importer les classes nécessaires
use Model\Amqp\Handler;

/** @var Handler $handler */
$handler = new Handler();

// Chemin du fichier de log
$log_file = "../log/status_history.txt";

// Récupérer l'action depuis la requête POST
$action = $_POST['action'] ?? '';
$response = ['message' => 'Action non reconnue.', 'success' => false];

// Journaliser l'action demandée, même en cas d'erreur
$log_message = "[" . date('Y-m-d H:i:s') . "] Gestion du service - Action demandée : " . $action . " - Données reçues : " . json_encode($_POST) . "\n";
file_put_contents($log_file, $log_message, FILE_APPEND | LOCK_EX);

try {
    if ($action === 'stop') {
        // Arrêter le service spotdl-consumer.service
        $command = "sudo systemctl stop spotdl-consumer.service 2>&1";
        exec($command, $output, $return_var);
        if ($return_var === 0) {
            $response = ['message' => 'Service arrêté avec succès.', 'success' => true];
            $log_message = "[" . date('Y-m-d H:i:s') . "] Service arrêté avec succès.\n";
        } else {
            $error = 'Erreur lors de l’arrêt du service : ' . implode("\n", $output);
            $response = ['message' => $error, 'success' => false];
            $log_message = "[" . date('Y-m-d H:i:s') . "] " . $error . "\n";
        }
    } elseif ($action === 'purge') {
        // Retirer le premier message de la file spotdl_queue via Handler
        $message = $handler->sendMessage('spotdl_queue', ['action' => 'purge']); // Ajustement : utiliser Handler
        if ($message) {
            $response = ['message' => 'Premier message retiré avec succès.', 'success' => true];
            $log_message = "[" . date('Y-m-d H:i:s') . "] Premier message retiré avec succès.\n";
        } else {
            $response = ['message' => 'Aucun message dans la file.', 'success' => false];
            $log_message = "[" . date('Y-m-d H:i:s') . "] Aucun message dans la file.\n";
        }
    } elseif ($action === 'start') {
        // Relancer le service spotdl-consumer.service
        $command = "sudo systemctl start spotdl-consumer.service 2>&1";
        exec($command, $output, $return_var);
        if ($return_var === 0) {
            $response = ['message' => 'Service relancé avec succès.', 'success' => true];
            $log_message = "[" . date('Y-m-d H:i:s') . "] Service relancé avec succès.\n";
        } else {
            $error = 'Erreur lors du redémarrage du service : ' . implode("\n", $output);
            $response = ['message' => $error, 'success' => false];
            $log_message = "[" . date('Y-m-d H:i:s') . "] " . $error . "\n";
        }
    } else {
        $response = ['message' => 'Action non reconnue : ' . $action, 'success' => false];
        $log_message = "[" . date('Y-m-d H:i:s') . "] " . $response['message'] . "\n";
    }

    // Journaliser le résultat
    file_put_contents($log_file, $log_message, FILE_APPEND | LOCK_EX);
} catch (Exception $e) {
    // Gérer les erreurs de manière sécurisée
    $error = 'Erreur inattendue : ' . $e->getMessage();
    $response = ['message' => $error, 'success' => false];
    $log_message = "[" . date('Y-m-d H:i:s') . "] " . $error . "\n";
    file_put_contents($log_file, $log_message, FILE_APPEND | LOCK_EX);
    error_log($error); // Journaliser dans les logs PHP
}

// Retourner la réponse en JSON
echo json_encode($response);