"""
REST API endpoints dla serwera czatu
Udostępnia HTTP API do zarządzania czatem.
"""

import logging
from flask import Flask, jsonify, request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chat_server import ChatServer

from .templates import get_chat_client_html

logger = logging.getLogger(__name__)


def create_api_routes(app: Flask, chat_server: 'ChatServer'):
    """
    Tworzy i rejestruje REST API routes.
    
    Args:
        app: Instancja Flask
        chat_server: Instancja ChatServer
    """
    
    @app.route('/')
    def index():
        """Strona główna API."""
        return jsonify({
            'name': 'Game Launcher Chat Server',
            'version': '1.0',
            'status': 'running' if chat_server.is_running() else 'stopped',
            'endpoints': {
                '/chat': 'Web chat client',
                '/api/health': 'Health check',
                '/api/stats': 'Server statistics',
                '/api/users': 'Online users list',
                '/api/messages': 'Message history',
                '/api/rooms': 'Chat rooms list'
            }
        })
    
    @app.route('/chat')
    def chat_client():
        """Webowy klient czatu."""
        html = get_chat_client_html()
        return html
    
    @app.route('/api/health')
    def health_check():
        """Sprawdzenie zdrowia serwera."""
        return jsonify({
            'status': 'healthy',
            'running': chat_server.is_running()
        })
    
    @app.route('/api/stats')
    def get_stats():
        """Pobiera statystyki serwera."""
        try:
            stats = chat_server.get_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Błąd pobierania statystyk: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/users')
    def get_users():
        """Pobiera listę użytkowników online."""
        try:
            users = chat_server.get_online_users()
            return jsonify({
                'count': len(users),
                'users': users
            })
        except Exception as e:
            logger.error(f"Błąd pobierania użytkowników: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/messages')
    def get_messages():
        """Pobiera historię wiadomości."""
        try:
            limit = request.args.get('limit', 50, type=int)
            messages = chat_server.get_message_history(limit)
            
            return jsonify({
                'count': len(messages),
                'messages': messages
            })
        except Exception as e:
            logger.error(f"Błąd pobierania wiadomości: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/rooms')
    def get_rooms():
        """Pobiera listę pokoi czatu."""
        try:
            rooms = chat_server.chat_rooms
            return jsonify({
                'count': len(rooms),
                'rooms': rooms
            })
        except Exception as e:
            logger.error(f"Błąd pobierania pokoi: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/broadcast', methods=['POST'])
    def broadcast_message():
        """Wysyła wiadomość broadcast do wszystkich użytkowników."""
        try:
            data = request.get_json()
            
            if not data or 'message' not in data:
                return jsonify({'error': 'Brak wiadomości'}), 400
            
            message = data['message']
            username = data.get('username', 'System')
            
            chat_server.broadcast_message(message, username)
            
            return jsonify({
                'status': 'success',
                'message': 'Wiadomość wysłana'
            })
            
        except Exception as e:
            logger.error(f"Błąd broadcast: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/room/create', methods=['POST'])
    def create_room():
        """Tworzy nowy pokój czatu."""
        try:
            data = request.get_json()
            
            if not data or 'room_id' not in data or 'name' not in data:
                return jsonify({'error': 'Brak wymaganych pól'}), 400
            
            room_id = data['room_id']
            
            if room_id in chat_server.chat_rooms:
                return jsonify({'error': 'Pokój już istnieje'}), 400
            
            from datetime import datetime
            
            chat_server.chat_rooms[room_id] = {
                'name': data['name'],
                'description': data.get('description', ''),
                'created_at': datetime.now().isoformat(),
                'users': []
            }
            
            return jsonify({
                'status': 'success',
                'room_id': room_id,
                'room': chat_server.chat_rooms[room_id]
            })
            
        except Exception as e:
            logger.error(f"Błąd tworzenia pokoju: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/room/<room_id>', methods=['DELETE'])
    def delete_room(room_id):
        """Usuwa pokój czatu."""
        try:
            if room_id == 'general':
                return jsonify({'error': 'Nie można usunąć głównego pokoju'}), 400
            
            if room_id not in chat_server.chat_rooms:
                return jsonify({'error': 'Pokój nie istnieje'}), 404
            
            del chat_server.chat_rooms[room_id]
            
            return jsonify({
                'status': 'success',
                'message': f'Pokój {room_id} usunięty'
            })
            
        except Exception as e:
            logger.error(f"Błąd usuwania pokoju: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handler dla 404."""
        return jsonify({'error': 'Endpoint nie znaleziony'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handler dla 500."""
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Wewnętrzny błąd serwera'}), 500
    
    logger.info("API routes zarejestrowane")
