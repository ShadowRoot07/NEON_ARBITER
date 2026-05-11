import asyncio
import logging
import ujson
from collections import deque
from api.binance_client import BinanceClient
from api.groq_client import GroqClient
from config import Config
from core.trading_logic import TradingLogic
# IMPORTANTE: Nueva ruta para la estrategia robusta
from core.strategies.multitimeframe_strategy import MultiTimeframeStrategy
from database.schema import engine, MarketData, sessionmaker, AIAudit
from datetime import datetime

class Engine:
    def __init__(self, test_balance=None):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.cfg = Config()
        self.client = BinanceClient()
        self.groq = GroqClient(api_key=self.cfg.groq_api_key)
        self.Session = sessionmaker(bind=engine)
        self.trading = TradingLogic(initial_test_balance=test_balance)
        self.strategy = MultiTimeframeStrategy()
        self.tick_count = 0
        # 3600 ticks = 1 hora de memoria RAM si recibimos 1 tick por segundo
        self.price_buffer = deque(maxlen=3600) 

    async def pedir_decision_ia(self, context):
        tengo_btc = self.trading.inventory > 0
        
        # Ajustamos el acceso a datos según el nuevo MultiTimeframeStrategy
        micro_trend = context['micro']['trend']
        meso_change = context['meso']['change_pct']
        macro_mom = context['macro']['momentum']

        prompt = f"""
        ACTÚA COMO ORÁCULO DE TRADING PROFESIONAL.
        CONTEXTO MULTI-CAPA:
        - MICRO (Tendencia): {micro_trend}
        - MESO (Cambio 10m): {meso_change:.4f}%
        - MACRO (Momentum 1h): {macro_mom}
        - Volatilidad Micro: {context['micro']['volatility']:.2f}

        ESTADO: {'CON POSICIÓN' if tengo_btc else 'SIN POSICIÓN'}

        TAREA: Analiza si el MICRO es una anomalía o sigue la tendencia MACRO.
        Responde SOLO JSON: {{"decision": "BUY/SELL/HOLD", "motivo": "...", "confianza": 0.0-1.0}}
        """
        try:
            respuesta = await self.groq.get_decision(prompt)
            return ujson.loads(respuesta['choices'][0]['message']['content'])
        except:
            return {"decision": "HOLD"}

    async def run_bot(self):
        self.logger.info("🚀 NEON ARBITER: Modo Multicapa + Trailing Activo.")

        async for data in self.client.connect():
            price = float(data['c'])
            self.price_buffer.append(price)
            self.tick_count += 1

            if self.tick_count % 1 == 0:  # Ver CADA tick
                    print(f"DEBUG: Tick #{self.tick_count} | Precio: {price}")

            if self.trading.test_mode:
                self.trading.ejecutar_simulacion(price)

                # Cambiamos analyze_trends por analyze
                self.logger.debug(f"Tick #{self.tick_count} recibido: {price}")
                if self.tick_count % 10 == 0 and len(self.price_buffer) >= 60:
                    self.logger.info("🧠 Analizando contexto...")
                    context = self.strategy.analyze(self.price_buffer)

                    if context:
                        analisis = await self.pedir_decision_ia(context)
                        decision = analisis.get('decision')
                        confianza = analisis.get('confianza', 0)
                        
                        if self.strategy.should_execute(decision, confianza):
                            if decision == 'BUY' and not self.trading.active_position:
                                self.logger.info(f"⚡ ORÁCULO VALIDADO ({confianza}): {analisis.get('motivo')}")
                                self.trading.abrir_posicion_test(price)
                            elif decision == 'SELL' and self.trading.active_position:
                                self.logger.info(f"🔥 VENTA DE EMERGENCIA ({confianza}): {analisis.get('motivo')}")
                                self.trading.cerrar_posicion_test(price, "IA_STRATEGY")
                        else: # Identación corregida aquí
                            print("DEBUG: Contexto aún no listo (Estrategia retornó None)")

                            if decision != 'HOLD':
                                self.logger.info(f"⚠️ FILTRADO: Confianza baja ({confianza}) para {decision}")
                if self.tick_count % 5 == 0:
                    total = self.trading.balance + (self.trading.inventory * price)
                    print(f"📊 MONITOR: Balance actual ${total:.2f}")

    def start(self):
        try: asyncio.run(self.run_bot())
        except KeyboardInterrupt: self.stop()

    def stop(self):
        self.logger.warning("🛑 Sistema apagado.")

