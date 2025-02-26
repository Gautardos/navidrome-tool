<?php

require __DIR__ . '/vendor/autoload.php';

// Utiliser la classe ConfigReader sans require
use Model\ConfigReader;

session_start();

$config = new ConfigReader();

$userConfig = $config->getUserAuthConfig();

$history_file = "../log/history.txt";
$status_history_file = "../log/status_history.txt";

if (isset($_GET['logout'])) {
    session_destroy();
    header("Location: /");
}

// Vérification de l'authentification
if (!isset($_SESSION['logged_in'])) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        if (isset($_POST['username']) && $_POST['username'] === $userConfig['username'] && $_POST['password'] === $userConfig['password']) {
            $_SESSION['logged_in'] = true;
        } else {
            $error_message = "Identifiants incorrects.";
        }
    }

    if (!isset($_SESSION['logged_in'])) {
        ?>
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Connexion - SpotDL Queue Manager</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/semantic-ui@2.5.0/dist/semantic.min.css">
            <style>
                body {
                    background: #f9fafb;
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .login-container {
                    width: 100%;
                    max-width: 400px;
                    padding: 20px;
                }
                .ui.form .field {
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
        <div class="login-container">
            <div class="ui raised segment">
                <h2 class="ui header">Connexion</h2>
                <?php if (isset($error_message)) { ?>
                    <div class="ui negative message">
                        <?php echo $error_message; ?>
                    </div>
                <?php } ?>
                <form class="ui form" method="POST">
                    <div class="field">
                        <label>Nom d'utilisateur</label>
                        <input type="text" name="username" placeholder="Nom d'utilisateur" required>
                    </div>
                    <div class="field">
                        <label>Mot de passe</label>
                        <input type="password" name="password" placeholder="Mot de passe" required>
                    </div>
                    <button class="ui blue button" type="submit">Se connecter</button>
                </form>
            </div>
        </div>
        </body>
        </html>
        <?php
        exit;
    }
}

if (isset($_SESSION['logged_in'])) {
    ?>
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SpotDL Queue Manager</title>
        <!-- Semantic UI CSS -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/semantic-ui@2.5.0/dist/semantic.min.css">
        <!-- jQuery -->
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <!-- Semantic UI JS -->
        <script src="https://cdn.jsdelivr.net/npm/semantic-ui@2.5.0/dist/semantic.min.js"></script>
        <style>
            body { padding: 20px; margin: 0; }
            .section {padding: 20px;}
            .ui.container { max-width: 1200px !important; margin: 0 auto; }
            .ui.segment.output { white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
            .ui.sidebar { background: #f8f8f8; width: 250px; }
            .ui.sidebar .item { font-size: 1.2em; padding: 15px; color: #333; }
            .mobile-toggle { display: none; }
            @media (max-width: 767px) {
                .mobile-toggle { display: block; position: fixed; top: 10px; left: 10px; z-index: 1000; }
                .ui.top.menu .item { display: none !important; }
                .ui.top.menu a.mobile-toggle.item { display: block !important; top:0; }
                .ui.container { padding: 10px; }
            }
        </style>
        <script>
            function showSection(page) {
                $('.section').hide();
                $('#' + page).show();
                if (page === 'download') {
                    updateQueueStatus();
                    updateDownloads();
                } else if (page === 'status') {
                    updateCurrentStatus();
                    updateStatusHistory();
                } else if (page === 'history') {
                    updateDownloadHistory();
                }
                $('.ui.sidebar').sidebar('hide'); // Ferme la sidebar après sélection
            }

            function updateQueueStatus() {
                $.ajax({
                    url: 'queue_status.php',
                    method: 'GET',
                    success: function(data) {
                        $('#queueStatus').html(data);
                    },
                    error: function(xhr, status, error) {
                        $('#queueStatus').html('Erreur lors de la récupération de l’état de la file.');
                    }
                });
            }

            function updateCurrentStatus() {
                $.ajax({
                    url: 'current_status.php',
                    method: 'GET',
                    success: function(response) {
                        $('#currentStatus').html(response || 'Aucun traitement en cours...');
                    },
                    error: function(xhr, status, error) {
                        $('#currentStatus').html('Erreur lors de la récupération des statuts.');
                    }
                });
            }

            function updateStatusHistory() {
                $.ajax({
                    url: 'status_history.php',
                    method: 'GET',
                    success: function(response) {
                        $('#statusHistory').html(response || 'Aucun historique de traitement.');
                    },
                    error: function(xhr, status, error) {
                        $('#statusHistory').html('Erreur lors de la récupération de l’historique.');
                    }
                });
            }

            function updateDownloadHistory() {
                $.ajax({
                    url: 'download_history.php',
                    method: 'GET',
                    success: function(response) {
                        $('#downloadHistory').html(response || 'Aucun historique de téléchargement.');
                    },
                    error: function(xhr, status, error) {
                        $('#downloadHistory').html('Erreur lors de la récupération de l’historique.');
                    }
                });
            }

            function updateDownloads() {
                $.ajax({
                    url: 'current_downloads.php',
                    method: 'GET',
                    success: function(response) {
                        $('#currentDownloads').html(response || 'Aucun téléchargement en cours.');
                    },
                    error: function(xhr, status, error) {
                        $('#currentDownloads').html('Erreur lors de la récupération des téléchargements.');
                    }
                });
            }

            function addToQueue() {
                const urls = $('#urls').val();
                const sync = $('#sync').is(':checked') ? 1 : 0;
                $.ajax({
                    url: 'add_to_queue.php',
                    method: 'POST',
                    data: { urls: urls, sync: sync },
                    success: function(response) {
                        console.log('Réponse brute:', response); // Débogage
                        try {
                            const data = typeof response === 'string' ? JSON.parse(response) : response;
                            $('#output').html(data.message || data.error || 'Réponse inattendue');
                            $('#urls').val('');
                            updateCurrentStatus();
                        } catch (e) {
                            $('#output').html('Erreur de parsing JSON: ' + e.message);
                        }
                    },
                    error: function(xhr, status, error) {
                        $('#output').html('Erreur AJAX: ' + error);
                        console.log('Erreur AJAX:', xhr.responseText); // Débogage
                    }
                });
            }

            function manageService(action) {
                $.ajax({
                    url: 'manage_service.php',
                    method: 'POST',
                    data: { action: action },
                    success: function(response) {
                        alert(response.message || 'Action exécutée avec succès.');
                        updateQueueStatus(); // Rafraîchir l’état de la file après l’action
                    },
                    error: function(xhr, status, error) {
                        alert('Erreur lors de l’exécution de l’action : ' + error);
                    }
                });
            }

            function generateSmartPlaylist() {
                const description = $('#playlistDescription').val();
                $.ajax({
                    url: 'generate_smart_playlist.php',
                    method: 'POST',
                    data: { description: description },
                    success: function(response) {
                        if (response.error) {
                            $('#playlistPreview').html('Erreur : ' + response.error);
                        } else {
                            $('#playlistPreview').html(JSON.stringify(response, null, 2));
                            $('#savePlaylistSection').show();
                        }
                    },
                    error: function(xhr, status, error) {
                        $('#playlistPreview').html('Erreur lors de la génération de la playlist.');
                    }
                });
            }

            function saveSmartPlaylist() {
                const name = $('#playlistName').val();
                if (!name) {
                    alert('Veuillez entrer un nom pour la playlist.');
                    return;
                }
                $.ajax({
                    url: 'save_smart_playlist.php',
                    method: 'POST',
                    data: { name: name, playlist: $('#playlistPreview').text().replace('Playlist générée :\n', '') },
                    success: function(response) {
                        if (response.success) {
                            alert('Playlist sauvegardée avec succès sous ' + name + '.nsp');
                            cancelSmartPlaylist();
                        } else {
                            alert('Erreur : ' + response.error);
                        }
                    },
                    error: function(xhr, status, error) {
                        alert('Erreur lors de la sauvegarde de la playlist.');
                    }
                });
            }

            function cancelSmartPlaylist() {
                $('#playlistPreview').html('Aucune playlist générée pour le moment.');
                $('#savePlaylistSection').hide();
                $('#playlistDescription').val('');
            }

            $(document).ready(function() {
                $('.ui.sidebar').append('<a class="item" href="javascript:void(0)" onclick="showSection(\'smart-playlist\')">Créer une playlist</a>');
                $('.ui.top.menu').append('<a class="item" href="javascript:void(0)" onclick="showSection(\'smart-playlist\')">Créer une playlist</a>');
            });

            $(document).ready(function() {
                showSection('download');
                setInterval(updateQueueStatus, 5000);
                setInterval(updateCurrentStatus, 5000);
                setInterval(updateStatusHistory, 5000);
                setInterval(updateDownloadHistory, 5000);
                setInterval(updateDownloads, 30000);

                // Initialisation de la sidebar
                $('.ui.sidebar').sidebar({
                    transition: 'overlay',
                    mobileTransition: 'overlay'
                });

                // Ouvrir/Fermer la sidebar avec le burger
                $('.mobile-toggle').click(function() {
                    $('.ui.sidebar').sidebar('toggle');
                });
            });
        </script>
    </head>
    <body>
    <div class="ui sidebar vertical menu">
        <a class="item" href="javascript:void(0)" onclick="showSection('download')">Gestion de file</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('status')">Statuts & Historique</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('history')">Historique</a>
        <a class="item" href="?logout">Déconnexion</a>
    </div>

    <div class="ui container pusher">
        <div class="ui top attached menu">
            <a class="mobile-toggle item" href="javascript:void(0)"><i class="bars icon"></i></a>
            <a class="item" href="javascript:void(0)" onclick="showSection('download')">Gestion de file</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('status')">Statuts & Historique</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('history')">Historique</a>
            <a class="right item" href="?logout">Déconnexion</a>
        </div>

        <div id="download" class="section" style="display: block;">
            <h1 class="ui header">Gestion de la file de téléchargements Spotify</h1>
            <form id="downloadForm" class="ui form" onsubmit="event.preventDefault(); addToQueue();">
                <div class="field">
                    <textarea id="urls" name="urls" placeholder="Entrez les URLs Spotify" required></textarea>
                </div>
                <div class="field">
                    <div class="ui checkbox">
                        <input type="checkbox" id="sync" name="sync">
                        <label>Synchroniser</label>
                    </div>
                </div>
                <button class="ui green button" type="submit">Ajouter à la file</button>
            </form>
            <h2 class="ui header">Résultat</h2>
            <div id="output" class="ui segment output">Aucun téléchargement en cours.</div>
            <h2 class="ui header">État de la file</h2>
            <div id="queueStatus" class="ui segment output">Chargement...</div>
            <h2 class="ui header">Téléchargements en cours</h2>
            <div id="currentDownloads" class="ui segment output">Chargement...</div>
            <h2 class="ui header">Gestion du service</h2>
            <div class="ui segment">
                <button class="ui red button" onclick="manageService('stop')">Arrêter le service</button>
                <button class="ui orange button" onclick="manageService('purge')">Retirer le premier message</button>
                <button class="ui green button" onclick="manageService('start')">Relancer le service</button>
            </div>
        </div>

        <div id="status" class="section" style="display: none;">
            <h1 class="ui header">Statuts des téléchargements & Historique des traitements</h1>
            <h2 class="ui header">Statut en cours</h2>
            <div id="currentStatus" class="ui segment output">Aucun traitement en cours...</div>
            <h2 class="ui header">Historique des traitements</h2>
            <div id="statusHistory" class="ui segment output">Chargement de l’historique...</div>
        </div>

        <div id="history" class="section" style="display: none;">
            <h1 class="ui header">Historique des téléchargements</h1>
            <div id="downloadHistory" class="ui segment output">Chargement de l’historique...</div>
        </div>

        <div id="smart-playlist" class="section" style="display: none;">
            <h1 class="ui header">Créer une playlist intelligente</h1>
            <form id="smartPlaylistForm" class="ui form" onsubmit="event.preventDefault(); generateSmartPlaylist();">
                <div class="field">
                    <label>Description de la playlist</label>
                    <textarea id="playlistDescription" name="description" placeholder="Exemple : Mes 100 derniers morceaux écoutés dans les 30 derniers jours, ordonnés par date de dernière écoute décroissante" required></textarea>
                </div>
                <button class="ui blue button" type="submit">Générer la playlist</button>
            </form>
            <h2 class="ui header">Playlist proposée</h2>
            <div id="playlistPreview" class="ui segment output">Aucune playlist générée pour le moment.</div>
            <div id="savePlaylistSection" style="display: none;">
                <h2 class="ui header">Sauvegarder la playlist</h2>
                <div class="ui form">
                    <div class="field">
                        <label>Nom de la playlist</label>
                        <input type="text" id="playlistName" placeholder="Ma playlist intelligente">
                    </div>
                    <button class="ui green button" onclick="saveSmartPlaylist()">Sauvegarder</button>
                    <button class="ui red button" onclick="cancelSmartPlaylist()">Annuler</button>
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>
    <?php
    exit;
}
