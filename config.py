import os

class Config:
    def __init__(self):
        self.binance_api_key = os.environ.get('BINANCE_API_KEY')
        self.binance_api_secret = os.environ.get('BINANCE_API_SECRET')
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.groq_api_secret = os.environ.get('GROQ_API_SECRET')
