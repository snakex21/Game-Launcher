"""
Serwer czatu Flask + Socket.IO
Obsługuje real-time komunikację między użytkownikami.
"""

import logging
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import uuid

from config.constants import CHAT_SERVER_HOST, CHAT_SERVER_PORT

logger = logging.getLogger(__name__)


class ChatServer:
    """
    Serwer czatu z Flask i Socket.IO.
    Obsługuje wieloużytkownikowy czat w czasie rzeczywistym.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje serwer czatu.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        self.app: Optional[Flask] = None
        self.socketio: Optional[SocketIO] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running: bool = False
        
        # Dane użytkowników online {session_id: user_data}
        self.online_users: Dict[str, Dict[str, Any]] = {}
        
        # Historia wiadomości (ostatnie 100)
        self.message_history: List[Dict[str, Any]] = []
        self.max_history: int = 100
        
        # Pokoje czatu {room_id: room_data}
        self.chat_rooms: Dict[str, Dict[str, Any]] = {
            'general': {
                'name': 'Ogólny',
                'description': 'Główny pokój czatu',
                'created_at': datetime.now().isoformat(),
                'users': []
            }
        }
        
        logger.debug("ChatServer zainicjalizowany")
    
    def create_app(self) -> Flask:
        """
        Tworzy aplikację Flask.
        
        Returns:
            Instancja Flask app
        """
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'game-launcher-secret-key-change-in-production'
        
        # Import i rejestracja API routes
        from .api import create_api_routes
        create_api_routes(app, self)
        
        return app
    
    def start(self, host: str = CHAT_SERVER_HOST, port: int = CHAT_SERVER_PORT) -> bool:
        """
        Uruchamia serwer czatu w osobnym wątku.
        
        Args:
            host: Host serwera
            port: Port serwera
            
        Returns:
            True jeśli uruchomiono pomyślnie
        """
        try:
            if self.running:
                logger.warning("Serwer czatu już działa")
                return True
            
            # Utwórz Flask app
            self.app = self.create_app()
            
            # Utwórz Socket.IO
            self.socketio = SocketIO(
                self.app,
                cors_allowed_origins="*",
                async_mode='threading'
            )
            
            # Zarejestruj handlery Socket.IO
            self._register_socketio_handlers()
            
            # Uruchom w osobnym wątku
            self.running = True
            self.server_thread = threading.Thread(
                target=self._run_server,
                args=(host, port),
                daemon=True
            )
            self.server_thread.start()
            
            logger.info(f"Serwer czatu uruchomiony na {host}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd uruchamiania serwera czatu: {e}")
            self.running = False
            return False
    
    def _run_server(self, host: str, port: int):
        """
        Uruchamia serwer Flask+SocketIO.
        
        Args:
            host: Host serwera
            port: Port serwera
        """
        try:
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            logger.error(f"Błąd w serwerze czatu: {e}")
            self.running = False
    
    def stop(self):
        """Zatrzymuje serwer czatu."""
        try:
            self.running = False
            
            # Socket.IO nie ma prostego sposobu na zatrzymanie
            # Serwer zatrzyma się gdy główna aplikacja się zamknie
            
            logger.info("Serwer czatu zatrzymany")
            
        except Exception as e:
            logger.error(f"Błąd zatrzymywania serwera czatu: {e}")
    
    def _register_socketio_handlers(self):
        """Rejestruje handlery Socket.IO."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Obsługuje połączenie klienta."""
            session_id = request.sid
            logger.info(f"Klient połączony: {session_id}")
            
            # Wyślij aktualną listę użytkowników
            emit('user_list', {'users': list(self.online_users.values())})
            
            # Wyślij historię wiadomości
            emit('message_history', {'messages': self.message_history})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Obsługuje rozłączenie klienta."""
            session_id = request.sid
            
            # Usuń użytkownika z listy online
            if session_id in self.online_users:
                user = self.online_users[session_id]
                username = user.get('username', 'Nieznany')
                
                del self.online_users[session_id]
                
                # Powiadom innych o rozłączeniu
                emit('user_disconnected', {
                    'username': username,
                    'timestamp': datetime.now().isoformat()
                }, broadcast=True)
                
                # Zaktualizuj listę użytkowników
                emit('user_list', {'users': list(self.online_users.values())}, broadcast=True)
                
                logger.info(f"Klient rozłączony: {username} ({session_id})")
        
        @self.socketio.on('login')
        def handle_login(data):
            """Obsługuje logowanie użytkownika."""
            session_id = request.sid
            username = data.get('username', 'Gość')
            
            # Dodaj użytkownika do listy online
            user_data = {
                'session_id': session_id,
                'username': username,
                'connected_at': datetime.now().isoformat()
            }
            
            self.online_users[session_id] = user_data
            
            # Powiadom innych o nowym użytkowniku
            emit('user_connected', user_data, broadcast=True, include_self=False)
            
            # Zaktualizuj listę użytkowników dla wszystkich
            emit('user_list', {'users': list(self.online_users.values())}, broadcast=True)
            
            # Potwierdź logowanie
            emit('login_success', {'username': username})
            
            logger.info(f"Użytkownik zalogowany: {username} ({session_id})")
        
        @self.socketio.on('message')
        def handle_message(data):
            """Obsługuje wiadomość od użytkownika."""
            session_id = request.sid
            
            # Sprawdź czy użytkownik jest zalogowany
            if session_id not in self.online_users:
                emit('error', {'message': 'Nie jesteś zalogowany'})
                return
            
            user = self.online_users[session_id]
            username = user.get('username', 'Nieznany')
            message_text = data.get('message', '').strip()
            
            if not message_text:
                return
            
            # Utwórz wiadomość
            message = {
                'id': str(uuid.uuid4()),
                'username': username,
                'message': message_text,
                'timestamp': datetime.now().isoformat(),
                'room': data.get('room', 'general')
            }
            
            # Dodaj do historii
            self.message_history.append(message)
            
            # Ogranicz historię
            if len(self.message_history) > self.max_history:
                self.message_history = self.message_history[-self.max_history:]
            
            # Rozgłoś wiadomość
            emit('new_message', message, broadcast=True)
            
            logger.debug(f"Wiadomość od {username}: {message_text[:50]}")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """Obsługuje dołączenie do pokoju."""
            session_id = request.sid
            room_id = data.get('room', 'general')
            
            if session_id not in self.online_users:
                emit('error', {'message': 'Nie jesteś zalogowany'})
                return
            
            user = self.online_users[session_id]
            username = user.get('username', 'Nieznany')
            
            # Dołącz do pokoju Socket.IO
            join_room(room_id)
            
            # Dodaj do listy użytkowników pokoju
            if room_id in self.chat_rooms:
                if username not in self.chat_rooms[room_id]['users']:
                    self.chat_rooms[room_id]['users'].append(username)
            
            # Powiadom pokój
            emit('user_joined_room', {
                'username': username,
                'room': room_id,
                'timestamp': datetime.now().isoformat()
            }, room=room_id)
            
            logger.info(f"{username} dołączył do pokoju: {room_id}")
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """Obsługuje opuszczenie pokoju."""
            session_id = request.sid
            room_id = data.get('room', 'general')
            
            if session_id not in self.online_users:
                return
            
            user = self.online_users[session_id]
            username = user.get('username', 'Nieznany')
            
            # Opuść pokój Socket.IO
            leave_room(room_id)
            
            # Usuń z listy użytkowników pokoju
            if room_id in self.chat_rooms:
                if username in self.chat_rooms[room_id]['users']:
                    self.chat_rooms[room_id]['users'].remove(username)
            
            # Powiadom pokój
            emit('user_left_room', {
                'username': username,
                'room': room_id,
                'timestamp': datetime.now().isoformat()
            }, room=room_id)
            
            logger.info(f"{username} opuścił pokój: {room_id}")
        
        @self.socketio.on('typing')
        def handle_typing(data):
            """Obsługuje status 'pisze...'."""
            session_id = request.sid
            
            if session_id not in self.online_users:
                return
            
            user = self.online_users[session_id]
            username = user.get('username', 'Nieznany')
            is_typing = data.get('typing', False)
            room_id = data.get('room', 'general')
            
            # Rozgłoś status pisania
            emit('user_typing', {
                'username': username,
                'typing': is_typing,
                'room': room_id
            }, room=room_id, include_self=False)
    
    def get_online_users(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę użytkowników online.
        
        Returns:
            Lista użytkowników
        """
        return list(self.online_users.values())
    
    def get_message_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Zwraca historię wiadomości.
        
        Args:
            limit: Maksymalna liczba wiadomości
            
        Returns:
            Lista wiadomości
        """
        return self.message_history[-limit:]
    
    def broadcast_message(self, message: str, username: str = "System"):
        """
        Wysyła wiadomość systemową do wszystkich.
        
        Args:
            message: Treść wiadomości
            username: Nazwa nadawcy (domyślnie "System")
        """
        try:
            if not self.socketio:
                return
            
            message_data = {
                'id': str(uuid.uuid4()),
                'username': username,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'system': True
            }
            
            self.message_history.append(message_data)
            self.socketio.emit('new_message', message_data)
            
            logger.debug(f"Broadcast: {message}")
            
        except Exception as e:
            logger.error(f"Błąd broadcast: {e}")
    
    def is_running(self) -> bool:
        """
        Sprawdza czy serwer działa.
        
        Returns:
            True jeśli działa
        """
        return self.running
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Zwraca statystyki serwera.
        
        Returns:
            Słownik ze statystykami
        """
        return {
            'online_users': len(self.online_users),
            'total_messages': len(self.message_history),
            'rooms': len(self.chat_rooms),
            'running': self.running
        }
    
    def cleanup(self):
        """Czyści zasoby serwera czatu."""
        try:
            self.stop()
            self.online_users.clear()
            self.message_history.clear()
            logger.info("ChatServer oczyszczony")
        except Exception as e:
            logger.error(f"Błąd czyszczenia ChatServer: {e}")
