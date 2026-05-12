from .base_strategy import BaseStrategy
from core.analyzers.trend_analyzer import TrendAnalyzer

class MultiTimeframeStrategy(BaseStrategy):
    def __init__(self):
        self.analyzer = TrendAnalyzer()

    def analyze(self, buffer, extra_market_data=None):
        """
        extra_market_data: Diccionario con { 'ETHUSDT': [precios], 'SOLUSDT': [precios] }
        """
        data = list(buffer)
        if len(data) < 60: return None

        micro = data[-20:]
        avg_inicio = sum(micro[:5]) / 5
        avg_final = sum(micro[-5:]) / 5

        # --- Lógica de Sentimiento de Mercado ---
        market_sentiment = "NEUTRAL"
        if extra_market_data:
            up_votes = 0
            for symbol, prices in extra_market_data.items():
                if len(prices) > 5 and prices[-1] > prices[0]:
                    up_votes += 1
            
            if up_votes >= 2: market_sentiment = "BULLISH_CORRELATED"
            elif up_votes == 0: market_sentiment = "BEARISH_CORRELATED"

        analysis = {
            "micro": {
                "trend": "UP" if avg_final > avg_inicio else "DOWN",
                "volatility": self.analyzer.get_volatility(micro),
                "change_pct": ((avg_final - avg_inicio) / avg_inicio) * 100
            },
            "market_context": market_sentiment, # Nuevo campo para la IA
            "macro": {
                "momentum": self.analyzer.identify_momentum(data),
                "change_pct": ((data[-1] - data[0]) / data[0]) * 100
            }
        }
        return analysis

    def should_execute(self, signal, confidence):
        # Convertimos a float por seguridad si viene de la IA
        try:
            conf = float(confidence)
        except:
            conf = 0.0

        if signal == "BUY":
            # Bajamos de 0.75 a 0.65 para ser más activos en Scalping
            umbral = 0.65 
            result = conf >= umbral
            if not result and conf > 0:
                print(f"⚠️ COMPRA DESCARTADA: Confianza {conf:.2f} < {umbral}")
            return result

        if signal == "SELL":
            # Bajamos de 0.60 a 0.55
            umbral = 0.55
            result = conf >= umbral
            if not result and conf > 0:
                print(f"⚠️ VENTA DESCARTADA: Confianza {conf:.2f} < {umbral}")
            return result
        
        return False
