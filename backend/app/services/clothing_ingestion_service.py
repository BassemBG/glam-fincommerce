from app.core.config import settings
import json
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
from app.services.groq_vision_service import groq_vision_service

logger = logging.getLogger(__name__)

# Clothing analysis schema
CLOTHING_SCHEMA = {
    "category": "clothing|shoes|accessory",
    "sub_category": "e.g., T-shirt, Jeans, Midi Dress, Sneakers",
    "body_region": "head|top|bottom|feet|full_body|outerwear|accessory",
    "colors": ["list of primary colors"],
    "material": "denim, silk, wool, cotton, etc.",
    "vibe": "minimalist|boho|chic|streetwear|classic|casual",
    "season": "Spring|Summer|Autumn|Winter|All Seasons",
    "description": "Brief natural language description of the item"
}

# Body analysis schema
BODY_ANALYSIS_SCHEMA = {
    "gender_presentation": "male|female|neutral|other",
    "body_type": "pear|apple|hourglass|rectangle|inverted_triangle|other",
    "skin_tone": "fair|light|medium|olive|tan|deep|rich",
    "estimated_height": "short|average|tall",
    "body_confidence": 0.0  # 0-1 confidence score
}


class ClothingIngestionService:
    """
    Comprehensive clothing ingestion service that:
    1. Analyzes clothing images using Groq Vision API
    2. Performs full body analysis (gender, body type, skin tone)
    3. Detects brands and looks up prices via Tavily
    4. Generates embeddings for Qdrant
    5. Stores metadata (price, purchase date, etc.)
    """

    def __init__(self):
        # Use Groq service (global singleton)
        self.groq_service = groq_vision_service
        
        if not self.groq_service.client:
            logger.warning("GROQ_API_KEY not found. Clothing ingestion will fail.")
        
        self.tavily_api_key = getattr(settings, 'TAVILY_API_KEY', None)
        
        # Import Qdrant service
        try:
            from app.services.qdrant_service import qdrant_service
            self.qdrant_service = qdrant_service
        except Exception as e:
            logger.warning(f"Could not initialize Qdrant: {e}")
            self.qdrant_service = None

    # ==================== STEP 1: Clothing Analysis ====================
    
    async def analyze_clothing(self, image_data: bytes) -> Dict[str, Any]:
        """
        Step 1: Analyze clothing item from image
        Returns detailed clothing attributes matching the schema
        """
        if not self.groq_service.client:
            logger.error("Groq service not configured")
            raise ValueError("Groq API not configured. Check GROQ_API_KEY.")

        try:
            result = await self.groq_service.analyze_clothing(image_data)
            return result
        except Exception as e:
            logger.error(f"Clothing analysis failed: {e}")
            raise

    # ==================== STEP 2: Full Body Analysis ====================
    
    async def analyze_body_type(self, image_data: bytes) -> Dict[str, Any]:
        """
        Step 2: Analyze full body attributes from image
        Returns gender presentation, body type, skin tone, height estimate
        """
        if not self.groq_service.client:
            logger.error("Groq service not configured")
            raise ValueError("Groq API not configured. Check GROQ_API_KEY.")

        try:
            result = await self.groq_service.analyze_body_type(image_data)
            return result
        except Exception as e:
            logger.error(f"Body analysis failed: {e}")
            raise

    # ==================== STEP 3: Brand Detection ====================
    
    async def detect_brand(self, image_data: bytes, clothing_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Detect brand name or logo from clothing image
        """
        if not self.groq_service.client:
            logger.error("Groq service not configured")
            raise ValueError("Groq API not configured. Check GROQ_API_KEY.")

        try:
            brand_data = await self.groq_service.detect_brand(image_data, clothing_analysis)
            return brand_data
        except Exception as e:
            logger.error(f"Brand detection failed: {e}")
            return {
                "detected_brand": "Unknown",
                "brand_confidence": 0.0,
                "brand_indicators": [],
                "possible_alternatives": []
            }

    # ==================== STEP 4: Price Lookup via Tavily ====================
    
    async def lookup_brand_price(self, brand: str, sub_category: str, color: str = None) -> Dict[str, Any]:
        """
        Step 4: Look up brand and price range using Tavily API
        Search query format: sub_category + brand + "price" (e.g., "T-shirt Nike price")
        """
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY not configured - skipping price lookup")
            logger.warning("   Set TAVILY_API_KEY in .env file to enable price lookup")
            return {
                "brand": brand,
                "price_range": "unknown",
                "typical_price": None,
                "stores": [],
                "error": "TAVILY_API_KEY not configured"
            }

        # Build search query: sub_category + brand + "price"
        # Skip if brand is Unknown
        if brand.lower() == "unknown" or not brand or brand.strip() == "":
            logger.info("Brand is unknown, skipping Tavily price lookup")
            return {
                "brand": brand,
                "price_range": "unknown",
                "typical_price": None,
                "stores": []
            }

        # Format search query: sub_category + brand + "price"
        search_query = f"{sub_category} {brand} price".strip()
        
        logger.info(f"Tavily search query: {search_query}")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_api_key,
                        "query": search_query,
                        "search_depth": "advanced",
                        "include_answer": False,
                        "include_raw_content": False,
                        "max_results": 10
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"Tavily API error {response.status_code}: {response.text[:200]}")
                    return {
                        "brand": brand,
                        "price_range": "unknown",
                        "typical_price": None,
                        "stores": [],
                        "error": f"Tavily API error {response.status_code}"
                    }
                
                results = response.json()
                logger.info(f"Tavily search successful for: {search_query}")
                
                # Extract price and store information from results
                return self._parse_tavily_results(results, brand)
                
        except httpx.TimeoutException:
            logger.error("Tavily API request timed out")
            return {
                "brand": brand,
                "price_range": "unknown",
                "typical_price": None,
                "stores": [],
                "error": "Tavily API timeout"
            }
        except Exception as e:
            logger.error(f"Tavily API call failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "brand": brand,
                "price_range": "unknown",
                "typical_price": None,
                "stores": [],
                "error": str(e)
            }

    def _parse_tavily_results(self, results: Dict, brand: str) -> Dict[str, Any]:
        """
        Parse Tavily results to extract pricing information using smart filtering
        Exact same method as test_serper.py with IQR outlier removal
        Output: median * 3.3 (TND conversion)
        """
        import re
        
        prices = []
        
        # Price regex pattern (matches $, €, £, USD, EUR) - exact same as test_serper.py
        price_regex = re.compile(
            r"(?:\$|€|£|usd|eur)\s*(\d{2,4}(?:\.\d{1,2})?)",
            re.IGNORECASE,
        )
        
        # Extract prices from Tavily results - exact same logic as test_serper.py
        for item in results.get("results", []):
            text = f"{item.get('title', '')} {item.get('content', '')}".lower()
            
            # Skip pages that smell like ads or coupons - exact same filter
            if any(x in text for x in ["coupon", "discount", "shipping", "promo"]):
                continue
            
            # Find all price matches in the text
            for match in price_regex.findall(text):
                try:
                    value = float(match)
                    
                    # 🚫 HARD FILTER - exact same as test_serper.py
                    if 20 <= value <= 500:
                        prices.append(value)
                except ValueError:
                    continue
        
        # Need at least 3 prices for reliable analysis - exact same as test_serper.py
        if len(prices) < 3:
            logger.info(f"Not enough prices found ({len(prices)}), need at least 3")
            return {
                "brand": brand,
                "price_range": "unknown",
                "typical_price": None,
                "stores": [],
                "price_count": len(prices)
            }
        
        prices.sort()
        
        # -------- IQR OUTLIER REMOVAL - exact same as test_serper.py --------
        q1 = prices[len(prices) // 4]
        q3 = prices[(len(prices) * 3) // 4]
        iqr = q3 - q1
        
        filtered = [
            p for p in prices
            if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr
        ]
        
        if not filtered:
            logger.info("All prices filtered out as outliers")
            return {
                "brand": brand,
                "price_range": "unknown",
                "typical_price": None,
                "stores": [],
                "price_count": len(prices)
            }
        
        # Calculate median - exact same as test_serper.py
        median = filtered[len(filtered) // 2]
        
        # -------- CATEGORY - exact same as test_serper.py --------
        if median < 40:
            category = "budget"
        elif median < 90:
            category = "mid-range"
        elif median < 200:
            category = "premium"
        else:
            category = "luxury"
        
        # Output: median * 3.3 (TND conversion)
        typical_price_tnd = round(median * 3, 2)
        typical_price_usd = round(median, 2)
        
        logger.info(f"Price analysis: median=${typical_price_usd:.2f} USD (${typical_price_tnd:.2f} TND), range={category}, found {len(filtered)}/{len(prices)} valid prices")
        
        return {
            "brand": brand,
            "price_range": category,
            "typical_price": typical_price_tnd,  # Output in TND (median * 3.3)
            "typical_price_usd": typical_price_usd,  # Also include USD for reference
            "stores": [],
            "price_count": len(filtered),
            "price_min_usd": round(min(filtered), 2),
            "price_max_usd": round(max(filtered), 2),
            "price_min_tnd": round(min(filtered) * 3.3, 2),
            "price_max_tnd": round(max(filtered) * 3.3, 2),
            "exchange_rate": 3.3
        }

    # ==================== STEP 5: Generate Embeddings ====================
    
    async def generate_embeddings(self, clothing_analysis: Dict[str, Any], body_analysis: Optional[Dict[str, Any]] = None) -> list:
        """
        Step 5: Generate embeddings from clothing analysis
        Combines text from clothing analysis into a description and generates vector embeddings
        
        Note: Body analysis is kept as independent function - not integrated into Qdrant yet
        """
        if not self.groq_service.client:
            logger.warning("Groq service not configured, using fallback embeddings")

        # Create comprehensive description for embedding
        combined_text = f"""
        Clothing: {clothing_analysis.get('sub_category', '')}
        Category: {clothing_analysis.get('category', '')}
        Colors: {', '.join(clothing_analysis.get('colors', []))}
        Material: {clothing_analysis.get('material', '')}
        Vibe: {clothing_analysis.get('vibe', '')}
        Season: {clothing_analysis.get('season', '')}
        Description: {clothing_analysis.get('description', '')}
        """

        try:
            embeddings = await self.groq_service.generate_text_embedding(combined_text)
            logger.info(f"Generated embeddings: {len(embeddings)} dimensions")
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    # ==================== STEP 6: Store in Qdrant ====================
    
    async def store_in_qdrant(
        self,
        embeddings: list,
        clothing_analysis: Dict[str, Any],
        brand_info: Dict[str, Any],
        price: Optional[float] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Step 6: Store clothing data in Qdrant vector database
        Includes metadata: clothing attributes, brand, price, purchase date
        
        Note: Body analysis is stored separately and not included in Qdrant embeddings for now
        """
        
        # Create metadata payload
        metadata = {
            "user_id": user_id,
            "clothing": clothing_analysis,
            "brand": brand_info.get("detected_brand", "Unknown"),
            "brand_confidence": brand_info.get("brand_confidence", 0),
            "price": price,
            "price_range": brand_info.get("price_range"),
            "ingested_at": datetime.now().isoformat()
        }
        
        logger.info(f"Storing in Qdrant for user {user_id}")
        
        # Generate unique point ID
        point_id = str(uuid.uuid4())
        
        # Store in Qdrant if available
        if self.qdrant_service:
            try:
                success = await self.qdrant_service.store_embedding(
                    point_id=point_id,
                    embeddings=embeddings,
                    metadata=metadata
                )
                
                if success:
                    logger.info(f"✓ Stored in Qdrant: {point_id}")
                    return {
                        "status": "stored",
                        "point_id": point_id,
                        "embeddings_size": len(embeddings),
                        "qdrant_point": {
                            "point_id": point_id,
                            "vector_size": len(embeddings),
                            "payload": metadata
                        }
                    }
                else:
                    logger.warning("Qdrant storage returned False")
                    return {
                        "status": "prepared_for_storage",
                        "embeddings_size": len(embeddings),
                        "point_id": point_id,
                        "metadata": metadata
                    }
            except Exception as e:
                logger.warning(f"Qdrant storage failed: {e}. Returning prepared data.")
                return {
                    "status": "prepared_for_storage",
                    "embeddings_size": len(embeddings),
                    "point_id": point_id,
                    "metadata": metadata,
                    "error": str(e)
                }
        else:
            logger.warning("Qdrant service not available. Returning prepared data.")
            return {
                "status": "prepared_for_storage",
                "embeddings_size": len(embeddings),
                "point_id": point_id,
                "metadata": metadata,
                "qdrant_point": {
                    "vector": embeddings,
                    "payload": metadata
                }
        }

    # ==================== ORCHESTRATION ====================
    
    async def ingest_clothing(
        self,
        image_data: bytes,
        user_id: str,
        price: Optional[float] = None,
        full_body_image: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Complete clothing ingestion pipeline:
        1. Analyze clothing item
        2. Analyze body type (if full body image provided)
        3. Detect brand
        4. Look up brand/price via Tavily
        5. Generate embeddings
        6. Store in Qdrant
        
        Returns complete ingestion result with all analysis data
        """
        
        logger.info(f"Starting clothing ingestion for user {user_id}")
        
        try:
            # Step 1: Analyze clothing
            logger.info("Step 1: Analyzing clothing item...")
            clothing_analysis = await self.analyze_clothing(image_data)
            
            # Step 2: Analyze body type (if full body image provided)
            body_analysis = {}
            if full_body_image:
                logger.info("Step 2: Analyzing body type...")
                body_analysis = await self.analyze_body_type(full_body_image)
            
            # Step 3: Detect brand
            logger.info("Step 3: Detecting brand...")
            brand_info = await self.detect_brand(image_data, clothing_analysis)
            
            # Step 4: Look up brand/price using sub_category + brand
            logger.info("Step 4: Looking up brand pricing...")
            price_info = await self.lookup_brand_price(
                brand=brand_info.get("detected_brand", "Unknown"),
                sub_category=clothing_analysis.get("sub_category", ""),
                color=clothing_analysis.get("colors", [None])[0] if clothing_analysis.get("colors") else None
            )
            brand_info.update(price_info)
            
            # Use provided price or Tavily result
            final_price = price or (brand_info.get("typical_price"))
            
            # Step 5: Generate embeddings
            logger.info("Step 5: Generating embeddings...")
            embeddings = await self.generate_embeddings(clothing_analysis, body_analysis)
            
            # Step 6: Store in Qdrant
            logger.info("Step 6: Storing in Qdrant...")
            qdrant_result = await self.store_in_qdrant(
                embeddings=embeddings,
                clothing_analysis=clothing_analysis,
                brand_info=brand_info,
                price=final_price,
                user_id=user_id
            )
            
            result = {
                "status": "success",
                "user_id": user_id,
                "clothing_analysis": clothing_analysis,
                "body_analysis": body_analysis,
                "brand_info": brand_info,
                "price": final_price,
                "qdrant_storage": qdrant_result,
                "note": "Body analysis stored in database but not yet integrated with Qdrant embeddings"
            }
            
            logger.info(f"✓ Clothing ingestion complete for {clothing_analysis.get('sub_category')}")
            return result
            
        except Exception as e:
            logger.error(f"Clothing ingestion failed: {e}")
            raise


# Global instance
clothing_ingestion_service = ClothingIngestionService()
