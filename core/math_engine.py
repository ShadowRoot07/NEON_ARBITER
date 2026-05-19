import numpy as np

def calculate_rsi(prices, period=14):
    """Calcula el RSI usando la fórmula de suavizado de Welles Wilder."""
    if len(prices) <= period:
        return 50.0

    prices = np.array(prices)
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    
    # Manejo seguro si no hay deltas suficientes positivos o negativos
    up_sum = seed[seed >= 0].sum()
    down_sum = -seed[seed < 0].sum()
    
    up = up_sum / period
    down = down_sum / period if down_sum != 0 else 0.00001
    
    rs = up / down
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)     
    
    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        down = down if down != 0 else 0.00001
        rs = up / down
        rsi[i] = 100. - 100. / (1. + rs)

    return rsi[-1]

def calculate_moving_average(prices, period=20):
    """Media móvil simple optimizada."""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0.0
    return np.mean(prices[-period:])

def calcular_monto_seguro(balance_disponible, precio_activo, min_usd=11.0):
    """Calcula cuánto comprar asegurando superar el mínimo de Binance."""
    if balance_disponible < min_usd:
        return 0.0
    monto_a_usar = max(min_usd, balance_disponible * 0.98)
    return monto_a_usar / precio_activo

def calculate_linear_regression(prices):
    """Calcula la pendiente (slope) y el coeficiente de determinación (R^2)."""
    if len(prices) < 10:
        return 0.0, 0.0

    y = np.array(prices)
    x = np.arange(len(y))

    slope, intercept = np.polyfit(x, y, 1)

    predict = slope * x + intercept
    error_res = np.sum((y - predict) ** 2)
    error_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (error_res / error_tot) if error_tot != 0 else 0

    return slope, r_squared

def calculate_z_score(prices, period=20):
    """Mide cuántas desviaciones estándar está el precio de su media reciente."""
    if len(prices) < period:
        return 0.0

    recent_prices = np.array(prices)[-period:]
    mean = np.mean(recent_prices)
    std = np.std(recent_prices)

    if std == 0: return 0.0
    return (prices[-1] - mean) / std

# ==========================================
# 🔥 NUEVAS DIMENSIONES MATEMÁTICAS MACRO
# ==========================================

def calculate_rvol(volume_deltas, period=50):
    """
    Calcula el Volumen Relativo (RVOL).
    Compara el volumen inyectado en el último tick contra la media móvil de deltas.
    RVOL > 2.0 significa volumen el doble de lo normal (Inyección institucional).
    """
    if len(volume_deltas) < period:
        return 1.0
    
    recent_deltas = np.array(volume_deltas)[-period:]
    mean_volume = np.mean(recent_deltas)
    
    if mean_volume == 0: 
        return 1.0
        
    return volume_deltas[-1] / mean_volume

def calculate_pearson_correlation(prices_a, prices_b, period=50):
    """
    Calcula el Coeficiente de Correlación de Pearson entre dos activos en tiempo real.
    Retorna un valor entre -1.0 y 1.0.
    > 0.70: Alta correlación directa (Movimiento sincronizado).
    """
    if len(prices_a) < period or len(prices_b) < period:
        return 1.0
        
    arr_a = np.array(prices_a)[-period:]
    arr_b = np.array(prices_b)[-period:]
    
    if np.std(arr_a) == 0 or np.std(arr_b) == 0:
        return 1.0
        
    correlation_matrix = np.corrcoef(arr_a, arr_b)
    return correlation_matrix[0, 1]

def calculate_adaptive_std(prices, period=200):
    """
    Retorna la desviación estándar histórica adaptativa de la muestra.
    Sirve para calibrar dinámicamente los umbrales de volatilidad según la hora del día.
    """
    if len(prices) < 10:
        return 0.0
    actual_period = min(len(prices), period)
    return float(np.std(np.array(prices)[-actual_period:]))
