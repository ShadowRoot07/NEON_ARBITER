import asyncio
import logging
import ujson
from collections import deque
from api.binance_client import BinanceClient
from config import Config
from core.trading_logic import TradingLogic
from core.strategies.algorithmic_scalper import AlgorithmicScalper # Nueva Estrategia
from database.schema import Trades, AIAudit, BotState, sessionmaker, engine as db_engine

from datetime import datetime

class Engine:
    def __init__(self, test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.is_scalper = is_scalper
        self.cfg = Config()

         # 1. Definimos los símbolos que va a escuchar el WebSocket de la API
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        # 2. Se los inyectamos al constructor del cliente
        self.client = BinanceClient(symbols=self.symbols)

        self.trading = TradingLogic(initial_test_balance=test_balance, is_scalper=is_scalper)
        self.strategy = AlgorithmicScalper()
        self.market_buffers = { "ETHUSDT": deque(maxlen=100), "SOLUSDT": deque(maxlen=100) }

        self.tick_count = 0
        self.price_buffer = deque(maxlen=3600)
        self.tick_interval = 30 if not is_scalper else 2
        self.Session = sessionmaker(bind=db_engine)


    async def run_bot(self, duration_mins=None):
        self.logger.info(f"🚀 NEON ARBITER: MODO ALGORÍTMICO PURO (SIN IA-LATENCY)")

        # 1. Warm-up: Sincronización e Historial para el Clima
        # 1. Warm-up: Sincronización e Historial para el Clima
        # 1. Warm-up: Sincronización e Historial para el Clima (Blindado contra fallos)

        self.logger.info("📡 Intentando descargar últimas 100 velas para análisis de clima...")
        start_time = datetime.now()
        historico = None

        try:
            # Intentamos llamar al método del historial
            if hasattr(self.client, 'get_historical_data'):
                historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=100)

                if historico:
                    for p in historico:
                        self.price_buffer.append(p)
                    self.trading.sincronizar_estado(historico[-1])
                    self.logger.info("✅ Historial cargado y sincronizado con éxito.")

            else:
                self.logger.warning("⚠️ 'get_historical_data' no está implementado en BinanceClient. Saltando warm-up...")
        except Exception as e:
                # Si el generador asíncrono cae por desconexión en el cel, se atrapa aquí
                self.logger.warning(f"⚠️ Stream interrumpido en bucle principal: {e}. Sincronizando de nuevo...")
                await asyncio.sleep(3)

                # RE-SINCRONIZACIÓN DE EMERGENCIA SEGURA
                try:
                    if hasattr(self.client, 'get_historical_data'):
                        historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=50)
                        if historico:
                            self.price_buffer.clear()
                            for p in historico:
                                self.price_buffer.append(p)
                            self.trading.sincronizar_estado(historico[-1])
                except Exception as ex_db:
                    self.logger.warning(f"⚠️ No se pudo re-sincronizar el historial en caliente: {ex_db}")

        from core.analyzers.trend_analyzer import TrendAnalyzer

        while True:
            try:
                # Iteramos directo sobre el generador asíncrono
                async for data in self.client.connect():
                    symbol = data['s_name']
                    price = float(data['c'])

                    # --- CONTROL DE TIEMPO DE SESIÓN ---
                    if duration_mins:
                        elapsed = (datetime.now() - start_time).total_seconds() / 60
                        if elapsed >= duration_mins:
                            self.logger.info(f"⏰ Tiempo de sesión agotado ({duration_mins} min). Guardando y saliendo...")
                            total_equity = self.trading.get_total_equity(price)
                            self.save_current_state(total_equity)
                            return 
                    # ----------------------------------

                    if symbol == "BTCUSDT":
                        self.price_buffer.append(price)
                        self.tick_count += 1

                        if not self.trading.can_trade(): continue

                        if self.trading.test_mode:
                            # 1. Gestión de salida (Trailing Stop / Stop Loss)
                            self.trading.ejecutar_simulacion(price)

                            # 2. Análisis Matemático por Intervalo
                            # 2. Análisis Matemático por Intervalo
                            if self.tick_count % self.tick_interval == 0:
                                precios_lista = list(self.price_buffer)
                                # PASAMOS EL FLAG: is_scalper influye en la sensibilidad
                                clima = TrendAnalyzer.get_market_climate(precios_lista, is_scalper=self.is_scalper)

                                # FILTRO PROTECTOR ACTUALIZADO:
                                if clima == "RANGING_DEAD":
                                    if not self.is_scalper:
                                        if self.tick_count % 100 == 0:
                                            self.logger.info("💤 Mercado lateral sin volatilidad. Esperando...")
                                        continue
                                    else:
                                        # Si es Scalper y está DEAD, significa que el spread es menor a las comisiones.
                                        # Congelamos operaciones para evitar pérdidas por fricción de corretaje.
                                        if self.tick_count % 100 == 0:
                                            self.logger.info("🎯 [SCALPER] Rango demasiado estrecho (Comisiones > Spread). Esperando volatilidad...")
                                        continue

                                analysis = self.strategy.analyze(self.price_buffer, self.market_buffers)

                                if analysis:
                                    decision, confianza = self.strategy.should_execute(analysis, clima)

                                    if decision == 'BUY' and not self.trading.active_position:
                                        self.trading.abrir_posicion_test(price, clima=clima)

                                    elif decision == 'SELL' and self.trading.active_position:
                                        self.trading.cerrar_posicion_test(price, f"ALGO_{clima}")

                        # Monitor visual en la consola de Termux
                        if self.tick_count % 20 == 0:
                            precios_lista = list(self.price_buffer)
                            # También pasamos el flag en el print del monitor visual
                            clima_actual = TrendAnalyzer.get_market_climate(precios_lista, is_scalper=self.is_scalper)
                            total_equity = self.trading.get_total_equity(price)

                            self.save_current_state(total_equity)

                            pnl_c = "\033[32m" if self.trading.daily_pnl >= 0 else "\033[31m"
                            c_map = {"TRENDING_UP": "\033[32m", "TRENDING_DOWN": "\033[31m", "RANGING": "\033[34m"}
                            c_color = c_map.get(clima_actual, "\033[0m")

                            print(f"📊 [{self.trading.mode}] [BTC: ${price:,.2f}] Clima: {c_color}{clima_actual}\033[0m | "
                                  f"TOTAL: ${total_equity:.2f} | "
                                  f"Cash: ${self.trading.balance:.2f} | "
                                  f"PnL Diar: {pnl_c}${self.trading.daily_pnl:.2f}\033[0m")
                    else:
                        if symbol in self.market_buffers:
                            self.market_buffers[symbol].append(price)

            except Exception as e:
                # Si el generador asíncrono cae por desconexión en el cel, se atrapa aquí
                self.logger.warning(f"⚠️ Stream interrumpido en bucle principal: {e}. Sincronizando de nuevo...")
                await asyncio.sleep(3)
                
                # RE-SINCRONIZACIÓN DE EMERGENCIA: Volvemos a bajar datos frescos para no operar con buffers desfasados
                historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=50)
                if historico:
                    self.price_buffer.clear()
                    for p in historico:
                        self.price_buffer.append(p)
                    self.trading.sincronizar_estado(historico[-1])

    def save_current_state(self, total_equity):
        """Guarda el estado en la DB para que GitHub Actions lo herede"""
        with self.Session() as session:
            new_state = BotState(
                total_balance=self.trading.balance,
                daily_pnl=self.trading.daily_pnl,
                current_mode=self.trading.mode,
                is_active=1
            )
            session.add(new_state)
            session.commit()
