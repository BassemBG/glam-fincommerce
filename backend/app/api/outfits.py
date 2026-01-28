from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.models import Outfit, User, ClothingItem, ClothingIngestionHistory
from app.services.shopping_advisor import shopping_advisor
from app.services.clip_qdrant_service import clip_qdrant_service
from sqlmodel import select
import json

from app.api.user import get_current_user

router = APIRouter()

@router.get("")
async def get_user_outfits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all outfits for the current user from the relational database."""
    user_id = current_user.id
    
    # Fetch from SQL as the primary source
    statement = select(Outfit).where(Outfit.user_id == user_id).order_by(Outfit.created_at.desc())
    outfits = db.execute(statement).scalars().all()
    
    result = []
    
    for outfit in outfits:
        # 1. Parse item IDs
        try:
            item_ids = json.loads(outfit.items) if isinstance(outfit.items, str) else outfit.items
        except:
            item_ids = []
            
        # 2. Fetch full item details from ClothingIngestionHistory
        # This enhances the payload so the frontend can display item previews
        detailed_items = []
        if item_ids:
            item_statement = select(ClothingIngestionHistory).where(
                ClothingIngestionHistory.id.in_(item_ids)
            )
            ingested_items = db.execute(item_statement).scalars().all()
            
            # Map items to the format expected by the frontend pieces gallery
            for it in ingested_items:
                detailed_items.append({
                    "id": it.id,
                    "category": it.category,
                    "sub_category": it.sub_category,
                    "body_region": it.body_region,
                    "image_url": it.image_url,
                    "mask_url": it.image_url
                })
        
        # 3. Parse style tags
        try:
            tags = json.loads(outfit.style_tags) if isinstance(outfit.style_tags, str) else (outfit.style_tags or [])
        except:
            tags = []
            
        result.append({
            "id": outfit.id,
            "name": outfit.name,
            "occasion": outfit.occasion,
            "vibe": outfit.vibe,
            "score": outfit.score,
            "reasoning": outfit.reasoning,
            "description": outfit.description,
            "style_tags": tags,
            "tryon_image_url": outfit.tryon_image_url,
            "created_by": outfit.created_by,
            "items": detailed_items,
            "created_at": outfit.created_at.isoformat() if outfit.created_at else None
        })
    
    return result

@router.get("/{outfit_id}")
async def get_outfit_detail(
    outfit_id: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single outfit with full item details from SQLite."""
    # 1. Fetch from SQL primary source
    outfit = db.query(Outfit).filter(Outfit.id == outfit_id, Outfit.user_id == current_user.id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    # 2. Parse items and fetch details
    try:
        item_ids = json.loads(outfit.items) if isinstance(outfit.items, str) else outfit.items
    except:
        item_ids = []
    
    detailed_items = []
    if item_ids:
        item_statement = select(ClothingIngestionHistory).where(
            ClothingIngestionHistory.id.in_(item_ids)
        )
        ingested_items = db.execute(item_statement).scalars().all()
        
        for it in ingested_items:
            detailed_items.append({
                "id": it.id,
                "category": it.category,
                "sub_category": it.sub_category,
                "body_region": it.body_region,
                "image_url": it.image_url,
                "mask_url": it.image_url
            })
    
    # 3. Parse style tags
    try:
        tags = json.loads(outfit.style_tags) if isinstance(outfit.style_tags, str) else (outfit.style_tags or [])
    except:
        tags = []
        
    return {
        "id": outfit.id,
        "name": outfit.name,
        "occasion": outfit.occasion,
        "vibe": outfit.vibe,
        "score": outfit.score,
        "reasoning": outfit.reasoning,
        "description": outfit.description,
        "style_tags": tags,
        "created_by": outfit.created_by,
        "tryon_image_url": outfit.tryon_image_url,
        "items": detailed_items,
        "created_at": outfit.created_at.isoformat() if outfit.created_at else None
    }

@router.post("/compare")
async def compare_new_item(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare a new item against the closet using AI."""
    user = current_user
    if not user:
        raise HTTPException(status_code=400, detail="No user found.")
    
    closet_items = db.query(ClothingItem).filter(ClothingItem.user_id == user.id).all()
    
    content = await file.read()
    result = await shopping_advisor.evaluate_new_item(content, closet_items)
    
    return result

@router.delete("/{outfit_id}")
async def delete_outfit(
    outfit_id: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an outfit from both DB and Qdrant."""
    outfit = db.query(Outfit).filter(Outfit.id == outfit_id, Outfit.user_id == current_user.id).first()
    if not outfit:
        # Fallback check: if it only exists in Qdrant, we might want to delete it there too
        # but usually SQL is the source of truth for deletion
        raise HTTPException(status_code=404, detail="Outfit not found")
        
    # Delete from Qdrant first
    await clip_qdrant_service.delete_outfit(outfit_id)
    
    # Delete from SQL
    db.delete(outfit)
    db.commit()
    return {"message": "Outfit deleted"}
