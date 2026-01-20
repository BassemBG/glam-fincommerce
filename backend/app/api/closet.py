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
def get_closet_items(db: Session = Depends(get_db)):
    """Get all clothing items for the current user."""
    user = db.query(User).first()
    if not user:
        return []
    return db.query(ClothingItem).filter(ClothingItem.user_id == user.id).all()

@router.delete("/items/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)):
    """Delete a clothing item."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}
