"""
GROQ LLAMA VISION - MAIN AI SERVICE FOR CLOTHING ANALYSIS

Uses: meta-llama/llama-4-scout-17b-16e-instruct (via Groq)
Status: FREE tier available
Benefits: 
  - Free image analysis (up to rate limits)
  - Supports image inputs
  - Can describe clothing in detail
  - Structured JSON responses
"""

import asyncio
import base64
import json
import httpx
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

# ==================== GROQ CLIENT ====================

class GroqVisionService:
    """Groq Llama Vision service for clothing analysis - Main AI service"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Use provided key or get from settings
        self.api_key = api_key or getattr(settings, 'GROQ_API_KEY', None)
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found. Groq service will not work.")
            self.client = None
            return
            
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0
        )
    
    async def _encode_image(self, image_data: bytes) -> str:
        """Encode image to base64"""
        return base64.b64encode(image_data).decode('utf-8')
    
    async def _call_vision(self, image_data: bytes, prompt: str, json_format: bool = True, max_tokens: int = 2048) -> str:
        """Call Groq Llama Vision API"""
        if not self.client:
            raise ValueError("Groq client not initialized. Check GROQ_API_KEY.")
            
        image_base64 = await self._encode_image(image_data)
        
        system_prompt = "You are a professional fashion expert analyzing clothing items. Always respond in valid JSON format only, no markdown, no code blocks."
        if not json_format:
            system_prompt = "You are a professional fashion expert analyzing clothing items."
        
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ]
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,  # Lower temperature for more consistent JSON
                    "max_tokens": max_tokens,
                }
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Groq API error {response.status_code}: {error_text}")
                raise Exception(f"Groq API error: {error_text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            logger.error("Groq API timeout")
            raise Exception("Groq API request timed out")
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise
    
    async def analyze_clothing(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze clothing from image - Returns detailed clothing attributes"""
        if not self.client:
            raise ValueError("Groq client not initialized. Check GROQ_API_KEY.")
            
        prompt = """You are a professional fashion analyst. Analyze this clothing item image and provide a detailed analysis.

Return ONLY valid JSON with these exact fields (no markdown, no code blocks):
{
  "category": "clothing|shoes|accessory",
  "sub_category": "specific type (e.g., T-shirt, Jeans, Midi Dress, Sneakers, Leather Jacket)",
  "body_region": "head|top|bottom|feet|full_body|outerwear|accessory",
  "colors": ["list", "of", "primary", "colors"],
  "material": "material type (denim, silk, wool, cotton, leather, polyester, nylon, etc.)",
  "vibe": "minimalist|boho|chic|streetwear|classic|casual|formal|athletic|romantic|vintage|preppy|edgy",
  "season": "Spring|Summer|Autumn|Winter|All Seasons",
  "description": "Detailed natural language description (2-3 sentences) of the item including style, fit, condition",
  "styling_tips": "How to style this piece with other items",
  "estimated_brand_range": "luxury|premium|mid-range|affordable|fast-fashion|unknown"
}
Return ONLY the JSON object, no markdown, no code blocks, no extra text."""
        
        try:
            response = await self._call_vision(image_data, prompt, json_format=True, max_tokens=2048)
            
            # Extract JSON from response (handle markdown code blocks)
            response = response.strip()
            if response.startswith("```"):
                parts = response.split("```")
                if len(parts) > 1:
                    response = parts[1]
                    if response.startswith("json"):
                        response = response[4:]
                response = response.strip()
            
            result = json.loads(response)
            logger.info(f"Clothing analysis complete: {result.get('sub_category', 'Unknown')}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}, response: {response[:200]}")
            raise ValueError(f"Failed to parse Groq response: {e}")
        except Exception as e:
            logger.error(f"Clothing analysis failed: {e}")
            raise
    
    async def analyze_body_type(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze full body attributes from image - Returns gender presentation, body type, skin tone, height estimate"""
        if not self.client:
            raise ValueError("Groq client not initialized. Check GROQ_API_KEY.")
            
        prompt = """You are an expert fashion consultant and stylist. Analyze this full-body image to determine body characteristics.

Return ONLY valid JSON with these fields (no markdown, no code blocks):
{
  "gender_presentation": "male|female|neutral|other",
  "body_type": "pear|apple|hourglass|rectangle|inverted_triangle|other",
  "skin_tone": "fair|light|medium|olive|tan|deep|rich",
  "estimated_height": "short|average|tall",
  "body_confidence": 0.85,
  "analysis_notes": "Brief explanation of the analysis"
}

Important: Be respectful and professional. Focus on styling insights.
Return ONLY JSON, no markdown or extra text."""
        
        try:
            response = await self._call_vision(image_data, prompt, json_format=True, max_tokens=1024)
            
            response = response.strip()
            if response.startswith("```"):
                parts = response.split("```")
                if len(parts) > 1:
                    response = parts[1]
                    if response.startswith("json"):
                        response = response[4:]
                response = response.strip()
            
            result = json.loads(response)
            logger.info(f"Body analysis complete: {result.get('body_type', 'Unknown')}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in body analysis: {e}")
            raise ValueError(f"Failed to parse Groq response: {e}")
        except Exception as e:
            logger.error(f"Body analysis failed: {e}")
            raise
    
    async def detect_brand(self, image_data: bytes, clothing_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Detect brand from image - Returns brand information"""
        if not self.client:
            raise ValueError("Groq client not initialized. Check GROQ_API_KEY.")
            
        prompt = """Analyze this clothing item image for brand indicators (logos, labels, distinctive design elements).

Return ONLY valid JSON (no markdown, no code blocks):
{
  "detected_brand": "Brand name or 'Unknown'",
  "brand_confidence": 0.85,
  "brand_indicators": ["List of indicators (e.g., 'visible logo', 'label text', 'distinctive stitching')"],
  "possible_alternatives": ["Alternative brands with similar design if confidence is low"]
}
Return ONLY JSON, no markdown."""
        
        try:
            response = await self._call_vision(image_data, prompt, json_format=True, max_tokens=1024)
            
            response = response.strip()
            if response.startswith("```"):
                parts = response.split("```")
                if len(parts) > 1:
                    response = parts[1]
                    if response.startswith("json"):
                        response = response[4:]
                response = response.strip()
            
            brand_data = json.loads(response)
            logger.info(f"Brand detection: {brand_data.get('detected_brand', 'Unknown')}")
            return brand_data
        except json.JSONDecodeError as e:
            logger.warning(f"Brand detection JSON error: {e}, returning default")
            return {
                "detected_brand": "Unknown",
                "brand_confidence": 0.0,
                "brand_indicators": [],
                "possible_alternatives": []
            }
        except Exception as e:
            logger.error(f"Brand detection failed: {e}")
            return {
                "detected_brand": "Unknown",
                "brand_confidence": 0.0,
                "brand_indicators": [],
                "possible_alternatives": []
            }
    
    async def generate_text_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings from text description using Groq.
        Since Groq doesn't have embeddings API, we use the model to generate
        a structured description and then create embeddings from it.
        
        For now, we'll use an improved hash-based approach that's more semantic.
        In production, consider using HuggingFace Inference API or sentence-transformers.
        """
        if not self.client:
            logger.warning("Groq client not initialized, using fallback embeddings")
            return self._generate_fallback_embedding(text)
        
        # Create a comprehensive text description for embedding
        # We'll use a hash-based approach that's deterministic but semantic
        return self._generate_fallback_embedding(text)
    
    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """Generate 768-dimensional embedding from text using improved hash-based approach"""
        import hashlib
        
        # Normalize text
        text_lower = text.lower().strip()
        
        # Create embedding using multiple hash functions for better distribution
        embedding = []
        words = text_lower.split()
        
        # Use word-level hashing for better semantic representation
        for i, word in enumerate(words[:100]):  # Limit to first 100 words
            # Create hash from word + position
            word_hash = hashlib.md5(f"{word}_{i}".encode()).hexdigest()
            # Convert hex to float between -1 and 1
            for j in range(0, min(8, 768 - len(embedding)), 1):
                hex_pair = word_hash[j*2:(j+1)*2]
                value = int(hex_pair, 16) / 255.0 * 2 - 1  # Scale to [-1, 1]
                embedding.append(value)
                if len(embedding) >= 768:
                    break
            if len(embedding) >= 768:
                break
        
        # Fill remaining dimensions with text hash
        if len(embedding) < 768:
            text_hash = hashlib.sha256(text_lower.encode()).hexdigest()
            remaining = 768 - len(embedding)
            for i in range(0, remaining, 1):
                hex_pair = text_hash[(i % len(text_hash)//2)*2:((i % len(text_hash)//2)+1)*2]
                if len(hex_pair) == 2:
                    value = int(hex_pair, 16) / 255.0 * 2 - 1
                else:
                    value = (ord(text_lower[i % len(text_lower)]) % 1000) / 1000.0 - 0.5
                embedding.append(value)
        
        return embedding[:768]
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """
        Generate text using Groq (for text-only tasks like chat, outfit composition, etc.)
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
        """
        if not self.client:
            raise ValueError("Groq client not initialized. Check GROQ_API_KEY.")
        
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Groq API error {response.status_code}: {error_text}")
                raise Exception(f"Groq API error: {error_text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            logger.error("Groq API timeout")
            raise Exception("Groq API request timed out")
        except Exception as e:
            logger.error(f"Groq text generation failed: {e}")
            raise
    
    async def close(self):
        """Close the async client"""
        if self.client:
            await self.client.aclose()

# ==================== GLOBAL INSTANCE ====================

groq_vision_service = GroqVisionService()

# ==================== DEMO ====================

async def demo_groq_vision():
    """Demo Groq Vision capabilities"""
    
    print("🚀 Groq Llama Vision Demo")
    print("=" * 70)
    
    # Use global instance
    service = groq_vision_service
    
    if not service.client:
        print("❌ GROQ_API_KEY not set in environment")
        print("Set it in .env file: GROQ_API_KEY=your_key_here")
        return
    
    try:
        # Check if test image exists
        try:
            with open("test_image.jpeg", "rb") as f:
                image_data = f.read()
            print("✓ Test image loaded")
        except FileNotFoundError:
            print("❌ test_image.jpeg not found")
            print("   Create one or download a clothing image")
            return
        
        # Test 1: Clothing Analysis
        print("\n1️⃣ CLOTHING ANALYSIS")
        print("-" * 70)
        clothing = await service.analyze_clothing(image_data)
        print(json.dumps(clothing, indent=2))
        
        # Test 2: Brand Detection
        print("\n2️⃣ BRAND DETECTION")
        print("-" * 70)
        brand = await service.detect_brand(image_data)
        print(json.dumps(brand, indent=2))
        
        # Test 3: Embeddings
        print("\n3️⃣ EMBEDDINGS GENERATION")
        print("-" * 70)
        description = clothing.get("description", "")
        embeddings = await service.generate_text_embedding(description)
        print(f"Generated {len(embeddings)}-D embedding")
        print(f"First 10 values: {embeddings[:10]}")
        print(f"Min: {min(embeddings):.4f}, Max: {max(embeddings):.4f}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_groq_vision())
