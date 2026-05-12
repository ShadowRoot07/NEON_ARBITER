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
from database.schema import AIAudit, sessionmaker, engine as db_engine
from datetime import datetime


class Engine:
    def __init__(self, test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.ENGINE")
        self.is_scalper = is_scalper
        self.cfg = Config()
        self.client = BinanceClient()
        self.groq = GroqClient(api_key=self.cfg.groq_api_key)
        self.trading = TradingLogic(initial_test_balance=test_balance, is_scalper=is_scalper)
        self.strategy = MultiTimeframeStrategy()
        self.market_buffers = { "ETHUSDT": deque(maxlen=100), "SOLUSDT": deque(maxlen=100) }
        
        self.tick_count = 0
        self.price_buffer = deque(maxlen=3600)
        # MEMORIA DE DECISIONES
        self.decision_history = deque(maxlen=self.cfg.ai_history_limit)
        
        self.tick_interval = 10 if is_scalper else 30
        self.last_ai_tick = 0
        self.cooldown_ticks = 5
        self.Session = sessionmaker(bind=db_engine)

    async def pedir_decision_ia(self, context):
        tengo_btc = self.trading.inventory > 0
        micro = context.get('micro', {})
        macro = context.get('macro', {})
        m_context = context.get('market_context', 'NEUTRAL')

        hist_str = " | ".join([f"{d['decision']}({d['motivo']})" for d in self.decision_history])

        ctx_min = {
            "m_trend": micro.get('trend', 'NEUTRAL'),
            "m_change": round(micro.get('change_pct', 0), 4),
            "macro": macro.get('momentum', 'STABLE'),
            "market_mood": m_context,
            "vol": round(micro.get('volatility', 0), 2),
            "hist_prev": hist_str
        }

        prompt = (
            f"SCALP:{self.is_scalper} | CTX:{ctx_min} | POS:{tengo_btc}. "
            f"RESPONDE SOLO JSON: {{\"decision\": \"BUY/SELL/HOLD\", \"motivo\": \"...\", \"confianza\": 0.0-1.0}}"
        )

        try:
            respuesta = await self.groq.get_decision(prompt, model="llama-3.1-8b-instant")
            content = respuesta['choices'][0]['message']['content']

            # Limpieza de Markdown si Groq lo incluye
            if "```json" in content:
                content = content.split("
```json")[1].split("```")[0]
            
            res_json = ujson.loads(content)

            # Normalización de confianza y valores
            decision = res_json.get('decision', 'HOLD')
            conf = res_json.get('confianza', 0)
            if conf > 1: conf = conf / 100 # Maneja escala 0-100 si la IA se confunde
            
            res_json['confianza'] = conf
            motivo = res_json.get('motivo', 'Sin motivo')

            # Feedback visual
            color = "\033[1;34m" if decision == "HOLD" else "\033[1;33m"
            print(f"{color}🧠 IA PENSÓ: {decision} ({conf*100:.0f}%) | Motivo: {motivo}\033[0m")

            # --- PERSISTENCIA EN DB (AIAudit) ---
            try:
                with self.Session() as session:
                    audit_entry = AIAudit(
                        timestamp=datetime.now(),
                        decision=decision,
                        confidence=conf
                    )
                    session.add(audit_entry)
                    session.commit()
            except Exception as db_e:
                self.logger.error(f"⚠️ Error guardando auditoría: {db_e}")

            # Guardar en historial de memoria para el próximo prompt
            if decision != "HOLD":
                self.decision_history.append({
                    "decision": decision,
                    "motivo": motivo
                })

            return res_json

        except Exception as e:
            self.logger.error(f"❌ Error crítico en pedir_decision_ia: {e}")
            return {"decision": "HOLD", "motivo": "PARSE_ERROR", "confianza": 0}

    async def run_bot(self):
        self.logger.info(f"🚀 NEON ARBITER: MODO MULTI-STREAM (BTC, ETH, SOL)")

        # 1. Sincronización Inicial (Reinicio Invisible)
        # Obtenemos el último precio de BTC para que la lógica de recuperación tenga contexto
        historico_inicial = await self.client.get_historical_data(symbol="BTCUSDT", limit=1)
        if historico_inicial:
            precio_actual_init = historico_inicial[-1]
            self.trading.sincronizar_estado(precio_actual_init)

        # 2. Configuración de Buffers
        self.market_buffers = {
            "ETHUSDT": deque(maxlen=100),
            "SOLUSDT": deque(maxlen=100)
        }

        # Warm up: Llenamos el buffer de BTC para tener datos de análisis inmediatos
        historico = await self.client.get_historical_data(symbol="BTCUSDT", limit=500)
        for p in historico:
            self.price_buffer.append(p)

        while True:
            try:
                async for data in self.client.connect():
                    symbol = data['s_name']
                    price = float(data['c'])

                    # --- GESTIÓN DE BTC (Eje de Trading) ---
                    if symbol == "BTCUSDT":
                        self.price_buffer.append(price)
                        self.tick_count += 1

                        if not self.trading.can_trade():
                            if self.tick_count % 100 == 0:
                                self.logger.error("🚨 STOP DIARIO ACTIVO. Bot en espera.")
                            continue

                        if self.trading.test_mode:
                            # Ejecutar Trailing Stop y lógica de salida automática
                            self.trading.ejecutar_simulacion(price)

                            # Lógica de consulta a la IA (Oráculo Spica)
                            time_to_ask = self.tick_count % self.tick_interval == 0
                            no_cooldown = (self.tick_count - self.last_ai_tick) > self.cooldown_ticks

                            if time_to_ask and no_cooldown:
                                context = self.strategy.analyze(
                                    self.price_buffer,
                                    extra_market_data=self.market_buffers
                                )

                                if context:
                                    analisis = await self.pedir_decision_ia(context)
                                    decision = analisis.get('decision')
                                    confianza = analisis.get('confianza', 0)

                                    if decision != 'HOLD':
                                        self.last_ai_tick = self.tick_count

                                    if self.strategy.should_execute(decision, confianza):
                                        if decision == 'BUY' and not self.trading.active_position:
                                            self.trading.abrir_posicion_test(price)
                                        elif decision == 'SELL' and self.trading.active_position:
                                            self.trading.cerrar_posicion_test(price, "IA_STRATEGY")

                        # Monitor visual de rendimiento
                        if self.tick_count % 20 == 0:
                            total = self.trading.balance + (self.trading.inventory * price)
                            pnl_c = "\033[32m" if self.trading.daily_pnl >= 0 else "\033[31m"
                            print(f"📊 [BTC: ${price:,.2f}] | Balance: ${total:.2f} | PnL Diar: {pnl_c}${self.trading.daily_pnl:.2f}\033[0m")

                    # --- GESTIÓN DE ALTS (Consciencia de Mercado) ---
                    else:
                        if symbol in self.market_buffers:
                            self.market_buffers[symbol].append(price)

            except Exception as e:
                self.logger.warning(f"🔄 Error en el loop principal: {e}. Reintentando en 10s...")
                await asyncio.sleep(10)

    def start(self):
        try: asyncio.run(self.run_bot())
        except KeyboardInterrupt: self.logger.warning("🛑 Apagado por usuario.")

