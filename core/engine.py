import asyncio
import logging
from api.binance_client import BinanceClient
from database.schema import engine, MarketData, sessionmaker
from datetime import datetime

class Engine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = BinanceClient()
        self.Session = sessionmaker(bind=engine)

    async def run_bot(self):
        self.logger.info('Conectando con el flujo de Binance...')
        async for data in self.client.connect():
            # Extraer datos del ticker
            price = float(data['c'])
            volume = float(data['v'])
            
            # Guardar en DB local (SQLite)
            session = self.Session()
            new_data = MarketData(
                timestamp=datetime.now(),
                close=price,
                volume=volume
            )
            session.add(new_data)
            session.commit()
            session.close()
            
            self.logger.info(f"Precio Actual: {price} | Vol: {volume}")

    def start(self):
        try:
            asyncio.run(self.run_bot())
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.logger.info('Deteniendo NEON ARBITER de forma segura...')

