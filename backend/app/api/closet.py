from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.vision_analyzer import vision_analyzer
from app.services.storage import storage_service
from app.models.models import ClothingItem, User
import uuid
import logging

router = APIRouter()

@router.post("/upload")
async def upload_clothing(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and analyze a clothing item."""
    content = await file.read()
    
    # Get user first
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="No user found. Please visit /settings first.")
    
    file_id = str(uuid.uuid4())
    
    # 1. Upload original image first (fast)
    logging.info(f"Uploading image {file_id}...")
    image_name = f"{file_id}.jpg"
    image_url = await storage_service.upload_file(content, image_name, file.content_type or "image/jpeg")
    
    # 2. AI Analysis (few seconds)
    logging.info("Running AI analysis...")
    analysis = await vision_analyzer.analyze_clothing(content)
    if "error" in analysis:
        raise HTTPException(status_code=500, detail=analysis["error"])
    
    # 3. Background removal (can be slow on first run - skipped if fails)
    logging.info("Attempting background removal...")
    try:
        masked_content = await vision_analyzer.remove_background(content)
        mask_name = f"{file_id}_mask.png"
        mask_url = await storage_service.upload_file(masked_content, mask_name, "image/png")
    except Exception as e:
        logging.warning(f"Background removal failed, using original: {e}")
        mask_url = image_url  # Fallback to original
    
    # 4. Save to database
    db_item = ClothingItem(
        user_id=user.id,
        category=analysis.get("category", "clothing"),
        sub_category=analysis.get("sub_category"),
        body_region=analysis.get("body_region", "top"),
        image_url=image_url,
        mask_url=mask_url,
        metadata_json=analysis
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    logging.info(f"Item saved: {db_item.id}")
    
    return {
        "id": db_item.id,
        "analysis": analysis,
        "image_url": image_url,
        "mask_url": mask_url
    }

@router.get("/items")
async def get_closet_items(db: Session = Depends(get_db)):
    """Get all clothing items for the current user from Qdrant."""
    from app.services.clip_qdrant_service import clip_qdrant_service
    
    # For demo purposes, we are forcing the Qdrant user ID to ensure items are visible
    # regardless of the SQL user state. 
    # In a real app, this would be: user_id = str(user.id)
    target_user_id = "full_test_user"
        
    # Fetch from Qdrant
    qdrant_result = await clip_qdrant_service.get_user_items(target_user_id, limit=100)
    items = qdrant_result.get("items", [])
    
    # Map to frontend format
    mapped_items = []
    for item in items:
        clothing = item.get("clothing", {})
        image_base64 = item.get("image_base64")
        
        # Construct image URL (Data URI for base64)
        image_url = ""
        if image_base64:
            image_url = f"data:image/jpeg;base64,{image_base64}"
            
        mapped_items.append({
            "id": item.get("id"),
            "category": clothing.get("category", "clothing"),
            "sub_category": clothing.get("sub_category", ""),
            "body_region": clothing.get("body_region", "unknown"),
            "image_url": image_url,
            "mask_url": image_url, # Fallback since Qdrant doesn't store mask
            "metadata_json": {
                "colors": clothing.get("colors", []),
                "vibe": clothing.get("vibe", ""),
                "material": clothing.get("material", ""),
                "description": clothing.get("description", ""),
                "styling_tips": clothing.get("styling_tips", ""),
                "season": clothing.get("season", ""),
                "brand": item.get("brand"),
                "price": item.get("price")
            }
        })
        
    return mapped_items

@router.delete("/items/{item_id}")
async def delete_closet_item(item_id: str, db: Session = Depends(get_db)):
    """Delete a clothing item from the closet (Qdrant)."""
    from app.services.clip_qdrant_service import clip_qdrant_service
    
    # Delete from Qdrant
    success = await clip_qdrant_service.delete_item(item_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete item")
        
    return {"status": "success", "id": item_id}


