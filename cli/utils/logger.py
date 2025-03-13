# utils/logger.py
import sqlite3
import datetime
import time

class Logger:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        self._create_logs_table()

    def _create_logs_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            level TEXT,
            "group" TEXT,
            message TEXT
        )''')
        self.conn.commit()

    def log(self, type_, level, group, message, retries=5, delay=0.1):
        date = datetime.datetime.now().isoformat()
        for attempt in range(retries):
            try:
                self.cursor.execute(
                    "INSERT INTO logs (date, type, level, \"group\", message) VALUES (?, ?, ?, ?, ?)",
                    (date, type_, level, group, message)
                )
                self.conn.commit()
                return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retries - 1:
                    time.sleep(delay)
                    continue
                else:
                    print(f"Erreur lors de la journalisation après {retries} tentatives : {e}")
                    self.conn.rollback()
                    raise