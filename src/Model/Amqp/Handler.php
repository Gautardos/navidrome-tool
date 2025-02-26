<?php
namespace Model\Amqp;

use Model\ConfigReader;
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Channel\AMQPChannel;
use PhpAmqpLib\Message\AMQPMessage;

class Handler
{
    private $connection;
    private $channel;
    private $config;

    public function __construct()
    {
        try {
            $this->config = new ConfigReader(__DIR__ . '/../etc/config.json');
            $rabbitConfig = $this->config->getRabbitMQConfig();

            // Définir des valeurs par défaut si les clés sont absentes
            $host = $rabbitConfig['host'] ?? 'localhost';
            $port = $rabbitConfig['port'] ?? 5672;
            $username = $rabbitConfig['username'] ?? 'guest';
            $password = $rabbitConfig['password'] ?? 'guest';
            $virtualHost = $rabbitConfig['virtual_host'] ?? '/';

            $this->connection = new AMQPStreamConnection(
                $host,
                $port,
                $username,
                $password,
                $virtualHost
            );
            $this->channel = $this->connection->channel();
        } catch (Exception $e) {
            throw new Exception("Erreur lors de l'initialisation de RabbitMQ : " . $e->getMessage());
        }
    }

    public function sendMessage(string $queue, array $data): void
    {
        // Déclarer la file avec durable=true pour cohérence
        $this->channel->queue_declare($queue, false, true, false, false);

        $messageBody = json_encode($data);
        $message = new AMQPMessage($messageBody, ['delivery_mode' => AMQPMessage::DELIVERY_MODE_PERSISTENT]);

        $this->channel->basic_publish($message, '', $queue);
    }

    public function purgeQueue(string $queue): ?string
    {
        // Déclarer la file avec durable=true pour cohérence
        $this->channel->queue_declare($queue, false, true, false, false);
        $message = $this->channel->basic_get($queue, true); // Retire et supprime le message
        return $message ? $message->getBody() : null;
    }

    public function getQueueInfo(string $queue): array
    {
        // Vérifier les informations sans redéclarer la file inutilement
        $queueInfo = $this->channel->queue_declare($queue, false, true, false, false); // passive=true pour ne pas modifier
        return [
            'message_count' => $queueInfo[1], // Nombre de messages
            'consumer_count' => $queueInfo[2] // Nombre de consommateurs
        ];
    }

    public function handleAuth(string $username, string $password): void
    {
        $data = ['action' => 'auth', 'username' => $username, 'password' => $password, 'timestamp' => date('Y-m-d H:i:s')];
        $this->sendMessage('auth_queue', $data);
    }

    public function handleLog(string $filePath, string $content): void
    {
        // Vérifier si le fichier existe ou peut être créé
        if (!file_exists($filePath)) {
            $dir = dirname($filePath);
            if (!is_dir($dir) && !mkdir($dir, 0755, true)) {
                $content = "Erreur : Impossible de créer le dossier $dir";
            } elseif (!is_writable($dir)) {
                $content = "Erreur : Pas de permissions d'écriture dans $dir";
            } else {
                touch($filePath); // Créer le fichier s'il n'existe pas
            }
        } elseif (!is_writable($filePath)) {
            $content = "Erreur : Pas de permissions d'écriture sur $filePath";
        }

        $data = ['action' => 'log', 'file' => $filePath, 'content' => $content, 'timestamp' => date('Y-m-d H:i:s')];
        $this->sendMessage('log_queue', $data);
    }

    public function handleLogout(): void
    {
        $data = ['action' => 'logout', 'timestamp' => date('Y-m-d H:i:s')];
        $this->sendMessage('logout_queue', $data);
    }

    public function __destruct()
    {
        if ($this->channel) {
            $this->channel->close();
        }
        if ($this->connection) {
            $this->connection->close();
        }
    }
}