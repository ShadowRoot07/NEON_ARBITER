import statistics

class TrendAnalyzer:
    @staticmethod
    def get_volatility(data):
        """Calcula volatilidad protegida."""
        if len(data) < 2: return 0.0
        try:
            # Si todos los precios son iguales, la desviación es 0
            if len(set(data)) == 1: return 0.0
            return statistics.stdev(data)
        except Exception:
            return 0.0

    @staticmethod
    def identify_momentum(data):
        """Determina la aceleración con mayor sensibilidad."""
        if len(data) < 10: return "NEUTRAL"

        recent = data[-5:]
        older = data[-10:-5]

        # Evitamos divisiones por cero o promedios vacíos
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        diff = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0
        
        # Umbral mínimo para considerar aceleración (0.01%)
        if diff > 0.0001: return "ACCELERATING_UP"
        if diff < -0.0001: return "ACCELERATING_DOWN"
        return "STABLE"

