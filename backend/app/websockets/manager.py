import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import WebSocket


PayloadProducer = Callable[[], Awaitable[object] | object]


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, stream: str) -> None:
        await websocket.accept()
        self._connections[stream].add(websocket)
        await self.send(websocket, stream, {"status": "connected"})

    def disconnect(self, websocket: WebSocket, stream: str | None = None) -> None:
        if stream:
            self._connections[stream].discard(websocket)
            return
        for connections in self._connections.values():
            connections.discard(websocket)

    async def send(self, websocket: WebSocket, stream: str, payload: object) -> bool:
        try:
            await websocket.send_json(
                {
                    "type": stream,
                    "payload": payload,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            return True
        except RuntimeError:
            self.disconnect(websocket, stream)
            return False

    async def stream(
        self,
        websocket: WebSocket,
        stream: str,
        producer: PayloadProducer,
        interval_seconds: float = 5.0,
    ) -> None:
        await self.connect(websocket, stream)
        try:
            while True:
                payload = producer()
                if hasattr(payload, "__await__"):
                    payload = await payload
                connected = await self.send(websocket, stream, payload)
                if not connected:
                    return
                await asyncio.sleep(interval_seconds)
        finally:
            self.disconnect(websocket, stream)


websocket_manager = WebSocketManager()
