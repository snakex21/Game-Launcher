"""
Chat Server - Prosty serwer czatu Flask + SocketIO
AI-Friendly: Real-time chat dla lokalnej sieci
"""

import threading
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from utils.logger import get_logger


class ChatServer:
    """
    Prosty serwer czatu HTTP + WebSocket.
    
    AI Note:
    - Flask + SocketIO
    - Działa w osobnym wątku
    - Real-time messaging
    """
    
    def __init__(self, port=5000):
        """
        Inicjalizuje serwer czatu.
        
        Args:
            port (int): Port serwera (domyślnie 5000)
        """
        self.logger = get_logger()
        self.port = port
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'game_launcher_chat_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self.is_running = False
        self.server_thread = None
        
        # Setup routes
        self._setup_routes()
        self._setup_socket_handlers()
    
    def _setup_routes(self):
        """Konfiguruje Flask routes."""
        
        @self.app.route('/')
        def index():
            """Główna strona czatu."""
            return render_template_string(CHAT_HTML_TEMPLATE)
    
    def _setup_socket_handlers(self):
        """Konfiguruje Socket.IO event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Nowe połączenie."""
            self.logger.info("Client connected to chat")
            emit('message', {
                'user': 'System',
                'text': 'Witaj w czacie!',
                'timestamp': self._get_timestamp()
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Rozłączenie."""
            self.logger.info("Client disconnected from chat")
        
        @self.socketio.on('send_message')
        def handle_message(data):
            """Nowa wiadomość."""
            username = data.get('user', 'Anonymous')
            text = data.get('text', '')
            
            self.logger.info(f"Chat message from {username}: {text}")
            
            # Broadcast do wszystkich
            emit('message', {
                'user': username,
                'text': text,
                'timestamp': self._get_timestamp()
            }, broadcast=True)
    
    def start(self):
        """
        Startuje serwer czatu w osobnym wątku.
        
        Returns:
            bool: True jeśli sukces
        
        AI Note: Serwer działa w tle, nie blokuje GUI
        """
        if self.is_running:
            self.logger.warning("Chat server already running")
            return False
        
        try:
            self.is_running = True
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            
            self.logger.info(f"Chat server started on port {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start chat server: {e}")
            self.is_running = False
            return False
    
    def _run_server(self):
        """Uruchamia serwer Flask+SocketIO."""
        try:
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=self.port,
                debug=False,
                use_reloader=False,
                log_output=False
            )
        except Exception as e:
            self.logger.error(f"Chat server error: {e}")
            self.is_running = False
    
    def stop(self):
        """
        Zatrzymuje serwer czatu.
        
        AI Note: Wywołaj przy zamykaniu aplikacji
        """
        if self.is_running:
            self.is_running = False
            # Flask nie ma łatwego sposobu na shutdown, więc daemon thread się zamknie
            self.logger.info("Chat server stopped")
    
    def _get_timestamp(self):
        """Zwraca aktualny timestamp."""
        from datetime import datetime
        return datetime.now().strftime('%H:%M:%S')
    
    def get_server_url(self):
        """
        Zwraca URL serwera czatu.
        
        Returns:
            str: URL (np. http://localhost:5000)
        """
        return f"http://localhost:{self.port}"


# HTML Template dla czatu
CHAT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Game Launcher Chat</title>
    <meta charset="utf-8">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            background: #2c3e50;
            color: #ecf0f1;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        #header {
            background: #1a252f;
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid #3498db;
        }
        
        h1 {
            color: #3498db;
        }
        
        #messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #34495e;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 10px;
            background: #2c3e50;
            border-radius: 5px;
            border-left: 3px solid #3498db;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 12px;
            color: #95a5a6;
        }
        
        .message-user {
            font-weight: bold;
            color: #3498db;
        }
        
        .message-text {
            color: #ecf0f1;
        }
        
        .system-message {
            border-left-color: #95a5a6;
            font-style: italic;
        }
        
        #input-area {
            background: #1a252f;
            padding: 20px;
            display: flex;
            gap: 10px;
            border-top: 2px solid #3498db;
        }
        
        #username-input {
            width: 150px;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: #34495e;
            color: #ecf0f1;
        }
        
        #message-input {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: #34495e;
            color: #ecf0f1;
        }
        
        #send-button {
            padding: 10px 30px;
            border: none;
            border-radius: 5px;
            background: #3498db;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        #send-button:hover {
            background: #2980b9;
        }
        
        input::placeholder {
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div id="header">
        <h1>🎮 Game Launcher Chat</h1>
        <p>Czat dla graczy w lokalnej sieci</p>
    </div>
    
    <div id="messages"></div>
    
    <div id="input-area">
        <input type="text" id="username-input" placeholder="Twoja nazwa..." value="Gracz">
        <input type="text" id="message-input" placeholder="Wpisz wiadomość...">
        <button id="send-button" onclick="sendMessage()">Wyślij</button>
    </div>
    
    <script>
        const socket = io();
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('message-input');
        const usernameInput = document.getElementById('username-input');
        
        // Odbieranie wiadomości
        socket.on('message', function(data) {
            addMessage(data);
        });
        
        // Dodawanie wiadomości do UI
        function addMessage(data) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            if (data.user === 'System') {
                messageDiv.className += ' system-message';
            }
            
            messageDiv.innerHTML = `
                <div class="message-header">
                    <span class="message-user">${escapeHtml(data.user)}</span>
                    <span class="message-timestamp">${data.timestamp}</span>
                </div>
                <div class="message-text">${escapeHtml(data.text)}</div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        // Wysyłanie wiadomości
        function sendMessage() {
            const text = messageInput.value.trim();
            const username = usernameInput.value.trim() || 'Anonymous';
            
            if (text === '') return;
            
            socket.emit('send_message', {
                user: username,
                text: text
            });
            
            messageInput.value = '';
        }
        
        // Enter do wysłania
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Escape HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""