import numpy as np
import logging

class MacroAnalyzer:
    def __init__(self, binance_client):
        self.client = binance_client
        self.logger = logging.getLogger("NEON.MACRO_ANALYZER")
        
        # Estado macro inicial por seguridad (neutral)
        self.current_macro_trend = "SIDEWAYS"
        self.macro_slope = 0.0

    async def update_trend(self, symbol="BTCUSDT", interval="15m"):
        """
        Descarga velas mayores y calcula la pendiente usando una Regresión Lineal con NumPy.
        Diseñado para ejecutarse de fondo de manera asíncrona periódica.
        """
        try:
            # Bajamos las últimas 60 velas de 15 minutos (representa las últimas 15 horas de mercado)
            candles = await self.client.get_historical_data(symbol=symbol, interval=interval, limit=60)
            
            if not candles or len(candles) < 10:
                self.logger.warning("⚠️ Historial macro insuficiente. Manteniendo último estado conocido.")
                return self.current_macro_trend

            # Convertimos a numpy array rápido
            y = np.array(candles, dtype=np.float64)
            x = np.arange(len(y), dtype=np.float64)

            # Algoritmo rápido de mínimos cuadrados para obtener la pendiente (slope)
            # Formula: slope = Cov(x,y) / Var(x)
            x_mean = np.mean(x)
            y_mean = np.mean(y)
            
            numerator = np.sum((x - x_mean) * (y - y_mean))
            denominator = np.sum((x - x_mean) ** 2)

            if denominator == 0:
                slope = 0.0
            else:
                slope = numerator / denominator

            # Normalizamos la pendiente en porcentaje relativo al precio actual para evitar distorsiones
            normalized_slope = (slope / y[-1]) * 10000  # Multiplicador por coeficientes de escala base
            self.macro_slope = normalized_slope

            # --- UMBRALES DE DECISIÓN CRÍTICA ---
            # Si la pendiente normalizada es mayor a 0.25, el océano empuja con fuerza hacia arriba.
            if normalized_slope > 0.25:
                self.current_macro_trend = "BULLISH"
            elif normalized_slope < -0.25:
                self.current_macro_trend = "BEARISH"
            else:
                self.current_macro_trend = "SIDEWAYS"

            self.logger.info(f"🧭 [BRÚJULA] Inercia Macro calculada: {self.current_macro_trend} (Pendiente: {normalized_slope:.4f})")
            return self.current_macro_trend

        except Exception as e:
            self.logger.error(f"❌ Error en cálculo de tendencia macro: {e}")
            return self.current_macro_trend

