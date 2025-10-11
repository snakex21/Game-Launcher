# Chat Server

Serwer czatu Flask + Socket.IO dla Game Launcher.

## 🚀 Uruchamianie

```python
from server import ChatServer

# W main.py lub core/launcher.py
chat_server = ChatServer(launcher_instance=self)
chat_server.start(host='0.0.0.0', port=5000)
```

## 🌐 Endpointy

### HTTP REST API

- `GET /` - Informacje o serwerze
- `GET /chat` - Webowy klient czatu
- `GET /api/health` - Health check
- `GET /api/stats` - Statystyki serwera
- `GET /api/users` - Lista użytkowników online
- `GET /api/messages?limit=50` - Historia wiadomości
- `GET /api/rooms` - Lista pokoi czatu
- `POST /api/broadcast` - Wysłanie wiadomości broadcast
- `POST /api/room/create` - Utworzenie pokoju
- `DELETE /api/room/<room_id>` - Usunięcie pokoju

### Socket.IO Events

#### Client → Server
- `connect` - Połączenie
- `disconnect` - Rozłączenie
- `login` - Logowanie `{username: "..."}`
- `message` - Wysłanie wiadomości `{message: "...", room: "general"}`
- `join_room` - Dołączenie do pokoju `{room: "room_id"}`
- `leave_room` - Opuszczenie pokoju `{room: "room_id"}`
- `typing` - Status pisania `{typing: true/false, room: "general"}`

#### Server → Client
- `login_success` - Potwierdzenie logowania `{username: "..."}`
- `user_list` - Lista użytkowników `{users: [...]}`
- `message_history` - Historia `{messages: [...]}`
- `new_message` - Nowa wiadomość `{id, username, message, timestamp, room}`
- `user_connected` - Nowy użytkownik `{username, connected_at}`
- `user_disconnected` - Rozłączenie `{username, timestamp}`
- `user_joined_room` - Dołączenie do pokoju
- `user_left_room` - Opuszczenie pokoju
- `user_typing` - Status pisania `{username, typing, room}`
- `error` - Błąd `{message: "..."}`

## 💻 Web Client

Otwórz w przeglądarce: `http://localhost:5000/chat`

Pełnofunkcjonalny interfejs webowy z:
- Login screen
- Lista użytkowników online
- Historia wiadomości
- Real-time chat
- Typing indicators
- Responsywny design

## 📦 Przykład użycia w Pythonie

```python
import socketio

# Utwórz klienta Socket.IO
sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Połączono z serwerem')
    sio.emit('login', {'username': 'TestUser'})

@sio.on('new_message')
def on_message(data):
    print(f"{data['username']}: {data['message']}")

# Połącz
sio.connect('http://localhost:5000')

# Wyślij wiadomość
sio.emit('message', {'message': 'Cześć!'})

# Czekaj
sio.wait()
```

## 🔧 Konfiguracja

W `config/constants.py`:

```python
CHAT_SERVER_HOST = "0.0.0.0"  # Wszystkie interfejsy
CHAT_SERVER_PORT = 5000       # Port serwera
```

## 📊 Monitoring

```python
# Pobierz statystyki
stats = chat_server.get_stats()
# {'online_users': 5, 'total_messages': 142, 'rooms': 3, 'running': True}

# Lista użytkowników
users = chat_server.get_online_users()

# Historia wiadomości
messages = chat_server.get_message_history(limit=50)

# Broadcast
chat_server.broadcast_message("Serwer zostanie zrestartowany za 5 minut", "Admin")
```

## 🛑 Zatrzymanie

```python
chat_server.stop()
chat_server.cleanup()
```
