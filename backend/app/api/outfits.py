from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.models import Outfit, User, ClothingItem
from app.services.shopping_advisor import shopping_advisor
import json

router = APIRouter()

@router.get("/")
def get_user_outfits(db: Session = Depends(get_db)):
    """Get all outfits for the current user with item details."""
    user = db.query(User).first()
    if not user:
        return []
    
    outfits = db.query(Outfit).filter(Outfit.user_id == user.id).all()
    result = []
    
    for outfit in outfits:
        # Parse item IDs and fetch actual items
        try:
            item_ids = json.loads(outfit.items) if isinstance(outfit.items, str) else outfit.items
        except:
            item_ids = []
        
        items = []
        for item_id in item_ids:
            item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
            if item:
                items.append({
                    "id": item.id,
                    "sub_category": item.sub_category,
                    "body_region": item.body_region,
                    "image_url": item.image_url,
                    "mask_url": item.mask_url,
                    "colors": item.metadata_json.get("colors", []),
                    "vibe": item.metadata_json.get("vibe", "")
                })
        
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
def get_outfit_detail(outfit_id: str, db: Session = Depends(get_db)):
    """Get a single outfit with full item details."""
    outfit = db.query(Outfit).filter(Outfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    try:
        item_ids = json.loads(outfit.items) if isinstance(outfit.items, str) else outfit.items
    except:
        item_ids = []
    
    items = []
    for item_id in item_ids:
        item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
        if item:
            items.append({
                "id": item.id,
                "category": item.category,
                "sub_category": item.sub_category,
                "body_region": item.body_region,
                "image_url": item.image_url,
                "mask_url": item.mask_url,
                "metadata": item.metadata_json
            })
    
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
    db: Session = Depends(get_db)
):
    """Compare a new item against the closet using AI."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="No user found.")
    
    closet_items = db.query(ClothingItem).filter(ClothingItem.user_id == user.id).all()
    
    content = await file.read()
    result = await shopping_advisor.evaluate_new_item(content, closet_items)
    
    return result

@router.delete("/{outfit_id}")
def delete_outfit(outfit_id: str, db: Session = Depends(get_db)):
    """Delete an outfit."""
    outfit = db.query(Outfit).filter(Outfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    db.delete(outfit)
    db.commit()
    return {"message": "Outfit deleted"}
