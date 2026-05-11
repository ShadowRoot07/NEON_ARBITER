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
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=payload) as resp:
                return await resp.json()

