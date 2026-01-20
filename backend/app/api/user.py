from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.storage import storage_service
from app.models.models import User
import uuid

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

@router.get("/me")
def get_me(db: Session = Depends(get_db)):
    try:
        user = db.query(User).first()
        if not user:
            # Return a mock user if no user exists yet
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
        # Fallback for schema issues
        return {
            "id": None,
            "email": "demo@example.com",
            "full_name": "Demo User",
            "full_body_image": None
        }
