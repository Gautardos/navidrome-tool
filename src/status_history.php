<?php
header('Content-Type: text/html');

$status_history_file = '/home/gautard/spotdl-web/log/status_history.txt';

if (file_exists($status_history_file)) {
    $history = file_get_contents($status_history_file);
    echo htmlspecialchars($history);
} else {
    echo "Aucun historique de traitement disponible.";
}
?>
