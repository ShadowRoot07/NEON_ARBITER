# ⚡ Neon Arbiter (V1.0 - Beta)

[![Developer](https://img.shields.io/badge/Developer-ShadowRoot07-00ff00?style=for-the-badge&logo=github)](https://github.com/tu_usuario)
[![Alias](https://img.shields.io/badge/Alias-ShadowRoot07-purple?style=for-the-badge)]()
[![Environment](https://img.shields.io/badge/Environment-Termux%20%7C%20NeoVim-black?style=for-the-badge&logo=neovim)]()

**Neon Arbiter** es un bot autónomo de trading algorítmico asíncrono de alta frecuencia (Scalping) diseñado de forma nativa para ejecutarse en entornos móviles ligeros (Termux) y despliegues programados en la nube (GitHub Actions). 

El sistema implementa un motor cuantitativo optimizado que procesa flujos de datos en tiempo real mediante WebSockets, protegiendo el capital simulado a través de avanzados escudos matemáticos y filtros de comisiones antes de la ejecución de órdenes.

---

## 🧭 Portal de Documentación Modular

Para mantener el código limpio y una arquitectura de software institucional, la documentación técnica avanzada del grimorio se encuentra dividida en los siguientes módulos especializados:

* 🧮 **[Core Math Engine](./docs/math_engine.md):** Optimización estadística vectorial con NumPy, cálculo de RSI, regresión lineal, Z-Score y gestión del tamaño seguro de órdenes.
* ⚙️ **[Orquestador Asíncrono (Engine)](./docs/engine.md):** Gestión del ciclo de vida del bot, bucle principal de WebSockets, fases de calentamiento (*warm-up*) y control de límites de pérdida diaria.
* 📊 **[Estrategia Algorítmica y Escudos](./docs/strategy.md):** Lógica del Scalper, evaluación de correlaciones en altcoins (ETH/SOL) y el escudo crítico *Anti-Falling Knife*.
* 💾 **[Persistencia e Infraestructura Híbrida](./docs/database.md):** Modelado relacional con SQLAlchemy, conmutación automática (*failover*) entre Neon.tech (Cloud PostgreSQL con SSL) y SQLite (Local).
* 🛰️ **[Servicios Cron e Inteligencia Macro](./docs/cron_services.md):** Extractor de noticias crypto y orquestación de reportes de sentimiento con modelos de IA (Groq) hacia Discord adaptados al horario de Venezuela.

---

## 🚀 Guía de Inicio Rápido (QuickStart) en Termux

### 🔧 1. Preparación del Entorno Operativo
Ejecuta los siguientes comandos en tu terminal de Termux para instalar las herramientas de compilación y dependencias de criptografía necesarias:
```bash
pkg update && pkg upgrade -y
pkg install python python-pip openssl-tool ca-certificates clang make -y
```
### 📦 2. Clonación e Instalación
1. Clona este repositorio en tu espacio de trabajo:
```bash
git clone [https://github.com/tu_usuario/NEON_ARBITER.git](https://github.com/tu_usuario/NEON_ARBITER.git)
cd NEON_ARBITER
```
2. Instala las librerías requeridas (optimizadas para el hardware de tu dispositivo):
```bash
pip install -r requirements.txt
```
### 🔑 3. Variables de Entorno (.env)
Crea un archivo llamado .env en la raíz del proyecto basándote en el archivo de ejemplo:
```fargmento de codigo
# Configuración de Binance (Requerido para producción / Opcional en Test)
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_SECRET_KEY=tu_secret_key_aqui

# Infraestructura Híbrida (Deja vacío para conmutar automáticamente a SQLite local)
DATABASE_URL=postgres://usuario:password@ep-neon-pooler.neon.tech/neondb?sslmode=require

# Canales de Alerta e Inteligencia Externa
GROQ_API_KEY=gsk_tu_llave_de_groq
DISCORD_WEBHOOK_URL=[https://discord.com/api/webhooks/](https://discord.com/api/webhooks/)...
```
## 🧪 Laboratorio de Pruebas (Paper Trading)
El sistema viene configurado por defecto para operar de forma estrictamente segura en modo simulación, lo que permite auditar las estrategias y el comportamiento de los deques sin arriesgar capital real.

Para lanzar una carrera de prueba de 30 minutos con $1000 USD de balance ficticio bajo la estrategia de Scalping, ejecuta:

```bash 
python main.py bot_on --test 1000 --scalper --duration 30
```
## 📊 Comportamiento Esperado del Escudo en Rango Muerto
Si el mercado experimenta una fase lateral sin volatilidad donde los costes de corretaje superen el spread aprovechable, el motor suspenderá temporalmente el disparo de órdenes imprimiendo el siguiente reporte preventivo:
```Plaintext
23:05:42 [NEON.ENGINE] 🎯 [SCALPER] Rango demasiado estrecho (Comisiones > Spread). Esperando volatilidad...
📊 [DAY] [BTC: $64,673.99] Clima: RANGING | TOTAL: $1000.00 | Cash: $1000.00 | PnL Diar: $0.00
```
## 🗺️ Plan de Desarrollo Futuro (Roadmap V2.0)
Neon Arbiter está diseñado bajo un modelo de evolución continua. La siguiente versión mayor del software estará enfocada en dos pilares fundamentales:
1. **Arbitraje Multimoneda Multihilo:** Activación e integración completa de los buffers paralelos de ETHUSDT y SOLUSDT para capturar spreads concurrentes mientras el activo principal lateraliza.
2. **Hardening de Ciberseguridad (Seguridad Ofensiva):**
    * Implementación de almacenamiento cifrado local para el resguardo de llaves secretas de la API.
    * Auditoría de dependencias y análisis estático de vulnerabilidades para mitigar ataques de inyección sobre la base de datos cloud.
    * Establecimiento de firmas digitales y tokens de rotación eficientes para la transmisión segura de los estados del bot.
