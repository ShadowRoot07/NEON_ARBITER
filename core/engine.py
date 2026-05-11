import asyncio
import logging
import ujson
from api.binance_client import BinanceClient
from api.groq_client import GroqClient
from config import Config
from core.trading_logic import TradingLogic
from database.schema import engine, MarketData, sessionmaker
from datetime import datetime

class Engine:
    def __init__(self, test_balance=None):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.cfg = Config()
        self.client = BinanceClient()
        self.groq = GroqClient(api_key=self.cfg.groq_api_key)
        self.Session = sessionmaker(bind=engine)
        self.trading = TradingLogic(initial_test_balance=test_balance)
        self.tick_count = 0

    async def pedir_decision_ia(self, historico_precios):
        tengo_btc = self.trading.inventory > 0
        prompt = f"""
        Analiza BTC/USDT. Historial (20 ticks): {historico_precios}
        Estado: {'CON POSICIÓN' if tengo_btc else 'SIN POSICIÓN'}
        
        Responde SOLO JSON:
        - Si SIN POSICIÓN y subirá: {{"decision": "BUY", "motivo": "..."}}
        - Si CON POSICIÓN y caerá: {{"decision": "SELL", "motivo": "..."}}
        - De lo contrario: {{"decision": "HOLD", "motivo": "..."}}
        """
        try:
            respuesta = await self.groq.get_decision(prompt)
            return ujson.loads(respuesta['choices'][0]['message']['content'])
        except:
            return {"decision": "HOLD"}

    async def run_bot(self):
        self.logger.info("📡 NEON ARBITER: IA y Motor en línea.")

        async for data in self.client.connect():
            price = float(data['c'])
            self.tick_count += 1

            if self.trading.test_mode:
                self.trading.ejecutar_simulacion(price)

                # Consultar IA cada 30 ticks
                if self.tick_count % 30 == 0:
                    with self.Session() as session:
                        rows = session.query(MarketData).order_by(MarketData.id.desc()).limit(20).all()
                        precios = [r.close for r in reversed(rows)]

                    if len(precios) >= 20:
                        self.logger.info("🧠 Consultando al Oráculo...")
                        analisis = await self.pedir_decision_ia(precios)
                        decision = analisis.get('decision')

                        if decision == 'BUY' and not self.trading.active_position:
                            self.logger.info(f"⚡ IA COMPRA: {analisis.get('motivo')}")
                            self.trading.abrir_posicion_test(price)
                        elif decision == 'SELL' and self.trading.active_position:
                            self.logger.info(f"🔥 IA VENTA: {analisis.get('motivo')}")
                            self.trading.cerrar_posicion_test(price, "IA_STRATEGY")
                        else:
                            self.logger.info(f"💤 IA HOLD: {analisis.get('motivo')}")

            if self.tick_count % 10 == 0:
                total = self.trading.balance + (self.trading.inventory * price)
                self.logger.info(f"📊 BTC: ${price:,.2f} | Billetera: ${total:.2f}")

            try:
                with self.Session() as session:
                    session.add(MarketData(timestamp=datetime.now(), close=price, volume=float(data['v'])))
                    session.commit()
            except Exception as e: self.logger.error(f"DB Error: {e}")

    def start(self):
        try: asyncio.run(self.run_bot())
        except KeyboardInterrupt: self.stop()

    def stop(self):
        self.logger.warning("🛑 Sistema apagado.")

