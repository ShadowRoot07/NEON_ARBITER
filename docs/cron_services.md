# 🛰️ Módulo: Servicios Cron e Inteligencia Fundamental Macro (`./cron/`)

## 📝 Descripción General
Este subsistema opera de forma independiente al bucle de trading de alta frecuencia, actuando como un centinela de análisis fundamental. Su propósito es rastrear noticias globales del ecosistema cripto en tiempo real, filtrar eventos irrelevantes y utilizar modelos avanzados de Inteligencia Artificial a través de **Groq** para emitir dictámenes macro directos hacia tu canal de comunicación en Discord.

---

## 📥 1. Extractor de Noticias (`./cron/news_fetcher.py`)

El componente `NewsFetcher` es el encargado del rastreo y limpieza de la información financiera del mercado general.

* **Conectividad:** Se enlaza asíncronamente con la API de **CryptoCompare** utilizando `httpx`.
* **Filtro Temporal de 24 Horas:** Para evitar saturar los prompts con datos viejos o descontados por el mercado, el script calcula el timestamp actual y descarta de forma estricta cualquier artículo cuya antigüedad supere las 24 horas (`86,400` segundos).
* **Filtro por Palabras Clave:** Evalúa el título, el cuerpo y las categorías del artículo buscando términos de alto impacto macro: `btc`, `bitcoin`, `binance`, `fed`, `sec`, `regulation`, `crypto`, `market`. Si la noticia no contiene ninguna palabra clave, es ignorada inmediatamente.
* **Control de Volumen:** Limita el set de datos a un máximo de 15 artículos frescos y sanitizados para optimizar el contexto enviado a la IA.

---

## 🧠 2. Orquestador de Alertas y Análisis (`./cron/discord_notifier.py`)

El componente `NeonMacroNotifier` es el cerebro fundamental que procesa los datos limpios del fetcher y emite el reporte.

### 🤖 Integración con el Oráculo Spica (Groq API)
* **Modelo Utilizado:** Consume el modelo de alto razonamiento analítico `llama-3.3-70b-versatile` a través de la API de Groq.
* **Estructuración del Prompt:** Configura un rol de sistema estricto que encarna al **Oráculo Spica**. El modelo analiza el string consolidado de noticias y determina de forma obligatoria el Sentimiento Macro y la ventana horaria óptima de liquidez global adaptada específicamente al **Horario de Venezuela (VET, UTC-4)**.
* **Ventanas de Liquidez Evaluadas:**
  * `08:30 AM a 11:30 AM VET` (Apertura de Nueva York - Alta Liquidez).
  * `02:00 PM a 04:00 PM VET` (Cierre de Nueva York - Movimientos Agresivos).
  * `09:00 PM a 11:30 PM VET` (Apertura de Asia - Volatilidad Sutil).

### 🎨 Despliegue Estético en Discord (Webhooks)
Una vez que la IA genera el dictamen en formato Cyberpunk limpio, el servicio empaqueta la información en un objeto **Embed** de Discord de alta calidad visual:
* **Identidad Visual:** Despacha la alerta bajo el nombre "NEON ARBITER ORACLE" utilizando un avatar cyberpunk dedicado.
* **Colorimetría:** Aplica un color verde neón decimal (`5763719`) para mantener la coherencia estética del proyecto.
* **Campos del Reporte:** Muestra de forma estructurada el Sentimiento Macro (ALCISTA/BAJISTA/LATERAL), el Factor Crítico de la noticia más importante, la Ventana Recomendada (VET) detallando el porqué, y el Nivel de Riesgo (BAJO/MEDIO/ALTO).

---

## 🛡️ Configuración de Entornos y Automatización
* **Detección Dinámica de Contexto:** El punto de entrada del script detecta si está corriendo de forma local en Termux (cargando variables desde el archivo `.env`) o si es disparado de forma automatizada por un flujo externo en la nube o tareas automatizadas (utilizando variables nativas del sistema).
* **Resiliencia ante Errores:** Cuenta con capturas de excepciones globales (`try/except`) y tiempos de espera límites (`timeout=20.0`) en las peticiones HTTP. Esto evita que el servicio se quede colgado o bloquee recursos del dispositivo si las API externas experimentan caídas temporales.
