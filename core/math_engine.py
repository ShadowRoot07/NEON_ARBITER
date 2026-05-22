import numpy as np

def calculate_rsi(prices, period=14):
    """Calcula el RSI usando operaciones vectorizadas de NumPy, evitando bucles manuales de Python."""
    if len(prices) <= period:
        return 50.0

    prices_arr = np.asarray(prices, dtype=np.float64)
    deltas = np.diff(prices_arr)
    
    seed = deltas[:period]
    up_sum = np.sum(seed[seed >= 0])
    down_sum = -np.sum(seed[seed < 0])

    up = up_sum / period
    down = down_sum / period if down_sum != 0 else 0.00001

    for delta in deltas[period:]:
        if delta > 0:
            upval, downval = delta, 0.0
        else:
            upval, downval = 0.0, -delta
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period

    down = down if down != 0 else 0.00001
    rs = up / down
    return 100.0 - 100.0 / (1.0 + rs)

def calculate_moving_average(prices, period=20):
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0.0
    return float(np.mean(prices[-period:]))

def calcular_monto_seguro(balance_disponible, precio_activo, min_usd=11.0):
    if balance_disponible < min_usd:
        return 0.0
    monto_a_usar = max(min_usd, balance_disponible * 0.98)
    return monto_a_usar / precio_activo

def calculate_linear_regression(prices):
    n = len(prices)
    if n < 10:
        return 0.0, 0.0

    y = np.asarray(prices, dtype=np.float64)
    x = np.arange(n, dtype=np.float64)

    # El polyfit interno de numpy corre sobre binarios C puros
    slope, intercept = np.polyfit(x, y, 1)

    predict = slope * x + intercept
    error_res = np.sum((y - predict) ** 2)
    error_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1.0 - (error_res / error_tot) if error_tot != 0 else 0.0

    return float(slope), float(r_squared)

def calculate_z_score(prices, period=20):
    if len(prices) < period:
        return 0.0
    recent_prices = np.asarray(prices, dtype=np.float64)[-period:]
    mean = np.mean(recent_prices)
    std = np.std(recent_prices)
    if std == 0: 
        return 0.0
    return float((prices[-1] - mean) / std)

def calculate_rvol(volume_deltas, period=50):
    if len(volume_deltas) < period:
        return 1.0
    recent_deltas = np.asarray(volume_deltas, dtype=np.float64)[-period:]
    mean_volume = np.mean(recent_deltas)
    if mean_volume == 0:
        return 1.0
    return float(volume_deltas[-1] / mean_volume)

def calculate_pearson_correlation(prices_a, prices_b, period=50):
    if len(prices_a) < period or len(prices_b) < period:
        return 1.0
    arr_a = np.asarray(prices_a, dtype=np.float64)[-period:]
    arr_b = np.asarray(prices_b, dtype=np.float64)[-period:]
    if np.std(arr_a) == 0 or np.std(arr_b) == 0:
        return 1.0
    correlation_matrix = np.corrcoef(arr_a, arr_b)
    return float(correlation_matrix[0, 1])

def calculate_adaptive_std(prices, period=200):
    if len(prices) < 10:
        return 0.0
    actual_period = min(len(prices), period)
    return float(np.std(np.asarray(prices, dtype=np.float64)[-actual_period:]))

