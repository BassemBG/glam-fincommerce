"""
Virtual Try-On Image Generator Service

This service generates composite images showing clothing items on the user's body.
- Primary: Uses Gemini's image generation capabilities
- Fallback: Uses Pillow for simple image compositing when API is rate-limited
"""

import os
import uuid
import logging
from typing import List, Optional
from PIL import Image
import io
import requests

import google.generativeai as genai
from app.core.config import settings
from app.services.storage import storage_service


class TryOnGenerator:
    def __init__(self):
        self.upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
        
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None
    
    async def generate_tryon_image(
        self,
        body_image_url: str,
        clothing_items: List[dict]
    ) -> Optional[str]:
        """
        Generate a try-on image with clothing items on the body.
        
        Args:
            body_image_url: URL/path to the user's full body image
            clothing_items: List of dicts with 'image_url' and 'body_region' keys
        
        Returns:
            URL to the generated image, or None if generation fails
        """
        
        # Try AI approach first
        try:
            result = await self._generate_with_ai(body_image_url, clothing_items)
            if result:
                return result
        except Exception as e:
            logging.warning(f"AI try-on failed: {e}")
        
        # Fallback to Pillow compositing
        try:
            return await self._generate_with_pillow(body_image_url, clothing_items)
        except Exception as e:
            logging.error(f"Pillow try-on also failed: {e}")
            return None
    
    async def _generate_with_ai(
        self,
        body_image_url: str,
        clothing_items: List[dict]
    ) -> Optional[str]:
        """
        Use AI to generate a virtual try-on image.
        
        TODO: Integrate with nanobanana for AI-powered virtual try-on.
        nanobanana provides advanced image generation and editing capabilities
        that can create realistic try-on visualizations.
        
        Implementation steps:
        1. Upload body image and clothing items to nanobanana
        2. Use virtual try-on model to composite clothing
        3. Download and save the resulting image
        """
        
        if not self.model:
            return None
        
        # TODO: Implement nanobanana virtual try-on
        # Example workflow:
        # from nanobanana import VirtualTryOn
        # 
        # tryon = VirtualTryOn(api_key=settings.NANOBANANA_API_KEY)
        # result = await tryon.generate(
        #     body_image=body_image_url,
        #     garments=[item["mask_url"] for item in clothing_items]
        # )
        # return result.image_url
        
        # For now, fall through to Pillow approach
        return None
    
    async def _generate_with_pillow(
        self,
        body_image_url: str,
        clothing_items: List[dict]
    ) -> Optional[str]:
        """
        Simple image compositing using Pillow.
        Overlays clothing masks onto the body image based on body regions.
        """
        
        # Load the body image
        body_img = await self._load_image(body_image_url)
        if not body_img:
            logging.error("Could not load body image")
            return None
        
        # Convert to RGBA for transparency support
        body_img = body_img.convert("RGBA")
        body_width, body_height = body_img.size
        
        # Define body region positions (approximate percentages)
        region_positions = {
            "head": {"y": 0.0, "height": 0.15, "width": 0.25},
            "top": {"y": 0.15, "height": 0.30, "width": 0.50},
            "bottom": {"y": 0.45, "height": 0.35, "width": 0.45},
            "feet": {"y": 0.85, "height": 0.15, "width": 0.30},
            "full_body": {"y": 0.10, "height": 0.80, "width": 0.60},
        }
        
        # Composite each clothing item
        for item in clothing_items:
            item_url = item.get("mask_url") or item.get("image_url")
            region = item.get("body_region", "top")
            
            if not item_url:
                continue
            
            clothing_img = await self._load_image(item_url)
            if not clothing_img:
                continue
            
            # Get position for this region
            pos = region_positions.get(region, region_positions["top"])
            
            # Calculate target size and position
            target_width = int(body_width * pos["width"])
            target_height = int(body_height * pos["height"])
            
            # Resize clothing to fit the region
            clothing_img = clothing_img.convert("RGBA")
            clothing_img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Calculate center position
            paste_x = (body_width - clothing_img.width) // 2
            paste_y = int(body_height * pos["y"])
            
            # Paste with alpha compositing
            body_img.paste(clothing_img, (paste_x, paste_y), clothing_img)
        
        # Save the composite image to storage (Azure Blob, S3, or local)
        output_filename = f"tryon_{uuid.uuid4().hex}.png"
        
        # Convert image to bytes
        img_buffer = io.BytesIO()
        body_img.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()
        
        # Upload via storage service
        image_url = await storage_service.upload_file(img_bytes, output_filename, "image/png")
        return image_url
    
    async def _load_image(self, image_path: str) -> Optional[Image.Image]:
        """Load an image from a URL or local path."""
        try:
            # Convert localhost URLs to local file paths to avoid self-request deadlock
            if "localhost" in image_path or "127.0.0.1" in image_path:
                # Extract the path from the URL (e.g., /uploads/filename.jpg)
                from urllib.parse import urlparse
                parsed = urlparse(image_path)
                image_path = parsed.path  # Now it's just /uploads/filename.jpg
            
            if image_path.startswith(("http://", "https://")):
                # Fetch remote URLs (including Azure Blob URLs)
                response = requests.get(image_path, timeout=10)
                response.raise_for_status()
                return Image.open(io.BytesIO(response.content))
            else:
                # Handle local paths
                if image_path.startswith("/uploads/"):
                    local_path = os.path.join(self.upload_dir, image_path.replace("/uploads/", ""))
                else:
                    local_path = image_path
                
                if os.path.exists(local_path):
                    return Image.open(local_path)
                else:
                    logging.error(f"Image file not found: {local_path}")
                    
        except Exception as e:
            logging.error(f"Failed to load image {image_path}: {e}")
        
        return None


# Singleton instance
tryon_generator = TryOnGenerator()
