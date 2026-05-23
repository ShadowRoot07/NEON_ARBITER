import logging
from database.schema import Trades, BotState, sessionmaker, engine as db_engine
from datetime import datetime, timedelta

class TradingLogic:
    def __init__(self, initial_test_balance=None, is_scalper=False, mode="DAY"):
        self.logger = logging.getLogger("NEON.TRADING")
        self.test_mode = initial_test_balance is not None

        self.initial_balance = initial_test_balance if self.test_mode else 0.0
        self.balance = self.initial_balance
        self.inventory = 0.0
        self.active_position = None
        self.daily_pnl = 0.0
        self.max_loss_limit = 0.05 

        # Freno de Mano y Contexto
        self.last_trade_time = None
        self.cooldown_minutes = 3 
        self.modo_conservador = False
        
        # --- NUEVA BANDERA DEL PROTOCOLO DE RED ---
        self.net_unstable = False 

        self.mode = "SCALPER" if is_scalper else mode

        if is_scalper:
            self.stop_loss_pct, self.trailing_pct = 0.003, 0.002
        else:
            self.stop_loss_pct, self.trailing_pct = 0.01, 0.005

    def get_total_equity(self, current_price):
        valor_crypto = self.inventory * current_price
        return self.balance + valor_crypto

    def can_trade(self):
        """Bloquea operaciones si el internet es inestable, si hay pérdidas o cooldown."""
        # BLOQUEO CRÍTICO: Si el escudo detecta red precaria, prohíbe abrir nuevos trades
        if self.net_unstable:
            return False

        if self.initial_balance == 0.0:
            return True
        limit = self.initial_balance * self.max_loss_limit
        if self.daily_pnl <= -limit:
            return False

        if self.mode == "SCALPER" and self.last_trade_time:
            if datetime.now() < self.last_trade_time + timedelta(minutes=self.cooldown_minutes):
                return False

        return True

    def obtener_autocontexto_db(self):
        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            ventas = session.query(Trades).filter(Trades.side == "SELL").order_by(Trades.id.desc()).limit(2).all()
            if len(ventas) >= 2:
                if self.daily_pnl < 0:
                    self.modo_conservador = True
                    self.logger.warning("⚠️ [CONCIENCIA] Detectada racha negativa. Activando MODO CONSERVADOR.")
                    return
            self.modo_conservador = False

    def abrir_posicion_test(self, precio, clima="RANGING", confianza=0.0):
        self.obtener_autocontexto_db()

        # can_trade() ya evalúa si self.net_unstable está activo
        if not self.can_trade() or self.balance < 10.0:
            return

        if self.mode == "SCALPER" and clima == "RANGING_DEAD":
            pct_inversion = 0.40
        else:
            pct_inversion = 0.60 if clima == "TRENDING_UP" else 0.30

        if self.modo_conservador:
            pct_inversion *= 0.5
            self.logger.info(f"🛡️ Aplicando reducción de riesgo por Modo Conservador: Exposición al {pct_inversion*100:.1f}%")

        monto_a_invertir = self.balance * pct_inversion

        if monto_a_invertir < 11.0:
            monto_a_invertir = self.balance if self.balance >= 11.0 else 0.0
        if monto_a_invertir <= 0:
            return

        current_sl_pct = self.stop_loss_pct if clima != "TRENDING_UP" else self.stop_loss_pct * 1.5
        take_profit_pct = current_sl_pct * 2.0

        self.inventory = monto_a_invertir / precio
        self.active_position = {
            'entry': precio,
            'sl': precio * (1 - current_sl_pct),
            'tp': precio * (1 + take_profit_pct),
            'clima_origen': clima,
            'confianza_origen': confianza  # Guardado en el diccionario de la posición viva
        }
        self.balance -= monto_a_invertir

        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            # Guardamos el registro del trade en la tabla de operaciones
            nuevo_trade = Trades(symbol="BTCUSDT", side="BUY", amount=self.inventory, price=precio)
            session.add(nuevo_trade)
            
            # --- NUEVA AUDITORÍA DEL GATILLO UNIFICADO (Paso 4) ---
            registro_auditoria = AIAudit(decision=f"ALGO_BUY_{clima}", confidence=float(confianza))
            session.add(registro_auditoria)
            # ------------------------------------------------------
            
            session.commit()

        self.logger.info(
            f"🛒 COMPRA EN DB: {self.inventory:.6f} BTC | SL: {current_sl_pct*100:.2f}% | "
            f"TP: {take_profit_pct*100:.2f}% | GATILLO UNIFICADO (Confianza: {confianza*100:.1f}%)"
        )

    def ejecutar_simulacion(self, precio_actual):
        if not self.active_position:
            return
        pos = self.active_position
        precio_entrada = pos['entry']

        if precio_actual >= pos.get('tp', float('inf')):
            self.cerrar_posicion_test(precio_actual, "TAKE_PROFIT")
            return

        if self.mode == "SCALPER":
            rendimiento = (precio_actual - precio_entrada) / precio_entrada
            target_sl_breakeven = precio_entrada * (1 + 0.0002)
            if rendimiento >= 0.0015 and pos['sl'] < target_sl_breakeven:
                pos['sl'] = target_sl_breakeven
                self.logger.info(f"🛡️ [BREAKEVEN BLINDADO] Ajustado stop de seguridad a: ${target_sl_breakeven:,.2f}")
            elif rendimiento >= 0.0035:
                nuevo_sl_scalper = precio_actual * (1 - 0.0010)
                if nuevo_sl_scalper > pos['sl']:
                    pos['sl'] = nuevo_sl_scalper

        elif self.mode != "SCALPER" and precio_actual > precio_entrada:
            nuevo_sl_potencial = precio_actual * (1 - self.trailing_pct)
            if nuevo_sl_potencial > pos['sl']:
                pos['sl'] = nuevo_sl_potencial

        if precio_actual <= pos['sl']:
            if pos['sl'] >= precio_entrada:
                motivo_salida = "BREAKEVEN_EXIT"
            elif pos['sl'] > precio_entrada * (1 + 0.0002):
                motivo_salida = "TRAILING_SCALPER"
            else:
                motivo_salida = "STOP_LOSS"
            self.cerrar_posicion_test(precio_actual, motivo_salida)

    def forzar_cierre_panico(self, precio_actual):
        """Ejecuta una salida inmediata del mercado si la red está muriendo y hay peligro de vuelco."""
        if not self.active_position:
            return
        self.logger.warning("🚨 [CONCIENCIA DE RED] Forzando PANIC_CLOSE preventivo por degradación crítica de internet.")
        self.cerrar_posicion_test(precio_actual, "PANIC_CLOSE_RED")

    def sincronizar_estado(self, precio_actual):
        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            state = session.query(BotState).order_by(BotState.id.desc()).first()
            if state:
                self.balance = state.total_balance
                if self.initial_balance == 0.0:
                    self.initial_balance = state.total_balance
                self.daily_pnl = state.daily_pnl
                self.logger.info(f"💰 Balance recuperado de Neon: ${self.balance:.2f} | PnL Hoy: ${self.daily_pnl:.2f}")
            else:
                self.logger.info("🆕 No se encontró un estado previo en BotState. Usando valores por defecto.")

            last_trade = session.query(Trades).order_by(Trades.id.desc()).first()
            if last_trade and last_trade.side == "BUY":
                self.logger.info(f"🔄 [RECONEXIÓN] Recuperando posición activa desde el precio exacto de DB: ${last_trade.price:,.2f}")
                self.inventory = last_trade.amount
                sl = last_trade.price * (1 - self.stop_force_pct) if hasattr(self, 'stop_force_pct') else last_trade.price * (1 - self.stop_loss_pct)
                tp = last_trade.price * (1 + (self.stop_loss_pct * 2.0))
                self.active_position = {
                    'entry': last_trade.price,
                    'sl': sl,
                    'tp': tp
                }
                self.logger.info(f"📡 Estado sincronizado con éxito. Posición restaurada: {self.inventory:.6f} BTC | SL original: ${sl:,.2f}")
            else:
                self.active_position = None
                self.inventory = 0.0
                self.logger.info("🆕 No existen posiciones colgadas en Trades. Operando balance limpio.")

    def cerrar_posicion_test(self, precio_actual, motivo="EXIT"):
        if not self.active_position:
            return
        pos = self.active_position
        precio_entrada = pos['entry']

        rendimiento = (precio_actual - precio_entrada) / precio_entrada
        efectivo_recuperado = self.inventory * precio_actual
        monto_inicial_invertido = self.inventory * precio_entrada
        pnl_trade = efectivo_recuperado - monto_inicial_invertido

        self.balance += efectivo_recuperado
        self.inventory = 0.0
        self.daily_pnl += pnl_trade
        self.last_trade_time = datetime.now()  

        self.logger.info(
            f"⚡ [VENTA SIM] Motivo: {motivo} | Entrada: ${precio_entrada:,.2f} | "
            f"Salida: ${precio_actual:,.2f} | PnL Trade: ${pnl_trade:+.2f} ({rendimiento*100:+.2f}%)"
        )

        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            nuevo_trade = Trades(
                symbol="BTCUSDT",
                side="SELL",
                amount=monto_inicial_invertido / precio_entrada,
                price=precio_actual
            )
            session.add(nuevo_trade)
            session.commit()

        self.active_position = None

