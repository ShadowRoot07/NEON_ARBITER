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
            "momentum": self.analyzer.identify_momentum(data)
        }

    def should_execute(self, analysis, climate):
        """
        Ajusta la agresividad según el clima del mercado.
        """
        if not analysis or climate == "CHAOS" or climate == "WARMING_UP":
            return "HOLD", 0.0

        rsi = analysis['rsi']
        z_score = analysis['z_score']

        # --- ESTRATEGIA PARA MERCADO LATERAL (RANGING) ---
        # Basada en Reversión a la Media
        if climate == "RANGING":
            # Si el precio está 2 desviaciones abajo y RSI bajo, es compra probable
            if z_score < -2.0 and rsi < 35:
                return "BUY", 0.90
            # Si el precio está 2 desviaciones arriba o RSI muy alto, es venta
            if z_score > 2.0 or rsi > 70:
                return "SELL", 0.85

        # --- ESTRATEGIA PARA TENDENCIA ALCISTA (TRENDING_UP) ---
        if climate == "TRENDING_UP":
            # Comprar en "pullbacks" (pequeñas bajadas dentro de la subida)
            if analysis['ma_fast'] > analysis['ma_slow'] and rsi < 50:
                return "BUY", 0.80
            # Venta preventiva si el RSI se dispara demasiado
            if rsi > 75:
                return "SELL", 0.80

        # --- ESTRATEGIA PARA TENDENCIA BAJISTA (TRENDING_DOWN) ---
        if climate == "TRENDING_DOWN":
            # En tendencia bajista no compramos, solo buscamos salir si estamos dentro
            if rsi > 55:
                return "SELL", 0.95

        return "HOLD", 0.0

