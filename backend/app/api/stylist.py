from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.db.session import get_db
from app.services.stylist_chat import stylist_chat
from app.services.vision_analyzer import vision_analyzer
from app.services.clip_qdrant_service import clip_qdrant_service
from app.models.models import ClothingItem, User, Outfit, ClothingIngestionHistory
from sqlmodel import select
import uuid
import json

from app.api.user import get_current_user

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    history: Optional[List[dict]] = []

@router.post("/chat")
async def chat_with_stylist(
    message: str = Form(...),
    history: Optional[str] = Form(None), # JSON string of history
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    db_user = current_user
    
    # Parse history if provided
    parsed_history = []
    if history:
        try:
            parsed_history = json.loads(history)
        except:
            parsed_history = []

    # Get items from Qdrant instead of just SQL DB
    qdrant_resp = await clip_qdrant_service.get_user_items(user_id=user_id, limit=200)
    closet_items = qdrant_resp.get("items", [])
    
    # Outfits can still come from DB as primary source of metadata, or Qdrant for visual outfits
    outfits = db.query(Outfit).filter(Outfit.user_id == user_id).all() if db_user else []
    
    # Read file content if provided
    image_data = None
    if file:
        image_data = await file.read()

    result = await stylist_chat.chat(
        user_id=user_id,
        message=message,
        closet_items=closet_items,
        user_photo=db_user.full_body_image if db_user else None,
        outfits=outfits,
        history=parsed_history,
        image_data=image_data
    )
    
    return result

from app.services.embedding_service import embedding_service
from app.services.qdrant_service import qdrant_service
from app.services.tryon_generator import tryon_generator
import json
import logging

@router.post("/outfits/save")
async def save_outfit(
    outfit_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    db_user = current_user
    
    user_id_to_save = user_id
    
    # 1. Get item IDs and fetch actual items from SQLite
    item_ids = outfit_data.get("items", [])
    if isinstance(item_ids, str):
        try:
            item_ids = json.loads(item_ids)
        except:
            item_ids = []
    
    # Fetch item details from SQLite instead of Qdrant
    statement = select(ClothingIngestionHistory).where(
        ClothingIngestionHistory.id.in_(item_ids) if item_ids else (ClothingIngestionHistory.id == "none")
    )
    db_items = db.execute(statement).scalars().all()
    
    # 2. Generate global description and tags
    # Map SQLite objects to ClothingItem-like structure for metadata generation
    pseudo_items = [
        ClothingItem(
            id=item.id,
            sub_category=item.sub_category,
            body_region=item.body_region,
            image_url=item.image_url,
            metadata_json={
                "category": item.category,
                "sub_category": item.sub_category,
                "body_region": item.body_region,
                "colors": item.colors,
                "material": item.material,
                "vibe": item.vibe,
                "season": item.season,
                "description": item.description,
                "styling_tips": item.styling_tips
            }
        ) for item in db_items
    ]
    
    meta = await stylist_chat.generate_outfit_metadata(pseudo_items)
    description = meta.get("description", "")
    style_tags = json.dumps(meta.get("style_tags", []))
    
    tryon_image_url = ""
    tryon_image_bytes = ""

    if db_user and db_user.full_body_image and db_items:
        clothing_items_for_tryon = [
            {
                "image_url": item.image_url,
                "body_region": item.body_region,
                "category": item.category or "clothing",
                "sub_category": item.sub_category or ""
            }
            for item in db_items
        ]
        try:
            print(f"[DEBUG] Calling tryon_generator.generate_tryon_image...")
            tryon_result = await tryon_generator.generate_tryon_image(
                body_image_url=db_user.full_body_image,
                clothing_items=clothing_items_for_tryon
            )
            if tryon_result:
                tryon_image_url = tryon_result.get("url")
                tryon_image_bytes = tryon_result.get("bytes")
                print(f"[DEBUG] Try-on generation SUCCESS: {tryon_image_url}")
                logging.info(f"Generated try-on image: {tryon_image_url}")
            else:
                print(f"[DEBUG] Try-on generation returned None, trying collage fallback")
                collage_result = await tryon_generator.generate_outfit_collage(clothing_items_for_tryon)
                if collage_result:
                    tryon_image_url = collage_result.get("url")
                    tryon_image_bytes = collage_result.get("bytes")
                    print(f"[DEBUG] Collage generation SUCCESS: {tryon_image_url}")
        except Exception as e:
            print(f"[DEBUG] Try-on/Collage generation ERROR: {str(e)}")
            logging.error(f"Try-on generation failed: {e}")
            # Final attempt: Collage if try-on failed with error
            try:
                collage_result = await tryon_generator.generate_outfit_collage(clothing_items_for_tryon)
                if collage_result:
                    tryon_image_url = collage_result.get("url")
                    tryon_image_bytes = collage_result.get("bytes")
            except:
                pass
    else:
        # No user photo, generate collage directly
        try:
            print(f"[DEBUG] No user photo, creating collage for {len(db_items)} items")
            clothing_items_for_collage = [
                {
                    "image_url": item.image_url,
                    "mask_url": item.image_url, # Fallback
                    "category": item.category or "clothing"
                }
                for item in db_items
            ]
            collage_result = await tryon_generator.generate_outfit_collage(clothing_items_for_collage)
            if collage_result:
                tryon_image_url = collage_result.get("url")
                tryon_image_bytes = collage_result.get("bytes")
                print(f"[DEBUG] Direct collage SUCCESS: {tryon_image_url}")
        except Exception as e:
            print(f"[DEBUG] Collage failed: {e}")
    
    # 4. Create initial DB record (Optional but good for fallback/relational tracking)
    provided_name = outfit_data.get("name", "")
    ai_name = meta.get("name")
    
    # Prioritize AI name if provided name is generic or missing
    final_name = ai_name if (ai_name and (not provided_name or "Outfit " in provided_name)) else provided_name
    if not final_name:
        final_name = f"Outfit {uuid.uuid4().hex[:6]}"

    db_outfit = Outfit(
        user_id=user_id_to_save,
        name=final_name,
        occasion=outfit_data.get("occasion"),
        vibe=outfit_data.get("vibe"),
        items=json.dumps(item_ids) if isinstance(item_ids, list) else item_ids,
        score=outfit_data.get("score", 0.0),
        reasoning=outfit_data.get("reasoning"),
        description=description,
        style_tags=style_tags,
        tryon_image_url=tryon_image_url,
        created_by="ai"
    )
    
    db.add(db_outfit)
    db.commit()
    db.refresh(db_outfit)
    
    # 5. Save to Qdrant (CLIP Visual Storage for Outfits)
    if tryon_image_bytes:
        outfit_metadata = {
            "name": final_name,
            "description": description,
            "items": item_ids,
            "reasoning": db_outfit.reasoning,
            "score": db_outfit.score,
            "style_tags": meta.get("style_tags", []),
            "item_images": [item.image_url for item in db_items if item.image_url]
        }
        await clip_qdrant_service.store_outfit_with_image(
            outfit_id=str(db_outfit.id),
            image_data=tryon_image_bytes,
            outfit_data=outfit_metadata,
            user_id=user_id_to_save,
            image_url=tryon_image_url
        )

    return db_outfit

@router.post("/advisor/compare")
async def advisor_compare(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    
    content = await file.read()
    
    try:
        # Step 1: Analyze the target piece
        analysis = await vision_analyzer.analyze_clothing(content)
        category = analysis.get("category")
        sub_category = analysis.get("sub_category")
        colors = analysis.get("colors", [])
        
        # Step 2: Search visually (Low threshold to find 'vibe' matches)
        visual_matches = await clip_qdrant_service.search_similar_clothing_by_image(
            image_data=content,
            user_id=user_id,
            limit=10,
            min_score=0.35 # Very permissive for comparison
        )
        
        # Step 3: Global Metadata Check & Unified Scoring
        all_items_resp = await clip_qdrant_service.get_user_items(user_id, limit=100)
        all_items = all_items_resp.get("items", [])
        
        # Create a lookup for visual scores from CLIP
        visual_scores = {str(item["id"]): item["score"] for item in visual_matches}
        
        matches = []
        for item in all_items:
            item_id = str(item.get("id"))
            item_clothing = item.get("clothing", {})
            
            # 1. Base Score (Visual)
            v_score = visual_scores.get(item_id, 0.0)
            
            # 2. Category Boost
            cat_boost = 0.0
            if item_clothing.get("category") == category:
                cat_boost = 0.15 
                if item_clothing.get("sub_category") == sub_category:
                    cat_boost = 0.25 
            
            # 3. Color Boost
            color_boost = 0.0
            item_colors = item_clothing.get("colors", [])
            shared_colors = set(colors) & set(item_colors)
            if shared_colors:
                color_boost = min(0.20, len(shared_colors) * 0.05)
            
            # Calculate Unified Score
            if v_score > 0:
                # Weighted: 60% Visual, 40% Metadata
                unified_score = (v_score * 0.6) + (cat_boost + color_boost)
            elif cat_boost > 0:
                # No visual match found by CLIP (or below threshold), but metadata matches
                unified_score = cat_boost + color_boost
            else:
                continue 
                
            item["score"] = min(0.98, unified_score) # Cap at 98%
            
            if item["score"] > 0.30:
                img_b64 = item.get("image_base64", "")
                item["image_url"] = f"data:image/jpeg;base64,{img_b64}" if img_b64 else ""
                matches.append(item)
        
        # Sort by unified score
        matches.sort(key=lambda x: x.get("score", 0), reverse=True)
                
        return {
            "status": "success",
            "target_analysis": analysis,
            "matches": matches[:10],
            "summary": f"Unified analysis complete. Found {len(matches)} relevant matches."
        }
        
    except Exception as e:
        import logging
        logging.error(f"Advisor comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
