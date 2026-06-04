# ⚙️ Módulo: Core Engine (`./core/engine.py`)

## 📝 Descripción General
[cite_start]El `Engine` es el orquestador y motor de ejecución asíncrono central de **Neon Arbiter**[cite: 12]. [cite_start]Su función fundamental es inicializar las conexiones de datos con la API de Binance [cite: 12, 13][cite_start], alimentar y gestionar los búferes cíclicos de precios en memoria [cite: 13, 26, 46][cite_start], evaluar las condiciones climáticas del mercado mediante análisis técnicos en intervalos definidos [cite: 29, 30] [cite_start]y coordinar la ejecución segura de órdenes simuladas y la persistencia de estados en la base de datos[cite: 25, 38, 41, 49].

## 🏗️ Flujo de Operación y Ciclo de Vida

### 1. Inicialización y Configuración Híbrida
Al instanciarse, el motor realiza las siguientes tareas automáticas en su constructor:
* [cite_start]Registra los canales de suscripción para múltiples activos en paralelo (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`)[cite: 12].
* [cite_start]Instancia el cliente asíncrono de WebSockets compartiendo el listado de símbolos configurados[cite: 12, 13].
* [cite_start]Inicializa la lógica de trading (`TradingLogic`) y define si operará bajo la estrategia especializada de Scalping (`is_scalper`)[cite: 13].
* [cite_start]Asigna colas de doble extremo de tamaño controlado (`deque(maxlen=100)`) como buffers de datos secundarios para las altcoins[cite: 13].
* [cite_start]Crea una fábrica de sesiones con soporte para transacciones en caliente conectada a la base de datos remota u local (`sessionmaker`)[cite: 14].

### 2. Fase de Calentamiento (Warm-up) e Historial
[cite_start]Para evitar lecturas erróneas de indicadores técnicos al momento de encender el sistema, el motor ejecuta un protocolo de carga inicial[cite: 14]:
* [cite_start]**Descarga Base:** Solicita un bloque de 100 velas históricas base para inicializar el búfer de precios (`price_buffer`)[cite: 14, 15, 16].
* [cite_start]**Sincronización:** Consume el último tick del historial cargado para sincronizar los balances, pérdidas diarias y posiciones activas guardadas previamente en la base de datos de Neon.tech[cite: 16, 83, 85].
* [cite_start]**Blindaje contra interrupciones:** Si ocurre un fallo de red o una excepción en el bucle asíncrono del dispositivo móvil, el motor captura el error, suspende la ejecución 3 segundos y ejecuta una **Re-sincronización de Emergencia Segura** [cite: 18, 19] [cite_start]descargando un bloque fresco de 50 velas para limpiar los deques desfasados antes de volver a operar[cite: 19, 20, 21].

### 3. El Bucle Principal Asíncrono (`async for data in client.connect()`)
[cite_start]El bucle principal actúa como un consumidor continuo del generador asíncrono de ticks del WebSocket[cite: 22]:
* [cite_start]**Control del Tiempo de Sesión:** Evalúa si se ha alcanzado la duración máxima de simulación definida en minutos (`duration_mins`)[cite: 23]. Al cumplirse, calcula el patrimonio total neto actual, guarda el estado financiero en la tabla de persistencia y finaliza la rutina limpiamente (`return`)[cite: 23, 25].
* [cite_start]**Distribución de Buffers:** Los ticks provenientes de `BTCUSDT` se anexan al búfer de análisis principal, incrementando el contador global de ticks operativos[cite: 26]. [cite_start]Los ticks de `ETHUSDT` y `SOLUSDT` se redirigen en paralelo a sus respectivos deques secundarios para análisis correlativos[cite: 45, 46].
* [cite_start]**Filtro de Límite de Pérdidas:** En cada ciclo se valida si el bot cuenta con permisos financieros para operar (`can_trade`)[cite: 27]. [cite_start]Si la pérdida diaria alcanzó el límite máximo tolerado del balance (5%), el procesamiento se detiene de inmediato por control de riesgo[cite: 27, 72].

### 4. Filtros Protectores y Ejecución Algorítmica
[cite_start]El motor ejecuta el análisis matemático de la estrategia en intervalos configurables (cada 2 ticks si está activo el modo Scalper)[cite: 28]:
* [cite_start]**Bloqueo de Rango Muerto (`RANGING_DEAD`):** Llama a `TrendAnalyzer.get_market_climate`[cite: 30]. [cite_start]Si el mercado es determinado como un lateral plano sin volatilidad donde las comisiones del exchange consumirían el spread operativo, el motor congela las operaciones, imprime una alerta detallada en la consola de Termux y salta el ciclo de compra (`continue`)[cite: 34, 35, 36].
* [cite_start]**Disparo de Órdenes:** Si el clima es apto, consulta las señales analizadas por el `AlgorithmicScalper`[cite: 36]. [cite_start]Si la estrategia arroja una orden de compra (`BUY`) y no existen operaciones abiertas en la sesión, ejecuta la simulación adquiriendo el activo[cite: 37, 38]. [cite_start]Si arroja una señal de venta (`SELL`) teniendo inventario, cierra la posición calculando el PnL neto[cite: 37, 38, 79].

### 5. Monitor Visual de Consola e Inyección de Estado
[cite_start]Cada 20 ticks, el motor limpia y renderiza una fila de estado estético en la terminal de Termux utilizando códigos de color ANSI según el clima del mercado[cite: 39, 41, 42]:
* [cite_start]Muestra el modo de ejecución actual, el precio en vivo de Bitcoin, el dictamen del clima, el patrimonio total unificado (Efectivo + Cripto), el efectivo líquido y el PnL diario acumulado[cite: 42, 43, 44, 45, 71].
* [cite_start]**Heredabilidad Cloud:** En ese mismo intervalo ejecuta `save_current_state(total_equity)` [cite: 41][cite_start], el cual abre un contexto transaccional asíncrono en la base de datos de la nube, inyectando un registro en la tabla `BotState` con el balance actualizado y los estados de actividad para que puedan ser heredados de forma transparente por workflows en la nube o ejecuciones consecutivas[cite: 49, 50].

***

## 🛡️ Blindajes del Sistema en este Componente
1.  **Aislamiento Total de Caídas de Red:** La captura global de excepciones encapsula los fallos del generador, evitando que el script muera de forma definitiva en el celular y forzando reintentos con purga segura de datos viejos[cite: 46, 47, 48].
2.  **Protección de Fricción de Corretaje:** El descarte de operaciones en bloques `RANGING_DEAD` actúa como un escudo matemático directo que preserva los balances de prueba intactos ante la falta de volumen o spread mínimo[cite: 34, 35].
