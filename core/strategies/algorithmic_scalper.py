from .base_strategy import BaseStrategy
from core.math_engine import calculate_rsi, calculate_moving_average, calculate_z_score # Añadido Z-Score
from core.analyzers.trend_analyzer import TrendAnalyzer

class AlgorithmicScalper(BaseStrategy):
    def __init__(self):
        self.analyzer = TrendAnalyzer()
        self.rsi_period = 14
        self.fast_ma = 9
        self.slow_ma = 21

    def analyze(self, buffer, extra_market_data=None):
        data = list(buffer)
        if len(data) < 30: return None

        # Cálculos Técnicos Locales
        rsi = calculate_rsi(data, period=self.rsi_period)
        ma_fast = calculate_moving_average(data, period=self.fast_ma)
        ma_slow = calculate_moving_average(data, period=self.slow_ma)
        z_score = calculate_z_score(data) # <--- CALCULO FUNDAMENTAL PARA RANGING

        # Análisis de correlación (Alts)
        correlation_score = 0
        if extra_market_data:
            for symbol, prices in extra_market_data.items():
                if len(prices) > 5 and prices[-1] > prices[-5]:
                    correlation_score += 1

        return {
            "rsi": rsi,
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "z_score": z_score,
            "price": data[-1],
            "correlation": correlation_score,
            "momentum": TrendAnalyzer.identify_momentum(data)
        }

    def should_execute(self, analysis, climate):
        if not analysis or climate in ["CHAOS", "WARMING_UP"]:
            return "HOLD", 0.0

        rsi = analysis['rsi']
        z_score = analysis['z_score']

        # COMPRA: Z-Score bajo (sobreventa local) + RSI recuperándose
        if climate in ["RANGING", "TRENDING_UP"]:
            if z_score < -2.0 and rsi < 40:
                return "BUY", 0.85
        
        # VENTA: Solo vendemos si hay señales de agotamiento real
        if climate == "TRENDING_DOWN":
            return "SELL", 0.95 # Salir rápido si la tendencia se invierte

        # En RANGING o TRENDING_UP, NO vendemos por clima. 
        # Dejamos que el TP o el Trailing SL de trading_logic hagan su trabajo.
        if rsi > 80: # Solo venta de emergencia por sobrecompra extrema
            return "SELL", 0.80

        return "HOLD", 0.0

