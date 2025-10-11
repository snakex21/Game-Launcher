"""
HTML templates dla web chat client
Prosty interfejs webowy do czatu (opcjonalny).
"""

# Prosty HTML template dla web klienta czatu
CHAT_CLIENT_HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Game Launcher Chat</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1e1e1e;
            color: #ffffff;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        #login-screen {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        #login-box {
            background: #2d2d2d;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        #login-box h1 {
            margin-bottom: 20px;
            text-align: center;
        }
        
        #login-box input {
            width: 300px;
            padding: 12px;
            margin-bottom: 15px;
            border: none;
            border-radius: 5px;
            background: #3d3d3d;
            color: white;
            font-size: 16px;
        }
        
        #login-box button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 5px;
            background: #667eea;
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        #login-box button:hover {
            background: #5568d3;
        }
        
        #chat-screen {
            display: none;
            height: 100vh;
            flex-direction: column;
        }
        
        #header {
            background: #2d2d2d;
            padding: 15px 20px;
            border-bottom: 2px solid #667eea;
        }
        
        #header h1 {
            font-size: 24px;
            color: #667eea;
        }
        
        #main-container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        
        #users-sidebar {
            width: 250px;
            background: #2d2d2d;
            border-right: 1px solid #3d3d3d;
            padding: 20px;
            overflow-y: auto;
        }
        
        #users-sidebar h2 {
            margin-bottom: 15px;
            font-size: 18px;
            color: #667eea;
        }
        
        .user-item {
            padding: 10px;
            margin-bottom: 8px;
            background: #3d3d3d;
            border-radius: 5px;
            display: flex;
            align-items: center;
        }
        
        .user-status {
            width: 10px;
            height: 10px;
            background: #4caf50;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        #chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        #messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #1e1e1e;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px;
            background: #2d2d2d;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }
        
        .message.system {
            background: #3d3d3d;
            border-left-color: #ffa500;
        }
        
        .message-username {
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        
        .message-text {
            color: #e0e0e0;
            line-height: 1.4;
        }
        
        .message-timestamp {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }
        
        #input-container {
            padding: 20px;
            background: #2d2d2d;
            border-top: 1px solid #3d3d3d;
        }
        
        #message-form {
            display: flex;
            gap: 10px;
        }
        
        #message-input {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            background: #3d3d3d;
            color: white;
            font-size: 16px;
        }
        
        #send-button {
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            background: #667eea;
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        #send-button:hover {
            background: #5568d3;
        }
        
        #typing-indicator {
            padding: 10px 20px;
            color: #888;
            font-style: italic;
            min-height: 30px;
        }
    </style>
</head>
<body>
    <div id="login-screen">
        <div id="login-box">
            <h1>🎮 Game Launcher Chat</h1>
            <input type="text" id="username-input" placeholder="Wpisz swoją nazwę..." autofocus>
            <button onclick="login()">Dołącz do czatu</button>
        </div>
    </div>
    
    <div id="chat-screen">
        <div id="header">
            <h1>🎮 Game Launcher Chat</h1>
            <span id="user-info"></span>
        </div>
        
        <div id="main-container">
            <div id="users-sidebar">
                <h2>Online (<span id="user-count">0</span>)</h2>
                <div id="users-list"></div>
            </div>
            
            <div id="chat-container">
                <div id="messages"></div>
                <div id="typing-indicator"></div>
                <div id="input-container">
                    <form id="message-form">
                        <input type="text" id="message-input" placeholder="Wpisz wiadomość..." autocomplete="off">
                        <button type="submit" id="send-button">Wyślij</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        let currentUsername = '';
        let typingTimeout = null;
        
        // Logowanie
        function login() {
            const username = document.getElementById('username-input').value.trim();
            if (!username) return;
            
            currentUsername = username;
            socket.emit('login', { username: username });
            
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('chat-screen').style.display = 'flex';
            document.getElementById('user-info').textContent = `Zalogowany jako: ${username}`;
            document.getElementById('message-input').focus();
        }
        
        // Enter w polu login
        document.getElementById('username-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') login();
        });
        
        // Wysyłanie wiadomości
        document.getElementById('message-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (message) {
                socket.emit('message', { message: message });
                input.value = '';
            }
        });
        
        // Typing indicator
        document.getElementById('message-input').addEventListener('input', () => {
            socket.emit('typing', { typing: true });
            
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                socket.emit('typing', { typing: false });
            }, 1000);
        });
        
        // Socket handlers
        socket.on('login_success', (data) => {
            addSystemMessage(`Witaj, ${data.username}!`);
        });
        
        socket.on('user_list', (data) => {
            updateUsersList(data.users);
        });
        
        socket.on('message_history', (data) => {
            data.messages.forEach(msg => addMessage(msg));
        });
        
        socket.on('new_message', (data) => {
            addMessage(data);
        });
        
        socket.on('user_connected', (data) => {
            addSystemMessage(`${data.username} dołączył do czatu`);
        });
        
        socket.on('user_disconnected', (data) => {
            addSystemMessage(`${data.username} opuścił czat`);
        });
        
        socket.on('user_typing', (data) => {
            const indicator = document.getElementById('typing-indicator');
            if (data.typing) {
                indicator.textContent = `${data.username} pisze...`;
            } else {
                indicator.textContent = '';
            }
        });
        
        // Funkcje pomocnicze
        function addMessage(msg) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message' + (msg.system ? ' system' : '');
            
            const timestamp = new Date(msg.timestamp).toLocaleTimeString();
            
            messageDiv.innerHTML = `
                <div class="message-username">${msg.username}</div>
                <div class="message-text">${escapeHtml(msg.message)}</div>
                <div class="message-timestamp">${timestamp}</div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function addSystemMessage(text) {
            addMessage({
                username: 'System',
                message: text,
                timestamp: new Date().toISOString(),
                system: true
            });
        }
        
        function updateUsersList(users) {
            const usersList = document.getElementById('users-list');
            const userCount = document.getElementById('user-count');
            
            usersList.innerHTML = '';
            userCount.textContent = users.length;
            
            users.forEach(user => {
                const userDiv = document.createElement('div');
                userDiv.className = 'user-item';
                userDiv.innerHTML = `
                    <div class="user-status"></div>
                    <div>${escapeHtml(user.username)}</div>
                `;
                usersList.appendChild(userDiv);
            });
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""


def get_chat_client_html():
    """
    Zwraca HTML template dla web klienta.
    
    Returns:
        HTML jako string
    """
    return CHAT_CLIENT_HTML
