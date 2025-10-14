"""
Database - Zarządzanie bazą danych SQLite dla gier
AI-Friendly: Wszystkie operacje na bazie w jednym miejscu
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from utils.logger import get_logger


class Database:
    """
    Zarządza bazą danych SQLite dla launchera.
    
    AI Note: Tabele:
    - games: Lista gier
    - play_sessions: Sesje gry (tracking czasu)
    - achievements: Osiągnięcia użytkownika
    - roadmap: Planowane gry
    """
    
    def __init__(self, db_path="data/games.db"):
        """
        Inicjalizuje połączenie z bazą danych.
        
        Args:
            db_path (str): Ścieżka do pliku bazy danych
        """
        self.logger = get_logger()
        self.db_path = Path(db_path)
        
        # Upewnij się że folder istnieje
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Połącz z bazą i utwórz tabele
        self.conn = self._connect()
        self._create_tables()
        self.logger.info(f"Database initialized: {db_path}")
    
    def _connect(self):
        """
        Tworzy połączenie z bazą danych.
        
        Returns:
            sqlite3.Connection: Połączenie do bazy
        
        AI Note: Automatycznie konwertuje Row na dict
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Pozwala na dict-like access
        return conn
    
    def _create_tables(self):
        """
        Tworzy tabele w bazie danych jeśli nie istnieją.
        
        AI Note: Możesz dodać nowe tabele tutaj
        """
        cursor = self.conn.cursor()
        
        # Tabela gier
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exe_path TEXT,
                cover_path TEXT,
                platform TEXT DEFAULT 'PC',
                genre TEXT,
                release_date TEXT,
                added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                favorite INTEGER DEFAULT 0,
                total_playtime INTEGER DEFAULT 0,
                last_played TEXT,
                notes TEXT
            )
        """)
        
        # Tabela sesji gry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS play_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration INTEGER DEFAULT 0,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)
        
        # Tabela osiągnięć
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                unlocked INTEGER DEFAULT 0,
                unlock_date TEXT,
                icon_path TEXT,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)
        
        # Tabela roadmapy
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmap (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                planned_date TEXT,
                status TEXT DEFAULT 'planned',
                notes TEXT,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)
        
        self.conn.commit()
        self.logger.debug("Database tables created/verified")
    
    # ===== OPERACJE NA GRACH =====
    
    def add_game(self, name, exe_path=None, **kwargs):
        """
        Dodaje nową grę do bazy.
        
        Args:
            name (str): Nazwa gry
            exe_path (str): Ścieżka do exe
            **kwargs: Dodatkowe pola (cover_path, platform, genre, etc.)
        
        Returns:
            int: ID dodanej gry lub None
        
        AI Note: Użyj **kwargs dla elastyczności (np. genre="RPG")
        """
        try:
            cursor = self.conn.cursor()
            
            # Przygotuj dane
            data = {
                'name': name,
                'exe_path': exe_path,
                'added_date': datetime.now().isoformat()
            }
            data.update(kwargs)
            
            # Dynamiczne tworzenie query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            cursor.execute(
                f"INSERT INTO games ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
            self.conn.commit()
            
            game_id = cursor.lastrowid
            self.logger.info(f"Added game: {name} (ID: {game_id})")
            return game_id
            
        except Exception as e:
            self.logger.error(f"Failed to add game {name}: {e}")
            return None
    
    def get_all_games(self):
        """
        Pobiera wszystkie gry z bazy.
        
        Returns:
            list[dict]: Lista gier jako słowniki
        
        AI Note: Każda gra to dict z kluczami: id, name, exe_path, etc.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM games ORDER BY added_date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_game_by_id(self, game_id):
        """
        Pobiera grę po ID.
        
        Args:
            game_id (int): ID gry
        
        Returns:
            dict or None: Dane gry lub None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_game(self, game_id, **kwargs):
        """
        Aktualizuje dane gry.
        
        Args:
            game_id (int): ID gry
            **kwargs: Pola do aktualizacji
        
        Returns:
            bool: True jeśli sukces
        
        Examples:
            >>> db.update_game(1, name="New Name", genre="RPG")
        """
        if not kwargs:
            return False
        
        try:
            set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [game_id]
            
            cursor = self.conn.cursor()
            cursor.execute(
                f"UPDATE games SET {set_clause} WHERE id = ?",
                values
            )
            self.conn.commit()
            
            self.logger.info(f"Updated game ID {game_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update game {game_id}: {e}")
            return False
    
    def delete_game(self, game_id):
        """
        Usuwa grę z bazy (cascade: usuwa też sesje, osiągnięcia).
        
        Args:
            game_id (int): ID gry
        
        Returns:
            bool: True jeśli sukces
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
            self.conn.commit()
            
            self.logger.info(f"Deleted game ID {game_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete game {game_id}: {e}")
            return False
    
    # ===== OPERACJE NA SESJACH GRY =====
    
    def start_play_session(self, game_id):
        """
        Rozpoczyna nową sesję gry.
        
        Args:
            game_id (int): ID gry
        
        Returns:
            int: ID sesji lub None
        
        AI Note: Wywołaj gdy gra się uruchamia
        """
        try:
            cursor = self.conn.cursor()
            start_time = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO play_sessions (game_id, start_time) VALUES (?, ?)",
                (game_id, start_time)
            )
            self.conn.commit()
            
            session_id = cursor.lastrowid
            self.logger.info(f"Started play session {session_id} for game {game_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start session for game {game_id}: {e}")
            return None
    
    def end_play_session(self, session_id, duration):
        """
        Kończy sesję gry i aktualizuje czas.
        
        Args:
            session_id (int): ID sesji
            duration (int): Czas gry w sekundach
        
        Returns:
            bool: True jeśli sukces
        
        AI Note: Wywołaj gdy gra się zamyka
        """
        try:
            cursor = self.conn.cursor()
            end_time = datetime.now().isoformat()
            
            # Zakończ sesję
            cursor.execute(
                "UPDATE play_sessions SET end_time = ?, duration = ? WHERE id = ?",
                (end_time, duration, session_id)
            )
            
            # Pobierz game_id
            cursor.execute("SELECT game_id FROM play_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                game_id = row['game_id']
                
                # Aktualizuj total_playtime i last_played w games
                cursor.execute(
                    """UPDATE games 
                       SET total_playtime = total_playtime + ?,
                           last_played = ?
                       WHERE id = ?""",
                    (duration, end_time, game_id)
                )
            
            self.conn.commit()
            self.logger.info(f"Ended play session {session_id}, duration: {duration}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to end session {session_id}: {e}")
            return False
    
    def get_game_sessions(self, game_id):
        """
        Pobiera wszystkie sesje dla gry.
        
        Args:
            game_id (int): ID gry
        
        Returns:
            list[dict]: Lista sesji
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM play_sessions WHERE game_id = ? ORDER BY start_time DESC",
            (game_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self):
        """
        Zamyka połączenie z bazą danych.
        
        AI Note: Wywołaj przy zamykaniu aplikacji
        """
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")