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
        ma_fast = analysis['ma_fast']
        ma_slow = analysis['ma_slow']
        current_price = analysis['price']

        # FILTRO DE EMERGENCIA: Si las medias móviles están cruzadas a la baja
        # o el precio actual está muy por debajo de la media rápida, hay caída libre.
        is_falling_knife = ma_fast is not None and ma_slow is not None and (current_price < ma_fast or ma_fast < ma_slow)

        # COMPRA: Z-Score bajo (sobreventa local).
        # Protegemos al bot bloqueando compras en RANGING_DEAD si los spreads no valen la pena,
        # y prohibimos comprar si el filtro detecta caída libre (falling knife).
        if climate in ["RANGING", "TRENDING_UP", "RANGING_DEAD"]:
            if not is_falling_knife:  # <--- ¡EL BLINDAJE CRÍTICO!
                if z_score < -2.0 and rsi < 40:
                    return "BUY", 0.85

        # VENTA: Salir rápido si la tendencia se invierte o si quedamos atrapados en caída libre
        if climate == "TRENDING_DOWN" or is_falling_knife:
            return "SELL", 0.95

        # Venta de emergencia por sobrecompra extrema (aplica a Rangos y tendencias alcistas)
        if rsi > 80:
            return "SELL", 0.80

        return "HOLD", 0.0
