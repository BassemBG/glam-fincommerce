from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.storage import storage_service
from app.models.models import User
import uuid
import os

router = APIRouter()

@router.post("/body-photo")
async def upload_body_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads the user's full-body photo for try-ons."""
    content = await file.read()
    
    # Simple dummy user logic as used in other parts
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")
        
    file_id = str(uuid.uuid4())
    file_name = f"user_body_{file_id}.jpg"
    
    image_url = await storage_service.upload_file(content, file_name, file.content_type)
    
    user.full_body_image = image_url
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"image_url": image_url}

@router.post("/analyze-profile")
async def analyze_user_profile(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads a full-body photo, analyzes physical characteristics via Groq,
    and returns the morphology, skin tone, height, and weight.
    """
    from app.services.groq_vision_service import groq_vision_service
    import json
    
    content = await file.read()
    
    prompt = """Analyze this full-body photo for fashion styling.
    Return ONLY JSON:
    {
      "morphology": "body shape (hourglass, pear, apple, rectangle, inverted triangle, athletic)",
      "skin_color": "skin tone",
      "height": "estimated height in cm",
      "weight": "estimated weight in kg",
      "summary": "short physiological description"
    }"""
    
    try:
        # 1. Get AI analysis
        raw_result = await groq_vision_service._call_vision(content, prompt, json_format=True)
        
        # Clean JSON
        clean_text = raw_result.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("```")[1]
            if clean_text.startswith("json"):
                clean_text = clean_text[4:]
            clean_text = clean_text.strip()
            
        analysis = json.loads(clean_text)
        
        # 2. Save result to a local JSON for 'stocking' as requested
        file_id = str(uuid.uuid4())
        save_dir = "profile_data"
        os.makedirs(save_dir, exist_ok=True)
        json_path = os.path.join(save_dir, f"user_{file_id}.json")
        
        with open(json_path, "w") as f:
            json.dump(analysis, f, indent=2)
            
        return {
            "status": "success",
            "analysis": analysis,
            "saved_to": json_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me")
def get_me(db: Session = Depends(get_db)):
    try:
        user = db.query(User).first()
        if not user:
            return {
                "id": None,
                "email": "demo@example.com",
                "full_name": "Demo User",
                "full_body_image": None
            }
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "full_body_image": getattr(user, 'full_body_image', None)
        }
    except Exception as e:
        return {
            "id": None,
            "email": "demo@example.com",
            "full_name": "Demo User",
            "full_body_image": None
        }
