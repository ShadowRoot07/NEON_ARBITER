from .base_strategy import BaseStrategy
from core.math_engine import calculate_rsi, calculate_moving_average
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

        # Cálculos Técnicos Locales (Sin API)
        rsi = calculate_rsi(data, period=self.rsi_period)
        ma_fast = calculate_moving_average(data, period=self.fast_ma)
        ma_slow = calculate_moving_average(data, period=self.slow_ma)
        
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
            "price": data[-1],
            "correlation": correlation_score,
            "momentum": self.analyzer.identify_momentum(data)
        }

    def should_execute(self, analysis):
        if not analysis: return "HOLD", 0.0

        rsi = analysis['rsi']
        price = analysis['price']
        ma_fast = analysis['ma_fast']
        ma_slow = analysis['ma_slow']
        
        # --- LÓGICA DE COMPRA (BULLISH) ---
        # 1. RSI saliendo de sobreventa (> 35) pero no sobrecomprado (< 65)
        # 2. Cruce de Medias (Fast > Slow)
        # 3. Correlación de Alts positiva
        if rsi > 35 and rsi < 60 and ma_fast > ma_slow and analysis['correlation'] >= 1:
            return "BUY", 0.85

        # --- LÓGICA DE VENTA (BEARISH) ---
        # 1. RSI en sobrecompra o bajando rápido
        # 2. Cruce de Medias inverso
        if rsi > 70 or ma_fast < ma_slow:
            return "SELL", 0.90

        return "HOLD", 0.0

