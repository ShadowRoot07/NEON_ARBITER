import aiohttp
import ujson

class GroqClient:
    def __init__(self, api_key):
        self.url = 'https://api.groq.com/openai/v1/chat/completions'
        self.api_key = api_key

    async def get_decision(self, prompt, model="llama-3.1-8b-instant"): # Modelo cambiado por defecto
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Eres un experto trader de alta frecuencia. Responde solo JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=payload) as resp:
                data = await resp.json()
                if "choices" not in data:
                    # Si hay error de Rate Limit, lo lanzamos para que engine lo maneje
                    if "error" in data:
                        raise Exception(f"GROQ_ERROR: {data['error'].get('code', 'unknown')}")
                return data

