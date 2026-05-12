import asyncio
import logging
import ujson
from collections import deque
from api.binance_client import BinanceClient
from api.groq_client import GroqClient
from config import Config
from core.trading_logic import TradingLogic
from core.strategies.multitimeframe_strategy import MultiTimeframeStrategy
from database.schema import engine, MarketData, sessionmaker
from datetime import datetime

class Engine:
    def __init__(self, test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.is_scalper = is_scalper
        self.cfg = Config()
        self.client = BinanceClient()
        self.groq = GroqClient(api_key=self.cfg.groq_api_key)
        self.Session = sessionmaker(bind=engine)
        self.trading = TradingLogic(initial_test_balance=test_balance, is_scalper=is_scalper)
        self.strategy = MultiTimeframeStrategy()
        self.tick_count = 0
        self.price_buffer = deque(maxlen=3600)
        self.tick_interval = 10 if is_scalper else 30

    async def pedir_decision_ia(self, context):
        tengo_btc = self.trading.inventory > 0

        # Usamos .get() para evitar el error 'KeyError' si el buffer es joven
        micro = context.get('micro', {})
        macro = context.get('macro', {})

        ctx_min = {
            "m_trend": micro.get('trend', 'NEUTRAL'),
            "m_change": round(micro.get('change_pct', 0), 4),
            "macro": macro.get('momentum', 'STABLE'),
            "vol": round(micro.get('volatility', 0), 2)
        }

        instrucciones = "MODO SCALPER: Prioriza micro-tendencias." if self.is_scalper \
            else "MODO NORMAL: Prioriza tendencias macro."

        confianza_min = 0.55 if self.is_scalper else 0.75

        prompt = f"{instrucciones} | CTX: {ctx_min} | POS: {tengo_btc}. JSON: decision, motivo, confianza."

        try:
            respuesta = await self.groq.get_decision(prompt, model="llama-3.1-8b-instant")
            return ujson.loads(respuesta['choices'][0]['message']['content'])
        
        except Exception as e:
            if "rate_limit_exceeded" in str(e).lower():
                self.logger.warning("🕒 Límite de API alcanzado. Esperando 30s para enfriar...")
                await asyncio.sleep(30)
            else:
                self.logger.error(f"Error en decisión IA: {e}")
            return {"decision": "HOLD", "motivo": "API_LIMIT_REACHED", "confianza": 0}

    async def run_bot(self):
        self.logger.info(f"🚀 NEON ARBITER: {'MODO SCALPER' if self.is_scalper else 'MODO NORMAL'}")
        
        # --- WARM UP: Carga de datos históricos ---
        historico = await self.client.get_historical_data(limit=300)
        for p in historico:
            self.price_buffer.append(p)
        self.logger.info(f"✅ Buffer precargado con {len(self.price_buffer)} puntos. ¡Listo para analizar!")

        try:
            async for data in self.client.connect():
                price = float(data['c'])
                self.price_buffer.append(price)
                self.tick_count += 1

                if self.trading.test_mode:
                    self.trading.ejecutar_simulacion(price)

                    if self.tick_count % self.tick_interval == 0:
                        context = self.strategy.analyze(self.price_buffer)
                        if context:
                            analisis = await self.pedir_decision_ia(context)
                            decision, confianza = analisis.get('decision'), analisis.get('confianza', 0)
                            self.logger.info(f"🤔 IA ({'SCALP' if self.is_scalper else 'NORM'}): {decision} ({confianza})")

                            if self.strategy.should_execute(decision, confianza) or (self.is_scalper and confianza >= 0.55):
                                if decision == 'BUY' and not self.trading.active_position:
                                    self.trading.abrir_posicion_test(price)
                                elif decision == 'SELL' and self.trading.active_position:
                                    self.trading.cerrar_posicion_test(price, "IA_STRATEGY")

                if self.tick_count % 10 == 0:
                    total = self.trading.balance + (self.trading.inventory * price)
                    print(f"📊 MONITOR: Balance ${total:.2f} | Ticks: {self.tick_count}")

        except Exception as e:
            self.logger.error(f"❌ Error: {e}")

    def start(self):
        try: asyncio.run(self.run_bot())
        except KeyboardInterrupt: self.logger.warning("🛑 Apagado.")

