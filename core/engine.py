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

        # 1. Warm-up: Sincronización e Historial para el Clima
        self.logger.info("📡 Descargando últimas 100 velas para análisis de clima...")
        historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=100)
        for p in historico: 
            self.price_buffer.append(p)
        
        if historico: 
            self.trading.sincronizar_estado(historico[-1])

        from core.analyzers.trend_analyzer import TrendAnalyzer
        
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
                            # 1. Gestión de salida (Trailing Stop / Stop Loss)
                            self.trading.ejecutar_simulacion(price)

                            # 2. Análisis Matemático por Intervalo
                            if self.tick_count % self.tick_interval == 0:
                                precios_lista = list(self.price_buffer)
                                clima = TrendAnalyzer.get_market_climate(precios_lista)
                                analysis = self.strategy.analyze(self.price_buffer, self.market_buffers)
                                
                                if analysis:
                                    decision, confianza = self.strategy.should_execute(analysis, clima)

                                    if decision == 'BUY' and not self.trading.active_position:
                                        # Pasamos el clima para que el trading ajuste el SL
                                        self.trading.abrir_posicion_test(price, clima=clima)
                                        
                                    elif decision == 'SELL' and self.trading.active_position:
                                        self.trading.cerrar_posicion_test(price, f"ALGO_{clima}")

                        # Monitor visual cada 20 ticks
                        if self.tick_count % 20 == 0:
                            precios_lista = list(self.price_buffer)
                            clima_actual = TrendAnalyzer.get_market_climate(precios_lista)
                            
                            # CÁLCULOS DE VALOR REAL
                            valor_en_crypto = self.trading.inventory * price
                            total_equity = self.trading.balance + valor_en_crypto
                            
                            pnl_c = "\033[32m" if self.trading.daily_pnl >= 0 else "\033[31m"
                            
                            # Color para el clima
                            c_map = {"TRENDING_UP": "\033[32m", "TRENDING_DOWN": "\033[31m", "RANGING": "\033[34m", "CHAOS": "\033[33m"}
                            c_color = c_map.get(clima_actual, "\033[0m")
                            
                            # LOG MEJORADO: Total es lo que importa, Cash es lo que sobra
                            print(f"📊 [BTC: ${price:,.2f}] Clima: {c_color}{clima_actual}\033[0m | "
                                  f"TOTAL: ${total_equity:.2f} | "
                                  f"Cash: ${self.trading.balance:.2f} | "
                                  f"PnL Diar: {pnl_c}${self.trading.daily_pnl:.2f}\033[0m")

                    else:
                        if symbol in self.market_buffers:
                            self.market_buffers[symbol].append(price)

            except Exception as e:
                self.logger.warning(f"🔄 Reintentando conexión... Error: {e}")
                await asyncio.sleep(5)

