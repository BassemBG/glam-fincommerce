from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.db.session import get_db
from app.services.storage import storage_service
from app.models.models import User
from app.schemas.user import UserOnboarding, UserOut
from app.core.config import settings
from app.core.security import ALGORITHM
from app.services.zep_service import add_onboarding_to_thread, add_onboarding_to_graph, create_zep_thread
import uuid
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract user ID from JWT token and return user object."""
    print(f"\n*** GET_CURRENT_USER CALLED *** authorization={authorization[:20] if authorization else None}...")
    logger.info(f"[AUTH] ****GET_CURRENT_USER**** called, auth header present: {bool(authorization)}")
    
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

@router.post("/analyze-profile")
async def analyze_user_profile(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        
        # 2. Save result to a local JSON for 'stocking'
        user_id = current_user.id
        save_dir = "profile_data"
        os.makedirs(save_dir, exist_ok=True)
        json_path = os.path.join(save_dir, f"user_{user_id}.json")
        
        with open(json_path, "w") as f:
            json.dump(analysis, f, indent=2)
            
        return {
            "status": "success",
            "analysis": analysis,
            "saved_to": json_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/onboarding", response_model=UserOut)
def complete_onboarding(
    onboarding_data: UserOnboarding,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete user onboarding profile and save to Zep thread."""
    user = current_user
    print(f"\n*** ONBOARDING ENDPOINT CALLED *** user_id={user.id}")
    logger.info(f"[ONBOARDING] ****ENTRY**** for user {user.id}")
    logger.info(f"[ONBOARDING] ****COMPLETE_ONBOARDING_START**** for user {user.id}")
    
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
    
    logger.info(f"[ONBOARDING] ****ONBOARDING_SAVED_TO_DB**** for user {user.id}")
    
    # Prepare onboarding dict for debugging
    onboarding_dict = {
        "age": user.age,
        "education": user.education,
        "daily_style": user.daily_style,
        "color_preferences": user.color_preferences,
        "fit_preference": user.fit_preference,
        "price_comfort": user.price_comfort,
        "buying_priorities": user.buying_priorities,
        "clothing_description": user.clothing_description,
        "styled_combinations": user.styled_combinations,
    }
    logger.info(f"[ONBOARDING] ****PAYLOAD**** {onboarding_dict}")
    
    # Add onboarding data to Zep thread (create thread if missing)
    try:
        thread_id = user.zep_thread_id
        logger.info(f"[ONBOARDING] ****EXISTING_THREAD**** {thread_id}")
        
        if not thread_id:
            logger.warning(f"[ONBOARDING] ****NO_THREAD**** User {user.id} has no Zep thread_id; creating one now")
            thread_id = create_zep_thread(user.id)
            logger.info(f"[ONBOARDING] ****CREATED_THREAD**** {thread_id}")
            
            if thread_id:
                user.zep_thread_id = thread_id
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"[ONBOARDING] ****THREAD_SAVED_TO_DB**** {thread_id}")
        
        if thread_id:
            logger.info(f"[ONBOARDING] ****CALLING_ADD_ONBOARDING**** user={user.id}, thread={thread_id}")
            result = add_onboarding_to_graph(user.id, onboarding_dict, user_email=user.email, thread_id=thread_id)
            if result:
                logger.info(f"[ONBOARDING] ****SUCCESS**** Added onboarding data to Zep graph for user {user.id}")
            else:
                logger.error(f"[ONBOARDING] ****FAILED**** Failed to add onboarding data to Zep graph for user {user.id}")
        else:
            logger.error(f"[ONBOARDING] ****ERROR**** User {user.id}: failed to obtain Zep thread_id; onboarding not pushed to Zep")
    except Exception as e:
        logger.exception(f"[ONBOARDING] ****EXCEPTION**** Failed to push onboarding data to Zep for user {user.id}: {e}")
    
    logger.info(f"[ONBOARDING] ****COMPLETE_ONBOARDING_END**** for user {user.id}")
    return user

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "full_body_image": getattr(current_user, 'full_body_image', None),
        "onboarding_completed": current_user.onboarding_completed,
        "zep_thread_id": getattr(current_user, "zep_thread_id", None),
    }
