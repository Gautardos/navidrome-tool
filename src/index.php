<?php
require __DIR__ . '/vendor/autoload.php';

use Model\ConfigReader;
use Model\Logger;

session_start();

$config = new ConfigReader();
$userConfig = $config->getUserAuthConfig();

// Vérifier si l'utilisateur demande une déconnexion
if (isset($_GET['logout'])) {
    try {
        $logger = new Logger();
        $logger->log('auth', 'info', 'logout', 'Utilisateur déconnecté avec succès');
    } catch (Exception $e) {
        error_log($e->getMessage());
    }
    session_destroy();
    header("Location: /");
    exit;
}

// Vérification de l'authentification
if (!isset($_SESSION['logged_in'])) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        if (isset($_POST['username']) && $_POST['username'] === $userConfig['username'] && $_POST['password'] === $userConfig['password']) {
            $_SESSION['logged_in'] = true;
            try {
                $logger = new Logger();
                $logger->log('auth', 'info', 'login', 'Utilisateur ' . $_POST['username'] . ' connecté avec succès');
            } catch (Exception $e) {
                error_log($e->getMessage());
            }
        } else {
            $error_message = "Identifiants incorrects.";
            try {
                $logger = new Logger();
                $logger->log('auth', 'error', 'login', 'Échec de connexion pour l\'utilisateur ' . ($_POST['username'] ?? 'inconnu'));
            } catch (Exception $e) {
                error_log($e->getMessage());
            }
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
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/semantic-ui@2.5.0/dist/semantic.min.css">
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/semantic-ui@2.5.0/dist/semantic.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { padding: 20px; margin: 0; }
            .section { padding: 20px; }
            .ui.container { max-width: 1900px !important; margin: 0 auto; }
            .ui.segment.output { white-space: pre-wrap; overflow-y: auto; }
            .ui.sidebar { background: #f8f8f8; width: 250px; }
            .ui.sidebar .item { font-size: 1.2em; padding: 15px; color: #333; }
            .mobile-toggle { display: none; }
            .ui.table { font-size: 0.9em; }
            .ui.table th.sortable { cursor: pointer; }
            .ui.table th.sortable:hover { background-color: #f5f5f5; }
            .pagination { margin-top: 20px; }
            @media (max-width: 767px) {
                .mobile-toggle { display: block; position: fixed; top: 10px; left: 10px; z-index: 1000; }
                .ui.top.menu .item { display: none !important; }
                .ui.top.menu a.mobile-toggle.item { display: block !important; }
                .ui.container { padding: 10px; }
            }
        </style>
        <script>
            let sortStates = {
                'logs': { column: 'date', order: 'DESC' },
                'tracks': { column: 'id', order: 'DESC' }
            };

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
                } else if (page === 'logs') {
                    loadTable('logs', 1);
                } else if (page === 'tracks') {
                    loadTable('tracks', 1);
                } else if (page === 'smart-playlist') {
                    // rien à faire
                } else if (page === 'completeness') {
                    updateCompletenessChart();
                    updateGenreChart();
                }
                $('.ui.sidebar').sidebar('hide');
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

            function updateCompletenessChart() {
                $.ajax({
                    url: 'completeness_stats.php',
                    method: 'GET',
                    dataType: 'json',
                    success: function(response) {
                        const ctx = document.getElementById('completenessChart').getContext('2d');
                        
                        if (window.completenessChart instanceof Chart) {
                            window.completenessChart.destroy();
                        }

                        window.completenessChart = new Chart(ctx, {
                            type: 'pie',
                            data: {
                                labels: response.labels,
                                datasets: [{
                                    data: response.values,
                                    backgroundColor: [
                                        '#2ecc71', // Success (100%)
                                        '#3498db', // Good (75-99%)
                                        '#f1c40f', // Warning (50-74%)
                                        '#e74c3c', // Danger (<50%)
                                        '#95a5a6'  // Unknown (NULL)
                                    ]
                                }]
                            },
                            options: {
                                responsive: true,
                                plugins: {
                                    legend: {
                                        position: 'top',
                                    },
                                    title: {
                                        display: true,
                                        text: 'Répartition des morceaux par niveau de complétude'
                                    },
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                let label = context.label || '';
                                                if (label) {
                                                    label += ': ';
                                                }
                                                label += context.raw + ' morceaux (' + 
                                                    ((context.raw / response.total) * 100).toFixed(1) + '%)';
                                                return label;
                                            }
                                        }
                                    }
                                },
                                onClick: (event, elements) => {
                                    if (elements.length > 0) {
                                        const index = elements[0].index;
                                        const label = response.labels[index];
                                        let filterValue;

                                        // Déterminer la plage de complétude pour le filtre
                                        if (label === 'Complète (100%)') {
                                            filterValue = '1';
                                        } else if (label === 'Bonne (75-99%)') {
                                            filterValue = '0.75-0.99';
                                        } else if (label === 'Moyenne (50-74%)') {
                                            filterValue = '0.5-0.74';
                                        } else if (label === 'Faible (<50%)') {
                                            filterValue = '<0.5';
                                        } else if (label === 'Inconnue') {
                                            filterValue = 'NULL';
                                        }

                                        // Rediriger vers la section Tracks avec un filtre
                                        showSection('tracks');
                                        loadTableWithFilter('tracks', 1, { completeness: filterValue });
                                    }
                                }
                            }
                        });
                        
                        $('#totalTracks').text('Total des morceaux : ' + response.total);
                    },
                    error: function(xhr, status, error) {
                        $('#completenessChartContainer').html('Erreur lors du chargement des statistiques.');
                    }
                });
            }

            function generateColors(count) {
                const colors = [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CB3F',
                    '#7BCB3F', '#3FCB7B', '#3F7BCB', '#CB3F7B', '#7B3FCB', '#CB7B3F', '#3FCBFF',
                    '#FF3FCB', '#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A1FF33', '#33A1FF',
                    '#FF8333', '#33FF83', '#8333FF', '#FF3383', '#83FF33', '#3383FF', '#FF3333',
                    '#33FF33', '#3333FF', '#FF33FF', '#FFFF33', '#33FFFF', '#FF6633', '#33FF66',
                    '#6633FF', '#FF3366', '#66FF33', '#3366FF', '#FF9933', '#33FF99', '#9933FF',
                    '#FF3399', '#99FF33', '#3399FF', '#FFCC33', '#33FFCC', '#CC33FF', '#FF33CC',
                    '#CCFF33', '#33CCFF', '#FF3333', '#33FF33', '#3333FF', '#FF33FF', '#FFFF33',
                    '#33FFFF', '#FF6666', '#66FF66', '#6666FF'
                ];

                // Si plus de couleurs sont nécessaires, générer dynamiquement
                if (count > colors.length) {
                    for (let i = colors.length; i < count; i++) {
                        const hue = (i * 137.508) % 360; // Utilisation de la "golden angle" pour des couleurs bien réparties
                        colors.push(`hsl(${hue}, 70%, 50%)`);
                    }
                }

                return colors.slice(0, count);
            }

            function updateGenreChart() {
                $.ajax({
                    url: 'genre_stats.php',
                    method: 'GET',
                    dataType: 'json',
                    success: function(response) {
                        const ctx = document.getElementById('genreChart').getContext('2d');
                        
                        if (window.genreChart instanceof Chart) {
                            window.genreChart.destroy();
                        }

                        // Générer les couleurs en fonction du nombre de genres
                        const colors = generateColors(response.labels.length);

                        window.genreChart = new Chart(ctx, {
                            type: 'pie',
                            data: {
                                labels: response.labels,
                                datasets: [{
                                    data: response.values,
                                    backgroundColor: colors
                                }]
                            },
                            options: {
                                responsive: true,
                                plugins: {
                                    legend: {
                                        position: 'top',
                                    },
                                    title: {
                                        display: true,
                                        text: 'Répartition des morceaux par genre'
                                    },
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                let label = context.label || '';
                                                if (label) {
                                                    label += ': ';
                                                }
                                                label += context.raw + ' morceaux (' + 
                                                    ((context.raw / response.total) * 100).toFixed(1) + '%)';
                                                return label;
                                            }
                                        }
                                    }
                                },
                                onClick: (event, elements) => {
                                    if (elements.length > 0) {
                                        const index = elements[0].index;
                                        const label = response.labels[index];

                                        // Rediriger vers la section Tracks avec un filtre sur le genre
                                        showSection('tracks');
                                        loadTableWithFilter('tracks', 1, { genre: label });
                                    }
                                }
                            }
                        });
                        
                        $('#totalGenres').text('Nombre total de genres : ' + response.uniqueGenres);
                    },
                    error: function(xhr, status, error) {
                        $('#genreChartContainer').html('Erreur lors du chargement des statistiques de genre.');
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
                        updateQueueStatus();
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
                            $('#playlistPreview').val('Erreur : ' + response.error);
                        } else {
                            $('#playlistPreview').val(JSON.stringify(response, null, 2));
                            $('#savePlaylistSection').show();
                        }
                    },
                    error: function(xhr, status, error) {
                        $('#playlistPreview').val('Erreur lors de la génération de la playlist.');
                    }
                });
            }

            function saveSmartPlaylist() {
                const name = $('#playlistName').val();
                if (!name) {
                    alert('Veuillez entrer un nom pour la playlist.');
                    return;
                }
                const modifiedPlaylist = $('#playlistPreview').val();
                $.ajax({
                    url: 'save_smart_playlist.php',
                    method: 'POST',
                    data: { name: name, playlist: modifiedPlaylist },
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
                $('#playlistPreview').val('Aucune playlist générée pour le moment.');
                $('#savePlaylistSection').hide();
                $('#playlistDescription').val('');
            }

            function loadTable(table, page) {
                const filters = {};
                $(`#${table}Filters .field input`).each(function() {
                    if ($(this).val()) filters[$(this).attr('name')] = $(this).val();
                });
                const perPage = $(`#${table}PerPage`).val();
                const sortColumn = sortStates[table].column || (table === 'logs' ? 'date' : 'path');
                const sortOrder = sortStates[table].order || 'ASC';

                $.ajax({
                    url: 'fetch_table.php',
                    method: 'POST',
                    data: { table, page, filters, sortColumn, sortOrder, perPage },
                    success: function(response) {
                        $(`#${table}Table`).html(response.table);
                        $(`#${table}Pagination`).html(response.pagination);
                        $(`#${table}Table th.sortable`).off('click').on('click', function() {
                            const column = $(this).data('column');
                            if (sortStates[table].column === column) {
                                sortStates[table].order = sortStates[table].order === 'ASC' ? 'DESC' : 'ASC';
                            } else {
                                sortStates[table] = { column: column, order: 'DESC' };
                            }
                            loadTable(table, 1);
                        });
                    },
                    error: function() {
                        $(`#${table}Table`).html('Erreur lors du chargement des données.');
                    }
                });
            }

            function loadTableWithFilter(table, page, predefinedFilters) {
                // Réinitialiser les champs de filtre
                $(`#${table}Filters .field input`).val('');

                // Appliquer les filtres prédéfinis
                const filters = predefinedFilters || {};
                for (const [key, value] of Object.entries(filters)) {
                    $(`#${table}Filters input[name="${key}"]`).val(value);
                }

                const perPage = $(`#${table}PerPage`).val();
                const sortColumn = sortStates[table].column || (table === 'logs' ? 'date' : 'path');
                const sortOrder = sortStates[table].order || 'ASC';

                $.ajax({
                    url: 'fetch_table.php',
                    method: 'POST',
                    data: { table, page, filters, sortColumn, sortOrder, perPage },
                    success: function(response) {
                        $(`#${table}Table`).html(response.table);
                        $(`#${table}Pagination`).html(response.pagination);
                        $(`#${table}Table th.sortable`).off('click').on('click', function() {
                            const column = $(this).data('column');
                            if (sortStates[table].column === column) {
                                sortStates[table].order = sortStates[table].order === 'ASC' ? 'DESC' : 'ASC';
                            } else {
                                sortStates[table] = { column: column, order: 'DESC' };
                            }
                            loadTable(table, 1);
                        });
                    },
                    error: function() {
                        $(`#${table}Table`).html('Erreur lors du chargement des données.');
                    }
                });
            }

            function bulkAction(table, action) {
                const selected = [];
                $(`#${table}Table .checkbox input[type=checkbox]:checked`).each(function() {
                    selected.push($(this).data('id'));
                });
                if (selected.length === 0) {
                    alert('Aucune entrée sélectionnée.');
                    return;
                }

                $.ajax({
                    url: 'manage_table.php',
                    method: 'POST',
                    data: { table, action, ids: selected },
                    success: function(response) {
                        alert(response.message);
                        loadTable(table, 1);
                    },
                    error: function(xhr, status, error) {
                        alert('Erreur lors de l’action : ' + error);
                    }
                });
            }

            function purgeTable(table) {
                if (confirm('Voulez-vous vraiment purger toute la table ' + table + ' ?')) {
                    $.ajax({
                        url: 'manage_table.php',
                        method: 'POST',
                        data: { table, action: 'purge' },
                        success: function(response) {
                            alert(response.message);
                            loadTable(table, 1);
                        },
                        error: function(xhr, status, error) {
                            alert('Erreur lors de la purge : ' + error);
                        }
                    });
                }
            }

            $(document).ready(function() {
                $('.ui.sidebar').sidebar({
                    transition: 'overlay',
                    mobileTransition: 'overlay'
                });
                $('.mobile-toggle').click(function() {
                    $('.ui.sidebar').sidebar('toggle');
                });

                showSection('download');
                setInterval(updateQueueStatus, 5000);
                setInterval(updateCurrentStatus, 5000);
                setInterval(updateStatusHistory, 5000);
                setInterval(updateDownloadHistory, 5000);
                setInterval(updateDownloads, 30000);
                //setInterval(updateCompletenessChart, 30000);
                //setInterval(updateGenreChart, 30000);
            });
        </script>
    </head>
    <body>
    <div class="ui sidebar vertical menu">
        <a class="item" href="javascript:void(0)" onclick="showSection('download')">Gestion de file</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('status')">Statuts & Historique</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('history')">Historique</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('smart-playlist')">Créer une playlist</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('logs')">Logs</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('tracks')">Tracks</a>
        <a class="item" href="javascript:void(0)" onclick="showSection('completeness')">Complétude</a>
        <a class="item" href="?logout">Déconnexion</a>
    </div>

    <div class="ui container pusher">
        <div class="ui top attached menu">
            <a class="mobile-toggle item" href="javascript:void(0)"><i class="bars icon"></i></a>
            <a class="item" href="javascript:void(0)" onclick="showSection('download')">Gestion de file</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('status')">Statuts & Historique</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('history')">Historique</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('smart-playlist')">Créer une playlist</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('logs')">Logs</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('tracks')">Tracks</a>
            <a class="item" href="javascript:void(0)" onclick="showSection('completeness')">Complétude</a>
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
            <textarea id="playlistPreview" class="ui segment output" style="width: 100%; min-height: 200px;">Aucune playlist générée pour le moment.</textarea>
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

        <div id="logs" class="section" style="display: none;">
            <h1 class="ui header">Gestion des logs</h1>
            <div id="logsFilters" class="ui form">
                <div class="fields">
                    <div class="field"><input type="text" name="date" placeholder="Filtrer par date"></div>
                    <div class="field"><input type="text" name="type" placeholder="Filtrer par type"></div>
                    <div class="field"><input type="text" name="level" placeholder="Filtrer par niveau"></div>
                    <div class="field"><input type="text" name="group" placeholder="Filtrer par groupe"></div>
                    <div class="field"><input type="text" name="message" placeholder="Filtrer par message"></div>
                </div>
                <div class="field">
                    <label>Par page</label>
                    <select id="logsPerPage">
                        <option value="10">10</option>
                        <option value="25">25</option>
                        <option value="50" selected>50</option>
                        <option value="100">100</option>
                    </select>
                </div>
                <button class="ui blue button" onclick="loadTable('logs', 1)">Appliquer</button>
            </div>
            <div class="ui segment">
                <button class="ui red button" onclick="purgeTable('logs')">Purger la table</button>
                <button class="ui orange button" onclick="bulkAction('logs', 'delete')">Supprimer sélection</button>
            </div>
            <div id="logsTable" class="ui segment output"></div>
            <div id="logsPagination" class="pagination"></div>
        </div>

        <div id="tracks" class="section" style="display: none;">
            <h1 class="ui header">Gestion des pistes</h1>
            <div id="tracksFilters" class="ui form">
                <div class="fields">
                    <div class="field"><input type="text" name="path" placeholder="Filtrer par chemin"></div>
                    <div class="field"><input type="text" name="title" placeholder="Filtrer par titre"></div>
                    <div class="field"><input type="text" name="artist" placeholder="Filtrer par artiste"></div>
                    <div class="field"><input type="text" name="album" placeholder="Filtrer par album"></div>
                    <div class="field"><input type="text" name="year" placeholder="Filtrer par année"></div>
                    <div class="field"><input type="text" name="genre" placeholder="Filtrer par genre"></div>
                    <div class="field"><input type="text" name="completeness" placeholder="Filtrer par complétude (ex: 0.5-0.74, <0.5, 1, NULL)"></div>
                </div>
                <div class="field">
                    <label>Par page</label>
                    <select id="tracksPerPage">
                        <option value="10">10</option>
                        <option value="25">25</option>
                        <option value="50" selected>50</option>
                        <option value="100">100</option>
                    </select>
                </div>
                <button class="ui blue button" onclick="loadTable('tracks', 1)">Appliquer</button>
            </div>
            <div class="ui segment">
                <button class="ui red button" onclick="purgeTable('tracks')">Purger la table</button>
                <button class="ui orange button" onclick="bulkAction('tracks', 'delete')">Supprimer sélection</button>
            </div>
            <div id="tracksTable" class="ui segment output"></div>
            <div id="tracksPagination" class="pagination"></div>
        </div>

        <div id="completeness" class="section" style="display: none;">
            <h1 class="ui header">Analyse de la complétude de la base de données</h1>
            <div class="ui segment">
                <div id="completenessChartContainer" style="max-width: 600px; margin: 0 auto;">
                    <canvas id="completenessChart"></canvas>
                </div>
                <div id="totalTracks" style="text-align: center; margin-top: 20px;"></div>
                <div id="genreChartContainer" style="max-width: 600px; margin: 20px auto;">
                    <canvas id="genreChart"></canvas>
                </div>
                <div id="totalGenres" style="text-align: center; margin-top: 20px;"></div>
            </div>
        </div>
    </div>
    </body>
    </html>
    <?php
    exit;
}