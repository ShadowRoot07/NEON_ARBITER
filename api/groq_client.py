import asyncio
import aiohttp
import ujson

class GroqClient:
    def __init__(self):
        self.url = 'https://api.groq.com/predict'

    async def send_data(self, data):
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=data) as response:
                return await response.json()
