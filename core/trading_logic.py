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

    def abrir_posicion_test(self, precio):
        # 1. Validaciones previas
        if not self.can_trade():
            self.logger.warning("⛔ Límite de pérdida diario alcanzado.")
            return

        if self.balance < 10.0: 
            self.logger.warning(f"💸 Balance insuficiente: ${self.balance:.2f}")
            return

        # 2. Cálculos de posición
        self.inventory = self.balance / precio
        self.active_position = {
            'entry': precio, 
            'sl': precio * (1 - self.stop_loss_pct)
        }
        self.balance = 0.0

        # 3. Persistencia en DB (Ahora con datos reales)
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
            self.logger.error(f"❌ Error al registrar compra en DB: {e}")

        self.logger.info(f"🛒 EJECUTADO: {self.inventory:.6f} BTC | Costo: ${precio:,.2f}")

    def cerrar_posicion_test(self, precio, motivo="IA"):
        if self.inventory <= 0: return
        
        valor_venta = self.inventory * precio
        pnl = valor_venta - (self.inventory * self.active_position['entry'])
        cantidad_vendida = self.inventory # Guardamos para el registro

        # 1. Actualizar estado interno
        self.daily_pnl += pnl
        self.balance = valor_venta
        self.inventory = 0.0
        self.active_position = None

        # 2. Persistencia en DB de la Venta
        try:
            Session = sessionmaker(bind=db_engine)
            with Session() as session:
                venta_trade = Trades(
                    timestamp=datetime.now(),
                    symbol="BTCUSDT",
                    side="SELL",
                    amount=cantidad_vendida,
                    price=precio
                )
                session.add(venta_trade)
                session.commit()
        except Exception as e:
            self.logger.error(f"❌ Error al registrar venta en DB: {e}")

        color = "\033[1;32m" if pnl >= 0 else "\033[1;31m"
        self.logger.info(f"✅ VENTA ({motivo}): ${precio:,.2f} | PnL: {pnl:+.2f}")
        print(f"{color}>>> RESULTADO OPERACIÓN: ${pnl:+.2f} ({motivo}) | PnL Diario: {self.daily_pnl:+.2f}\033[0m")

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


