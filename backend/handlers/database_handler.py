# backend/handlers/database_handler.py

import sqlite3
from utils.logging_config import log_message

class DatabaseHandler:
    def __init__(self, db_path):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Initializes the SQLite database and table."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_text TEXT,
                sayo_text TEXT
            )
            """)
            conn.commit()
        except sqlite3.Error as e:
            log_message(f"Database error on initialization: {e}")
        finally:
            if conn:
                conn.close()
        log_message(f"Database initialized at {self.db_path}")

    def log_conversation(self, user_text, sayo_text):
        """Logs a single user-sayo interaction to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_logs (user_text, sayo_text) VALUES (?, ?)",
                (user_text, sayo_text)
            )
            conn.commit()
            log_message("Conversation logged.")
        except sqlite3.Error as e:
            log_message(f"Database error on logging: {e}")
        finally:
            if conn:
                conn.close()
