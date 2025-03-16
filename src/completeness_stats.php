<?php
header('Content-Type: application/json');

require __DIR__ . '/vendor/autoload.php';

use Model\Logger;

try {
    $logger = new Logger();
    $conn = $logger->getConnection();

    if ($conn === null) {
        throw new Exception("Connexion à la base de données non disponible.");
    }

    // Requête pour obtenir les statistiques de complétude
    $stmt = $conn->prepare("
        SELECT 
            CASE 
                WHEN completeness = 100 THEN 'Parfaite (100%)'
                WHEN completeness >= 90 THEN 'Excellente (90%)'
                WHEN completeness >= 80 THEN 'Moyenne (80%)'
                WHEN completeness >= 0.5 THEN 'Faible (50-79%)'
                WHEN completeness < 0.5 THEN 'Nul! (<50%)'
                ELSE 'Inconnue'
            END as completeness_range,
            COUNT(*) as count
        FROM tracks
        GROUP BY completeness_range
    ");
    $stmt->execute();
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // Calcul du total
    $totalStmt = $conn->query("SELECT COUNT(*) FROM tracks");
    $total = $totalStmt->fetchColumn();

    // Préparation des données pour le chart
    $labels = [];
    $values = [];
    foreach ($rows as $row) {
        $labels[] = $row['completeness_range'];
        $values[] = $row['count'];
    }

    echo json_encode([
        'labels' => $labels,
        'values' => $values,
        'total' => $total
    ]);

} catch (Exception $e) {
    $logger->log('completeness', 'error', 'stats', 'Erreur lors de la récupération des stats : ' . $e->getMessage());
    echo json_encode(['error' => $e->getMessage()]);
}
?>