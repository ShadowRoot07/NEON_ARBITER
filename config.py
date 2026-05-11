import os

class Config:
    def __init__(self):
        # Usar .get para evitar errores si no están las variables
        self.binance_api_key = os.environ.get('BINANCE_API_KEY', 'tu_key')
        self.groq_api_key = os.environ.get('GROQ_API_KEY', 'tu_key')
        
        self.api_endpoints = {
            'binance': 'wss://stream.binance.com:9443/ws/btcusdt@ticker',
            'groq': 'https://api.groq.com/openai/v1/chat/completions'
        }

