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

    // Récupérer tous les genres (y compris les multiples)
    $stmt = $conn->query("SELECT genre FROM tracks");
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // Calcul du total des morceaux
    $totalStmt = $conn->query("SELECT COUNT(*) FROM tracks");
    $total = $totalStmt->fetchColumn();

    // Tableau pour stocker le compte des genres
    $genreCounts = [];

    // Parcourir chaque morceau et séparer les genres multiples
    foreach ($rows as $row) {
        $genres = $row['genre'] ? $row['genre'] : 'Inconnu';

        // Séparer les genres multiples avec / ou ,
        $genreArray = preg_split('/[\/,]+/', $genres, -1, PREG_SPLIT_NO_EMPTY);

        // Nettoyer et compter chaque genre
        foreach ($genreArray as $genre) {
            $genre = trim($genre); // Supprimer les espaces
            if (!empty($genre)) {
                if (!isset($genreCounts[$genre])) {
                    $genreCounts[$genre] = 0;
                }
                $genreCounts[$genre]++;
            }
        }
    }

    // Trier les genres par nombre de morceaux (décroissant)
    arsort($genreCounts);

    // Préparer les données pour le chart
    $labels = array_keys($genreCounts);
    $values = array_values($genreCounts);

    // Nombre de genres uniques
    $uniqueGenres = count($labels);

    echo json_encode([
        'labels' => $labels,
        'values' => $values,
        'total' => $total,
        'uniqueGenres' => $uniqueGenres
    ]);

} catch (Exception $e) {
    $logger->log('genre', 'error', 'stats', 'Erreur lors de la récupération des stats de genre : ' . $e->getMessage());
    echo json_encode(['error' => $e->getMessage()]);
}
?>