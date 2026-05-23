import numpy as np
import logging

class OrderBookAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger("NEON.ORDERBOOK_ANALYZER")
        # Diccionario para guardar el ratio de presión actual por cada símbolo
        self.market_pressure = { "BTCUSDT": 1.0, "ETHUSDT": 1.0, "SOLUSDT": 1.0 }

    def process_depth_update(self, data):
        """
        Procesa el evento ligero @depth5 de Binance y calcula la presión del libro.
        Formato de datos esperado: data['b'] para bids (compras), data['a'] para asks (ventas).
        """
        try:
            # Binance envía el stream con el nombre en mayúsculas (ej. BTCUSDT) en data['s']
            symbol = data.get('s_name') or data.get('s')
            if not symbol or symbol not in self.market_pressure:
                return

            bids = data.get('b', [])  # Lista de [precio, cantidad]
            asks = data.get('a', [])  # Lista de [precio, cantidad]

            if not bids or not asks:
                return

            # Convertimos las cantidades a arrays de NumPy en float64 de golpe (las posiciones [1] son los volúmenes)
            total_bid_volume = np.sum([float(b[1]) for b in bids])
            total_ask_volume = np.sum([float(a[1]) for a in asks])

            # Evitamos división por cero si el libro se queda vacío en un flash-crash
            if total_ask_volume == 0:
                pressure_ratio = 2.0
            else:
                # Ratio > 1.0 significa más órdenes institucionales de compra (Soporte/Muros)
                # Ratio < 1.0 significa más órdenes institucionales de venta (Resistencia)
                pressure_ratio = total_bid_volume / total_ask_volume

            # Guardamos el resultado de manera inmediata en memoria (O(1))
            self.market_pressure[symbol] = float(pressure_ratio)

        except Exception as e:
            self.logger.error(f"❌ Error procesando el libro de órdenes: {e}")

