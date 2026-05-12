from .base_strategy import BaseStrategy
from core.analyzers.trend_analyzer import TrendAnalyzer

class MultiTimeframeStrategy(BaseStrategy):
    def __init__(self):
        self.analyzer = TrendAnalyzer()

    def analyze(self, buffer):
        data = list(buffer)
        if len(data) < 60: return None

        # Capas de tiempo
        micro = data[-20:]
        meso = data[-600:] if len(data) >= 600 else data
        macro = data # Buffer completo (hasta 3600)

        analysis = {
            "micro": {
                "trend": "UP" if micro[-1] > micro[0] else "DOWN",
                "volatility": self.analyzer.get_volatility(micro)
            },
            "meso": {
                "sma": self.analyzer.get_sma(meso, 50),
                "change_pct": ((meso[-1] - meso[0]) / meso[0]) * 100
            },
            "macro": {
                "momentum": self.analyzer.identify_momentum(macro),
                "change_pct": ((macro[-1] - macro[0]) / macro[0]) * 100
            }
        }
        return analysis

    def should_execute(self, signal, confidence):
        # Filtro de seguridad: Solo compra si la confianza es alta
        # Pero permite ventas con confianza media para proteger capital
        if signal == "BUY":
            return confidence >= 0.60
        if signal == "SELL":
            return confidence >= 0.45
        return False

