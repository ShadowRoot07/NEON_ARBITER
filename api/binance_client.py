import asyncio
import logging
import random
import ujson
import websockets

logger = logging.getLogger("NEON.API_BINANCE")

class BinanceClient:
    def __init__(self, symbols):
        self.symbols = symbols
        # Usamos el endpoint combinado para múltiples streams
        self.uri = "wss://stream.binance.com:9443/ws"
        self.is_running = True

    async def get_historical_data(self, symbol="BTCUSDT", limit=100):
        """
        Retorna datos históricos base para el calentamiento del buffer.
        Para evitar bloqueos por SSL de la API REST de Binance en Termux durante el testeo,
        generamos un set inicial estable que permita arrancar el motor técnico al tiro.
        """
        logger.info(f"📥 Generando historial base de calentamiento para {symbol} ({limit} velas)...")
        # Base matemática simulada simulando el precio real de mercado en rango
        precio_base = 67000.0 if symbol == "BTCUSDT" else (3000.0 if symbol == "ETHUSDT" else 140.0)
        historial = []
        for _ in range(limit):
            precio_base += random.uniform(-15.0, 15.0)
            historial.append(precio_base)
        return historial

    async def connect(self):
        """
        Generador asíncrono que actúa como stream de datos en vivo.
        Reemplaza la llamada en engine.py: 'async for data in self.client.connect()'
        """
        attempt = 0
        max_backoff = 60

        # Formatear streams para los símbolos asignados
        # Ejemplo: btcusdt@kline_1m / ethusdt@kline_1m
        streams = "/".join([f"{s.lower()}@kline_1m" for s in self.symbols])
        full_url = f"{self.uri}/{streams}"

        while self.is_running:
            try:
                logger.info("🔌 Conectando a los streams en tiempo real de Binance...")
                
                async with websockets.connect(
                    full_url,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:

                    attempt = 0
                    logger.info("⚡ [ONLINE] ¡Conectado al WebSocket con éxito!")

                    async for message in websocket:
                        if not self.is_running:
                            break
                        
                        # Desempaquetamos el mensaje JSON del stream de Binance
                        raw_data = ujson.loads(message)
                        
                        # Mapeamos al formato plano que tu engine.py consume: data['s_name'] y data['c']
                        if 's' in raw_data and 'k' in raw_data:
                            processed_payload = {
                                's_name': raw_data['s'],          # Símbolo (ej: BTCUSDT)
                                'c': raw_data['k']['c']           # Precio de cierre actual de la vela
                            }
                            yield processed_payload

            except (websockets.exceptions.ConnectionClosed, Exception) as e:
                attempt += 1
                backoff = min(2 ** attempt, max_backoff) + random.uniform(0, 1)
                logger.warning(
                    f"🔌 [OFFLINE] Conexión perdida ({e}). "
                    f"Reintentando en {backoff:.2f}s... (Intento {attempt})"
                )
                await asyncio.sleep(backoff)

    def stop(self):
        self.is_running = False
