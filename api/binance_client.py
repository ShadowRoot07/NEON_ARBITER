import asyncio
import logging
import httpx

class BinanceClient:
    def __init__(self):
        # Monedas a monitorear para el sentimiento del mercado
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.rest_url = 'https://api.binance.com/api/v3/klines'
        # Endpoint REST para precios múltiples instantáneos
        self.ticker_url = 'https://api.binance.com/api/v3/ticker/price'
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
        """
        Sustitución del Plan A (REST Polling). 
        Simula un generador WebSocket consultando la API REST cada 2 segundos.
        """
        self.logger.info(f"🛰️ Iniciando Modo REST Polling para: {self.symbols}")
        
        # Mapeo para transformar los símbolos al formato esperado por el Engine
        symbols_json = f'["' + '","'.join(self.symbols) + '"]'
        params = {"symbols": symbols_json}

        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.get(self.ticker_url, params=params)
                    
                    if response.status_code == 451:
                        self.logger.error("🚫 Bloqueo geográfico estricto detectado en REST (HTTP 451).")
                        raise Exception("HTTP 451: Región restringida por Binance.")

                    if response.status_code == 200:
                        data_list = response.json() # Retorna una lista de dicts: [{'symbol': 'BTCUSDT', 'price': '...'}]
                        
                        for item in data_list:
                            # Construimos la estructura exacta que el motor espera del stream original
                            yield {
                                's_name': item['symbol'],
                                'c': item['price']
                            }
                    else:
                        self.logger.warning(f"⚠️ API Binance respondió con código: {response.status_code}")

                    # Frecuencia de muestreo (2 segundos es óptimo para no saturar la cuota de peticiones)
                    await asyncio.sleep(2)

                except httpx.RequestError as exc:
                    self.logger.warning(f"🔄 Error de red en Polling REST: {exc}. Reintentando en 5s...")
                    await asyncio.sleep(5)
                except Exception as e:
                    self.logger.error(f"❌ Error crítico en ciclo REST: {e}")
                    await asyncio.sleep(5)

