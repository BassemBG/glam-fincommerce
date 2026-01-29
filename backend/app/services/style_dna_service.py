import logging
from typing import Dict, Any, List
from collections import Counter
from app.services.clip_qdrant_service import clip_qdrant_service

logger = logging.getLogger(__name__)

class StyleDNAService:
    @staticmethod
    async def get_user_style_dna(user_id: str) -> Dict[str, Any]:
        """
        Analyzes the user's closet to extract style statistics:
        - Vibe distribution (Chic, Streetwear, etc.)
        - Color palette
        - Category breakdown
        """
        try:
            # 1. Fetch closet items from Qdrant
            resp = await clip_qdrant_service.get_user_items(user_id, limit=200)
            items = resp.get("items", [])
            
            vibes = []
            colors = []
            categories = []
            
            # Extract from Closet
            for item in items:
                c = item.get("clothing", {})
                v = c.get("vibe")
                if v: vibes.append(v)
                
                cls = c.get("colors", [])
                if isinstance(cls, list): colors.extend(cls)
                elif isinstance(cls, str): colors.append(cls)
                
                cat = c.get("category")
                if cat: categories.append(cat)
            
            # 2. Extract from Zep (Pinterest Persona)
            from app.services.zep_service import zep_client
            if zep_client:
                try:
                    # Search for style-related facts in the graph
                    zep_results = zep_client.graph.search(query="style preferences, recurring colors, fashion vibes", user_id=user_id, limit=10)
                    for res in zep_results:
                        fact = getattr(res, 'fact', str(res)).lower()
                        # Simple heuristic extraction from Zep facts
                        for v in ["chic", "streetwear", "minimalist", "boho", "vintage", "casual", "formal", "sporty"]:
                            if v in fact: vibes.append(v.capitalize())
                        
                        # Extract colors mentioned in facts
                        common_colors = ["black", "white", "blue", "red", "green", "yellow", "pink", "beige", "grey", "brown"]
                        for color in common_colors:
                            if color in fact: colors.append(color.capitalize())
                except Exception as ze:
                    logger.warning(f"Zep DNA enrichment failed: {ze}")

            if not vibes and not colors and not items:
                return {
                    "vibes": {"Universal": 100},
                    "colors": [],
                    "top_categories": [],
                    "total_items": 0
                }
                
            # 3. Calculate Distributions
            total_v = len(vibes) or 1
            vibe_counts = Counter(vibes)
            vibe_dist = {k: round((v / total_v) * 100) for k, v in vibe_counts.items()}
            
            # 4. Top Colors
            color_counts = Counter(colors)
            top_colors = [c[0] for c in color_counts.most_common(10)]
            
            # 5. Top Categories
            cat_counts = Counter(categories)
            top_cats = [{"item": k, "count": v} for k, v in cat_counts.most_common(5)]
            
            return {
                "vibes": vibe_dist if vibe_dist else {"Casual": 100},
                "colors": top_colors,
                "top_categories": top_cats,
                "total_items": len(items)
            }
            
        except Exception as e:
            logger.error(f"Style DNA error: {e}")
            return {"error": str(e)}

style_dna_service = StyleDNAService()
