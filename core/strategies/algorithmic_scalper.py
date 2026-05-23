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

    def should_execute(self, analysis, climate_tuple, **kwargs):
        """
        🎯 GATILLO SUPREMO UNIFICADO (PASO 4)
        Combina de forma ponderada: Clima Multi-Tick + Inercia Macro + Libro de Órdenes + Dominancia.
        """
        if not analysis:
            return "HOLD", 0.0

        # Extracción segura de los sensores del Paso 2 y Paso 3 vía kwargs
        macro_trend = kwargs.get("macro_trend", "SIDEWAYS")
        book_pressure = kwargs.get("book_pressure", 1.0)
        btc_dom_drain = kwargs.get("btc_dom_drain", False)

        # Desempaquetamos la tupla con contexto temporal de ticks (Paso 1)
        climate, longevidad = climate_tuple

        # --- CANDADO INTERNACIONAL DE INERCIA MACRO (Paso 1) ---
        if macro_trend == "BEARISH":
            return "HOLD", 0.0

        # --- CANDADO DE FUERZA RELATIVA / DOMINANCIA (Paso 3) ---
        if btc_dom_drain:
            return "HOLD", 0.0

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
            if momentum > 0.04 and rvol > 2.10 and eth_corr > 0.70:
                # Confirmamos que el quiebre alcista esté respaldado por el libro institucional
                if book_pressure < 1.10:
                    return "HOLD", 0.0
                return "BUY", 0.98  # Retorna decisión y nivel de confianza alto

            return "HOLD", 0.0

        # ===================================================================
        # 🛒 ESCENARIO B: MODO SCALPING TRADICIONAL (Reversión en Rangos Jóvenes)
        # ===================================================================
        if climate in ["RANGING", "TRENDING_UP", "RANGING_DEAD"]:
            target_z = -1.5 if climate == "RANGING_DEAD" else -2.2
            target_rsi = 40 if climate == "RANGING_DEAD" else 35

            if z_score < target_z and rsi < target_rsi and momentum > -0.02:
                if rvol < 1.20 or eth_corr < 0.50:
                    return "HOLD", 0.0

                # --- CANDADO DE RAYOS X (Paso 2) ---
                if book_pressure < 1.0:
                    return "HOLD", 0.0

                if macro_trend == "SIDEWAYS" and z_score > -1.8 and climate == "RANGING":
                    return "HOLD", 0.0

                # Si todo alinea pero la presión es justa, bajamos levemente la confianza
                confianza = 0.95 if book_pressure >= 1.20 else 0.85
                return "BUY", confianza

        return "HOLD", 0.0

