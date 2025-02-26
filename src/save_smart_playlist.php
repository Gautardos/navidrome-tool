<?php
header('Content-Type: application/json');

if (!isset($_POST['name']) || !isset($_POST['playlist'])) {
    echo json_encode(['error' => 'Nom ou playlist manquant']);
    exit;
}

$name = trim($_POST['name']);
$playlistJson = $_POST['playlist'];

$playlist = json_decode($playlistJson, true);
if (!$playlist) {
    echo json_encode(['error' => 'JSON invalide']);
    exit;
}

$filePath = "/music/playlists/$name.nsp";
if (file_put_contents($filePath, json_encode($playlist, JSON_PRETTY_PRINT)) !== false) {
    chmod($filePath, 0664);
    chown($filePath, 'gautard');
    chgrp($filePath, 'gautard');
    echo json_encode(['success' => true]);
} else {
    echo json_encode(['error' => 'Erreur lors de l’écriture du fichier']);
}
?>