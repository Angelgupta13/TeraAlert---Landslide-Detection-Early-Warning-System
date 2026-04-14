import asyncio
import json
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "landslides": set(),
            "weather": set(),
            "alerts": set(),
            "all": set(),
        }
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str = "all"):
        await websocket.accept()
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
            self.active_connections["all"].add(websocket)
        logger.info(f"WebSocket connected: {channel}")

    async def disconnect(self, websocket: WebSocket, channel: str = "all"):
        async with self._lock:
            for ch in self.active_connections:
                self.active_connections[ch].discard(websocket)
        logger.info(f"WebSocket disconnected")

    async def broadcast(self, message: dict, channel: str = "all"):
        message["timestamp"] = datetime.now().isoformat()
        message_json = json.dumps(message)

        async with self._lock:
            connections = self.active_connections.get(channel, set()).copy()

        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send to websocket: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            await self.disconnect(conn, channel)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    def get_connection_count(self) -> Dict[str, int]:
        return {
            channel: len(connections)
            for channel, connections in self.active_connections.items()
        }


ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket, channel: str = "all"):
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await ws_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        websocket,
                    )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel)
