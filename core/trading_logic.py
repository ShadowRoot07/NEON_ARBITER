import logging

class TradingLogic:
    def __init__(self, initial_test_balance=None):
        self.logger = logging.getLogger("NEON.TRADING")
        self.test_mode = initial_test_balance is not None
        self.balance = initial_test_balance if self.test_mode else 0.0
        self.inventory = 0.0
        self.stop_loss_pct = 0.01
        self.take_profit_pct = 0.02
        self.active_position = None

    def ejecutar_simulacion(self, precio_actual):
        """Monitorea SL y TP automáticos."""
        if not self.active_position:
            return None

        pos = self.active_position
        if precio_actual <= pos['sl'] or precio_actual >= pos['tp']:
            motivo = "STOP LOSS" if precio_actual <= pos['sl'] else "TAKE PROFIT"
            self.cerrar_posicion_test(precio_actual, motivo)

    def abrir_posicion_test(self, precio):
        if self.balance <= 0:
            self.logger.warning("❌ Saldo insuficiente.")
            return

        self.inventory = self.balance / precio
        self.balance = 0.0
        
        sl = precio * (1 - self.stop_loss_pct)
        tp = precio * (1 + self.take_profit_pct)
        self.active_position = {'entry': precio, 'sl': sl, 'tp': tp}

        self.logger.info(f"🛒 COMPRA: {self.inventory:.6f} BTC a ${precio:,.2f}")
        self.logger.info(f"🛡️ NIVELES: SL: ${sl:,.2f} | TP: ${tp:,.2f}")

    def cerrar_posicion_test(self, precio, motivo="IA"):
        """Cierra la posición y vuelve a USD."""
        if self.inventory <= 0: return

        valor_venta = self.inventory * precio
        resultado = valor_venta - (self.inventory * self.active_position['entry'])
        
        self.balance = valor_venta
        self.inventory = 0.0
        self.active_position = None

        self.logger.info(f"✅ VENTA ({motivo}): ${precio:,.2f} | PnL: ${resultado:+.2f}")
        self.logger.info(f"💰 SALDO VIRTUAL: ${self.balance:.2f}")

