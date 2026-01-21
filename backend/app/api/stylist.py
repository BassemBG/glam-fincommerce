from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.services.stylist_chat import stylist_chat
from app.models.models import ClothingItem, User, Outfit
import uuid

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
