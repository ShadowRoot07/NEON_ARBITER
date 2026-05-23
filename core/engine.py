import asyncio
import logging
import ujson
import time
import numpy as np
from collections import deque
from api.binance_client import BinanceClient
from config import Config
from core.trading_logic import TradingLogic
from core.strategies.algorithmic_scalper import AlgorithmicScalper
from database.schema import BotState, AIAudit, sessionmaker, engine as db_engine
from datetime import datetime
from core.math_engine import calculate_rvol, calculate_pearson_correlation
from core.analyzers.macro_analyzer import MacroAnalyzer

class Engine:
    def __init__(self, test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.is_scalper = is_scalper
        self.cfg = Config()
        self.client = BinanceClient()
        self.trading = TradingLogic(initial_test_balance=test_balance, is_scalper=is_scalper)
        self.strategy = AlgorithmicScalper()

        self.market_buffers = {
            "ETHUSDT": deque(maxlen=500),
            "SOLUSDT": deque(maxlen=500)
        }

        self.volume_buffers = {
            "BTCUSDT": deque(maxlen=500),
            "ETHUSDT": deque(maxlen=500),
            "SOLUSDT": deque(maxlen=500)
        }

        self.last_raw_volumes = { "BTCUSDT": 0.0, "ETHUSDT": 0.0, "SOLUSDT": 0.0 }

        self.tick_count = 0
        self.price_buffer = deque(maxlen=500)
        self.Session = sessionmaker(bind=db_engine)

        # --- CONTROL DE DOWNSAMPLING POR TIEMPO REAL (En segundos) ---
        self.math_interval = 3.0 if is_scalper else 30.0  # Frecuencia de cálculos matemáticos
        self.print_interval = 15.0                       # Reducción de renderizado en Termux

        self.last_math_time = 0.0
        self.last_print_time = 0.0

        self.macro_analyzer = MacroAnalyzer(self.client)

    async def run_bot(self, duration_mins=None):
        self.logger.info(f"🚀 NEON ARBITER: MODO ALGORÍTMICO PURO (SIN IA-LATENCY)")

        self.logger.info("📡 Descargando últimas 500 velas para análisis de clima macro...")
        start_time = datetime.now()

        historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=500)
        for p in historico:
            self.price_buffer.append(p)

        if historico:
            self.trading.sincronizar_estado(historico[-1])
            # --- LANZAMIENTO DE LA BRÚJULA EN SEGUNDO PLANO (CERO PARÁLISIS) ---
            # Definimos el intervalo macro: 15 minutos para scalper, 1 hora para swing tradicional
            macro_interval_str = "15m" if self.is_scalper else "1h"

            async def macro_background_loop():
                while True:
                    await self.macro_analyzer.update_trend(symbol="BTCUSDT", interval=macro_interval_str)
                    await asyncio.sleep(60) # Se ejecuta de forma aislada cada 1 minuto

            # asyncio.create_task delega la ejecución al loop de fondo sin bloquear los ticks entrantes
            asyncio.create_task(macro_background_loop())
            # -------------------------------------------------------------------

        from core.analyzers.trend_analyzer import TrendAnalyzer

        while True:
            try:
                async for data in self.client.connect():
                    current_time = time.time()
                    symbol = data['s_name']
                    price = float(data['c'])
                    raw_volume = float(data['v'])

                    # --- CONTROL DE TIEMPO DE SESIÓN ---
                    if duration_mins:
                        elapsed = (datetime.now() - start_time).total_seconds() / 60
                        if elapsed >= duration_mins:
                            self.logger.info(f"⏰ Tiempo de sesión agotado ({duration_mins} min). Guardando y saliendo...")
                            total_equity = self.trading.get_total_equity(price)
                            self.save_current_state(total_equity)
                            return
                    # ----------------------------------

                    # --- CÁLCULO ULTRA-LIGERO DEL DELTA DE VOLUMEN ---
                    if self.last_raw_volumes[symbol] == 0.0:
                        self.last_raw_volumes[symbol] = raw_volume
                        delta_vol = 0.0
                    else:
                        delta_vol = raw_volume - self.last_raw_volumes[symbol]
                        if delta_vol < 0:
                            delta_vol = 0.0
                        self.last_raw_volumes[symbol] = raw_volume

                    self.volume_buffers[symbol].append(delta_vol)
                    # ---------------------------------------------------------------
                    if symbol == "BTCUSDT":
                        self.price_buffer.append(price)
                        self.tick_count += 1

                        # ===================================================================
                        # 📡 PROTOCOLO DE RED TERCERMUNDISTA (ESCUDO DE HISTÉRESIS)
                        # ===================================================================
                        tick_latency = data.get('latency_ms', 0.0)

                        # Inicializamos contadores dinámicos si no existen en el objeto
                        if not hasattr(self, 'unstable_ticks_counter'):
                            self.unstable_ticks_counter = 0
                            self.stable_ticks_counter = 0

                        if tick_latency > 1200.0:  # Techo de retraso: 1.2 segundos
                            self.unstable_ticks_counter += 1
                            self.stable_ticks_counter = 0
                        else:
                            self.stable_ticks_counter += 1
                            self.unstable_ticks_counter = 0

                        # GESTIÓN DE ESTADOS DE ALERTA
                        if self.unstable_ticks_counter >= 3 and not self.trading.net_unstable:
                            self.trading.net_unstable = True
                            self.logger.warning(f"⚠️ [ESCUDO] Red degradada detectada (Latencia: {tick_latency:.0f}ms). Congelando compras.")

                        elif self.stable_ticks_counter >= 5 and self.trading.net_unstable:
                            self.trading.net_unstable = False
                            self.logger.info(f"✅ [ESCUDO] Conexión estabilizada (Latencia: {tick_latency:.0f}ms). Reactivando gatillos.")

                        # CEREBRO DE CONTINGENCIA (Si el internet está dañado y estamos en medio de un trade)
                        if self.trading.net_unstable and self.trading.active_position:
                            pos = self.trading.active_position
                            rendimiento_actual = (price - pos['entry']) / pos['entry']

                            # EVALUACIÓN DE ESCENARIOS REALISTAS
                            if rendimiento_actual >= 0.0006:
                                self.logger.info("🚨 [CONTINGENCIA] Saliendo con ganancias seguras antes de quedar a ciegas.")
                                self.trading.forzar_cierre_panico(price)
                        # ===================================================================

                        if self.trading.test_mode:
                            self.trading.ejecutar_simulacion(price)

                            # DOWNSAMPLING CRÍTICO: ¿Toca hacer cálculos matemáticos pesados?
                            if (current_time - self.last_math_time) >= self.math_interval:
                                self.last_math_time = current_time

                                # Convertimos los deques a numpy arrays de golpe
                                btc_prices_arr = np.array(self.price_buffer, dtype=np.float64)
                                btc_vol_arr = np.array(self.volume_buffers["BTCUSDT"], dtype=np.float64)
                                eth_prices_arr = np.array(self.market_buffers["ETHUSDT"], dtype=np.float64)
                                sol_prices_arr = np.array(self.market_buffers["SOLUSDT"], dtype=np.float64)

                                # --- MODIFICACIÓN REQUERIDA (BLOQUE MATEMÁTICO) ---
                                # Desempaquetamos la tupla (clima, longevidad) que viene del TrendAnalyzer
                                clima_contexto = TrendAnalyzer.get_market_climate(list(self.price_buffer), is_scalper=self.is_scalper)
                                clima_actual = clima_contexto[0]

                                # FILTROS PROTECTORES MULTI-TICK
                                if clima_actual == "RANGING_DEAD" and not self.is_scalper:
                                    continue
                                elif clima_actual == "TRENDING_DOWN" and self.is_scalper:
                                    continue

                                # Llamamos a nuestras funciones matemáticas vectorizadas
                                btc_rvol = calculate_rvol(btc_vol_arr)
                                eth_corr = calculate_pearson_correlation(btc_prices_arr, eth_prices_arr)
                                sol_corr = calculate_pearson_correlation(btc_prices_arr, sol_prices_arr)

                                # Análisis de estrategia
                                analysis = self.strategy.analyze(self.price_buffer, self.market_buffers)
                                if analysis:
                                    analysis['rvol'] = btc_rvol
                                    analysis['eth_corr'] = eth_corr
                                    analysis['sol_corr'] = sol_corr

                                    # Pasamos la tupla completa clima_contexto y el estado de la brújula macro a la estrategia
                                    decision, confianza = self.strategy.should_execute(
                                        analysis, 
                                        clima_contexto,
                                        macro_trend=self.macro_analyzer.current_macro_trend
                                    )

                                    if decision == 'BUY' and not self.trading.active_position:
                                        self.trading.abrir_posicion_test(price, clima=clima_actual)
                                    elif decision == 'SELL' and self.trading.active_position:
                                        self.trading.cerrar_posicion_test(price, f"ALGO_{clima_actual}")

                        # --- MONITOR VISUAL REDUCIDO (DOWNSAMPLING DE LOGS) ---
                        if (current_time - self.last_print_time) >= self.print_interval:
                            self.last_print_time = current_time

                            btc_prices_arr = np.array(self.price_buffer, dtype=np.float64)
                            btc_vol_arr = np.array(self.volume_buffers["BTCUSDT"], dtype=np.float64)
                            eth_prices_arr = np.array(self.market_buffers["ETHUSDT"], dtype=np.float64)

                            # --- MODIFICACIÓN REQUERIDA (BLOQUE MONITOR) ---
                            # Desempaquetamos la tupla aquí también para el renderizado
                            clima_actual, longevidad_actual = TrendAnalyzer.get_market_climate(list(self.price_buffer), is_scalper=self.is_scalper)
                            total_equity = self.trading.get_total_equity(price)

                            self.save_current_state(total_equity)

                            btc_rvol = calculate_rvol(btc_vol_arr)
                            eth_corr = calculate_pearson_correlation(btc_prices_arr, eth_prices_arr)

                            pnl_c = "\033[32m" if self.trading.daily_pnl >= 0 else "\033[31m"
                            c_map = {"TRENDING_UP": "\033[32m", "TRENDING_DOWN": "\033[31m", "RANGING": "\033[34m", "RANGING_DEAD": "\033[33m"}
                            c_color = c_map.get(clima_actual, "\033[0m")

                            # Renderizamos incluyendo el contador de ticks de longevidad (longevidad_actual)
                            print(f"📊 [{self.trading.mode}] [BTC: ${price:,.2f}] Clima: {c_color}{clima_actual} ({longevidad_actual}t)\033[0m | "
                                  f"RVOL: {btc_rvol:.2f} | CorrETH: {eth_corr:.2f} | "
                                  f"TOTAL: ${total_equity:.2f} | PnL Diar: {pnl_c}${self.trading.daily_pnl:.2f}\033[0m")

                    else:
                        if symbol in self.market_buffers:
                            self.market_buffers[symbol].append(price)

            except Exception as e:
                self.logger.warning(f"⚠️ Stream interrumpido en bucle principal: {e}. Activando protocolo de reconexión...")
                await asyncio.sleep(4)

                try:
                    self.logger.info("🔄 Re-descargando 500 periodos macro para limpiar buffers tras el corte de red...")
                    historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=500)

                    if historico:
                        self.trading.sincronizar_estado(historico[-1])

                        # --- LANZAMIENTO DE LA BRÚJULA EN SEGUNDO PLANO (CERO PARÁLISIS) ---
                        # Definimos el intervalo macro: 15 minutos para scalper, 1 hora para swing tradicional
                        macro_interval_str = "15m" if self.is_scalper else "1h"

                        async def macro_background_loop():
                            while True:
                                await self.macro_analyzer.update_trend(symbol="BTCUSDT", interval=macro_interval_str)
                                await asyncio.sleep(60) # Se ejecuta de forma aislada cada 1 minuto

                        # asyncio.create_task delega la ejecución al loop de fondo sin bloquear los ticks entrantes
                        asyncio.create_task(macro_background_loop())
                        # -------------------------------------------------------------------

                        self.price_buffer.clear()
                        for p in historico:
                            self.price_buffer.append(p)

                        precio_actual_post_corte = historico[-1]
                        self.trading.sincronizar_estado(precio_actual_post_corte)

                        if self.trading.active_position:
                            self.logger.info("🕵️ Analizando si se ejecutaron stops o targets de la posición activa durante el apagón...")
                            self.trading.ejecutar_simulacion(precio_actual_post_corte)

                    self.logger.info("⚡ [SISTEMA BLINDADO] Conexión estabilizada y buffers purgados con éxito.")

                except Exception as ex_reconnect:
                    self.logger.error(f"❌ Fallo en el intento de estabilización: {ex_reconnect}. Reintentando en el próximo ciclo...")
                    await asyncio.sleep(5)

    def save_current_state(self, total_equity):
        with self.Session() as session:
            new_state = BotState(
                total_balance=self.trading.balance,
                daily_pnl=self.trading.daily_pnl,
                current_mode=self.trading.mode,
                is_active=1
            )
            session.add(new_state)
            session.commit()

