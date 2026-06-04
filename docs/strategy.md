# 📊 Módulo: Estrategia Algorítmica (`./core/strategies/algorithmic_scalper.py`)

## 📝 Descripción General
[cite_start]El `AlgorithmicScalper` es el componente táctico especializado de **Neon Arbiter** que hereda de la interfaz abstracta `BaseStrategy`[cite: 52, 61]. [cite_start]Su propósito fundamental es realizar un análisis cuantitativo de alta frecuencia sobre el flujo de ticks del activo principal, combinando osciladores de momentum, desviaciones estadísticas de precio y filtros de correlación en altcoins para identificar ventanas de entrada y salida ultra-rápidas[cite: 52, 53, 54].

---

## 📈 Indicadores Técnicos y Análisis de Datos

[cite_start]En cada intervalo de ejecución, el método `analyze` transforma el búfer cíclico de datos en una estructura de métricas de mercado estructuradas[cite: 52, 54]:

* [cite_start]**Índice de Fuerza Relativa (RSI):** Evalúa la velocidad y el cambio de los movimientos de precios en una ventana de 14 períodos para detectar zonas de agotamiento o sobreventa[cite: 52].
* [cite_start]**Cruces de Medias Móviles (Fast/Slow MA):** Rastrea una media rápida de 9 períodos y una lenta de 21 períodos para mapear la dirección inmediata del precio del activo[cite: 52].
* [cite_start]**Puntaje Z (Z-Score):** Mide de forma estadística cuántas desviaciones estándar está alejado el precio respecto a su media móvil de 20 períodos, actuando como la brújula fundamental durante fases de rango lateral[cite: 8, 52].
* [cite_start]**Mapeo de Correlación de Altcoins:** Escanea en tiempo real los buffers secundarios de `ETHUSDT` y `SOLUSDT`[cite: 13, 53]. [cite_start]Si detecta que las altcoins están moviéndose de forma positiva en sus últimos 5 ticks, incrementa un puntaje de correlación (`correlation_score`), proveyendo una confirmación de la fuerza del movimiento de mercado general[cite: 53].
* [cite_start]**Momento de Tendencia:** Calcula la tasa de cambio porcentual inmediata utilizando el analizador de tendencias del sistema[cite: 54, 95].

---

## 🛡️ Lógica de Disparo y Blindajes Financieros

[cite_start]El método `should_execute` procesa el análisis técnico cruzándolo con el dictamen del clima de mercado bajo reglas estrictas de control de riesgo[cite: 55, 61]:

### 1. Bloqueo de Estados Caóticos (`CHAOS` / `WARMING_UP`)
[cite_start]Si el mercado es dictaminado en fase de calentamiento de buffers o en volatilidad extrema impredecible (`CHAOS`), la estrategia cancela de forma inmediata cualquier evaluación algorítmica, devolviendo un estado neutro de espera (`HOLD`, `0.0`)[cite: 55].

### 2. El Blindaje Anti-Cuchillo en Caída (`Falling Knife`)
[cite_start]Es el escudo matemático crítico inyectado en el generador de órdenes de compra[cite: 58]. [cite_start]La estrategia evalúa si el precio se encuentra en una fase de caída libre vertical o si las medias móviles se encuentran cruzadas a la baja de forma agresiva ($Precio < MA_{fast}$ o $MA_{fast} < MA_{slow}$)[cite: 56]. 
* [cite_start]**Comportamiento:** Si estas condiciones se cumplen, el flag `is_falling_knife` se activa inmediatamente, bloqueando por completo cualquier orden de compra por más sobrevendido que se muestre el oscilador RSI o el Z-Score[cite: 56, 57, 58]. [cite_start]Esto previene que el bot intente capturar rebotes falsos mientras el mercado se desploma verticalmente[cite: 57].

### 3. Reglas de Ejecución de Órdenes

#### 🛒 Directiva de Compra (`BUY`)
* [cite_start]**Climas Aptos:** `RANGING`, `TRENDING_UP`, y `RANGING_DEAD` (sujeto a que el spread supere el costo de comisiones en el orquestador principal)[cite: 35, 58].
* [cite_start]**Condiciones Matemáticas:** Requiere de forma simultánea que el Z-Score se encuentre en sobreventa extrema local ($Z\_Score < -2.0$), el RSI esté por debajo de la línea de los 40 puntos y que el filtro protector `is_falling_knife` confirme que la caída se ha estabilizado[cite: 58, 59].
* [cite_start]**Confianza Asignada:** `0.85` (Garantiza alta prioridad de entrada)[cite: 59].

#### 🔨 Directiva de Venta de Emergencia y Cierre (`SELL`)
* [cite_start]**Salida por Inversión de Tendencia:** Si el clima conmuta a tendencia estrictamente bajista (`TRENDING_DOWN`) o si los buffers detectan que la posición activa quedó atrapada en una caída libre vertical (`is_falling_knife`), el bot ejecuta una orden de mercado inmediata para liquidar el inventario y mitigar pérdidas con un factor de confianza de `0.95`[cite: 59].
* [cite_start]**Salida por Sobrecompra Extrema:** Si el oscilador RSI supera el umbral crítico de los 80 puntos en mercados laterales o tendencias alcistas, el bot ejecuta una toma de ganancias preventiva con una confianza de `0.80`[cite: 60].

---

## ⚙️ Configuración de Parámetros de Riesgo Integrados
[cite_start]La estrategia trabaja de manera simbiótica con el gestor de órdenes (`TradingLogic`), el cual inyecta límites de control dinámicos según el modo operativo[cite: 70, 71]:
* [cite_start]**Modo Scalper Activo:** Configura un stop-loss ajustado de `0.3%` (`0.003`) y un trailing stop dinámico de `0.2%` (`0.002`) para asegurar ganancias rápidas ante micro-variaciones de spread[cite: 71].
