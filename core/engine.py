import asyncio
import logging
import ujson
from collections import deque
from api.binance_client import BinanceClient
from config import Config
from core.trading_logic import TradingLogic    
from core.strategies.algorithmic_scalper import AlgorithmicScalper
from database.schema import BotState, AIAudit, sessionmaker, engine as db_engine
from datetime import datetime
from core.math_engine import calculate_rvol, calculate_pearson_correlation # Importamos las nuevas dimensiones

class Engine:
    def __init__(self, test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.is_scalper = is_scalper
        self.cfg = Config()
        self.client = BinanceClient()
        self.trading = TradingLogic(initial_test_balance=test_balance, is_scalper=is_scalper)
        self.strategy = AlgorithmicScalper()
        
        # Buffers expandidos a maxlen=500 para evitar miopía macro
        self.market_buffers = { 
            "ETHUSDT": deque(maxlen=500), 
            "SOLUSDT": deque(maxlen=500) 
        }
        
        # Buffers dedicados para los deltas de volumen de cada activo
        self.volume_buffers = {
            "BTCUSDT": deque(maxlen=500),
            "ETHUSDT": deque(maxlen=500),
            "SOLUSDT": deque(maxlen=500)
        }

        # Trackers para calcular los deltas netos de volumen de Binance (v = volumen acumulado 24h)
        self.last_raw_volumes = { "BTCUSDT": 0.0, "ETHUSDT": 0.0, "SOLUSDT": 0.0 }

        self.tick_count = 0
        self.price_buffer = deque(maxlen=500) # Sincronizado a 500 periodos macro
        self.tick_interval = 30 if not is_scalper else 2
        self.Session = sessionmaker(bind=db_engine)

    async def run_bot(self, duration_mins=None):
        self.logger.info(f"🚀 NEON ARBITER: MODO ALGORÍTMICO PURO (SIN IA-LATENCY)")

        # 1. Warm-up: Sincronización e Historial Macro Avanzado (500 velas)
        self.logger.info("📡 Descargando últimas 500 velas para análisis de clima macro...")
        start_time = datetime.now()

        historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=500)
        for p in historico:
            self.price_buffer.append(p)

        if historico:
            self.trading.sincronizar_estado(historico[-1])

        from core.analyzers.trend_analyzer import TrendAnalyzer

        while True:
            try:
                # Iteramos directo sobre el generador asíncrono del WebSocket
                async for data in self.client.connect():
                    symbol = data['s_name']
                    price = float(data['c'])
                    raw_volume = float(data['v']) # Volumen acumulado de 24h que manda Binance

                    # --- CONTROL DE TIEMPO DE SESIÓN ---
                    if duration_mins:
                        elapsed = (datetime.now() - start_time).total_seconds() / 60
                        if elapsed >= duration_mins:
                            self.logger.info(f"⏰ Tiempo de sesión agotado ({duration_mins} min). Guardando y saliendo...")
                            total_equity = self.trading.get_total_equity(price)
                            self.save_current_state(total_equity)
                            return
                    # ----------------------------------

                    # --- CÁLCULO DEL DELTA DE VOLUMEN (LIQUIDEZ EN TIEMPO REAL) ---
                    if self.last_raw_volumes[symbol] == 0.0:
                        self.last_raw_volumes[symbol] = raw_volume
                        delta_vol = 0.0
                    else:
                        delta_vol = raw_volume - self.last_raw_volumes[symbol]
                        # Si cambia el día en Binance, el contador de 24h se resetea
                        if delta_vol < 0: 
                            delta_vol = 0.0
                        self.last_raw_volumes[symbol] = raw_volume
                    
                    self.volume_buffers[symbol].append(delta_vol)
                    # ---------------------------------------------------------------

                    if symbol == "BTCUSDT":
                        self.price_buffer.append(price)
                        self.tick_count += 1

                        # 1. Gestión de salida inmediata (Stop Loss / Take Profit / Trailing)
                        if self.trading.test_mode:
                            self.trading.ejecutar_simulacion(price)

                        # 2. El filtro can_trade verifica también el Cooldown temporal
                        if not self.trading.can_trade():
                            continue

                        if self.trading.test_mode:
                            # 3. Análisis Matemático por Intervalo
                            if self.tick_count % self.tick_interval == 0:
                                precios_lista = list(self.price_buffer)

                                # Nuestro TrendAnalyzer ahora lee con contexto real extendido
                                clima = TrendAnalyzer.get_market_climate(precios_lista, is_scalper=self.is_scalper)

                                # FILTRO PROTECTOR: Gestión de estados visuales y de congelamiento
                                if clima == "RANGING_DEAD":
                                    if not self.is_scalper:
                                        if self.tick_count % 100 == 0:
                                            self.logger.info("💤 Mercado lateral sin volatilidad. Esperando...")
                                        continue
                                    else:
                                        if self.tick_count % 100 == 0:
                                            self.logger.info("🎯 [SCALPER] Operando micro-rango lateral con Z-Score.")
                                elif clima == "TRENDING_DOWN" and self.is_scalper:
                                    if self.tick_count % 40 == 0:
                                        self.logger.info("🚨 [SCALPER] Tendencia bajista macro o quiebre de mínimos detectado. Bloqueando compras.")
                                    continue

                                # --- EXTRACCIÓN DE NUEVAS MÉTRICAS DIMENSIONALES ---
                                btc_rvol = calculate_rvol(list(self.volume_buffers["BTCUSDT"]))
                                eth_corr = calculate_pearson_correlation(precios_lista, list(self.market_buffers["ETHUSDT"]))
                                sol_corr = calculate_pearson_correlation(precios_lista, list(self.market_buffers["SOLUSDT"]))

                                # Guardamos las nuevas métricas en el diccionario de buffers para que la estrategia las lea
                                analysis = self.strategy.analyze(self.price_buffer, self.market_buffers)
                                if analysis:
                                    # Inyectamos los filtros avanzados al análisis antes de pasarlo al gatillo
                                    analysis['rvol'] = btc_rvol
                                    analysis['eth_corr'] = eth_corr
                                    analysis['sol_corr'] = sol_corr

                                    decision, confianza = self.strategy.should_execute(analysis, clima)

                                    # El Engine solo ejecuta compras. Las salidas las maneja ejecutar_simulacion
                                    if decision == 'BUY' and not self.trading.active_position:
                                        self.trading.abrir_posicion_test(price, clima=clima)

                                    elif decision == 'SELL' and self.trading.active_position:
                                        self.trading.cerrar_posicion_test(price, f"ALGO_{clima}")

                        # Monitor visual en la consola de Termux (Se ejecuta cada 20 ticks)
                        if self.tick_count % 20 == 0:
                            precios_lista = list(self.price_buffer)
                            clima_actual = TrendAnalyzer.get_market_climate(precios_lista, is_scalper=self.is_scalper)
                            total_equity = self.trading.get_total_equity(price)

                            self.save_current_state(total_equity)

                            # Métricas para el print del monitor
                            btc_rvol = calculate_rvol(list(self.volume_buffers["BTCUSDT"]))
                            eth_corr = calculate_pearson_correlation(precios_lista, list(self.market_buffers["ETHUSDT"]))

                            pnl_c = "\033[32m" if self.trading.daily_pnl >= 0 else "\033[31m"
                            c_map = {"TRENDING_UP": "\033[32m", "TRENDING_DOWN": "\033[31m", "RANGING": "\033[34m", "RANGING_DEAD": "\033[33m"}
                            c_color = c_map.get(clima_actual, "\033[0m")

                            # Añadimos RVOL y Correlación de ETH al print para monitorear en vivo desde Termux
                            print(f"📊 [{self.trading.mode}] [BTC: ${price:,.2f}] Clima: {c_color}{clima_actual}\033[0m | "
                                  f"RVOL: {btc_rvol:.2f} | CorrETH: {eth_corr:.2f} | "
                                  f"TOTAL: ${total_equity:.2f} | PnL Diar: {pnl_c}${self.trading.daily_pnl:.2f}\033[0m")

                    else:
                        if symbol in self.market_buffers:
                            self.market_buffers[symbol].append(price)

            except Exception as e:
                self.logger.warning(f"⚠️ Stream interrumpido en bucle principal: {e}. Sincronizando de nuevo...")
                await asyncio.sleep(3)

                # RE-SINCRONIZACIÓN DE EMERGENCIA MACRO: 50 velas para estabilizar el buffer rápido
                historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=50)
                if historico:
                    self.price_buffer.clear()
                    for p in historico:
                        self.price_buffer.append(p)
                    self.trading.sincronizar_estado(historico[-1])

    def save_current_state(self, total_equity):
        """Guarda el estado en la DB para persistencia"""
        with self.Session() as session:
            new_state = BotState(
                total_balance=self.trading.balance,
                daily_pnl=self.trading.daily_pnl,
                current_mode=self.trading.mode,
                is_active=1
            )
            session.add(new_state)
            session.commit()
