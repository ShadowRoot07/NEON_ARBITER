import asyncio
import websockets
import ujson
import logging
import httpx # Asegúrate de tenerlo instalado: pip install httpx

class BinanceClient:
    def __init__(self):
        self.ws_url = 'wss://stream.binance.com:9443/ws/btcusdt@ticker'
        self.rest_url = 'https://api.binance.com/api/v3/klines'
        self.logger = logging.getLogger("NEON.API_BINANCE")

    async def get_historical_data(self, symbol="BTCUSDT", limit=100):
        """Descarga precios de cierre históricos para llenar el buffer."""
        self.logger.info(f"📥 Descargando {limit} velas históricas...")
        params = {"symbol": symbol, "interval": "1m", "limit": limit}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.rest_url, params=params)
                data = response.json()
                # El índice 4 es el precio de cierre (Close) en la respuesta de Binance
                return [float(candle[4]) for candle in data]
        except Exception as e:
            self.logger.error(f"❌ Error descargando historial: {e}")
            return []

    async def connect(self):
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.logger.info("✅ Conexión WebSocket establecida.")
                    while True:
                        msg = await ws.recv()
                        yield ujson.loads(msg)
            except (websockets.ConnectionClosed, Exception) as e:
                self.logger.warning(f"🔄 Conexión perdida: {e}. Reintentando en 5 segundos...")
                await asyncio.sleep(5)

