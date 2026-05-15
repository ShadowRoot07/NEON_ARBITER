import logging
from database.schema import Trades, BotState, sessionmaker, engine as db_engine
from datetime import datetime

class TradingLogic:
    def __init__(self, initial_test_balance=None, is_scalper=False, mode="DAY"):
        self.logger = logging.getLogger("NEON.TRADING")
        self.test_mode = initial_test_balance is not None
        
        # Guardamos el balance inicial para el cálculo de límites de pérdida
        self.initial_balance = initial_test_balance if self.test_mode else 0.0
        self.balance = self.initial_balance
        
        self.inventory = 0.0
        self.active_position = None
        self.daily_pnl = 0.0
        self.mode = mode 
        self.max_loss_limit = 0.05 # 5% límite máximo de pérdida diaria

        # Configuración de stops según el modo
        if is_scalper:
            self.stop_loss_pct, self.trailing_pct = 0.003, 0.002
        else:
            self.stop_loss_pct, self.trailing_pct = 0.01, 0.005 

    def get_total_equity(self, current_price):
        """Cálculo infalible del patrimonio total (Efectivo + Crypto)"""
        valor_crypto = self.inventory * current_price
        return self.balance + valor_crypto

    def can_trade(self):
        """Verifica si no hemos quemado el límite diario tolerado"""
        # Evita bloquear el bot si el balance inicial no se ha cargado de la DB aún
        if self.initial_balance == 0.0:
            return True
        limit = self.initial_balance * self.max_loss_limit
        if self.daily_pnl <= -limit:
            return False
        return True

    def abrir_posicion_test(self, precio, clima="RANGING"):
        if not self.can_trade() or self.balance < 10.0: 
            return

        # 1. Porcentaje de inversión dinámico según el clima del mercado
        pct_inversion = 0.60 if clima == "TRENDING_UP" else 0.30
        monto_a_invertir = self.balance * pct_inversion

        if monto_a_invertir < 11.0:
            monto_a_invertir = self.balance if self.balance >= 11.0 else 0.0
        if monto_a_invertir <= 0: 
            return

        # 2. SL y TP dinámicos
        current_sl_pct = self.stop_loss_pct if clima != "TRENDING_UP" else self.stop_loss_pct * 1.5
        take_profit_pct = current_sl_pct * 2.0 

        self.inventory = monto_a_invertir / precio
        self.active_position = {
            'entry': precio,
            'sl': precio * (1 - current_sl_pct),
            'tp': precio * (1 + take_profit_pct), 
            'clima_origen': clima
        }
        self.balance -= monto_a_invertir
        
        # Registrar la compra en la base de datos para persistencia de sesión
        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            nuevo_trade = Trades(symbol="BTCUSDT", side="BUY", amount=self.inventory, price=precio)
            session.add(nuevo_trade)
            session.commit()

        self.logger.info(f"🛒 COMPRA EN DB: {self.inventory:.6f} BTC | SL: {current_sl_pct*100:.2f}% | TP: {take_profit_pct*100:.2f}%")

    def ejecutar_simulacion(self, precio_actual):
        if not self.active_position: 
            return
        pos = self.active_position

        # A. Verificar Take Profit (TP)
        if precio_actual >= pos.get('tp', float('inf')):
            self.cerrar_posicion_test(precio_actual, "TAKE_PROFIT")
            return

        # B. Trailing Stop Loss
        if precio_actual > pos['entry']:
            nuevo_sl_potencial = precio_actual * (1 - self.trailing_pct)
            if nuevo_sl_potencial > pos['sl']:
                pos['sl'] = nuevo_sl_potencial

        # C. Verificar Stop Loss (SL)
        if precio_actual <= pos['sl']:
            self.cerrar_posicion_test(precio_actual, "STOP_LOSS/TRAILING")

    def cerrar_posicion_test(self, precio, motivo="EXIT"):
        if not self.active_position:
            return

        monto_venta = self.inventory * precio
        monto_inicial = self.inventory * self.active_position['entry']
        pnl_operacion = monto_venta - monto_inicial

        self.balance += monto_venta
        self.daily_pnl += pnl_operacion
        
        # Registrar la venta en la base de datos para cerrar el ciclo
        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            nueva_venta = Trades(symbol="BTCUSDT", side="SELL", amount=self.inventory, price=precio)
            session.add(nueva_venta)
            session.commit()

        self.inventory = 0.0
        self.active_position = None

        self.logger.info(f"✅ VENTA EN DB ({motivo}): ${precio:,.2f} | PnL: {pnl_operacion:+.2f}")
        print(f">>> RESULTADO OPERACIÓN: ${pnl_operacion:+.2f} ({motivo}) | PnL Diario: {self.daily_pnl:.2f}")

    def sincronizar_estado(self, precio_actual):
        """Recupera el estado exacto de la DB para heredar balances y posiciones entre ejecuciones"""
        Session = sessionmaker(bind=db_engine)

        with Session() as session:
            # 1. Recuperar balance general e historial de pérdidas diarias del BotState
            state = session.query(BotState).order_by(BotState.id.desc()).first()
            if state:
                self.balance = state.total_balance
                # Si es la primera ejecución simulada, establecemos el balance inicial recuperado
                if self.initial_balance == 0.0:
                    self.initial_balance = state.total_balance
                self.daily_pnl = state.daily_pnl
                self.logger.info(f"💰 Balance recuperado de Neon: ${self.balance:.2f} | PnL Hoy: ${self.daily_pnl:.2f}")
            else:
                self.logger.info("🆕 No se encontró un estado previo en BotState. Usando valores por defecto.")

            # 2. Recomponer la posición si la última operación fue una compra sin cerrar
            last_trade = session.query(Trades).order_by(Trades.id.desc()).first()

            if last_trade and last_trade.side == "BUY":
                self.logger.info(f"🔄 RECOBRANDO POSICIÓN ACTIVA: Compra previa detectada a ${last_trade.price:,.2f}")
                
                self.inventory = last_trade.amount
                sl = last_trade.price * (1 - self.stop_loss_pct)
                tp = last_trade.price * (1 + (self.stop_loss_pct * 2.0))
                
                self.active_position = {
                    'entry': last_trade.price,
                    'sl': sl,
                    'tp': tp
                }
                print(f"📡 Estado sincronizado. Posición restaurada: {self.inventory:.6f} BTC | SL: ${sl:,.2f}")
            else:
                self.logger.info("🆕 No existen posiciones colgadas en Trades. Operando balance limpio.")

