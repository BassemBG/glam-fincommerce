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
from typing import Dict, Optional, Any
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
    user.gender = onboarding_data.gender
    user.age = onboarding_data.age
    user.education = onboarding_data.education
    user.country = onboarding_data.country
    user.daily_style = onboarding_data.daily_style
    user.color_preferences = onboarding_data.color_preferences
    user.fit_preference = onboarding_data.fit_preference
    user.price_comfort = onboarding_data.price_comfort
    user.buying_priorities = onboarding_data.buying_priorities
    user.clothing_description = onboarding_data.clothing_description
    user.styled_combinations = onboarding_data.styled_combinations
    user.min_budget = onboarding_data.min_budget
    user.max_budget = onboarding_data.max_budget
    user.wallet_balance = onboarding_data.wallet_balance if onboarding_data.wallet_balance is not None else 0.0
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

@router.put("/settings")
def update_user_settings(
    settings_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user-specific settings like budget, currency, and profile info."""
    user = current_user
    
    # Financial fields
    if "budget_limit" in settings_data: user.budget_limit = settings_data["budget_limit"]
    if "currency" in settings_data: user.currency = settings_data["currency"]
    if "min_budget" in settings_data: user.min_budget = settings_data["min_budget"]
    if "max_budget" in settings_data: user.max_budget = settings_data["max_budget"]
    if "wallet_balance" in settings_data: user.wallet_balance = settings_data["wallet_balance"]
    
    # Profile fields
    if "gender" in settings_data: user.gender = settings_data["gender"]
    if "age" in settings_data: user.age = settings_data["age"]
    if "education" in settings_data: user.education = settings_data["education"]
    if "country" in settings_data: user.country = settings_data["country"]
    if "daily_style" in settings_data: user.daily_style = settings_data["daily_style"]
    if "color_preferences" in settings_data: user.color_preferences = settings_data["color_preferences"]
    if "fit_preference" in settings_data: user.fit_preference = settings_data["fit_preference"]
    if "price_comfort" in settings_data: user.price_comfort = settings_data["price_comfort"]
    if "buying_priorities" in settings_data: user.buying_priorities = settings_data["buying_priorities"]
    if "clothing_description" in settings_data: user.clothing_description = settings_data["clothing_description"]
    if "styled_combinations" in settings_data: user.styled_combinations = settings_data["styled_combinations"]
        
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "gender": current_user.gender,
        "age": current_user.age,
        "education": current_user.education,
        "country": current_user.country,
        "daily_style": current_user.daily_style,
        "color_preferences": current_user.color_preferences,
        "fit_preference": current_user.fit_preference,
        "price_comfort": current_user.price_comfort,
        "buying_priorities": current_user.buying_priorities,
        "clothing_description": current_user.clothing_description,
        "styled_combinations": current_user.styled_combinations,
        "budget_limit": current_user.budget_limit,
        "min_budget": current_user.min_budget,
        "max_budget": current_user.max_budget,
        "currency": current_user.currency,
        "wallet_balance": current_user.wallet_balance,
        "full_body_image": getattr(current_user, 'full_body_image', None),
        "onboarding_completed": current_user.onboarding_completed,
        "zep_thread_id": getattr(current_user, "zep_thread_id", None),
    }

@router.post("/wallet/topup")
def topup_wallet(
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Securely add funds to the user's wallet."""
    if amount <= 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Amount must be positive")
        
    current_user.wallet_balance += amount
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"balance": current_user.wallet_balance}

@router.post("/wallet/spend")
def spend_from_wallet(
    amount: float,
    item_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deduct funds from the wallet after user confirmation."""
    if amount <= 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Amount must be positive")
        
    if current_user.wallet_balance < amount:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Insufficient funds")
        
    current_user.wallet_balance -= amount
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return {"status": "success", "new_balance": current_user.wallet_balance, "item": item_name}
