from app.services.azure_openai_service import azure_openai_service
import json
import logging
import json
import random
from typing import Dict, Any

# Static demo responses for when AI is unavailable
DEMO_RESPONSES = [
    {
        "category": "clothing",
        "sub_category": "Silk Blouse",
        "body_region": "top",
        "colors": ["Cream", "Ivory"],
        "material": "Silk",
        "vibe": "chic",
        "season": "All Seasons",
        "description": "A luxurious cream silk blouse with elegant draping and mother-of-pearl buttons. Perfect for both professional settings and evening occasions.",
        "styling_tips": "Pair with high-waisted trousers and gold jewelry for a sophisticated look."
    },
    {
        "category": "clothing",
        "sub_category": "Tailored Blazer",
        "body_region": "outerwear",
        "colors": ["Navy", "Dark Blue"],
        "material": "Wool Blend",
        "vibe": "classic",
        "season": "Autumn",
        "description": "A perfectly tailored navy blazer with subtle peak lapels. The structured silhouette creates a powerful, polished appearance.",
        "styling_tips": "Layer over a white tee and jeans for smart-casual, or with tailored pants for business meetings."
    },
    {
        "category": "clothing",
        "sub_category": "High-Waisted Jeans",
        "body_region": "bottom",
        "colors": ["Indigo", "Blue"],
        "material": "Denim",
        "vibe": "casual",
        "season": "All Seasons",
        "description": "Classic high-waisted straight-leg jeans in a deep indigo wash. Features a flattering rise and comfortable stretch.",
        "styling_tips": "Tuck in a simple blouse and add loafers for effortless French-girl style."
    },
    {
        "category": "shoes",
        "sub_category": "Leather Loafers",
        "body_region": "feet",
        "colors": ["Tan", "Camel"],
        "material": "Leather",
        "vibe": "minimalist",
        "season": "Spring",
        "description": "Handcrafted Italian leather loafers in a warm tan shade. The cushioned insole provides all-day comfort.",
        "styling_tips": "Perfect with cropped trousers or midi skirts for a polished finish."
    },
    {
        "category": "clothing",
        "sub_category": "Midi Dress",
        "body_region": "full_body",
        "colors": ["Emerald", "Green"],
        "material": "Satin",
        "vibe": "chic",
        "season": "Summer",
        "description": "An elegant emerald satin midi dress with a flattering cowl neckline and delicate spaghetti straps.",
        "styling_tips": "Add strappy heels and a clutch for date night or special occasions."
    },
    {
        "category": "accessory",
        "sub_category": "Leather Tote",
        "body_region": "accessory",
        "colors": ["Black"],
        "material": "Leather",
        "vibe": "minimalist",
        "season": "All Seasons",
        "description": "A spacious structured leather tote with elegant gold hardware. Features interior pockets for organization.",
        "styling_tips": "Your everyday essential—pairs with everything from workwear to weekend outfits."
    }
]

class VisionAnalyzer:
    def __init__(self):
        self.ai_service = azure_openai_service
        self._rembg_session = None

    def _get_demo_response(self) -> Dict[str, Any]:
        """Returns a random demo response for when AI is unavailable."""
        return random.choice(DEMO_RESPONSES).copy()

    async def analyze_clothing(self, image_data: bytes) -> Dict[str, Any]:
        """Analyzes a clothing item image using Azure OpenAI, falls back to demo data."""
        if not self.ai_service.client:
            logging.info("Using demo response (no Azure OpenAI credentials)")
            return self._get_demo_response()

        prompt = """Analyze this clothing item image and provide a detailed fashion analysis.
        Return ONLY valid JSON with these exact fields:
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
        }"""

        try:
            result = await self.ai_service.analyze_image(image_data, prompt)
            return result
        except Exception as e:
            logging.error(f"Azure AI analysis failed ({e}), using demo response")
            return self._get_demo_response()

    async def remove_background(self, image_data: bytes) -> bytes:
        """Removes background from an image using rembg library."""
        try:
            from rembg import remove, new_session
            
            if self._rembg_session is None:
                logging.info("Initializing background removal model...")
                self._rembg_session = new_session("u2net")
            
            logging.info("Removing background...")
            return remove(image_data, session=self._rembg_session)
            
        except ImportError:
            logging.warning("rembg not installed. Skipping background removal.")
            return image_data
        except Exception as e:
            logging.error(f"Background removal error: {e}")
            return image_data

vision_analyzer = VisionAnalyzer()
