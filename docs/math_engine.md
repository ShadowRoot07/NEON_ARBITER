# 🧮 Módulo: Core Math Engine (`./core/math_engine.py`)

## 📝 Descripción General
[cite_start]Este componente aloja las funciones matemáticas y estadísticas optimizadas mediante **NumPy**. [cite_start]Su objetivo primordial es procesar con alta velocidad y eficiencia los búferes de precios en tiempo real dentro del entorno restringido de Termux, eliminando la latencia en el cálculo de indicadores clave[cite: 228, 266].

## 🛠️ Especificación de Funciones

### 1. `calculate_rsi(prices, period=14)`
[cite_start]Calcula el Índice de Fuerza Relativa (RSI) aplicando la fórmula de suavizado original de Welles Wilder.
* [cite_start]**Optimización:** Transforma colecciones `deque` a arreglos nativos de NumPy para acelerar las operaciones vectoriales en bucle.
* **Parámetros:**
    * [cite_start]`prices` (list/deque): Historial de precios de cierre.
    * [cite_start]`period` (int): Ventana temporal para el indicador (Por defecto: `14`).
* [cite_start]**Retorno:** `float` - El valor de RSI más reciente (entre `0.0` y `100.0`)[cite: 228, 230]. [cite_start]Si el historial es insuficiente, retorna un valor neutro de `50.0`.

### 2. `calculate_moving_average(prices, period=20)`
[cite_start]Calcula la Media Móvil Simple (SMA) optimizada[cite: 230].
* **Parámetros:**
    * [cite_start]`prices` (list/deque): Búfer de precios[cite: 230].
    * [cite_start]`period` (int): Ventana de la media móvil (Por defecto: `20`)[cite: 230].
* [cite_start]**Retorno:** `float` - El promedio aritmético de los últimos $N$ periodos[cite: 231]. [cite_start]Si la muestra es menor al periodo, retorna el último precio disponible[cite: 231].

### 3. `calculate_linear_regression(prices)`
[cite_start]Ejecuta una regresión lineal simple sobre los últimos 100 precios para modelar tendencias estrictas[cite: 233, 319].
* **Parámetros:**
    * [cite_start]`prices` (list/deque): Muestra de precios del búfer[cite: 234].
* **Retorno:** `(slope, r_squared)`
    * `slope` (`float`): Pendiente de la recta de ajuste. [cite_start]Un valor $> 0$ indica tendencia alcista[cite: 233].
    * `r_squared` (`float`): Coeficiente de determinación ($R^2$). [cite_start]Valores $> 0.7$ confirman que la tendencia analizada es estadísticamente fuerte y confiable[cite: 233].

### 4. `calculate_z_score(prices)`
[cite_start]Mide cuántas desviaciones estándar está alejado el precio actual respecto de su media móvil de 20 periodos[cite: 235]. [cite_start]Es la métrica fundamental usada por las estrategias en mercados laterales[cite: 279].
* **Parámetros:**
    * [cite_start]`prices` (list/deque): Historial de precios[cite: 235].
* [cite_start]**Retorno:** `float` - Puntaje Z (Z-Score)[cite: 235]. [cite_start]Si la desviación estándar es `0`, retorna `0.0` para blindar el flujo contra errores de división por cero[cite: 235].

### 5. `calcular_monto_seguro(balance_disponible, precio_activo, min_usd=11.0)`
[cite_start]Filtro de seguridad que calcula el tamaño exacto de la orden a colocar en la moneda base (ej. BTC)[cite: 231, 232].
* [cite_start]**Propósito:** Asegura de forma infalible que cualquier transacción supere el umbral mínimo operativo impuesto por la API de Binance (~10 USD)[cite: 231].
* [cite_start]**Lógica:** Aplica una protección del `98%` del balance disponible en cash para absorber pequeñas variaciones de mercado y comisiones, o bien asigna el mínimo estricto (`11.0` USD)[cite: 301].
* [cite_start]**Retorno:** `float` - Cantidad exacta del activo a comprar/vender[cite: 232]. [cite_start]Retorna `0.0` si el balance es menor que el mínimo requerido[cite: 231].

***

## 🛡️ Blindajes implementados
1.  **Filtro de Historial Insuficiente:** Cada función valida que la longitud de los datos sea apta para el cálculo, retornando estados seguros en lugar de generar excepciones en cascada (`IndexError`, `ValueError`)[cite: 228, 231].
2.  **Eficiencia en Memoria:** Se prioriza la rebanada (`slice`) de arreglos NumPy en lugar de clonaciones masivas de memoria[cite: 228, 231].
