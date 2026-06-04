import numpy as np
from core.math_engine import calculate_linear_regression

class TrendAnalyzer:
    @staticmethod
    def get_market_climate(prices, is_scalper=False):
        if len(prices) < 100: return "WARMING_UP"

        # 1. Calculamos la volatilidad relativa de los últimos 20 períodos
        current_mean = np.mean(prices[-20:])
        volatilidad = (np.std(prices[-20:]) / current_mean) * 100

        # 2. UMBRAL ADAPTATIVO (Capa de protección financiera)
        # La comisión estándar de Binance es 0.1% por movimiento (0.2% por viaje completo Buy+Sell).
        # Si eres scalper, necesitas que la volatilidad supere al menos ese costo operativo + un margen.
        if is_scalper:
            # Filtro dinámico: Exigimos una oscilación mínima viable (ej. 0.035% o 0.04%)
            # Esto evita operar micro-ruido donde solo gana Binance en comisiones.
            umbral_minimo = 0.035 
        else:
            umbral_minimo = 0.08

        # 3. Clasificación de Clima con filtro de seguridad
        if volatilidad < umbral_minimo:
            return "RANGING_DEAD"

        # 4. Análisis de Tendencia Estricto (Regresión Lineal)
        slope, r2 = calculate_linear_regression(prices[-100:])

        if r2 > 0.70:
            # Un filtro extra: Si la pendiente es casi horizontal, sigue siendo rango
            # Multiplicamos por 100 para evaluar el cambio porcentual de la pendiente
            slope_percent = (slope / current_mean) * 100
            if abs(slope_percent) < 0.005:
                return "RANGING"
                
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
