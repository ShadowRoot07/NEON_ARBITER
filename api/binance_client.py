import asyncio
import websockets
import ujson
import logging

class BinanceClient:
    def __init__(self):
        self.ws_url = 'wss://stream.binance.com:9443/ws/btcusdt@ticker'
        self.logger = logging.getLogger("NEON.API_BINANCE")

    async def connect(self):
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.logger.info("✅ Conexión establecida con éxito.")
                    while True:
                        msg = await ws.recv()
                        yield ujson.loads(msg)
            except (websockets.ConnectionClosed, Exception) as e:
                self.logger.warning(f"🔄 Conexión perdida: {e}. Reintentando en 5 segundos...")
                await asyncio.sleep(5)

