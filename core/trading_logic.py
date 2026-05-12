import logging

class TradingLogic:
    def __init__(self, initial_test_balance=None, is_scalper=False):
        self.logger = logging.getLogger("NEON.TRADING")
        self.test_mode = initial_test_balance is not None
        self.balance = initial_test_balance if self.test_mode else 0.0
        self.inventory = 0.0
        self.active_position = None
        
        # Ajuste dinámico según el modo
        if is_scalper:
            self.stop_loss_pct = 0.0015 # 0.15% para salir rápido si falla
            self.trailing_pct = 0.001   # 0.1% para perseguir el precio de cerca
        else:
            self.stop_loss_pct = 0.005  # 0.5% modo normal
            self.trailing_pct = 0.003   # 0.3% modo normal

    def ejecutar_simulacion(self, precio_actual):
        if not self.active_position: return
        pos = self.active_position
        nuevo_sl_potencial = precio_actual * (1 - self.trailing_pct)
        if nuevo_sl_potencial > pos['sl']:
            pos['sl'] = nuevo_sl_potencial
        if precio_actual <= pos['sl']:
            self.cerrar_posicion_test(precio_actual, "TRAILING_STOP")

    def abrir_posicion_test(self, precio):
        if self.balance <= 0: return
        self.inventory = self.balance / precio
        self.balance = 0.0
        sl = precio * (1 - self.stop_loss_pct)
        self.active_position = {'entry': precio, 'sl': sl}
        self.logger.info(f"🛒 COMPRA: {self.inventory:.6f} BTC a ${precio:,.2f} | SL: ${sl:,.2f}")

    def cerrar_posicion_test(self, precio, motivo="IA"):
        if self.inventory <= 0: return
        valor_venta = self.inventory * precio
        pnl = valor_venta - (self.inventory * self.active_position['entry'])
        self.balance = valor_venta
        self.inventory = 0.0
        self.active_position = None
        color = "\033[1;32m" if pnl >= 0 else "\033[1;31m"
        self.logger.info(f"✅ VENTA ({motivo}): ${precio:,.2f} | PnL: {pnl:+.2f}")
        print(f"{color}>>> RESULTADO OPERACIÓN: ${pnl:+.2f} ({motivo})\033[0m")

