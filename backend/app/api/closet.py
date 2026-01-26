from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.vision_analyzer import vision_analyzer
from app.services.storage import storage_service
from app.models.models import ClothingItem, User, ClothingIngestionHistory
import uuid
import logging
from app.api.user import get_current_user

router = APIRouter()

@router.post("/upload")
async def upload_clothing(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and analyze a clothing item."""
    content = await file.read()
    
    # Get user first
    user = current_user
    if not user:
        raise HTTPException(status_code=400, detail="User session not found.")
    
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
async def get_closet_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all clothing items for the current user from SQLite ingestion history."""
    from sqlmodel import select
    
    user_id = current_user.id
    
    # Query SQLite instead of Qdrant
    statement = select(ClothingIngestionHistory).where(
        ClothingIngestionHistory.user_id == user_id,
        ClothingIngestionHistory.status == "completed"
    ).order_by(ClothingIngestionHistory.ingested_at.desc())
    
    results = db.execute(statement).scalars().all()
    
    # Map to frontend format
    mapped_items = []
    for item in results:
        # Construct mapped item matching the frontend interface
        mapped_items.append({
            "id": item.id,
            "category": item.category or "clothing",
            "sub_category": item.sub_category or "",
            "body_region": item.body_region or "unknown",
            "image_url": item.image_url,
            "mask_url": item.image_url, # Fallback
            "metadata_json": {
                "colors": item.colors or [],
                "vibe": item.vibe or "",
                "material": item.material or "",
                "description": item.description or "",
                "styling_tips": item.styling_tips or "",
                "season": item.season or "",
                "brand": item.detected_brand or "Unknown",
                "price": item.price
            }
        })
        
    return mapped_items

@router.delete("/items/{item_id}")
async def delete_closet_item(
    item_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a clothing item from SQLite and Qdrant."""
    from app.services.clip_qdrant_service import clip_qdrant_service
    
    # 1. Find the record in SQLite
    record = db.query(ClothingIngestionHistory).filter(
        ClothingIngestionHistory.id == item_id,
        ClothingIngestionHistory.user_id == current_user.id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # 2. Delete from Qdrant if we have a point_id
    if record.qdrant_point_id:
        try:
            await clip_qdrant_service.delete_item(record.qdrant_point_id)
        except Exception as e:
            logging.warning(f"Failed to delete from Qdrant: {e}")
            
    # 3. Delete from SQLite
    db.delete(record)
    db.commit()
        
    return {"status": "success", "id": item_id}


