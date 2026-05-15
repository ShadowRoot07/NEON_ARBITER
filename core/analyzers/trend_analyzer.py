import numpy as np
from core.math_engine import calculate_linear_regression

class TrendAnalyzer:
    @staticmethod
    def get_market_climate(prices):
        if len(prices) < 100: return "WARMING_UP"

        # Calculamos la desviación estándar como % del precio (volatilidad relativa)
        volatilidad = (np.std(prices[-20:]) / np.mean(prices[-20:])) * 100
        
        # Si la volatilidad es ínfima (< 0.05%), el mercado está muerto.
        if volatilidad < 0.05:
            return "RANGING_DEAD" # Evitar operar aquí

        slope, r2 = calculate_linear_regression(prices[-100:])

        if r2 > 0.70: # Subimos el umbral de confianza
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

