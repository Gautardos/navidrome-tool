<?php
header('Content-Type: text/html');

require __DIR__ . '/vendor/autoload.php';

use Model\Logger;

try {
    $logger = new Logger();
    $conn = $logger->getConnection();

    if ($conn === null) {
        echo '<div class="ui error message">Connexion à la base de données non disponible.</div>';
        exit;
    }

    // Requête pour récupérer les 20 dernières entrées avec type="download"
    $stmt = $conn->prepare('
        SELECT date, message 
        FROM logs 
        WHERE type = :type 
        ORDER BY id DESC 
        LIMIT 20
    ');
    $stmt->bindValue(':type', 'download', PDO::PARAM_STR);
    $stmt->execute();
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // Construction du tableau HTML
    $html = '<table class="ui celled table"><thead><tr>';
    $columns = ['date', 'message'];
    foreach ($columns as $col) {
        $html .= '<th>' . ucfirst($col) . '</th>';
    }
    $html .= '</tr></thead><tbody>';

    if (empty($rows)) {
        $html .= '<tr><td colspan="5">Aucun log de téléchargement disponible.</td></tr>';
    } else {
        foreach ($rows as $row) {
            $html .= '<tr>';
            foreach ($columns as $col) {
                $value = $row[$col] ?? '';
                $html .= '<td>' . htmlspecialchars($value) . '</td>';
            }
            $html .= '</tr>';
        }
    }

    $html .= '</tbody></table>';
    echo $html;

} catch (Exception $e) {
    $logger->log('status', 'error', 'current', 'Erreur lors de la récupération des logs : ' . $e->getMessage());
    echo '<div class="ui error message">Erreur : ' . htmlspecialchars($e->getMessage()) . '</div>';
}
?>