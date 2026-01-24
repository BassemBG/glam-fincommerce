"""
Outfit/Fashion Image Filtering Service using Groq LLM.
Filters Pinterest pins to only include outfit/clothing/fashion-related images.
"""

import logging
import os
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Groq client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

logger.info(f"[Filter Init] GROQ_API_KEY present: {bool(GROQ_API_KEY)}")

try:
    from groq import Groq
    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("✓ Groq client initialized successfully")
    else:
        groq_client = None
        logger.warning("✗ GROQ_API_KEY not set. Outfit filtering disabled.")
except ImportError:
    groq_client = None
    logger.error("✗ Groq package not installed. Install with: pip install groq")


def is_outfit_or_fashion(image_url: str, pin_description: str = "") -> Optional[bool]:
    """
    Use Groq LLM to determine if an image is an outfit/clothing/fashion-related content.
    
    Args:
        image_url: URL of the image to analyze
        pin_description: Optional description from Pinterest
    
    Returns:
        True if image is fashion/outfit related
        False if not
        None if analysis failed
    """
    if not groq_client:
        logger.warning("[Filter] Groq client not initialized. Skipping outfit filter.")
        return None
    
    if not image_url:
        logger.debug("[Filter] No image URL provided")
        return False
    
    try:
        logger.debug(f"[Filter] Analyzing image: {image_url}")
        
        # Build the prompt - focus on image analysis, not text description
        prompt_text = "Based ONLY on the IMAGE content (ignore any text), is this showing an outfit, clothing item, fashion styling, or wearable fashion inspiration? Answer ONLY 'YES' or 'NO'."
        
        logger.debug(f"[Filter] Calling Groq API for image analysis")
        
        # Call Groq API with vision capability
        completion = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,  # Low temperature for consistent responses
            max_completion_tokens=10,  # Only need YES or NO
            top_p=0.1,
            stream=False,
        )
        
        response_text = completion.choices[0].message.content.strip().upper()
        logger.debug(f"[Filter] Groq response: {response_text}")
        
        # Debug: Show raw response for inspection
        print(f"\n=== FILTER DEBUG: IS_OUTFIT_OR_FASHION ===")
        print(f"Raw response (repr): {repr(response_text)}")
        print(f"Response length: {len(response_text)}")
        print(f"First 20 chars: {response_text[:20]}")
        logger.debug(f"[Filter] Raw response repr: {repr(response_text)}, length={len(response_text)}")
        
        # Flexible parsing - accept YES/NO with optional whitespace/punctuation
        response_clean = response_text.strip().upper()
        
        # Remove common trailing punctuation/artifacts
        response_clean = response_clean.rstrip('.,!?;:\'" ')
        
        logger.debug(f"[Filter] Cleaned response: {repr(response_clean)}")
        
        # Check for YES or NO with tolerance
        if "YES" in response_clean:
            is_outfit = True
            logger.debug(f"[Filter] Detected YES in response: {response_clean}")
        elif "NO" in response_clean:
            is_outfit = False
            logger.debug(f"[Filter] Detected NO in response: {response_clean}")
        else:
            # Ambiguous response - treat as uncertain (reject)
            logger.warning(f"[Filter] Ambiguous response: {repr(response_text)}. Could not parse as YES or NO. Treating as NO.")
            is_outfit = False
        
        if is_outfit:
            logger.info("[Filter] ✓ ACCEPTED - Fashion/outfit related")
        else:
            logger.debug("[Filter] ✗ REJECTED - Not fashion/outfit related")
        
        return is_outfit
        
    except Exception as e:
        logger.error(f"[Filter] Failed to analyze image: {e}", exc_info=True)
        return None


def filter_pinterest_pins(pins: list, descriptions: dict = None, max_pins: int = 50) -> dict:
    """
    Filter a list of pins to keep only outfit/fashion-related ones.
    
    Args:
        pins: List of pin dictionaries
        descriptions: Optional dict mapping pin_id to description
        max_pins: Maximum number of pins to analyze (cost control). Default 50.
    
    Returns:
        Dictionary with:
        - "accepted": list of accepted pins
        - "rejected": list of rejected pins
        - "failed": list of pins where analysis failed
        - "stats": summary stats
    """
    descriptions = descriptions or {}
    
    # Apply cap to prevent excessive API costs
    original_count = len(pins)
    if len(pins) > max_pins:
        logger.warning(f"[Filter] Pin count ({len(pins)}) exceeds max ({max_pins}). Analyzing first {max_pins} only.")
        pins = pins[:max_pins]
    
    accepted = []
    rejected = []
    failed = []
    
    logger.info(f"[Filter] Starting to filter {len(pins)} pins (original: {original_count})")
    
    for i, pin in enumerate(pins, 1):
        pin_id = pin.get("id")
        image_url = pin.get("image_url")
        description = descriptions.get(pin_id, pin.get("description", ""))
        
        logger.debug(f"[Filter] Processing pin {i}/{len(pins)}: {pin_id}")
        
        result = is_outfit_or_fashion(image_url, description)
        
        if result is True:
            accepted.append(pin)
            logger.info(f"[Filter] Pin {pin_id}: ACCEPTED")
        elif result is False:
            rejected.append(pin)
            logger.debug(f"[Filter] Pin {pin_id}: REJECTED")
        else:
            failed.append(pin)
            logger.warning(f"[Filter] Pin {pin_id}: ANALYSIS FAILED")
    
    stats = {
        "total": len(pins),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "failed": len(failed),
        "acceptance_rate": f"{(len(accepted) / len(pins) * 100):.1f}%" if pins else "0%"
    }
    
    logger.info(f"[Filter] Filtering complete! Stats: {stats}")
    
    return {
        "accepted": accepted,
        "rejected": rejected,
        "failed": failed,
        "stats": stats
    }


def summarize_outfit(image_url: str) -> Optional[dict]:
    """
    Produce a structured outfit description from an image.

    Returns a dict with keys:
    - summary: short text
    - items: list[str]
    - colors: list[str]
    - style_keywords: list[str]
    - fit: Optional[str]
    - occasion: Optional[str]
    """
    if not groq_client:
        logger.warning("[Filter] Groq client not initialized. Cannot summarize outfit.")
        return None

    if not image_url:
        logger.debug("[Filter] No image URL provided for summarization")
        return None

    try:
        prompt = (
            "Analyze ONLY the IMAGE content and return a STRICT JSON object (no prose) with keys: "
            "summary (string), items (array of strings), colors (array of strings), "
            "style_keywords (array of strings), fit (string or null), occasion (string or null). "
            "Focus on wearable outfit components; if the image is not fashion, return an empty JSON object {}."
        )

        completion = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            temperature=0.1,
            max_completion_tokens=256,
            top_p=0.1,
            stream=False,
        )

        text = completion.choices[0].message.content.strip()
        import json
        
        print(f"\n=== FILTER DEBUG: SUMMARIZE_OUTFIT ===")
        print(f"Raw response (repr): {repr(text)}")
        print(f"Response length: {len(text)}")
        
        # Strip markdown code fences FIRST before JSON parsing
        if text.startswith("```"):
            logger.debug(f"[Filter] Response starts with markdown fence. Stripping...")
            # Remove leading ```json or just ```
            text = text.lstrip("`").lstrip("json").lstrip("`").strip()
            logger.debug(f"[Filter] After stripping leading fences: {repr(text[:50])}")
            
        if text.endswith("```"):
            logger.debug(f"[Filter] Response ends with markdown fence. Stripping...")
            text = text.rstrip("`").strip()
            logger.debug(f"[Filter] After stripping trailing fences: {repr(text[-50:])}")
        
        print(f"After fence stripping (repr): {repr(text[:100])}")
        logger.debug(f"[Filter] After fence cleanup: {repr(text[:100])}")
        
        try:
            data = json.loads(text)
        except Exception:
            logger.warning(f"[Filter] Non-JSON summary response; discarding. Raw (repr): {repr(text[:150])}")
            print(f"JSON parse failed. Raw text: {repr(text[:150])}")
            return None

        # Minimal validation
        if not isinstance(data, dict) or not data.get("summary"):
            return None

        # Normalize lists
        for k in ["items", "colors", "style_keywords"]:
            v = data.get(k)
            if isinstance(v, list):
                data[k] = [str(x).strip() for x in v if str(x).strip()]
            else:
                data[k] = []

        # Optional fields
        data["fit"] = data.get("fit") or None
        data["occasion"] = data.get("occasion") or None

        logger.debug(f"[Filter] Outfit summary generated: {data}")
        return data

    except Exception as e:
        logger.error(f"[Filter] Failed to summarize outfit: {e}", exc_info=True)
        return None
