import numpy as np
from core.math_engine import calculate_linear_regression

class TrendAnalyzer:
    @staticmethod
    def get_market_climate(prices, is_scalper=False):
        if len(prices) < 100: return "WARMING_UP"

        # Calculamos la desviación estándar como % del precio (volatilidad relativa)
        volatilidad = (np.std(prices[-20:]) / np.mean(prices[-20:])) * 100

        # Ajuste dinámico de umbral: El Scalper tolera micro-volatilidad de segundos
        umbral_minimo = 0.01 if is_scalper else 0.05

        if volatilidad < umbral_minimo:
            return "RANGING_DEAD"

        slope, r2 = calculate_linear_regression(prices[-100:])

        if r2 > 0.70: 
            return "TRENDING_UP" if slope > 0 else "TRENDING_DOWN"

        return "RANGING"

    @staticmethod
    def identify_momentum(prices):
        """Calcula el momentum simple basado en las últimas velas."""
        if len(prices) < 5:
            return 0.0
        # Cambio porcentual entre el precio actual y hace 5 velas
        momentum = ((prices[-1] - prices[-5]) / prices[-5]) * 100
        return momentum

