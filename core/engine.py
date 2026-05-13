import asyncio
import logging
import ujson
from collections import deque
from api.binance_client import BinanceClient
from config import Config
from core.trading_logic import TradingLogic
from core.strategies.algorithmic_scalper import AlgorithmicScalper # Nueva Estrategia
from database.schema import AIAudit, sessionmaker, engine as db_engine
from datetime import datetime

class Engine:
    def __init__(self, test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.is_scalper = is_scalper
        self.cfg = Config()
        self.client = BinanceClient()
        self.trading = TradingLogic(initial_test_balance=test_balance, is_scalper=is_scalper)
        self.strategy = AlgorithmicScalper() # Cambiado a Scalper Algorítmico
        self.market_buffers = { "ETHUSDT": deque(maxlen=100), "SOLUSDT": deque(maxlen=100) }

        self.tick_count = 0
        self.price_buffer = deque(maxlen=3600)
        self.tick_interval = 2 if is_scalper else 5 # ¡Mucho más rápido ahora!
        self.Session = sessionmaker(bind=db_engine)

    async def run_bot(self):
        self.logger.info(f"🚀 NEON ARBITER: MODO ALGORÍTMICO PURO (SIN IA-LATENCY)")

        # Sincronización e Historial
        historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=500)
        for p in historico: self.price_buffer.append(p)
        if historico: self.trading.sincronizar_estado(historico[-1])

        while True:
            try:
                async for data in self.client.connect():
                    symbol = data['s_name']
                    price = float(data['c'])

                    if symbol == "BTCUSDT":
                        self.price_buffer.append(price)
                        self.tick_count += 1

                        if not self.trading.can_trade(): continue

                        if self.trading.test_mode:
                            # 1. Gestión de salida (Trailing Stop siempre activo)
                            self.trading.ejecutar_simulacion(price)

                            # 2. Análisis Matemático (Tick Interval reducido)
                            if self.tick_count % self.tick_interval == 0:
                                analysis = self.strategy.analyze(self.price_buffer, self.market_buffers)
                                if analysis:
                                    decision, confianza = self.strategy.should_execute(analysis)

                                    if decision == 'BUY' and not self.trading.active_position:
                                        self.trading.abrir_posicion_test(price)
                                    elif decision == 'SELL' and self.trading.active_position:
                                        self.trading.cerrar_posicion_test(price, "ALGO_STRATEGY")

                        # Monitor visual cada 20 ticks
                        if self.tick_count % 20 == 0:
                            total = self.trading.balance + (self.trading.inventory * price)
                            pnl_c = "\033[32m" if self.trading.daily_pnl >= 0 else "\033[31m"
                            print(f"📊 [ALGO-MODE] BTC: ${price:,.2f} | Balance: ${total:.2f} | PnL: {pnl_c}${self.daily_pnl:.2f}\033[0m")

                    else:
                        if symbol in self.market_buffers:
                            self.market_buffers[symbol].append(price)

            except Exception as e:
                self.logger.warning(f"🔄 Error: {e}. Reintentando...")
                await asyncio.sleep(5)

