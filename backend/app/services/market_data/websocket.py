from collections import defaultdict

from fastapi import WebSocket

MARKET_DATA_CHANNELS = {"candles", "ticks", "order_books", "trades"}


class MarketDataWebsocket:
    def __init__(self) -> None:
        self._subscriptions: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, channels: list[str] | None = None) -> list[str]:
        await websocket.accept()
        selected_channels = self.normalize_channels(channels)
        for channel in selected_channels:
            self._subscriptions[channel].add(websocket)
        await websocket.send_json({"type": "subscribed", "channels": selected_channels})
        return selected_channels

    def disconnect(self, websocket: WebSocket) -> None:
        for subscribers in self._subscriptions.values():
            subscribers.discard(websocket)

    async def subscribe(self, websocket: WebSocket, channels: list[str]) -> list[str]:
        selected_channels = self.normalize_channels(channels)
        for channel in selected_channels:
            self._subscriptions[channel].add(websocket)
        await websocket.send_json({"type": "subscribed", "channels": selected_channels})
        return selected_channels

    async def publish(self, channel: str, payload: dict) -> None:
        if channel not in MARKET_DATA_CHANNELS:
            return
        stale: list[WebSocket] = []
        for websocket in list(self._subscriptions[channel]):
            try:
                await websocket.send_json({"type": "market_data", "channel": channel, "payload": payload})
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)

    def normalize_channels(self, channels: list[str] | None) -> list[str]:
        if not channels:
            return sorted(MARKET_DATA_CHANNELS)
        selected = [channel for channel in channels if channel in MARKET_DATA_CHANNELS]
        return selected or sorted(MARKET_DATA_CHANNELS)


market_data_websocket = MarketDataWebsocket()
