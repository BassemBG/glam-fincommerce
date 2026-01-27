import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =========================
# CONFIG
# =========================

@dataclass
class ExtractionConfig:
    """Configuration for profile extraction."""
    model: str = "hosted_vllm/Llama-3.1-70B-Instruct"
    temperature: float = 0.2
    max_retries: int = 2
    api_key: Optional[str] = None
    base_url: str = "https://tokenfactory.esprit.tn/api"


# =========================
# ERRORS
# =========================

class ProfileExtractorError(Exception):
    """Custom exception for profile extraction errors."""
    pass


# =========================
# MAIN EXTRACTOR
# =========================

class ProfileExtractor:
    EXTRACTION_PROMPT = """You are an expert fashion industry analyst. Extract brand and product information from the provided text.

CRITICAL RULES:
1. ONLY extract information explicitly mentioned in the text.
2. DO NOT invent, assume, or hallucinate any data.
3. If information is not clearly stated, leave the field EMPTY/NULL.
4. For missing data, use null values, not placeholders or estimates.
5. Be conservative - if unsure, mark as null.
6. Ensure all JSON keys and string values use double quotes (") to prevent syntax errors.
7. Return ONLY valid JSON. No explanations, no markdown, no extra text.

AESTHETIC KEYWORDS GUIDELINES:
- These describe the visual/design style of the brand or products.
- Examples include: "sporty", "casual", "minimalist", "luxe", "bohemian", "vintage", "streetwear", "formal".
- Only include keywords that are explicitly reflected in the text.
- Apply keywords to actual products mentioned in the style group (e.g., "hoodies" might be "casual", "sneakers" might be "sporty").

RETURN FORMAT:
Return a JSON object EXACTLY in this structure:

{
  "brand_name": "string or null",
  "style_groups": [
    {
      "style_name": "string or null",
      "product_types": ["string"] or [],
      "price_range": {
        "min_price": number or null,
        "max_price": number or null,
        "currency": "USD" or null
      } or null,
      "aesthetic_keywords": ["string"] or [],
      "target_demographic": "string or null",
      "sustainability_score": number 0-100 or null
    }
  ]
}
"""


    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        self.client = None
        self._initialize_client()

    # =========================
    # CLIENT INIT (LLAMA)
    # =========================

    def _initialize_client(self):
        """Initialize LLaMA (OpenAI-compatible) client."""
        try:
            import httpx
            from openai import OpenAI

            api_key = self.config.api_key or self._get_api_key()

            http_client = httpx.Client(verify=False)

            self.client = OpenAI(
                api_key=api_key,
                base_url=self.config.base_url,
                http_client=http_client
            )

        except ImportError:
            raise ProfileExtractorError(
                "Missing dependencies. Install with: pip install openai httpx"
            )
        except Exception as e:
            raise ProfileExtractorError(f"Failed to initialize LLaMA client: {str(e)}")

    @staticmethod
    def _get_api_key() -> str:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ProfileExtractorError("OPENAI_API_KEY environment variable not set")
        return api_key

    # =========================
    # PUBLIC API
    # =========================

    def extract(self, raw_text: str) -> Dict[str, Any]:
        if not raw_text or not raw_text.strip():
            logger.warning("Empty or whitespace-only text provided")
            return {"brand_name": None, "style_groups": []}

        for attempt in range(self.config.max_retries):
            try:
                response_text = self._call_llm(raw_text)
                response_text = self._extract_json(response_text)
                result = self._parse_response(response_text)
                return self._validate_extraction(result, raw_text)

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error (attempt {attempt + 1})")
                if attempt == self.config.max_retries - 1:
                    raise ProfileExtractorError(f"Invalid JSON from LLM: {str(e)}")

            except Exception as e:
                raise ProfileExtractorError(f"Extraction failed: {str(e)}")

        raise ProfileExtractorError("Max retries exceeded")

    # =========================
    # LLM CALL
    # =========================

    def _call_llm(self, raw_text: str) -> str:
        if not self.client:
            raise ProfileExtractorError("LLM client not initialized")

        # DEBUG: Log what we're sending to LLM
        logger.info(f"📝 Raw text length: {len(raw_text)} characters")
        logger.info(f"📝 First 500 chars of raw_text:\n{raw_text[:500]}")

        response = self.client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=800,
            messages=[
                {"role": "system", "content": self.EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Extract brand information from the text below.\n"
                        "Return ONLY valid JSON.\n\n"
                        f"{raw_text}"
                    )
                }
            ]
        )

        return response.choices[0].message.content

    # =========================
    # JSON HANDLING
    # =========================

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        Extract JSON object from LLaMA output safely.
        Handles cases where JSON is embedded in markdown or has trailing text.
        """
        # Remove markdown code blocks if present
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find the first { and match it to the corresponding }
        start_idx = text.find('{')
        if start_idx == -1:
            raise json.JSONDecodeError("No JSON object found", text, 0)
        
        # Try to find the matching closing brace
        brace_count = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = text[start_idx:i+1]
                    # Validate it's valid JSON
                    try:
                        json.loads(json_str)
                        return json_str
                    except json.JSONDecodeError:
                        pass
        
        # Fallback: try to extract any JSON-like structure
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise json.JSONDecodeError("No valid JSON object found", text, 0)
        
        return match.group(0)

    @staticmethod
    def _parse_response(response_text: str) -> Dict[str, Any]:
        response_json = json.loads(response_text)

        if not isinstance(response_json, dict):
            raise json.JSONDecodeError("Response is not a JSON object", response_text, 0)

        style_groups = response_json.get("style_groups", [])
        if not isinstance(style_groups, list):
            raise json.JSONDecodeError("style_groups is not a list", response_text, 0)

        return {
            "brand_name": response_json.get("brand_name"),
            "style_groups": style_groups
        }

    # =========================
    # VALIDATION
    # =========================

    @staticmethod
    def _validate_extraction(result: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        validated = []
        text_lower = raw_text.lower()

        for group in result.get("style_groups", []):
            if not isinstance(group, dict):
                continue

            if not group.get("style_name") and not group.get("product_types"):
                continue

            # Price sanity check
            price = group.get("price_range")
            if isinstance(price, dict):
                min_p, max_p = price.get("min_price"), price.get("max_price")
                if (
                    min_p is not None and max_p is not None
                    and (min_p < 0 or max_p < 0 or min_p > max_p or max_p > 100000)
                ):
                    group["price_range"] = None

            # Keep aesthetic keywords as extracted (no filtering)
            if group.get("aesthetic_keywords"):
                group["aesthetic_keywords"] = [
                    k for k in group["aesthetic_keywords"]
                    if isinstance(k, str)
                ]

            # Sustainability score
            score = group.get("sustainability_score")
            if score is not None and not (0 <= score <= 100):
                group["sustainability_score"] = None

            validated.append(group)

        return {
            "brand_name": result.get("brand_name"),
            "style_groups": validated
        }

    # =========================
    # OUTPUT
    # =========================

    @staticmethod
    def format_output(result: Dict[str, Any]) -> str:
        return json.dumps(result, indent=2)
    

# =========================
# MOCK (TESTING)
# =========================

class MockProfileExtractor:
    @staticmethod
    def extract(raw_text: str) -> List[Dict[str, Any]]:
        return [
            {   "brand_name": None,
                "style_name": None,
                "product_types": [],
                "price_range": None,
                "aesthetic_keywords": [],
                "target_demographic": None,
                "sustainability_score": None
            }
        ]
        