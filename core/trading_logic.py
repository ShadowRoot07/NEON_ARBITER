import logging
from database.schema import Trades, sessionmaker, engine as db_engine
from datetime import datetime

class TradingLogic:
    def __init__(self, initial_test_balance=None, is_scalper=False, mode="DAY"):
        self.logger = logging.getLogger("NEON.TRADING")
        self.test_mode = initial_test_balance is not None
        self.balance = initial_test_balance if self.test_mode else 0.0
        self.inventory = 0.0
        self.active_position = None
        self.daily_pnl = 0.0
        self.mode = mode # Guardamos el modo actual
        self.max_loss_limit = 0.05 # 5% para Day Trading

        # Configuración de stops según modo
        if is_scalper:
            self.stop_loss_pct, self.trailing_pct = 0.003, 0.002
        else:
            self.stop_loss_pct, self.trailing_pct = 0.01, 0.005 # Más holgura para Day TradingLogic

    def get_total_equity(self, current_price):
        """Cálculo infalible del patrimonio total"""
        valor_crypto = self.inventory * current_price
        return self.balance + valor_crypto

    def sincronizar_estado(self, precio_actual):
        """Recupera el estado exacto de la DB incluyendo el balance sobrante"""
        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            # 1. Recuperar el balance de efectivo guardado
            state = session.query(BotState).order_by(BotState.id.desc()).first()
            if state:
                self.balance = state.total_balance
                self.daily_pnl = state.daily_pnl
                self.logger.info(f"💰 Balance recuperado: ${self.balance:.2f} | PnL Hoy: ${self.daily_pnl:.2f}")

            # 2. Recuperar posición abierta
            last_trade = session.query(Trades).order_by(Trades.id.desc()).first()
            if last_trade and last_trade.side == "BUY":
                self.inventory = last_trade.amount
                # El balance ya se recuperó arriba, no lo seteamos a 0.0
                self.active_position = {
                    'entry': last_trade.price,
                    'sl': last_trade.price * (1 - self.stop_loss_pct),
                    'tp': last_trade.price * (1 + (self.stop_loss_pct * 2))
                }
                self.logger.info(f"📦 Posición reabierta: {self.inventory:.6f} BTC")


    def can_trade(self):
        """Verifica si no hemos quemado el límite diario"""
        limit = self.initial_balance * self.max_loss_limit
        if self.daily_pnl <= -limit:
            return False
        return True

    def abrir_posicion_test(self, precio, clima="RANGING"):
        if not self.can_trade() or self.balance < 10.0: return

        # 1. Porcentaje de inversión dinámico
        # 60% en tendencia clara, 30% en rangos (más cautela)
        pct_inversion = 0.60 if clima == "TRENDING_UP" else 0.30
        monto_a_invertir = self.balance * pct_inversion
        
        if monto_a_invertir < 11.0: 
            monto_a_invertir = self.balance if self.balance >= 11.0 else 0.0
        if monto_a_invertir <= 0: return

        # 2. SL y TP (Take Profit) dinámicos
        # En modo Swing (normal), buscamos un ratio 2:1 (ganar el doble de lo que arriesgamos)
        current_sl_pct = self.stop_loss_pct if clima != "TRENDING_UP" else self.stop_loss_pct * 1.5
        take_profit_pct = current_sl_pct * 2.0 # Objetivo de ganancia

        self.inventory = monto_a_invertir / precio
        self.active_position = {
            'entry': precio,
            'sl': precio * (1 - current_sl_pct),
            'tp': precio * (1 + take_profit_pct), # <--- NUEVO
            'clima_origen': clima
        }
        self.balance -= monto_a_invertir
        self.logger.info(f"🛒 COMPRA: {self.inventory:.6f} BTC | SL: {current_sl_pct*100:.2f}% | TP: {take_profit_pct*100:.2f}%")

    def ejecutar_simulacion(self, precio_actual):
        if not self.active_position: return
        pos = self.active_position

        # A. Verificar Take Profit (TP)
        if precio_actual >= pos.get('tp', float('inf')):
            self.cerrar_posicion_test(precio_actual, "TAKE_PROFIT")
            return

        # B. Trailing Stop Loss mejorado
        # Solo sube el SL si ya estamos en ganancias (protección de profit)
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

        # 1. Calcular cuánto dinero recibimos por la venta
        monto_venta = self.inventory * precio
        
        # 2. Calcular la ganancia o pérdida neta
        monto_inicial = self.inventory * self.active_position['entry']
        pnl_operacion = monto_venta - monto_inicial
        
        # --- EL ARREGLO CRÍTICO AQUÍ ---
        # Sumamos el dinero de la venta al balance que ya teníamos (el 70% restante)
        self.balance += monto_venta 
        # -------------------------------

        self.daily_pnl += pnl_operacion
        self.inventory = 0.0
        self.active_position = None

        self.logger.info(f"✅ VENTA ({motivo}): ${precio:,.2f} | PnL: {pnl_operacion:+.2f}")
        print(f">>> RESULTADO OPERACIÓN: ${pnl_operacion:+.2f} ({motivo}) | PnL Diario: {self.daily_pnl:.2f}")

    def sincronizar_estado(self, precio_actual):
        """
        Busca en la DB la última operación para recuperar posiciones abiertas tras un reinicio.
        """
        from database.schema import Trades, sessionmaker, engine
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # Buscamos la última transacción de este símbolo
            last_trade = session.query(Trades).order_by(Trades.id.desc()).first()
            
            if last_trade and last_trade.side == "BUY":
                self.logger.info(f"🔄 RECOBRANDO POSICIÓN: Detectada compra previa a ${last_trade.price:,.2f}")
                
                # Restauramos inventario y posición activa
                # Asumimos que usamos todo el balance previo para esa compra
                self.inventory = last_trade.amount
                self.balance = 0.0
                
                sl = last_trade.price * (1 - self.stop_loss_pct)
                self.active_position = {
                    'entry': last_trade.price, 
                    'sl': sl
                }
                print(f"📡 Estado sincronizado. Posición abierta: {self.inventory:.6f} BTC | SL: ${sl:,.2f}")
            else:
                self.logger.info("🆕 No hay posiciones abiertas detectadas en DB. Iniciando con balance limpio.")


