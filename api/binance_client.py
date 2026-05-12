import asyncio
import websockets
import ujson
import logging
import httpx

class BinanceClient:
    def __init__(self):
        # Monedas a monitorear para el sentimiento del mercado
        self.symbols = ["btcusdt", "ethusdt", "solusdt"]
        # URL para streams combinados
        streams = "/".join([f"{s}@ticker" for s in self.symbols])
        self.ws_url = f"wss://stream.binance.com:9443/stream?streams={streams}"
        self.rest_url = 'https://api.binance.com/api/v3/klines'
        self.logger = logging.getLogger("NEON.API_BINANCE")

    async def get_historical_data(self, symbol="BTCUSDT", limit=100):
        """Descarga precios de cierre históricos (por defecto BTC)."""
        self.logger.info(f"📥 Descargando historial para {symbol}...")
        params = {"symbol": symbol, "interval": "1m", "limit": limit}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.rest_url, params=params)
                data = response.json()
                return [float(candle[4]) for candle in data]
        except Exception as e:
            self.logger.error(f"❌ Error en historial: {e}")
            return []

    async def connect(self):
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.logger.info(f"✅ Conexión Multi-Stream establecida: {self.symbols}")
                    while True:
                        raw_msg = await ws.recv()
                        msg = ujson.loads(raw_msg)
                        # Al usar streams combinados, los datos vienen en msg['data']
                        data = msg.get('data', {})
                        # Inyectamos el símbolo para que el Engine sepa de quién es el precio
                        data['s_name'] = data['s'] 
                        yield data
            except (websockets.ConnectionClosed, Exception) as e:
                self.logger.warning(f"🔄 Reconexión en 5s: {e}")
                await asyncio.sleep(5)

