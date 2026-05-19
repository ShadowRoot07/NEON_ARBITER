import numpy as np
from core.math_engine import calculate_linear_regression

class TrendAnalyzer:
    @staticmethod
    def get_market_climate(prices, is_scalper=False):
        longitud = len(prices)
        if longitud < 100: 
            return "WARMING_UP"

        # 1. Análisis de micro-volatilidad (Últimos 20 ticks)
        # Esto sirve para detectar si el precio está congelado o lateralizando centavos
        volatilidad = (np.std(prices[-20:]) / np.mean(prices[-20:])) * 100
        umbral_minimo = 0.015 if is_scalper else 0.05

        if volatilidad < umbral_minimo:
            return "RANGING_DEAD"

        # 2. Análisis de Tendencia Multi-Temporal (La solución a la miopía)
        # Si es scalper, evaluamos una ventana de datos más profunda dentro de su buffer general
        # para capturar la inercia real del precio (ej. últimos 300-500 ticks si están disponibles)
        ventana_tendencia = min(500, longitud) if is_scalper else min(100, longitud)
        
        slope, r2 = calculate_linear_regression(prices[-ventana_tendencia:])

        # Exigimos una correlación estadística robusta (R² > 0.65) para confirmar tendencia
        if r2 > 0.65:
            return "TRENDING_UP" if slope > 0 else "TRENDING_DOWN"

        # 3. Filtro de seguridad Macro por quiebre de mínimos (Anti-Cuchillo Cayendo)
        # Si el precio actual está en el subsuelo del buffer reciente, no es rango, es caída libre.
        if is_scalper and longitud >= 60:
            precio_actual = prices[-1]
            minimo_reciente = min(prices[-60:])
            # Si estamos a menos del 0.05% del mínimo de los últimos 2 minutos, asumimos peligro bajista
            if precio_actual <= minimo_reciente * 1.0005 and slope < 0:
                return "TRENDING_DOWN"

        return "RANGING"

    @staticmethod
    def identify_momentum(prices):
        """Calcula el momentum estructural basado en el desplazamiento del precio."""
        if len(prices) < 10:
            return 0.0
        # Ampliamos la muestra a 10 ticks para suavizar el ruido del micro-scalping
        momentum = ((prices[-1] - prices[-10]) / prices[-10]) * 100
        return momentum

