<?php
header('Content-Type: text/html');

$history_file = '/home/gautard/spotdl-web/history/history.txt';

if (file_exists($history_file)) {
    $history = file_get_contents($history_file);
    echo htmlspecialchars($history);
} else {
    echo "Aucun historique de téléchargement disponible.";
}
?>
