<?php
header('Content-Type: application/json');

require __DIR__ . '/vendor/autoload.php';

use Model\Logger;

try {
    $logger = new Logger();

    if (!$logger->isWritable()) {
        throw new Exception("La base de données est en lecture seule. Aucune modification possible.");
    }

    $conn = $logger->getConnection();
    if ($conn === null) {
        throw new Exception("Connexion à la base de données non disponible.");
    }

    $table = $_POST['table'] ?? '';
    $action = $_POST['action'] ?? '';
    $ids = $_POST['ids'] ?? [];

    if (!in_array($table, ['logs', 'tracks'])) {
        throw new Exception("Tableau invalide.");
    }

    if ($action === 'purge') {
        $conn->exec("DELETE FROM $table");
        $message = "Table $table purgée avec succès.";
        $logger->log('manage', 'info', 'table_action', $message);
    } elseif ($action === 'delete' && !empty($ids)) {
        $placeholders = implode(',', array_fill(0, count($ids), '?'));
        $stmt = $conn->prepare("DELETE FROM $table WHERE id IN ($placeholders)");
        $stmt->execute($ids);
        $message = count($ids) . " entrées supprimées de $table.";
        //$logger->log('manage', 'info', 'table_action', $message);
    } else {
        throw new Exception("Action ou IDs invalides.");
    }

    echo json_encode(['message' => $message]);
} catch (Exception $e) {
    $logger->log('manage', 'error', 'table_action', $e->getMessage());
    echo json_encode(['message' => 'Erreur : ' . $e->getMessage()]);
}