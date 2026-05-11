import numpy as np
def calculate_rsi(prices, period=14):
    delta = np.diff(prices)
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    roll_up = np.cumsum(up)
    roll_down = np.cumsum(np.abs(down))
    rs = roll_up / roll_down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi
def calculate_moving_average(prices, period=20):
    return np.convolve(prices, np.ones(period) / period, mode='valid')