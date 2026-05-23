import asyncio
import logging
import websockets
import ujson
import httpx
import time  # <--- NUEVO IMPORT

class BinanceClient:
    def __init__(self):
        self.symbols = ["btcusdt", "ethusdt", "solusdt"]
        self.rest_url = 'https://api.binance.com/api/v3/klines'
        
        # --- NUEVA SUSCRIPCIÓN COMBINADA: TICKER + DEPTH (5 NIVELES) ---
        ticker_streams = [f"{s}@ticker" for s in self.symbols]
        depth_streams = [f"{s}@depth5" for s in self.symbols]
        all_streams = "/".join(ticker_streams + depth_streams)
        
        self.ws_url = f"wss://stream.binance.com:9443/stream?streams={all_streams}"
        self.logger = logging.getLogger("NEON.API_BINANCE")


    async def get_historical_data(self, symbol="BTCUSDT", interval="1m", limit=500):
        self.logger.info(f"📥 Descargando historial macro de {limit} velas ({interval}) para {symbol}...")
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.rest_url, params=params, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    return [float(candle[4]) for candle in data]
                else:
                    self.logger.error(f"⚠️ Error HTTP al bajar historial: {response.status_code}")
                    return []
        except Exception as e:
            self.logger.error(f"❌ Error en historial: {e}")
            return []

    async def connect(self):
        retries = 0
        base_delay = 2  
        max_delay = 30  

        while True:
            try:
                self.logger.info(f"🔌 Conectando a los streams en tiempo real de Binance...")

                # Ajustes agresivos para móviles: si la red muere, cerramos el socket rápido
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=10,  # Reducido a 10s para detectar cortes más rápido
                    ping_timeout=5     # Si en 5s no responde el pong de la vecina, se asume caída
                ) as ws:
                    self.logger.info(f"⚡ [ONLINE] ¡Conectado con éxito! Monitoreando: {self.symbols}")
                    retries = 0  

                    while True:
                        raw_msg = await ws.recv()
                        local_receive_time = time.time() * 1000 # Tiempo del celular en milisegundos
                        msg = ujson.loads(raw_msg)

                        data = msg.get('data', {})
                        if data:
                            data['s_name'] = data['s']
                            
                            # --- CÁLCULO PASIVO DE LATENCIA DE RED ---
                            server_time = data.get('E', local_receive_time)
                            latency = local_receive_time - server_time
                            # Si el reloj del celular está descalibrado unos ms, evitamos latencias negativas
                            data['latency_ms'] = max(0.0, latency) 
                            # ------------------------------------------
                            
                            yield data

            except (websockets.ConnectionClosed, Exception) as e:
                retries += 1
                delay = min(base_delay ** retries, max_delay)
                self.logger.warning(
                    f"🔌 [OFFLINE] Conexión perdida ({e}). "
                    f"Reintentando en {delay}s... (Intento {retries})"
                )
                await asyncio.sleep(delay)

