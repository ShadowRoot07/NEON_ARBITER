import os
import httpx
import asyncio
import logging
from datetime import datetime  # <-- Asegúrate de que esté así
from cron.news_fetcher import NewsFetcher

logger = logging.getLogger("NEON.DISCORD_NOTIFIER")

class NeonMacroNotifier:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        # Usamos Llama 3 70B para un razonamiento analítico superior
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

    async def analyze_and_notify(self):
        if not self.groq_key or not self.webhook_url:
            logger.error("❌ Faltan llaves en el .env (GROQ o DISCORD).")
            return

        # 1. Extraemos las noticias del fetcher
        fetcher = NewsFetcher()
        news_data = await fetcher.fetch_crypto_news(limit=10)
        
        if not news_data:
            logger.warning("⚠️ No hay noticias frescas para analizar hoy.")
            return

        # Formateamos las noticias en un string compacto para el prompt
        formatted_news = ""
        for i, n in enumerate(news_data, 1):
            formatted_news += f"[{i}] {n['title']}\nSummary: {n['summary']}\n\n"

        # 2. Construimos el reporte con Groq
        logger.info("🧠 Solicitando análisis predictivo de fundamentales a Groq...")
        
        system_prompt = (
            "Eres el Oráculo Spica integrado en el bot de trading Neon Arbiter. Tu trabajo es analizar las noticias proporcionadas "
            "y determinar el Sentimiento Macro del mercado (ALCISTA, BAJISTA o LATERAL/PELIGROSO) y recomendar la mejor ventana "
            "horaria para ejecutar operaciones de Scalping basado estrictamente en el Horario de Venezuela (VET, UTC-4).\n\n"
            "Toma en cuenta las siguientes ventanas de liquidez global adaptadas a Venezuela (VET):\n"
            "- 08:30 AM a 11:30 AM VET (Apertura NY - Alta Liquidez)\n"
            "- 02:00 PM a 04:00 PM VET (Cierre NY - Movimientos Agresivos)\n"
            "- 09:00 PM a 11:30 PM VET (Apertura Asia - Volatilidad sutil)\n\n"
            "Tu respuesta DEBE ser concisa, en español, con un tono Cyberpunk limpio y estructurada exactamente en este formato para Discord:\n"
            "**🟢 SENTIMIENTO MACRO:** [ALCISTA/BAJISTA/LATERAL]\n"
            "**📊 FACTOR CRÍTICO:** [Breve explicación de 2 líneas de la noticia más importante]\n"
            "**⚡ VENTANA RECOMENDADA (VET):** [Especifica cuál de las 3 ventanas es la óptima para hoy y por qué]\n"
            "**🛡️ NIVEL DE RIESGO:** [BAJO/MEDIO/ALTO]"
        )

        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",  #  Modelo ultra-rápido y activo en Groq
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Aquí están las noticias del día:\n\n{formatted_news}"}
            ],
            "temperature": 0.3
        }

        try:
            async with httpx.AsyncClient() as client:
                # Petición a Groq
                response = await client.post(self.groq_url, json=payload, headers=headers, timeout=20.0)
                if response.status_code != 200:
                    logger.error(f"❌ Groq API Error: {response.text}")
                    return
                
                ai_analysis = response.json()["choices"][0]["message"]["content"]

                # 3. Despachamos el Embed estético a Discord vía Webhook
                logger.info("🎨 Despachando reporte estético al canal de Discord...")
                
                discord_payload = {
                    "username": "NEON ARBITER ORACLE",
                    "avatar_url": "https://as2.ftcdn.net/jpg/04/37/18/97/1000_F_437189719_LtT2C9rI7daocWkV08C5FLlV3zQXGIjS.jpg",  # Un avatar genérico cyberpunk
                    "embeds": [{
                        "title": "🛰️ REPORTE DIARIO DE CONCIENCIA FUNDAMENTAL",
                        "description": f"Análisis macro generado el {datetime.now().strftime('%d/%m/%Y')} para la gestión de riesgo del Scalper.",
                        "color": 5763719,  # Color verde neón en formato decimal INT
                        "fields": [
                            {
                                "name": "🧠 DICTAMEN DEL ORÁCULO SPICA",
                                "value": ai_analysis,
                                "inline": False
                            }
                        ],
                        "footer": {
                            "text": "Neon Arbiter v1.0 • Sistema de Libertad Financiera",
                            "icon_url": "https://as2.ftcdn.net/jpg/04/37/18/97/1000_F_437189719_LtT2C9rI7daocWkV08C5FLlV3zQXGIjS.jpg"
                        }
                    }]
                }

                discord_res = await client.post(self.webhook_url, json=discord_payload, timeout=10.0)
                if discord_res.status_code in [200, 204]:
                    logger.info("✅ ¡Reporte macro enviado a Discord con éxito!")
                else:
                    logger.error(f"❌ Error al enviar a Discord: {discord_res.status_code} - {discord_res.text}")

        except Exception as e:
            logger.error(f"❌ Error crítico en el notifier: {e}")

if __name__ == "__main__":
    # Intentamos cargar dotenv de forma segura (solo para entorno local en Termux)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logging.info("📝 Entorno local detectado: Variables cargadas desde el archivo .env")
    except ImportError:
        logging.info("🛰️ Entorno de producción/Nube detectado: Usando variables de entorno nativas")

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
    notifier = NeonMacroNotifier()
    asyncio.run(notifier.analyze_and_notify())

