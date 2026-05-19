import asyncio
import logging
import websockets
import ujson
import httpx

class BinanceClient:
    def __init__(self):
        self.symbols = ["btcusdt", "ethusdt", "solusdt"]
        self.rest_url = 'https://api.binance.com/api/v3/klines'
        # Stream combinado en tiempo real de Binance (WSS)
        streams = "/".join([f"{s}@ticker" for s in self.symbols])
        self.ws_url = f"wss://stream.binance.com:9443/stream?streams={streams}"
        self.logger = logging.getLogger("NEON.API_BINANCE")

    async def get_historical_data(self, symbol="BTCUSDT", limit=500):
        """
        Descarga directa de las velas históricas por HTTP REST (Carga el buffer a 500 periodos).
        Evita el WARMING_UP ciego en el arranque del bot.
        """
        self.logger.info(f"📥 Descargando historial macro de {limit} velas para {symbol}...")
        params = {"symbol": symbol, "interval": "1m", "limit": limit}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.rest_url, params=params, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    # Retornamos los precios de cierre (Candle índice 4)
                    return [float(candle[4]) for candle in data]
                else:
                    self.logger.error(f"⚠️ Error HTTP al bajar historial: {response.status_code}")
                    return []
        except Exception as e:
            self.logger.error(f"❌ Error en historial: {e}")
            return []

    async def connect(self):
        """
        Generador asíncrono WebSocket nativo y resistente a desconexiones en móviles.
        Envía los deltas de precio y volumen acumulado para procesamiento en el Engine.
        """
        retries = 0
        base_delay = 2  # Segundos iniciales de espera tras una caída
        max_delay = 30  # Techo máximo de espera para reintentos

        while True:
            try:
                self.logger.info(f"🔌 Conectando a los streams en tiempo real de Binance...")

                # Configuramos ping_interval y ping_timeout para cortes de red rápidos en Termux
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10
                ) as ws:
                    self.logger.info(f"⚡ [ONLINE] ¡Conectado con éxito! Monitoreando: {self.symbols}")
                    retries = 0  # Reseteamos el contador de fallos

                    while True:
                        raw_msg = await ws.recv()
                        msg = ujson.loads(raw_msg)

                        data = msg.get('data', {})
                        if data:
                            # Inyectamos la llave s_name que el Engine espera nativamente
                            data['s_name'] = data['s']
                            yield data

            except (websockets.ConnectionClosed, Exception) as e:
                retries += 1
                delay = min(base_delay ** retries, max_delay)
                self.logger.warning(
                    f"🔌 [OFFLINE] Conexión perdida ({e}). "
                    f"Reintentando en {delay}s... (Intento {retries})"
                )
                await asyncio.sleep(delay)
