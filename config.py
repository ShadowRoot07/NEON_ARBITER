import os
import logging
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.logger = logging.getLogger("NEON.CONFIG")

        self.binance_api_key = os.environ.get('BINANCE_API_KEY')
        self.binance_api_secret = os.environ.get('BINANCE_API_SECRET')
        self.groq_api_key = os.environ.get('GROQ_API_KEY')

        # --- NUEVOS PARÁMETROS DE CONTROL ---
        self.max_daily_loss = 2.0  # % Máximo de pérdida diaria permitido
        self.ai_history_limit = 5  # Cuántas decisiones pasadas recuerda la IA
        # ------------------------------------

        if not self.binance_api_key or not self.groq_api_key:
            self.logger.warning("⚠️ API Keys incompletas.")
        else:
            self.logger.info("🔑 API Keys cargadas correctamente.")

        self.api_endpoints = {
            'binance': 'wss://stream.binance.com:9443/ws/btcusdt@ticker',
            'groq': 'https://api.groq.com/openai/v1/chat/completions'
        }

