import asyncio
import logging
import httpx

class BinanceClient:
    def __init__(self):
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.rest_url = 'https://api.binance.com/api/v3/klines'
        self.ticker_url = 'https://api.binance.com/api/v3/ticker/price'
        self.logger = logging.getLogger("NEON.API_BINANCE")
        
        # URL de la lista pública de proxies (Filtro HTTP limpios)
        self.proxy_source_url = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
        
        self.proxies = [] # Se llenará dinámicamente
        self.current_proxy_index = 0
        self.proxies_loaded = False

    async def _download_fresh_proxies(self):
        """Descarga una lista fresca de proxies públicos y los limpia."""
        self.logger.info("📡 Descargando lista de proxies automatizada...")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.proxy_source_url)
                if response.status_code == 200:
                    raw_lines = response.text.splitlines()
                    # Formateamos cada ip:puerto como un proxy http válido
                    fresh_list = [f"http://{line.strip()}" for line in raw_lines if line.strip()]
                    
                    # Guardamos un bloque seguro de los primeros 60 proxies para rotar
                    self.proxies = fresh_list[:60]
                    self.current_proxy_index = 0
                    self.proxies_loaded = True
                    self.logger.info(f"✅ Red Proxy cargada con {len(self.proxies)} nodos activos.")
                else:
                    self.logger.error(f"❌ Falló la descarga de proxies. Estatus: {response.status_code}")
        except Exception as e:
            self.logger.error(f"❌ Error al conectar con el servidor de proxies: {e}")
            
        # Respaldo de emergencia en memoria por si el repositorio público cae
        if not self.proxies:
            self.logger.warning("⚠️ Usando proxies de emergencia integrados.")
            self.proxies = [
                "http://185.122.57.14:8080",
                "http://195.201.144.135:80",
                "http://81.162.33.208:80"
            ]

    def _get_current_proxy(self):
        if not self.proxies:
            return None
        return self.proxies[self.current_proxy_index]

    def _rotate_proxy(self):
        if self.proxies:
            # Si el proxy falló, lo removemos para no repetir errores
            failed_proxy = self._get_current_proxy()
            if len(self.proxies) > 1:
                self.proxies.pop(self.current_proxy_index)
                self.current_proxy_index = self.current_proxy_index % len(self.proxies)
                self.logger.warning(f"🔌 Nodo fallido eliminado. Quedan {len(self.proxies)} proxies en el buffer.")
            else:
                self.logger.warning("⚠️ Último proxy en lista. Intentando re-conectar...")

    async def get_historical_data(self, symbol="BTCUSDT", limit=100):
        """Descarga historial esperando a que los proxies estén inicializados."""
        # Forzar la carga de proxies si no se ha hecho
        if not self.proxies_loaded:
            await self._download_fresh_proxies()

        params = {"symbol": symbol, "interval": "1m", "limit": limit}
        
        # Intentamos usar los proxies cargados en orden de supervivencia
        for _ in range(min(15, len(self.proxies))):
            proxy = self._get_current_proxy()
            try:
                async with httpx.AsyncClient(proxy=proxy, timeout=8.0) as client:
                    response = await client.get(self.rest_url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        return [float(candle[4]) for candle in data]
                    elif response.status_code == 451:
                        self._rotate_proxy()
            except Exception:
                self._rotate_proxy()
        return []

    async def connect(self):
        """REST Polling con descarga e inyección automática de proxies."""
        if not self.proxies_loaded:
            await self._download_fresh_proxies()

        self.logger.info(f"🛰️ Neon Arbiter conectado a la Red Proxy Dinámica.")
        
        symbols_json = f'["' + '","'.join(self.symbols) + '"]'
        params = {"symbols": symbols_json}

        while True:
            # Si nos quedamos sin proxies a mitad de la sesión, recargamos la lista
            if not self.proxies:
                self.logger.warning("♻️ El buffer de proxies se agotó. Recargando lista...")
                await self._download_fresh_proxies()

            proxy = self._get_current_proxy()
            
            try:
                async with httpx.AsyncClient(proxy=proxy, timeout=7.0) as client:
                    response = await client.get(self.ticker_url, params=params)
                    if response.status_code == 451:
                        self.logger.warning(f"🚫 Bloqueo regional (451) en {proxy}. Purgando...")
                        self._rotate_proxy()
                        continue

                    if response.status_code == 200:
                        data_list = response.json()
                        for item in data_list:
                            yield {
                                's_name': item['symbol'],
                                'c': item['price']
                            }
                    else:
                        self.logger.warning(f"⚠️ Código inusual {response.status_code} en {proxy}. Cambiando...")
                        self._rotate_proxy()

                    # Intervalo base de escaneo
                    await asyncio.sleep(2)

            except (httpx.RequestError, httpx.TimeoutException):
                self._rotate_proxy()
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"❌ Error interno en el ciclo de red: {e}")
                self._rotate_proxy()
                await asyncio.sleep(3)

