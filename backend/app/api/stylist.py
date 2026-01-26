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

from fastapi.responses import StreamingResponse

@router.post("/chat")
async def chat_with_stylist(
    message: str = Form(...),
    history: Optional[str] = Form(None), 
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    parsed_history = []
    if history:
        try: parsed_history = json.loads(history)
        except: parsed_history = []

    image_data = None
    if file:
        image_data = await file.read()

    async def sse_generator():
        async for event in agent_orchestrator.chat_stream(
            user_id=user_id,
            message=message,
            history=parsed_history,
            image_data=image_data
        ):
            yield f"data: {event}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


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
