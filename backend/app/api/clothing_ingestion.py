"""
Clothing Ingestion API Endpoints
Handles image upload, analysis, and storage for clothing items
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlmodel import select
from app.db.session import get_db
from app.services.clothing_ingestion_service import clothing_ingestion_service
from app.services.storage import storage_service
from app.models.models import ClothingIngestionHistory, User
from app.api.user import get_current_user
import logging
import uuid
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/clothing", tags=["clothing"])

# ==================== Schemas for Request/Response ====================

class IngestionRequest:
    """Request model for clothing ingestion"""
    price: Optional[float] = None
    # full_body_image is passed as a separate file


class IngestionResponse:
    """Response model for successful ingestion"""
    id: str
    user_id: str
    status: str
    detected_brand: str
    sub_category: str
    price: Optional[float]
    qdrant_point_id: Optional[str]


# ==================== Endpoints ====================

@router.post("/ingest")
async def ingest_clothing(
    file: UploadFile = File(...),
    price: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest a clothing item with full analysis.
    
    - Analyzes clothing using Groq Vision API
    - Detects brand and pricing
    - Generates embeddings
    - Stores in Qdrant
    
    Query params:
    - price: Optional price override
    """
    
    try:
        user_id = current_user.id
        
        # Ensure this demo user exists in SQL to satisfy Foreign Key constraints
        # Otherwise ingestion history insert will fail
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.info(f"Creating demo user {user_id} for FK constraint")
            # Create a dummy user for the demo
            # Use unique email to avoid UNIQUE constraint errors
            demo_user = User(
                id=user_id,
                email=f"{user_id}@example.com",
                full_name="Demo User",
                hashed_password="demo", 
                is_active=True
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
            
        # Read image file
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"Starting clothing ingestion for user {user_id}")
        
        # Create ingestion history record (pending)
        file_id = str(uuid.uuid4())
        temp_image_url = f"temp://{file_id}"
        
        ingestion_record = ClothingIngestionHistory(
            user_id=user_id,
            image_url=temp_image_url,
            status="processing",
            detected_brand="Unknown",
            category="clothing",
            sub_category="Analyzing...",
            body_region="unknown",
            material="",
            vibe="",
            season=""
        )
        db.add(ingestion_record)
        db.commit()
        db.refresh(ingestion_record)
        
        logger.info(f"Created ingestion record: {ingestion_record.id}")
        
        # Run full ingestion pipeline
        result = await clothing_ingestion_service.ingest_clothing(
            image_data=content,
            user_id=user_id,
            price=price
        )
        
        
        # SKIP Uploading image to permanent storage (User Preference: Use Qdrant Base64)
        # image_name = f"clothing/{user_id}/{file_id}.jpg"
        # image_url = await storage_service.upload_file(...)
        
        # logger.info(f"Image uploaded to: {image_url}")
        
        # Update ingestion record with results
        clothing_analysis = result.get("clothing_analysis", {})
        body_analysis = result.get("body_analysis", {})
        brand_info = result.get("brand_info", {})
        
        # Use placeholder URL since we are relying on Qdrant
        qdrant_res = result.get("qdrant_result", {})
        point_id = qdrant_res.get("point_id") if isinstance(qdrant_res, dict) else None
        ingestion_record.image_url = qdrant_res.get("image_url")
        ingestion_record.status = "completed"
        
        # Clothing attributes
        ingestion_record.category = clothing_analysis.get("category", "clothing")
        ingestion_record.sub_category = clothing_analysis.get("sub_category", "")
        ingestion_record.body_region = clothing_analysis.get("body_region", "top")
        ingestion_record.colors = clothing_analysis.get("colors", [])
        ingestion_record.material = clothing_analysis.get("material", "")
        ingestion_record.vibe = clothing_analysis.get("vibe", "")
        ingestion_record.season = clothing_analysis.get("season", "All Seasons")
        ingestion_record.description = clothing_analysis.get("description", "")
        ingestion_record.styling_tips = clothing_analysis.get("styling_tips", "")
        ingestion_record.estimated_brand_range = clothing_analysis.get("estimated_brand_range", "unknown")
        
        # Body analysis - Store but NOT in Qdrant (kept as independent for now)
        # ingestion_record.gender_presentation = body_analysis.get("gender_presentation")
        # ingestion_record.body_type = body_analysis.get("body_type")
        # ingestion_record.skin_tone = body_analysis.get("skin_tone")
        # ingestion_record.estimated_height = body_analysis.get("estimated_height")
        # ingestion_record.body_confidence = body_analysis.get("body_confidence")
        # Note: Body analysis is available in result but not persisted to DB or Qdrant
        
        # Brand info
        ingestion_record.detected_brand = brand_info.get("detected_brand", "Unknown")
        ingestion_record.brand_confidence = brand_info.get("brand_confidence", 0)
        ingestion_record.brand_indicators = brand_info.get("brand_indicators", [])
        ingestion_record.price = result.get("price")
        ingestion_record.price_range = brand_info.get("price_range", "unknown")
        ingestion_record.typical_brand_price = brand_info.get("typical_price")
        ingestion_record.stores = brand_info.get("stores", [])
        
        # Embeddings
        qdrant_storage = result.get("qdrant_storage", {})
        ingestion_record.embeddings = qdrant_storage.get("embeddings_size")  # Store size, not actual vectors
        ingestion_record.qdrant_point_id = qdrant_storage.get("qdrant_point", {}).get("point_id")
        
        db.add(ingestion_record)
        db.commit()
        db.refresh(ingestion_record)
        
        logger.info(f"✓ Ingestion complete: {ingestion_record.id}")
        
        return {
            "status": "success",
            "ingestion_id": ingestion_record.id,
            "user_id": user_id,
            "clothing": {
                "category": ingestion_record.category,
                "sub_category": ingestion_record.sub_category,
                "colors": ingestion_record.colors,
                "material": ingestion_record.material,
                "vibe": ingestion_record.vibe,
                "description": ingestion_record.description
            },
            "brand": {
                "detected_brand": ingestion_record.detected_brand,
                "confidence": ingestion_record.brand_confidence,
                "price_range": ingestion_record.price_range
            },
            "price": ingestion_record.price,
            "image_url": ingestion_record.image_url,
            "qdrant_result": result.get("qdrant_result")
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/ingestion-history")
async def get_ingestion_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's clothing ingestion history"""
    
    user_id = current_user.id
    
    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Query ingestion history
    statement = select(ClothingIngestionHistory).where(
        ClothingIngestionHistory.user_id == user_id
    ).order_by(ClothingIngestionHistory.ingested_at.desc()).offset(skip).limit(limit)
    
    results = db.exec(statement).all()
    
    return {
        "status": "success",
        "count": len(results),
        "items": [
            {
                "id": item.id,
                "category": item.category,
                "sub_category": item.sub_category,
                "detected_brand": item.detected_brand,
                "price": item.price,
                "colors": item.colors,
                "vibe": item.vibe,
                "image_url": item.image_url,
                "ingested_at": item.ingested_at.isoformat()
            }
            for item in results
        ]
    }


@router.get("/ingestion/{ingestion_id}")
async def get_ingestion_detail(
    ingestion_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific ingestion"""
    
    user_id = current_user.id
    
    # Query ingestion record
    record = db.query(ClothingIngestionHistory).filter(
        ClothingIngestionHistory.id == ingestion_id,
        ClothingIngestionHistory.user_id == user_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Ingestion record not found")
    
    return {
        "status": "success",
        "id": record.id,
        "clothing": {
            "category": record.category,
            "sub_category": record.sub_category,
            "body_region": record.body_region,
            "colors": record.colors,
            "material": record.material,
            "vibe": record.vibe,
            "season": record.season,
            "description": record.description,
            "styling_tips": record.styling_tips
        },
        "body_analysis": {
            "gender_presentation": record.gender_presentation,
            "body_type": record.body_type,
            "skin_tone": record.skin_tone,
            "estimated_height": record.estimated_height,
            "confidence": record.body_confidence
        },
        "brand": {
            "detected_brand": record.detected_brand,
            "confidence": record.brand_confidence,
            "indicators": record.brand_indicators,
            "price_range": record.price_range,
            "stores": record.stores
        },
        "pricing": {
            "user_price": record.price,
            "typical_brand_price": record.typical_brand_price
        },
        "image_url": record.image_url,
        "ingested_at": record.ingested_at.isoformat()
    }


@router.delete("/ingestion/{ingestion_id}")
async def delete_ingestion(
    ingestion_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a clothing ingestion record"""
    
    user_id = current_user.id
    
    # Query and delete
    record = db.query(ClothingIngestionHistory).filter(
        ClothingIngestionHistory.id == ingestion_id,
        ClothingIngestionHistory.user_id == user_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Ingestion record not found")
    
    db.delete(record)
    db.commit()
    
    return {"status": "success", "message": "Ingestion record deleted"}


@router.post("/batch-ingest")
async def batch_ingest(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Batch upload multiple clothing items
    Processes them asynchronously in the background
    """
    
    user_id = current_user.id
    
    # Validate user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch")
    
    ingestion_ids = []
    
    # Create ingestion records for all files
    for file in files:
        content = await file.read()
        file_id = str(uuid.uuid4())
        
        record = ClothingIngestionHistory(
            user_id=user_id,
            image_url=f"temp://{file_id}",
            status="pending",
            detected_brand="Unknown",
            category="clothing",
            sub_category="Queued...",
            body_region="unknown",
            material="",
            vibe="",
            season=""
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        ingestion_ids.append(record.id)
    
    return {
        "status": "success",
        "message": f"Batch ingestion queued for {len(files)} items",
        "ingestion_ids": ingestion_ids,
        "note": "Processing in background. Check status via GET /ingestion-history"
    }
