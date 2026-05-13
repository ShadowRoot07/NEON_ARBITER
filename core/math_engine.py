import numpy as np

def calculate_rsi(prices, period=14):
    """Calcula el RSI usando la fórmula de suavizado de Welles Wilder."""
    if len(prices) <= period:
        return 50.0
    
    # Convertir deque a numpy array para velocidad
    prices = np.array(prices)
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
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
        rs = up / down
        rsi[i] = 100. - 100. / (1. + rs)

    return rsi[-1] # Retornamos solo el valor más reciente

def calculate_moving_average(prices, period=20):
    """Media móvil simple optimizada."""
    if len(prices) < period:
        return prices[-1]
    return np.mean(prices[-period:])

def calcular_monto_seguro(balance_disponible, precio_activo, min_usd=11.0):
    """
    Calcula cuánto comprar asegurando que supere el mínimo de Binance (~10 USD).
    Retorna la cantidad en la moneda base (ej. BTC).
    """
    if balance_disponible < min_usd:
        return 0.0
    
    # Usamos un pequeño margen sobre el mínimo (11 USD)
    monto_a_usar = max(min_usd, balance_disponible * 0.98) # Usar el 98% del balance o el min_usd
    cantidad = monto_a_usar / precio_activo
    return cantidad

