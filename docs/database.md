# 💾 Módulo: Capa de Persistencia Híbrida (`./database/schema.py`)

## 📝 Descripción General
Este componente define el esquema relacional de datos de **Neon Arbiter** utilizando el ORM **SQLAlchemy**. Está diseñado bajo una arquitectura híbrida de conmutación por fallo (*failover*), lo que permite al bot operar con almacenamiento local en entornos aislados o sincronizarse en caliente con un clúster PostgreSQL en la nube.

---

## 🏗️ Lógica de Conexión Dinámica y Failover

El script evalúa la variable de entorno `DATABASE_URL` provista por el módulo de configuración para determinar el entorno de ejecución:

1. **Entorno en la Nube (PostgreSQL / Neon.tech):**
   * Si la URI comienza con `postgres://`, el sistema realiza un formateo de strings automático reemplazándola por `postgresql://`, cumpliendo estrictamente con los requerimientos de compatibilidad de SQLAlchemy $\ge$ 1.4.
   * Configura de forma transparente los parámetros de seguridad SSL inyectando `sslmode=require` en los argumentos de conexión (`connect_args`).
   * **Inyección de Pool Pre-Ping:** Se añade el flag `pool_pre_ping=True` al motor de la base de datos. Esto fuerza al pooler a realizar una verificación ligera (ping) del socket antes de ceder una conexión a un hilo de ejecución, eliminando por completo los errores de desconexión abrupta (`unexpected eof while reading`) causados por los reinicios y purgas de inactividad de las bases de datos serverless.

2. **Entorno Local Fallback (SQLite):**
   * En caso de que la variable `DATABASE_URL` no esté definida en el entorno `.env` o el dispositivo se encuentre offline, el sistema conmuta automáticamente a un motor local basado en archivo: `sqlite:///database.db`. Esto garantiza que el bot nunca crasheará por falta de infraestructura externa en Termux.

---

## 📊 Modelos y Tablas del Sistema

Todas las tablas heredan de la clase base declarativa (`declarative_base()`) y son mapeadas de la siguiente manera:

### 1. `MarketData` (`market_data`)
Almacena el registro histórico de velas rastreadas para análisis técnicos retrospectivos.
* `id` (Integer): Clave primaria.
* `timestamp` (DateTime): Fecha y hora del registro (Por defecto: `datetime.now`).
* `open`, `high`, `low`, `close` (Float): Métricas de la vela japonesa.
* `volume` (Float): Volumen transaccionado en el período.

### 2. `Trades` (`trades`)
Mantiene la bitácora financiera estricta de las compras y ventas ejecutadas por el sistema. Es el núcleo consultado por el Warm-up para recobrar posiciones activas.
* `id` (Integer): Clave primaria.
* `timestamp` (DateTime): Registro temporal de la orden.
* `symbol` (String): Activo operado (Ej: `BTCUSDT`).
* `side` (String): Dirección del trade (`BUY` o `SELL`).
* `amount` (Float): Cantidad de criptoactivos adquiridos o liquidados.
* `price` (Float): Precio de ejecución de la orden en el exchange.

### 3. `AIAudit` (`ai_audit`)
Diseñado para la auditoría y almacenamiento analítico de las decisiones tomadas por los orquestadores de IA en simulaciones avanzadas.
* `id` (Integer): Clave primaria.
* `timestamp` (DateTime): Sello de tiempo de la consulta.
* `decision` (String): Sentimiento o directiva sugerida.
* `confidence` (Float): Factor de confianza matemática otorgada al análisis.

### 4. `BotState` (`bot_state`)
Tabla crítica de sincronización que almacena instantáneas en vivo del rendimiento financiero del bot. Es actualizada cada 20 ticks por el motor operativo.
* `id` (Integer): Clave primaria.
* `last_update` (DateTime): Sello temporal de última actualización automática.
* `total_balance` (Float): Balance líquido actual disponible en cash.
* `daily_pnl` (Float): Pérdida o ganancia neta acumulada en la sesión diaria.
* `current_mode` (String): Modo de mercado asignado (Ej: `DAY` o `SCALPER`).
* `is_active` (Integer): Flag binario de actividad del bot (`1` activo, `0` inactivo).

---

## 🛡️ Protocolo Automatizado de Arranque y Mantenimiento
* **Auto-Migración Inicial:** Al final del archivo, el script ejecuta `Base.metadata.create_all(engine)`. Esto asegura que al levantar el bot por primera vez (ya sea en local o en una nueva base de datos en Neon.tech), las tablas se construirán de forma automática si no existen, evitando errores de consulta.
* **Script de Purga (`purge_db.py`):** El proyecto incluye una herramienta administrativa externa capaz de limpiar por completo las tablas (`drop_all`) tras confirmar la acción por consola, reconstruyendo la estructura limpia (`create_all`) de forma inmediata para reiniciar laboratorios de prueba.
