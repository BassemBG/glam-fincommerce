"""
Virtual Try-On Image Generator Service

This service generates composite images showing clothing items on the user's body.
- Primary: Uses Azure OpenAI gpt-image model for AI-powered try-on
- Fallback: Uses Pillow for simple image compositing when API is unavailable
"""

import os
import uuid
import logging
import base64
from typing import List, Optional
from PIL import Image
import io
import requests
from typing import Dict, Any

from app.core.config import settings
from app.services.storage import storage_service


class TryOnGenerator:
    def __init__(self):
        self.upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Azure OpenAI client
        self.openai_client = None
        self._init_azure_openai()
    
    def _init_azure_openai(self):
        """Initialize Azure OpenAI client for image generation."""
        try:
            from openai import AzureOpenAI
            
            if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
                self.openai_client = AzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version="2024-12-01-preview"
                )
                logging.info("Azure OpenAI client initialized for try-on")
        except ImportError:
            logging.warning("openai package not installed")
        except Exception as e:
            logging.warning(f"Azure OpenAI not configured: {e}")
    
    async def generate_tryon_image(
        self,
        body_image_url: str,
        clothing_items: List[dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a try-on image with clothing items on the body.
        
        Returns:
            Dict with 'url' and 'bytes' (original image data), or None if generation fails
        """
        
        # Try AI approach first
        try:
            print(f"[DEBUG] TryOnGenerator: Attempting AI generation...")
            result = await self._generate_with_ai(body_image_url, clothing_items)
            if result:
                print(f"[DEBUG] TryOnGenerator: AI generation SUCCESS")
                return result
            print(f"[DEBUG] TryOnGenerator: AI generation failed (returned None)")
        except Exception as e:
            print(f"[DEBUG] TryOnGenerator: AI generation ERROR: {str(e)}")
            logging.warning(f"AI try-on failed: {e}")
        
        # Fallback to Pillow compositing
        try:
            return await self._generate_with_pillow(body_image_url, clothing_items)
        except Exception as e:
            logging.error(f"Pillow try-on also failed: {e}")
            return None
    
        except Exception as e:
            logging.error(f"Azure OpenAI image generation failed: {e}")
            raise

    async def _generate_with_ai(
        self,
        body_image_url: str,
        clothing_items: List[dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Use Azure OpenAI gpt-image-1.5 model to generate a virtual try-on image.
        Returns Dict with 'url' and 'bytes'.
        """
        import time
        total_start = time.time()
        
        if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_API_KEY:
            logging.info("Azure OpenAI not configured, skipping AI try-on")
            return None
        
        # Load ALL images in PARALLEL for faster downloads
        import asyncio
        
        # Prepare all URLs to download
        all_urls = [body_image_url]
        clothing_metadata = []
        for item in clothing_items:
            # item.get("image_url") might be a data URI! _load_image now handles it.
            item_url = item.get("mask_url") or item.get("image_url")
            if item_url:
                all_urls.append(item_url)
                clothing_metadata.append({
                    "category": item.get("category", "clothing item"),
                    "sub_category": item.get("sub_category", ""),
                    "body_region": item.get("body_region", "")
                })
        
        logging.info(f"Downloading {len(all_urls)} images for AI try-on...")
        
        # Download all images in parallel
        all_images = await asyncio.gather(*[self._load_image(url) for url in all_urls])
        
        # Extract body and clothing images
        body_img = all_images[0]
        if not body_img:
            logging.error("❌ Could not load body image for AI try-on")
            return None
        
        logging.info(f"✅ Body image loaded: {body_img.size}")
        
        clothing_images = []
        clothing_descriptions = []
        for i, (img, meta) in enumerate(zip(all_images[1:], clothing_metadata)):
            if img:
                clothing_images.append(img)
                sub_cat = meta["sub_category"]
                cat = meta["category"]
                region = meta["body_region"]
                desc = f"{sub_cat} {cat} for {region}" if sub_cat else f"{cat} for {region}"
                clothing_descriptions.append(desc)
                logging.info(f"✅ Clothing image {i} loaded: {img.size}")
            else:
                logging.warning(f"⚠️ Clothing image {i} failed to load from: {all_urls[i+1][:50]}...")
        
        if not clothing_images:
            logging.error("❌ No clothing images successfully loaded for AI try-on")
            return None
        
        try:
            # Build the prompt
            clothing_list = ", ".join(clothing_descriptions)
            prompt = f"""Virtual try-on: Dress the person in the first image wearing the clothing items from the other images: {clothing_list}.

Requirements:
- Keep the person's face, body shape, skin tone, hairstyle, and pose EXACTLY the same
- Apply each clothing item to the correct body region naturally
- Match colors, patterns, and style precisely from the reference images
- Create realistic fabric folds, shadows, and natural fit
- Professional fashion photography quality, studio lighting

Output a single photorealistic image of the person wearing all the provided clothing."""

            # Build the REST API URL for images/edits
            endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
            deployment = settings.AZURE_OPENAI_IMAGE_DEPLOYMENT
            api_version = "2025-04-01-preview"
            url = f"{endpoint}/openai/deployments/{deployment}/images/edits?api-version={api_version}"
            
            print(f"[DEBUG] Azure OpenAI URL: {url}")
            print(f"[DEBUG] Deployment: {deployment}")
            print(f"[DEBUG] Prompt: {prompt[:100]}...")
            
            # Request headers
            headers = {
                "api-key": settings.AZURE_OPENAI_API_KEY
            }
            
            # Prepare files for multipart/form-data
            files = []
            
            # Add body image as first image
            body_bytes_input = self._image_to_bytes(body_img)
            files.append(("image[]", ("body.jpg", body_bytes_input, "image/jpeg")))
            
            # Add clothing images
            for idx, clothing_img in enumerate(clothing_images):
                clothing_bytes_input = self._image_to_bytes(clothing_img)
                files.append(("image[]", (f"clothing_{idx}.jpg", clothing_bytes_input, "image/jpeg")))
            
            # Request size
            body_aspect = body_img.width / body_img.height
            output_size = "1024x1536" if body_aspect < 0.8 else "1536x1024" if body_aspect > 1.2 else "1024x1024"
            
            data = {"prompt": prompt, "n": "1", "size": output_size}
            
            # Make the API call
            logging.info(f"🚀 Sending request to Azure OpenAI ({deployment})...")
            print(f"[DEBUG] POST {url}")
            response = requests.post(url, headers=headers, data=data, files=files, timeout=180)
            
            print(f"[DEBUG] Azure Response Status: {response.status_code}")
            if response.status_code != 200:
                print(f"[DEBUG] Azure Error Body: {response.text}")
                logging.error(f"❌ Azure OpenAI API error: {response.status_code}")
                logging.error(f"Response body: {response.text}")
                return None
            
            print(f"[DEBUG] Azure Response SUCCESS")
            logging.info("✅ Azure OpenAI API responded with 200")
            result = response.json()
            if result.get("data") and len(result["data"]) > 0:
                image_data = result["data"][0]
                
                if image_data.get("b64_json"):
                    generated_bytes = base64.b64decode(image_data["b64_json"])
                elif image_data.get("url"):
                    img_response = requests.get(image_data["url"], timeout=30)
                    img_response.raise_for_status()
                    generated_bytes = img_response.content
                else:
                    return None
                
                # Save to storage
                output_filename = f"tryon_ai_{uuid.uuid4().hex}.png"
                image_url = await storage_service.upload_file(generated_bytes, output_filename, "image/png")
                
                return {
                    "url": image_url,
                    "bytes": generated_bytes
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Azure OpenAI image generation failed: {e}")
            return None
    
    def _image_to_bytes(self, img: Image.Image) -> bytes:
        """Convert PIL Image to compressed bytes for faster API upload."""
        if img.mode == "RGBA":
            # If we want to keep transparency for PNG, we should convert to RGBA
            # But the edit API often prefers RGB. Most try-on flows need RGB.
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # Resize to standard size (DALL-E edits often like 1024x1024 or similar)
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Standardize on PNG for image edits
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()
    
    def _image_to_base64(self, img: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        # Ensure image is in a format suitable for API
        if img.mode == "RGBA":
            # Convert RGBA to RGB with white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # Resize if too large (max 4MB for API)
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    async def _generate_with_pillow(
        self,
        body_image_url: str,
        clothing_items: List[dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Simple image compositing using Pillow.
        Returns Dict with 'url' and 'bytes'.
        """
        logging.info("🎨 Falling back to Pillow compositing for try-on...")
        
        # Load the body image
        body_img = await self._load_image(body_image_url)
        if not body_img:
            logging.error("❌ Could not load body image for Pillow fallback")
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
        
        # Save the composite image to storage
        output_filename = f"tryon_{uuid.uuid4().hex}.png"
        
        # Convert image to bytes
        img_buffer = io.BytesIO()
        body_img.convert("RGB").save(img_buffer, format="JPEG", quality=90)
        img_bytes = img_buffer.getvalue()
        
        # Upload via storage service
        image_url = await storage_service.upload_file(img_bytes, output_filename, "image/jpeg")
        logging.info(f"✅ Pillow composite generated: {image_url}")
        
        return {
            "url": image_url,
            "bytes": img_bytes
        }
    
    async def _load_image(self, image_path: str) -> Optional[Image.Image]:
        """Load an image from a URL, local path, or base64 data."""
        if not image_path:
            return None
            
        print(f"[DEBUG] Loading image: {image_path[:70]}...")
        try:
            # 1. Handle base64 data URIs (e.g., data:image/jpeg;base64,...)
            if image_path.startswith("data:image"):
                print(f"[DEBUG] Detected base64 data URI")
                import base64
                try:
                    header, encoded = image_path.split(",", 1)
                    image_data = base64.b64decode(encoded)
                    img = Image.open(io.BytesIO(image_data))
                    print(f"[DEBUG] Decoded base64 successfully, size: {img.size}")
                    return img
                except Exception as e:
                    print(f"[DEBUG] Base64 decode failed: {str(e)}")
                    logging.error(f"Failed to decode base64 data URI: {e}")
                    return None
            
            # 2. Handle raw base64 strings (if they don't look like URLs or paths)
            if not image_path.startswith(("http", "/")) and len(image_path) > 100:
                import base64
                try:
                    image_data = base64.b64decode(image_path)
                    return Image.open(io.BytesIO(image_data))
                except Exception:
                    # Not base64, fall through
                    pass

            # 3. Convert localhost URLs to local file paths to avoid self-request deadlock
            if "localhost" in image_path or "127.0.0.1" in image_path:
                from urllib.parse import urlparse
                parsed = urlparse(image_path)
                image_path = parsed.path  # e.g., /uploads/filename.jpg
            
            # 4. Handle remote URLs
            if image_path.startswith(("http://", "https://")):
                response = requests.get(image_path, timeout=10)
                response.raise_for_status()
                return Image.open(io.BytesIO(response.content))
            
            # 5. Handle local paths
            else:
                # Try relative to upload_dir
                rel_path = image_path.replace("/uploads/", "").lstrip("/")
                local_path = os.path.join(self.upload_dir, rel_path)
                
                if not os.path.exists(local_path):
                    # Try absolute or relative to CWD
                    local_path = image_path
                
                if os.path.exists(local_path):
                    return Image.open(local_path)
                else:
                    logging.debug(f"Image info: Not a file, not a URL: {image_path[:50]}...")
                    
        except Exception as e:
            logging.error(f"Failed to load image {image_path[:100]}...: {e}")
        
        return None


# Singleton instance
tryon_generator = TryOnGenerator()
