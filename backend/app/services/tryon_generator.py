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
        Use Azure OpenAI gpt-image-1.5 model to generate a virtual try-on image.
        Uses /images/edits endpoint with multipart/form-data for multiple input images.
        """
        import time
        total_start = time.time()
        
        if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_API_KEY:
            logging.info("Azure OpenAI not configured, skipping AI try-on")
            return None
        
        # Load body image
        print(f"[TIMING] Starting body image download from: {body_image_url[:50]}...", flush=True)
        body_start = time.time()
        body_img = await self._load_image(body_image_url)
        body_time = time.time() - body_start
        print(f"[TIMING] Body image download: {body_time:.2f}s", flush=True)
        
        if not body_img:
            logging.error("Could not load body image for AI try-on")
            return None
        
        # Load clothing images
        clothing_images = []
        clothing_descriptions = []
        for i, item in enumerate(clothing_items):
            item_url = item.get("mask_url") or item.get("image_url")
            if not item_url:
                continue
            
            print(f"[TIMING] Starting clothing {i+1} download from: {item_url[:50]}...", flush=True)
            clothing_start = time.time()
            clothing_img = await self._load_image(item_url)
            clothing_time = time.time() - clothing_start
            print(f"[TIMING] Clothing {i+1} download: {clothing_time:.2f}s", flush=True)
            
            if clothing_img:
                clothing_images.append(clothing_img)
                # Build description from item metadata
                category = item.get("category", "clothing item")
                sub_category = item.get("sub_category", "")
                body_region = item.get("body_region", "")
                desc = f"{sub_category} {category} for {body_region}" if sub_category else f"{category} for {body_region}"
                clothing_descriptions.append(desc)
        
        if not clothing_images:
            logging.error("No clothing images loaded for AI try-on")
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
            
            # Request headers (no Content-Type - requests will set it for multipart)
            headers = {
                "api-key": settings.AZURE_OPENAI_API_KEY
            }
            
            # Prepare files for multipart/form-data
            print(f"[TIMING] Starting image conversion to bytes...", flush=True)
            convert_start = time.time()
            files = []
            
            # Add body image as first image (highest fidelity in gpt-image-1.5)
            body_bytes = self._image_to_bytes(body_img)
            files.append(("image[]", ("body.png", body_bytes, "image/png")))
            
            # Add clothing images
            for idx, clothing_img in enumerate(clothing_images):
                clothing_bytes = self._image_to_bytes(clothing_img)
                files.append(("image[]", (f"clothing_{idx}.png", clothing_bytes, "image/png")))
            
            convert_time = time.time() - convert_start
            print(f"[TIMING] Image conversion: {convert_time:.2f}s", flush=True)
            
            # Form data - choose size based on body image aspect ratio
            body_aspect = body_img.width / body_img.height
            if body_aspect < 0.8:  # Portrait (tall image)
                output_size = "1024x1536"
            elif body_aspect > 1.2:  # Landscape (wide image)
                output_size = "1536x1024"
            else:  # Square-ish
                output_size = "1024x1024"
            
            logging.info(f"Body image {body_img.width}x{body_img.height}, using output size: {output_size}")
            
            data = {
                "prompt": prompt,
                "n": "1",
                "size": output_size
            }
            
            # Make the API call with multipart/form-data
            print(f"[TIMING] Starting Azure OpenAI API call with {len(files)} images...", flush=True)
            api_start = time.time()
            response = requests.post(url, headers=headers, data=data, files=files, timeout=180)
            api_time = time.time() - api_start
            print(f"[TIMING] Azure OpenAI API call: {api_time:.2f}s", flush=True)
            
            if response.status_code != 200:
                logging.error(f"Azure OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Get the generated image
            if result.get("data") and len(result["data"]) > 0:
                image_data = result["data"][0]
                
                # Handle both base64 and URL responses
                if image_data.get("b64_json"):
                    print(f"[TIMING] Decoding base64 response...", flush=True)
                    decode_start = time.time()
                    generated_bytes = base64.b64decode(image_data["b64_json"])
                    decode_time = time.time() - decode_start
                    print(f"[TIMING] Base64 decode: {decode_time:.2f}s", flush=True)
                elif image_data.get("url"):
                    # Download image from URL
                    print(f"[TIMING] Downloading result from URL...", flush=True)
                    download_start = time.time()
                    img_response = requests.get(image_data["url"], timeout=30)
                    img_response.raise_for_status()
                    generated_bytes = img_response.content
                    download_time = time.time() - download_start
                    print(f"[TIMING] Result download: {download_time:.2f}s", flush=True)
                else:
                    logging.error("No image data in response")
                    return None
                
                # Save to storage
                print(f"[TIMING] Starting upload to Azure Blob Storage...", flush=True)
                upload_start = time.time()
                output_filename = f"tryon_ai_{uuid.uuid4().hex}.png"
                image_url = await storage_service.upload_file(
                    generated_bytes, 
                    output_filename, 
                    "image/png"
                )
                upload_time = time.time() - upload_start
                print(f"[TIMING] Azure Blob upload: {upload_time:.2f}s", flush=True)
                
                total_time = time.time() - total_start
                print(f"[TIMING] ===== TOTAL TRY-ON TIME: {total_time:.2f}s =====", flush=True)
                print(f"AI try-on generated: {image_url}", flush=True)
                return image_url
            
            logging.warning("No image data in Azure OpenAI response")
            return None
            
        except Exception as e:
            logging.error(f"Azure OpenAI image generation failed: {e}")
            raise
    
    def _image_to_bytes(self, img: Image.Image) -> bytes:
        """Convert PIL Image to bytes for API upload."""
        # Ensure image is in RGB mode (no alpha channel for edit API)
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # Resize if too large (API has size limits)
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
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
