import statistics

class TrendAnalyzer:
    """Calcula indicadores técnicos puros a partir de buffers de precios."""
    
    @staticmethod
    def get_sma(data, window):
        """Media Móvil Simple."""
        if len(data) < window: return None
        return sum(data[-window:]) / window

    @staticmethod
    def get_volatility(data):
        """Desviación estándar (volatilidad)."""
        if len(data) < 2: return 0
        return statistics.stdev(data)

    @staticmethod
    def identify_momentum(data):
        """Determina si la fuerza del movimiento está acelerando o frenando."""
        if len(data) < 10: return "NEUTRAL"
        
        recent = data[-5:]
        older = data[-10:-5]
        
        recent_avg = sum(recent) / 5
        older_avg = sum(older) / 5
        
        if recent_avg > older_avg: return "ACCELERATING_UP"
        if recent_avg < older_avg: return "ACCELERATING_DOWN"
        return "STABLE"

