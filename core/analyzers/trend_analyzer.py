import numpy as np                          
from core.math_engine import calculate_linear_regression                                

class TrendAnalyzer:
    # Variables de clase para dotar de memoria temporal al analizador
    _last_climate = "WARMING_UP"
    _climate_duration = 0

    @classmethod
    def get_market_climate(cls, prices, is_scalper=False):
        longitud = len(prices)
        if longitud < 100:                              
            return "WARMING_UP", 0

        # 1. Análisis de micro-volatilidad (Últimos 20 ticks)
        volatilidad = (np.std(prices[-20:]) / np.mean(prices[-20:])) * 100
        umbral_minimo = 0.015 if is_scalper else 0.05

        if volatilidad < umbral_minimo:
            current_clima = "RANGING_DEAD"
        else:
            # 2. Análisis de Tendencia Multi-Temporal
            ventana_tendencia = min(500, longitud) if is_scalper else min(100, longitud)
            slope, r2 = calculate_linear_regression(prices[-ventana_tendencia:])

            # Exigimos correlación estadística robusta (R² > 0.65)
            if r2 > 0.65:
                current_clima = "TRENDING_UP" if slope > 0 else "TRENDING_DOWN"
            else:
                current_clima = "RANGING"

        # 3. Filtro de seguridad Macro por quiebre de mínimos (Anti-Cuchillo Cayendo)
        if is_scalper and longitud >= 60 and current_clima != "TRENDING_DOWN":
            precio_actual = prices[-1]
            minimo_reciente = min(prices[-60:])
            if precio_actual <= minimo_reciente * 1.0005 and current_clima == "RANGING":
                current_clima = "TRENDING_DOWN"

        # ===================================================================
        # 🧠 ORQUESTADOR DE PERSISTENCIA Y LONGEVIDAD
        # ===================================================================
        if current_clima == cls._last_climate:
            cls._climate_duration += 1
        else:
            cls._last_climate = current_clima
            cls._climate_duration = 1  # Reset del contador al mutar el clima

        return current_clima, cls._climate_duration

    @staticmethod
    def identify_momentum(prices):
        """Calcula el momentum estructural basado en el desplazamiento del precio."""
        if len(prices) < 10:
            return 0.0
        momentum = ((prices[-1] - prices[-10]) / prices[-10]) * 100
        return momentum

