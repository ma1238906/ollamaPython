from fastapi import (
    WebSocket
)
from typing import List, Dict


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        user_token = websocket.query_params['token']
        self.active_connections[user_token] = websocket

    def disconnect(self, user_token):
        if user_token in self.active_connections:
            del self.active_connections[user_token]

    async def send_personal_message(self, message: str, user_token):
        await self.active_connections[user_token].send_text(message)

    async def broadcast(self, message: str):
        for user_token in self.active_connections:
            await self.active_connections[user_token].send_text(message)


manager = ConnectionManager()
