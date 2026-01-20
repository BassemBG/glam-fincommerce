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

@router.post("/outfits/save")
async def save_outfit(
    outfit_data: dict,
    db: Session = Depends(get_db)
):
    dummy_user = db.query(User).first()
    if not dummy_user:
        raise HTTPException(status_code=400, detail="No user found.")
    
    db_outfit = Outfit(
        user_id=dummy_user.id,
        name=outfit_data.get("name"),
        occasion=outfit_data.get("occasion"),
        vibe=outfit_data.get("vibe"),
        items=outfit_data.get("items"),
        score=outfit_data.get("score", 0.0),
        reasoning=outfit_data.get("reasoning"),
        created_by="ai"
    )
    
    db.add(db_outfit)
    db.commit()
    db.refresh(db_outfit)
    
    return db_outfit
