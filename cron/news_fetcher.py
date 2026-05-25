import os
import httpx
import logging
from datetime import datetime

logger = logging.getLogger("NEON.NEWS_FETCHER")

class NewsFetcher:
    def __init__(self):
        # Intentamos leer del .env local o de las variables de entorno de GitHub Actions
        self.api_key = os.getenv("CRYPTOCOMPARE_API_KEY")
        self.url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        
    async def fetch_crypto_news(self, limit=15):
        """Rastrilla las últimas noticias y filtra las que impactan a BTC y el mercado general."""
        if not self.api_key:
            logger.error("❌ No se encontró la API Key de CryptoCompare en las variables de entorno.")
            return []

        headers = {"Authorization": f"Apikey {self.api_key}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, headers=headers, timeout=10.0)
                
                if response.status_code != 200:
                    logger.error(f"❌ Error al consultar CryptoCompare: HTTP {response.status_code}")
                    return []
                
                data = response.json()
                raw_news = data.get("Data", [])
                
                import time # <-- Ponlo al inicio del método si prefieres

                current_time = int(time.time())
                seconds_in_24h = 86400
                
                sanitized_news = []
                for article in raw_news: # Quitamos el límite inicial para evaluar más volumen
                    title = article.get("title", "")
                    body = article.get("body", "")
                    categories = article.get("categories", "")
                    source = article.get("source_info", {}).get("name", "Unknown")
                    published_on = int(article.get("published_on", 0))

                    # ⏳ FILTRO CRÍTICO: ¿Está dentro de las últimas 24 horas?
                    if (current_time - published_on) > seconds_in_24h:
                        continue # Si es más vieja, la ignora y salta a la siguiente
                    
                    keywords = ["btc", "bitcoin", "binance", "fed", "sec", "regulation", "crypto", "market"]
                    text_to_check = (title + body + categories).lower()
                    
                    if any(kw in text_to_check for kw in keywords):
                        sanitized_news.append({
                            "title": title,
                            "summary": body[:200] + "...",
                            "source": source,
                            "categories": categories
                        })
                        
                    # Si ya juntamos suficientes noticias frescas, paramos para no saturar el prompt
                    if len(sanitized_news) >= limit:
                        break

                logger.info(f"📥 Rastrilladas con éxito {len(sanitized_news)} noticias de impacto macro.")
                return sanitized_news

        except Exception as e:
            logger.error(f"❌ Error crítico en el news_fetcher: {e}")
            return []

# Pequeño bloque de prueba local para Termux
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    logging.basicConfig(level=logging.INFO)
    fetcher = NewsFetcher()
    
    # Ejecutamos la prueba
    result = asyncio.run(fetcher.fetch_crypto_news(limit=5))
    print(f"\n--- Resultado de la prueba ({len(result)} artículos) ---")
    for i, item in enumerate(result, 1):
        print(f"[{i}] {item['title']} (Fuente: {item['source']})")

