from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.models import Outfit, User, ClothingItem
from app.services.shopping_advisor import shopping_advisor
from app.services.clip_qdrant_service import clip_qdrant_service
import json

from app.api.user import get_current_user

router = APIRouter()

@router.get("/")
async def get_user_outfits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all outfits for the current user from Qdrant."""
    user_id = current_user.id
    
    # Lead with Qdrant for visual outfits
    qdrant_resp = await clip_qdrant_service.get_user_outfits(user_id=user_id, limit=50)
    qdrant_outfits = qdrant_resp.get("items", [])
    
    if qdrant_outfits:
        return qdrant_outfits
        
    # Fallback to DB if Qdrant is empty (legacy or non-visual outfits)
    user = current_user
    
    if not user:
        return []
    
    outfits = db.query(Outfit).filter(Outfit.user_id == user.id).all()
    result = []
    
    for outfit in outfits:
        try:
            item_ids = json.loads(outfit.items) if isinstance(outfit.items, str) else outfit.items
        except:
            item_ids = []
        
        # We can also fetch item details from Qdrant here if needed
        # but for fallback, let's keep it simple or use the new helper
        items = await clip_qdrant_service.get_items_by_ids(item_ids)
        
        result.append({
            "id": outfit.id,
            "name": outfit.name,
            "occasion": outfit.occasion,
            "vibe": outfit.vibe,
            "score": outfit.score,
            "reasoning": outfit.reasoning,
            "description": outfit.description,
            "style_tags": outfit.style_tags,
            "tryon_image_url": outfit.tryon_image_url,
            "created_by": outfit.created_by,
            "items": items
        })
    
    return result

@router.get("/{outfit_id}")
async def get_outfit_detail(
    outfit_id: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single outfit with full item details."""
    # 1. Try Qdrant retrieval first as primary source
    qdrant_outfit = await clip_qdrant_service.get_outfit_by_id(outfit_id)
    
    if qdrant_outfit:
        # Fetch detailed item objects from Qdrant for this outfit
        item_ids = qdrant_outfit.get("items", [])
        detailed_items = await clip_qdrant_service.get_items_by_ids(item_ids)
        qdrant_outfit["items"] = detailed_items
        return qdrant_outfit
        
    # 2. Fallback to DB for legacy/non-visual outfits
    outfit = db.query(Outfit).filter(Outfit.id == outfit_id, Outfit.user_id == current_user.id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    try:
        item_ids = json.loads(outfit.items) if isinstance(outfit.items, str) else outfit.items
    except:
        item_ids = []
    
    # Even for legacy outfits, fetch item details from Qdrant Cloud
    items = await clip_qdrant_service.get_items_by_ids(item_ids)
    
    return {
        "id": outfit.id,
        "name": outfit.name,
        "occasion": outfit.occasion,
        "vibe": outfit.vibe,
        "score": outfit.score,
        "reasoning": outfit.reasoning,
        "description": outfit.description,
        "style_tags": outfit.style_tags,
        "created_by": outfit.created_by,
        "tryon_image_url": outfit.tryon_image_url,
        "items": items
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
