from .base_strategy import BaseStrategy
from core.math_engine import calculate_rsi, calculate_moving_average, calculate_z_score
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
        z_score = calculate_z_score(data)

        # Retornamos el diccionario base. El Engine le inyectará de forma
        # nativa las llaves 'rvol', 'eth_corr' y 'solusdt_corr'.
        return {
            "rsi": rsi,
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "z_score": z_score,
            "price": data[-1],
            "momentum": TrendAnalyzer.identify_momentum(data)
        }

    def should_execute(self, analysis, climate):
        # Si el mercado está en caos, calentando o en TENDENCIA BAJISTA MACRO, prohibido comprar
        if not analysis or climate in ["CHAOS", "WARMING_UP", "TRENDING_DOWN"]:
            return "HOLD", 0.0

        rsi = analysis['rsi']
        z_score = analysis['z_score']
        momentum = analysis['momentum']
        
        # Recuperamos las nuevas dimensiones inyectadas de manera segura
        rvol = analysis.get('rvol', 1.0)
        eth_corr = analysis.get('eth_corr', 1.0)
        sol_corr = analysis.get('sol_corr', 1.0)

        # GATILLO DE COMPRA AJUSTADO (Con filtros de volumen y correlación institucional)
        if climate in ["RANGING", "TRENDING_UP", "RANGING_DEAD"]:
            # Si el mercado está muy plano (RANGING_DEAD), exigimos menos margen pero más precisión
            target_z = -1.5 if climate == "RANGING_DEAD" else -2.2
            target_rsi = 40 if climate == "RANGING_DEAD" else 35

            # 1. VALIDACIÓN BASE TRADICIONAL: Z-Score y RSI en suelo + Frenado de velocidad (Momentum)
            if z_score < target_z and rsi < target_rsi and momentum > -0.02:
                
                # 2. FILTRO DE GASOLINA (RVOL): Asegurar que el rebote tiene volumen institucional real
                # Exigimos que el volumen actual sea un 20% superior al promedio (RVOL > 1.20)
                if rvol < 1.20:
                    # El log de esto se puede omitir para evitar inundar la TUI de Termux, pero bloquea el gatillo
                    return "HOLD", 0.0

                # 3. FILTRO DE BETA DE RED (CORRELACIÓN): Evitar divergencias trampa
                # Si Bitcoin da compra, pero Ethereum está cayendo en dirección opuesta (correlación rota), abortamos
                if eth_corr < 0.50:
                    return "HOLD", 0.0

                # Si pasa todos los filtros de realidad cuantitativos, la orden es matemáticamente óptima
                return "BUY", 0.95

        # Las salidas (VENTAS) quedan 100% delegadas a la matemática de trading_logic (TP/SL)
        return "HOLD", 0.0
