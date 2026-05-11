import os
import logging
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Carga las variables del archivo .env si existe
        load_dotenv()
        
        self.logger = logging.getLogger("NEON.CONFIG")

        # Carga de variables de entorno (ahora desde el .env o el sistema)
        self.binance_api_key = os.environ.get('BINANCE_API_KEY')
        self.binance_api_secret = os.environ.get('BINANCE_API_SECRET')
        self.groq_api_key = os.environ.get('GROQ_API_KEY')

        # Validación de las llaves
        if not self.binance_api_key or not self.groq_api_key:
            self.logger.warning("⚠️ No se detectaron todas las API Keys en el .env.")
            self.logger.warning("El bot funcionará solo en modo lectura (sin IA activa).")
        else:
            self.logger.info("🔑 API Keys cargadas correctamente desde el entorno.")

        self.api_endpoints = {
            'binance': 'wss://stream.binance.com:9443/ws/btcusdt@ticker',
            'groq': 'https://api.groq.com/openai/v1/chat/completions'
        }

