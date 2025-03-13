<?php
namespace Model;

class Logger {
    private $dbPath;
    private $conn;
    private $isWritable = true;

    public function __construct($dbPath = '/home/gautard/spotdl-web/db/database.db') {
        $this->dbPath = $dbPath;
        $this->connect();
    }

    private function connect() {
        try {
            if (!file_exists($this->dbPath)) {
                // Créer le fichier s'il n'existe pas
                touch($this->dbPath);
            }

            // Vérifier si le fichier est accessible en écriture
            if (!is_writable($this->dbPath)) {
                error_log("La base de données {$this->dbPath} est en lecture seule.");
                $this->isWritable = false;
                return;
            }

            $this->conn = new \PDO("sqlite:{$this->dbPath}");
            $this->conn->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);
            $this->initDatabase();
        } catch (\PDOException $e) {
            error_log("Erreur de connexion à la base de données : " . $e->getMessage());
            $this->isWritable = false;
        }
    }

    private function initDatabase() {
        if (!$this->isWritable) {
            return;
        }

        try {
            // Ajout d'une colonne id auto-incrémentée comme clé primaire
            $this->conn->exec('CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                type TEXT,
                level TEXT,
                "group" TEXT,
                message TEXT
            )');
            $this->conn->exec('CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT,
                updated_at TEXT,
                title TEXT,
                album TEXT,
                artist TEXT,
                album_artist TEXT,
                year INTEGER,
                genre TEXT,
                has_image INTEGER,
                lyrics_type TEXT,
                completeness REAL
            )');
        } catch (\PDOException $e) {
            error_log("Erreur lors de l'initialisation de la base de données : " . $e->getMessage());
            $this->isWritable = false;
        }
    }

    public function log($type, $level, $group, $message) {
        if (!$this->isWritable) {
            error_log("Impossible d'écrire dans la base de données : log non enregistré - $type, $level, $group, $message");
            return;
        }

        try {
            $date = date('c'); // Format ISO 8601
            $stmt = $this->conn->prepare("INSERT INTO logs (date, type, level, \"group\", message) VALUES (?, ?, ?, ?, ?)");
            $stmt->execute([$date, $type, $level, $group, $message]);
        } catch (\PDOException $e) {
            error_log("Erreur lors de l'écriture du log : " . $e->getMessage());
        }
    }

    public function getConnection() {
        return $this->conn;
    }

    public function isWritable() {
        return $this->isWritable;
    }

    public function __destruct() {
        $this->conn = null; // Ferme la connexion
    }
}