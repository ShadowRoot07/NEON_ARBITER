import asyncio
import websockets
import ujson

class BinanceClient:
    def __init__(self):
        self.ws_url = 'wss://stream.binance.com:9443/ws/btcusdt@ticker'

    async def connect(self):
        async with websockets.connect(self.ws_url) as ws:
            while True:
                try:
                    msg = await ws.recv()
                    yield ujson.loads(msg)
                except websockets.ConnectionClosed:
                    break
