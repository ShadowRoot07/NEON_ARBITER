import numpy as np
from core.math_engine import calculate_linear_regression

class TrendAnalyzer:
    @staticmethod
    def get_market_climate(prices):
        """
        Clasifica el mercado en: TRENDING, RANGING o CHAOS.
        Basado en Pendiente, R2 y Volatilidad Relativa.
        """
        if len(prices) < 100:
            return "WARMING_UP"

        slope, r2 = calculate_linear_regression(prices[-100:])
        
        # 1. Detectar Caos (Volatilidad explosiva)
        recent_std = np.std(prices[-10:])
        long_std = np.std(prices[-100:])
        if recent_std > (long_std * 2.5):
            return "CHAOS"

        # 2. Detectar Tendencia Fuerte
        # Si el ajuste es bueno (R2 alto) y la pendiente no es plana
        if r2 > 0.65:
            return "TRENDING_UP" if slope > 0 else "TRENDING_DOWN"

        # 3. Detectar Rango Lateral (R2 bajo o pendiente plana)
        return "RANGING"

