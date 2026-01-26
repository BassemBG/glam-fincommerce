from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.db.session import get_db
from app.services.outfit_service import outfit_service
from app.agents.orchestrator import agent_orchestrator
from app.services.vision_analyzer import vision_analyzer
from app.services.clip_qdrant_service import clip_qdrant_service
from app.models.models import ClothingItem, User, Outfit
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
    
    # Read file content if provided for multi-modal agent reasoning
    image_data = None
    if file:
        image_data = await file.read()

    # The Orchestrator now handles history conversion, temporal context, and agent execution
    result = await agent_orchestrator.chat(
        user_id=user_id,
        message=message,
        history=parsed_history,
        image_data=image_data
    )
    
    return result


import json
import logging

@router.post("/outfits/save")
async def save_outfit(
    outfit_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Saves an outfit by delegating metadata generation and storage to OutfitService."""
    return await outfit_service.save_outfit(current_user, outfit_data, db)

@router.post("/advisor/compare")
async def advisor_compare(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = await file.read()
    try:
        return await outfit_service.advisor_compare(current_user.id, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
