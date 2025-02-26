<?php
header('Content-Type: text/html');

$status_history_file = '/home/gautard/spotdl-web/history/status_history.txt';

if (file_exists($status_history_file)) {
    $lines = file($status_history_file, FILE_SKIP_EMPTY_LINES | FILE_IGNORE_NEW_LINES);
    $recent_lines = array_slice($lines, -10);  // Les 10 dernières entrées
    $current_status = implode("\n", $recent_lines);
    echo htmlspecialchars($current_status ?: 'Aucun traitement en cours...');
} else {
    echo "Aucun traitement en cours...";
}
?>
