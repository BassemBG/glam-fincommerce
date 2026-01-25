import os
import json
import logging
import base64
import httpx
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Service for interacting with Azure OpenAI models (GPT-4o)"""
    
    def __init__(self):
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.deployment = settings.AZURE_OPENAI_CHAT_DEPLOYMENT
        self.api_version = "2024-08-01-preview"
        
        if not self.api_key or not self.endpoint:
            logger.warning("Azure OpenAI credentials missing. Service will be limited.")
            self.client = None
        else:
            self.client = httpx.AsyncClient(
                timeout=60.0,
                headers={"api-key": self.api_key}
            )

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Generate text using Azure OpenAI chat completions"""
        if not self.client:
            raise ValueError("Azure OpenAI client not initialized.")
            
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        
        try:
            response = await self.client.post(
                url,
                json={
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Azure OpenAI Text Generation failed: {e}")
            raise

    async def analyze_image(self, image_data: bytes, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze an image using GPT-4o with Vision on Azure"""
        if not self.client:
            raise ValueError("Azure OpenAI client not initialized.")
            
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
            ]
        })

        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        
        try:
            response = await self.client.post(
                url,
                json={
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 2048
                }
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            
            # Extract JSON
            text = text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).rsplit("```", 1)[0].strip()
            elif text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"): text = text[4:]
                text = text.strip()
            
            return json.loads(text)
        except Exception as e:
            logger.error(f"Azure OpenAI Image Analysis failed: {e}")
            raise

    async def close(self):
        if self.client:
            await self.client.aclose()

azure_openai_service = AzureOpenAIService()
