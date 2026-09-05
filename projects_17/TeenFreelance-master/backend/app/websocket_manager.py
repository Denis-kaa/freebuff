from typing import Dict, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """Менеджер WebSocket подключений"""
    
    def __init__(self):
        # Храним подключения по user_id
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Подключение пользователя"""
        # WebSocket уже принят в endpoint, просто добавляем в список
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        print(f"ConnectionManager: User {user_id} added, total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Отключение пользователя"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Отправка сообщения конкретному пользователю"""
        if user_id in self.active_connections:
            disconnected = set()
            connections = self.active_connections[user_id]
            print(f"Sending message to user {user_id}, active connections: {len(connections)}")
            for connection in connections:
                try:
                    await connection.send_json(message)
                    print(f"Message sent successfully to user {user_id}")
                except Exception as e:
                    print(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(connection)
            
            # Удаляем отключенные соединения
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
            
            # Если все соединения отключены, удаляем запись
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        else:
            print(f"No active WebSocket connections for user {user_id}")
    
    async def broadcast(self, message: dict, exclude_user_id: int = None):
        """Отправка сообщения всем подключенным пользователям"""
        for user_id, connections in self.active_connections.items():
            if exclude_user_id and user_id == exclude_user_id:
                continue
            await self.send_personal_message(message, user_id)


# Глобальный менеджер подключений
manager = ConnectionManager()
