import aiohttp
import ujson

class GroqClient:
    def __init__(self, api_key):
        self.url = 'https://api.groq.com/openai/v1/chat/completions'
        self.api_key = api_key
    
    async def get_decision(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Eres un experto trader. Responde siempre en JSON puro."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=payload) as resp:
                data = await resp.json()
                if "choices" not in data:
                    print(f"DEBUG GROQ: {data}") # Esto nos dirá el error real
                return data

