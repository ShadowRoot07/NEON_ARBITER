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

        rsi = calculate_rsi(data, period=self.rsi_period)
        ma_fast = calculate_moving_average(data, period=self.fast_ma)
        ma_slow = calculate_moving_average(data, period=self.slow_ma)
        z_score = calculate_z_score(data)

        return {
            "rsi": rsi,
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "z_score": z_score,
            "price": data[-1],
            "momentum": TrendAnalyzer.identify_momentum(data)
        }

    def should_execute(self, analysis, climate_tuple, macro_trend="SIDEWAYS"):
        """
        Gatillo adaptativo optimizado con el Sentido de Inercia Macro.
        macro_trend es inyectado desde el estado asíncrono del Engine ('BULLISH', 'BEARISH', 'SIDEWAYS').
        """
        if not analysis:
            return "HOLD", 0.0

        # Desempaquetamos la tupla con contexto temporal de ticks
        climate, longevidad = climate_tuple

        # --- CANDADO INTERNACIONAL DE INERCIA MACRO ---
        # Si la tendencia en velas de 15m/1H es bajista, operar reversiones al alza es sumamente peligroso.
        # Bloqueamos cualquier intento de COMPRA (Long) para proteger capital de cuchillos cayendo.
        if macro_trend == "BEARISH":
            return "HOLD", 0.0
        # -----------------------------------------------

        if climate in ["CHAOS", "WARMING_UP", "TRENDING_DOWN"]:
            return "HOLD", 0.0

        rsi = analysis['rsi']
        z_score = analysis['z_score']
        momentum = analysis['momentum']

        rvol = analysis.get('rvol', 1.0)
        eth_corr = analysis.get('eth_corr', 1.0)

        # Umbral crítico para declarar acumulación masiva de energía en el rango lateral
        es_rango_viejo_y_comprimido = (climate == "RANGING_DEAD" or climate == "RANGING") and longevidad > 150

        # ===================================================================
        # 🔥 ESCENARIO A: MODO GATILLO BREAKOUT (Cazar la explosión del Rango Viejo)
        # ===================================================================
        if es_rango_viejo_y_comprimido:
            # Si el rango es viejo, operar reversión a la media es un suicidio táctico.
            # Buscamos dirección de quiebre alcista con volumen institucional masivo.
            if momentum > 0.04 and rvol > 2.10 and eth_corr > 0.70:
                # Si el precio rompe hacia arriba con más del doble de volumen normal, nos subimos a la ola
                return "BUY", 0.98

            return "HOLD", 0.0

        # ===================================================================
        # 🛒 ESCENARIO B: MODO SCALPING TRADICIONAL (Reversión en Rangos Jóvenes)
        # ===================================================================
        if climate in ["RANGING", "TRENDING_UP", "RANGING_DEAD"]:
            # Filtros dinámicos según el grado de congelamiento del canal
            target_z = -1.5 if climate == "RANGING_DEAD" else -2.2
            target_rsi = 40 if climate == "RANGING_DEAD" else 35

            if z_score < target_z and rsi < target_rsi and momentum > -0.02:
                # Filtro institucional de volumen mínimo para rebote
                if rvol < 1.20:
                    return "HOLD", 0.0

                # Filtro de correlación macro con Ethereum para evitar trampas
                if eth_corr < 0.50:
                    return "HOLD", 0.0

                # OPTIMIZACIÓN EXTRA: Si el mercado macro está lateral (SIDEWAYS), exigimos
                # un Z-Score un poco más estricto para evitar falsas salidas.
                if macro_trend == "SIDEWAYS" and z_score > -1.8 and climate == "RANGING":
                    return "HOLD", 0.0

                return "BUY", 0.95

        return "HOLD", 0.0

