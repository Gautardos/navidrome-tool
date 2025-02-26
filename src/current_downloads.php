<?php
$download_dir = "/downloads/"; // Chemin absolu vers le dossier

if (is_dir($download_dir)) {
    $files = scandir($download_dir);
    $output = "<h3>".(count($files) - 2)." fichiers téléchargés</h3><ul class='ui list'>";
    foreach ($files as $file) {
        if ($file !== "." && $file !== "..") {
            $file_path = $download_dir . $file;
            $file_size = filesize($file_path); // Taille en octets
            $size_in_mb = round($file_size / (1024 * 1024), 2); // Conversion en Mo
            $output .= "<li class='item'>$file - $size_in_mb Mo</li>";
        }
    }
    $output .= "</ul>";
    if ($output === "<ul class='ui list'></ul>") {
        echo "Aucun fichier en cours de téléchargement.";
    } else {
        echo $output;
    }
} else {
    echo "Le dossier des téléchargements n’existe pas.";
}
?>
