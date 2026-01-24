from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.db.session import get_db
from app.services.stylist_chat import stylist_chat
from app.services.vision_analyzer import vision_analyzer
from app.services.clip_qdrant_service import clip_qdrant_service
from app.models.models import ClothingItem, User, Outfit
import uuid
import json

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    history: Optional[List[dict]] = []

@router.post("/chat")
async def chat_with_stylist(
    chat_in: ChatMessage,
    db: Session = Depends(get_db)
):
    db_user = db.query(User).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="No user found.")
    
    closet_items = db.query(ClothingItem).filter(ClothingItem.user_id == db_user.id).all()
    outfits = db.query(Outfit).filter(Outfit.user_id == db_user.id).all()
    
    result = await stylist_chat.chat(
        user_id=str(db_user.id),
        message=chat_in.message,
        closet_items=closet_items,
        user_photo=db_user.full_body_image,
        outfits=outfits,
        history=chat_in.history
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
    db: Session = Depends(get_db)
):
    dummy_user = db.query(User).first()
    if not dummy_user:
        raise HTTPException(status_code=400, detail="No user found.")
    
    # 1. Get item IDs and fetch actual items
    item_ids = outfit_data.get("items", [])
    if isinstance(item_ids, str):
        try:
            item_ids = json.loads(item_ids)
        except:
            item_ids = []
    
    db_items = db.query(ClothingItem).filter(ClothingItem.id.in_(item_ids)).all()
    
    # 2. Generate global description and tags
    meta = await stylist_chat.generate_outfit_metadata(db_items)
    description = meta.get("description", "")
    style_tags = json.dumps(meta.get("style_tags", []))
    
    # 3. Generate try-on image if user has a body photo
    tryon_image_url = None
    if dummy_user.full_body_image and db_items:
        clothing_items = [
            {
                "image_url": item.image_url,
                "mask_url": item.mask_url,
                "body_region": item.body_region
            }
            for item in db_items
        ]
        try:
            tryon_image_url = await tryon_generator.generate_tryon_image(
                body_image_url=dummy_user.full_body_image,
                clothing_items=clothing_items
            )
            logging.info(f"Generated try-on image: {tryon_image_url}")
        except Exception as e:
            logging.error(f"Try-on generation failed: {e}")
    
    # 4. Create initial DB record
    db_outfit = Outfit(
        user_id=dummy_user.id,
        name=outfit_data.get("name"),
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
    
    # 5. Generate embedding and save to Qdrant
    embedding_text = f"{db_outfit.name or ''}. {description}. Tags: {style_tags}"
    vector = await embedding_service.get_text_embedding(embedding_text)
    
    if vector:
        payload = {
            "outfit_id": db_outfit.id,
            "user_id": str(db_outfit.user_id),
            "name": db_outfit.name,
            "occasion": db_outfit.occasion,
            "vibe": db_outfit.vibe,
            "style_tags": meta.get("style_tags", [])
        }
        success = await qdrant_service.upsert_outfit(
            outfit_id=db_outfit.id,
            vector=vector,
            payload=payload
        )
        
        if success:
            db_outfit.qdrant_vector_id = db_outfit.id
            db_outfit.qdrant_payload = payload
            db.commit()
    
    return db_outfit

@router.post("/advisor/compare")
async def advisor_compare(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Compare a potential purchase image with existing closet items.
    Checks for:
    1. Visual similarity (CLIP)
    2. Category & Color matches
    """
    # Force demo user ID for consistency
    user_id = "full_test_user"
    
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
