import logging

class TradingLogic:
    def __init__(self, initial_test_balance=None):
        self.logger = logging.getLogger("NEON.TRADING")
        self.test_mode = initial_test_balance is not None
        self.balance = initial_test_balance if self.test_mode else 0.0
        self.inventory = 0.0
        self.stop_loss_pct = 0.005  # 0.5% (Ajustado para scalping)
        self.trailing_pct = 0.003   # 0.3% (Distancia del trailing)
        self.active_position = None

    def ejecutar_simulacion(self, precio_actual):
        if not self.active_position:
            return

        pos = self.active_position
        
        # --- Lógica de TRAILING STOP ---
        # Si el precio sube, subimos el Stop Loss para asegurar ganancias
        nuevo_sl_potencial = precio_actual * (1 - self.trailing_pct)
        if nuevo_sl_potencial > pos['sl']:
            pos['sl'] = nuevo_sl_potencial
            # self.logger.debug(f"📈 Trailing SL subió a: ${pos['sl']:.2f}")

        # Ejecución del Stop (ya sea el inicial o el movido por el trailing)
        if precio_actual <= pos['sl']:
            self.cerrar_posicion_test(precio_actual, "TRAILING_STOP")

    def abrir_posicion_test(self, precio):
        if self.balance <= 0: return
        
        self.inventory = self.balance / precio
        self.balance = 0.0
        
        # Stop Loss inicial
        sl = precio * (1 - self.stop_loss_pct)
        self.active_position = {'entry': precio, 'sl': sl}

        self.logger.info(f"🛒 COMPRA: {self.inventory:.6f} BTC a ${precio:,.2f}")
        self.logger.info(f"🛡️ SL INICIAL: ${sl:,.2f} | Trailing: {self.trailing_pct*100}%")

    def cerrar_posicion_test(self, precio, motivo="IA"):
        if self.inventory <= 0: return
        valor_venta = self.inventory * precio
        pnl = valor_venta - (self.inventory * self.active_position['entry'])
        
        self.balance = valor_venta
        self.inventory = 0.0
        self.active_position = None

        color = "\033[1;32m" if pnl >= 0 else "\033[1;31m"
        self.logger.info(f"✅ VENTA ({motivo}): ${precio:,.2f} | PnL: {pnl:+.2f}")
        print(f"{color}>>> RESULTADO: ${pnl:+.2f} ({motivo})\033[0m")

