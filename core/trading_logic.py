import logging
from database.schema import Trades, sessionmaker, engine as db_engine
from datetime import datetime

class TradingLogic:
    def __init__(self, initial_test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.TRADING")
        self.test_mode = initial_test_balance is not None
        self.initial_balance = initial_test_balance if self.test_mode else 0.0
        self.balance = self.initial_balance
        self.inventory = 0.0
        self.active_position = None
        
        # Gestión de Riesgo
        self.daily_pnl = 0.0
        self.max_loss_limit = 0.02 # 2% (se puede jalar de Config)

        if is_scalper:
            self.stop_loss_pct = 0.0030 
            self.trailing_pct = 0.0020  
        else:
            self.stop_loss_pct = 0.005
            self.trailing_pct = 0.003

    def can_trade(self):
        """Verifica si no hemos quemado el límite diario"""
        limit = self.initial_balance * self.max_loss_limit
        if self.daily_pnl <= -limit:
            return False
        return True

    def ejecutar_simulacion(self, precio_actual):
        if not self.active_position: return
        pos = self.active_position
        nuevo_sl_potencial = precio_actual * (1 - self.trailing_pct)
        if nuevo_sl_potencial > pos['sl']:
            pos['sl'] = nuevo_sl_potencial
        if precio_actual <= pos['sl']:
            self.cerrar_posicion_test(precio_actual, "TRAILING_STOP")

    def abrir_posicion_test(self, precio, clima="RANGING"):
        # 1. Validaciones previas
        if not self.can_trade():
            self.logger.warning("⛔ Límite de pérdida diario alcanzado.")
            return

        if self.balance < 10.0:
            self.logger.warning(f"💸 Balance insuficiente para operar.")
            return

        # 2. Gestión de Riesgo Dinámica por Clima
        # Si el clima es Tendencia, permitimos un SL un poco más amplio para no ser sacados por ruido
        # Si es Rango, el SL debe ser cortísimo porque si sale del rango la tesis falló.
        current_sl_pct = self.stop_loss_pct
        if clima == "TRENDING_UP":
            current_sl_pct = self.stop_loss_pct * 1.5 # Un poco más de aire
        elif clima == "RANGING":
            current_sl_pct = self.stop_loss_pct * 0.8 # Más ajustado

        # 3. Cálculo de monto (Tu idea del 30% o el total si es poco)
        monto_a_invertir = self.balance * 0.30 
        if monto_a_invertir < 11.0: # Mínimo de Binance
            monto_a_invertir = self.balance if self.balance >= 11.0 else 0.0
            
        if monto_a_invertir <= 0: return

        self.inventory = monto_a_invertir / precio
        self.active_position = {
            'entry': precio,
            'sl': precio * (1 - current_sl_pct),
            'clima_origen': clima
        }
        self.balance -= monto_a_invertir

        # 4. Registro en DB
        try:
            Session = sessionmaker(bind=db_engine)
            with Session() as session:
                nuevo_trade = Trades(
                    timestamp=datetime.now(),
                    symbol="BTCUSDT",
                    side="BUY",
                    amount=self.inventory,
                    price=precio
                )
                session.add(nuevo_trade)
                session.commit()
        except Exception as e:
            self.logger.error(f"❌ Error DB: {e}")

        self.logger.info(f"🛒 COMPRA: {self.inventory:.6f} BTC | SL: {current_sl_pct*100:.2f}% | Clima: {clima}")

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


