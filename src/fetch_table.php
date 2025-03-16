<?php
header('Content-Type: application/json');

require __DIR__ . '/vendor/autoload.php';

use Model\Logger;

try {
    $logger = new Logger();
    $conn = $logger->getConnection();

    $table = $_POST['table'] ?? '';
    $page = (int)($_POST['page'] ?? 1);
    $perPage = (int)($_POST['perPage'] ?? 10);
    $filters = $_POST['filters'] ?? [];
    $sortColumn = $_POST['sortColumn'] ?? ($table === 'logs' ? 'date' : 'path');
    $sortOrder = strtoupper($_POST['sortOrder'] ?? 'ASC');

    if (!in_array($table, ['logs', 'tracks'])) {
        throw new Exception("Tableau invalide.");
    }

    $validColumns = [
        'logs' => ['id', 'date', 'type', 'level', 'group', 'message'],
        'tracks' => ['id', 'path', 'updated_at', 'title', 'album', 'artist', 'album_artist', 'year', 'genre', 'has_image', 'lyrics_type', 'completeness']
    ];

    // Fonction pour entourer les noms de colonnes avec des guillemets
    $escapeColumn = function($column) {
        return '"' . str_replace('"', '""', $column) . '"';
    };

    // Construction de la clause WHERE avec gestion spéciale pour completeness
    $whereClauses = [];
    $bindValues = [];
    foreach ($filters as $column => $value) {
        if (in_array($column, $validColumns[$table])) {
            if ($column === 'completeness' && $table === 'tracks') {
                if ($value === 'NULL') {
                    $whereClauses[] = $escapeColumn($column) . " IS NULL";
                } elseif ($value === '1') {
                    $whereClauses[] = $escapeColumn($column) . " = :completeness";
                    $bindValues[':completeness'] = 1;
                } elseif ($value === '<0.5') {
                    $whereClauses[] = $escapeColumn($column) . " < 0.5 AND " . $escapeColumn($column) . " IS NOT NULL";
                } elseif (preg_match('/^(\d*\.?\d+)-(\d*\.?\d+)$/', $value, $matches)) {
                    // Plage de valeurs (ex: 0.5-0.74)
                    $min = floatval($matches[1]);
                    $max = floatval($matches[2]);
                    $whereClauses[] = $escapeColumn($column) . " BETWEEN :completeness_min AND :completeness_max";
                    $bindValues[':completeness_min'] = $min;
                    $bindValues[':completeness_max'] = $max;
                }
            } else {
                $whereClauses[] = $escapeColumn($column) . " LIKE :$column";
                $bindValues[":$column"] = "%$value%";
            }
        }
    }
    $whereSql = !empty($whereClauses) ? 'WHERE ' . implode(' AND ', $whereClauses) : '';

    // Construction de la clause ORDER BY avec guillemets
    $orderSql = in_array($sortColumn, $validColumns[$table]) ? "ORDER BY " . $escapeColumn($sortColumn) . " $sortOrder" : '';

    if (!$logger->isWritable()) {
        $html = '<div class="ui warning message">La base de données est en lecture seule. Les données peuvent être affichées, mais les modifications ne sont pas possibles.</div>';
    } else {
        $html = '';
    }

    if ($conn === null) {
        throw new Exception("Connexion à la base de données non disponible.");
    }

    $countStmt = $conn->prepare("SELECT COUNT(*) FROM $table $whereSql");
    foreach ($bindValues as $key => $value) {
        $countStmt->bindValue($key, $value);
    }
    $countStmt->execute();
    $totalRows = $countStmt->fetchColumn();
    $totalPages = ceil($totalRows / $perPage);

    $offset = ($page - 1) * $perPage;
    $stmt = $conn->prepare("SELECT * FROM $table $whereSql $orderSql LIMIT :offset, :perPage");
    foreach ($bindValues as $key => $value) {
        $stmt->bindValue($key, $value);
    }
    $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stmt->bindValue(':perPage', $perPage, PDO::PARAM_INT);
    $stmt->execute();
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $html = '<table class="ui celled table"><thead><tr><th><input type="checkbox" onclick="$(\'#'.$table.'Table .checkbox input[type=checkbox]\').prop(\'checked\', this.checked);"></th>';
    foreach ($validColumns[$table] as $col) {
        if ($col !== 'id') {
            $thClass = in_array($col, ['date', 'type', 'level', 'group', 'message', 'path', 'updated_at', 'title', 'album', 'artist', 'album_artist', 'year', 'genre', 'has_image', 'lyrics_type', 'completeness']) ? 'sortable' : '';
            $arrow = ($sortColumn === $col) ? ($sortOrder === 'ASC' ? ' ↑' : ' ↓') : '';
            $html .= "<th class=\"$thClass\" data-column=\"$col\">" . ucfirst($col) . $arrow . "</th>";
        }
    }
    $html .= '</tr></thead><tbody>';
    foreach ($rows as $row) {
        $id = $row['id'];
        $html .= '<tr>';
        $html .= '<td><div class="ui checkbox"><input type="checkbox" class="checkbox" data-id="' . htmlspecialchars($id) . '"></div></td>';
        foreach ($validColumns[$table] as $col) {
            if ($col !== 'id') {
                $value = $row[$col] ?? '';
                $html .= '<td>' . htmlspecialchars($value) . '</td>';
            }
        }
        $html .= '</tr>';
    }
    $html .= '</tbody></table>';

    $pagination = '<div class="ui pagination menu">';
    for ($i = 1; $i <= $totalPages; $i++) {
        $active = $i === $page ? 'active' : '';
        $pagination .= "<a class=\"item $active\" href=\"javascript:void(0)\" onclick=\"loadTable('$table', $i)\">$i</a>";
    }
    $pagination .= '</div>';

    echo json_encode(['table' => $html, 'pagination' => $pagination]);
} catch (Exception $e) {
    $logger->log('fetch', 'error', 'table', 'Erreur lors du chargement des données : ' . $e->getMessage());
    echo json_encode(['table' => 'Erreur : ' . $e->getMessage(), 'pagination' => '']);
}