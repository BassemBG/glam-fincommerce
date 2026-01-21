from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.db.session import get_db
from app.services.storage import storage_service
from app.models.models import User
from app.schemas.user import UserOnboarding, UserOut
from app.core.config import settings
from app.core.security import ALGORITHM
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract user ID from JWT token and return user object."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/body-photo")
async def upload_body_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uploads the user's full-body photo for try-ons."""
    content = await file.read()
    user = current_user
        
    file_id = str(uuid.uuid4())
    file_name = f"user_body_{file_id}.jpg"
    
    image_url = await storage_service.upload_file(content, file_name, file.content_type)
    
    user.full_body_image = image_url
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"image_url": image_url}

@router.post("/onboarding", response_model=UserOut)
def complete_onboarding(
    onboarding_data: UserOnboarding,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete user onboarding profile."""
    user = current_user
    
    # Update user with onboarding data
    user.age = onboarding_data.age
    user.education = onboarding_data.education
    user.daily_style = onboarding_data.daily_style
    user.color_preferences = onboarding_data.color_preferences
    user.fit_preference = onboarding_data.fit_preference
    user.price_comfort = onboarding_data.price_comfort
    user.buying_priorities = onboarding_data.buying_priorities
    user.clothing_description = onboarding_data.clothing_description
    user.styled_combinations = onboarding_data.styled_combinations
    user.onboarding_completed = True
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user.id} completed onboarding")
    return user

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "full_body_image": getattr(current_user, 'full_body_image', None),
        "onboarding_completed": current_user.onboarding_completed
    }
