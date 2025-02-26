<?php

require __DIR__ . '/vendor/autoload.php';

use Model\ConfigReader;

$config = new ConfigReader();

$grokConfig = $config->getGrokAPIConfig();

header('Content-Type: application/json');

if (!$grokConfig['api_key']) {
    echo json_encode(['error' => 'Clé API Grok manquante']);
    exit;
}

if (!isset($_POST['description'])) {
    echo json_encode(['error' => 'Aucune description fournie']);
    exit;
}

$description = trim($_POST['description']);

// Contexte clair pour l'API Grok avec opérateurs, champs, exemple et instruction renforcée
$context = [
    'objective' => 'Générer une playlist DYNAMIQUE au format JSON compatible avec les "smart playlists" de Navidrome (voir https://github.com/navidrome/navidrome/issues/1417). La playlist doit utiliser DES RÈGLES ABSTRAITES basées sur les métadonnées et non une liste statique de titres ou d’artistes spécifiques.',
    'format' => 'Un objet JSON avec les clés possibles : `name`, `comment`, `all` ou `any` (tableaux de conditions), `sort`, `order`, `limit`, comme dans les exemples de Navidrome. NE RETOURNE PAS DE LISTE STATIQUE DE TITRES OU D’ARTISTES, mais uniquement des règles dynamiques.',
    'operators' => [
        'is', 'isNot', 'gt', 'lt', 'contains', 'notContains', 'startsWith', 'endsWith',
        'inTheRange', 'before', 'after', 'inTheLast', 'notInTheLast', 'inPlaylist', 'notInPlaylist'
    ],
    'fields' => [
        'title', 'album', 'artist', 'albumartist', 'hascoverart', 'tracknumber', 'discnumber',
        'year', 'size', 'compilation', 'dateadded', 'datemodified', 'discsubtitle', 'comment',
        'lyrics', 'sorttitle', 'sortalbum', 'sortartist', 'sortalbumartist', 'albumtype',
        'albumcomment', 'catalognumber', 'filepath', 'filetype', 'duration', 'bitrate', 'bpm',
        'channels', 'genre', 'loved', 'dateloved', 'lastplayed', 'playcount', 'rating'
    ],
    'example' => [
        'description' => "80's Top Songs",
        'json' => [
            'all' => [
                ['any' => [
                    ['is' => ['loved' => true]],
                    ['gt' => ['rating' => 3]]
                ]],
                ['inTheRange' => ['year' => [1981, 1990]]]
            ],
            'sort' => 'year',
            'order' => 'desc',
            'limit' => 25
        ]
    ],
    'instruction' => 'Interprète la description textuelle suivante et retourne UNIQUEMENT un JSON bien formaté (sans backticks, sans ```, sans sauts de ligne inutiles, et SANS AUCUN TEXTE SUPPLÉMENTAIRE comme "Playlist générée :" ou autres commentaires) correspondant au format DYNAMIQUE de Navidrome, en utilisant les opérateurs, champs et le format illustré par l’exemple. NE RETOURNE PAS DE LISTE STATIQUE DE TITRES OU D’ARTISTES, mais des règles dynamiques comme `inTheLast`, `sort`, `limit`, etc.'
];

// Appel à l'API réelle de Grok
$curl = curl_init($grokConfig['endpoint']);
curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
curl_setopt($curl, CURLOPT_POST, true);
curl_setopt($curl, CURLOPT_HTTPHEADER, [
    'Authorization: Bearer ' . $grokConfig['api_key'],
    'Content-Type: application/json'
]);
curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode([
    'model' => $grokConfig['model'],
    'messages' => [
        ['role' => 'system', 'content' => json_encode($context)],
        ['role' => 'user', 'content' => $description]
    ]
]));
$response = curl_exec($curl);
$httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
curl_close($curl);

// Débogage : enregistrez la réponse brute et le contenu nettoyé
file_put_contents('/tmp/grok_response.log', $response . "\n", FILE_APPEND);

if ($httpCode === 200) {
    $data = json_decode($response, true);
    if (isset($data['choices']) && isset($data['choices'][0]['message']['content'])) {
        $playlistJson = $data['choices'][0]['message']['content'];
        // Nettoyage approfondi
        $playlistJson = trim($playlistJson);
        $playlistJson = preg_replace('/^```json\s*|```$/', '', $playlistJson); // Supprime les ```json ou ```
        $playlistJson = preg_replace('/\s+/', ' ', $playlistJson); // Supprime espaces et sauts de ligne multiples
        $playlistJson = str_replace(["\n", "\r", "\t"], ' ', $playlistJson); // Supprime tous les sauts de ligne et tabulations
        $playlistJson = str_replace('`', '', $playlistJson); // Supprime les backticks

        // Débogage supplémentaire : enregistrez le JSON nettoyé
        file_put_contents('/tmp/grok_cleaned.log', $playlistJson . "\n", FILE_APPEND);

        // Essayez de décoder
        $playlist = json_decode($playlistJson, true);
        if ($playlist !== null) {
            echo json_encode($playlist);
        } else {
            // Si JSON encore invalide, essayez de détecter l’erreur
            $error = json_last_error_msg();
            echo json_encode(['error' => 'Réponse invalide de l’API : JSON mal formaté dans content - ' . $error]);
        }
    } else {
        echo json_encode(['error' => 'Réponse invalide de l’API : Structure inattendue']);
    }
} else {
    echo json_encode(['error' => 'Erreur API : ' . $response]);
}
?>