from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging
from app.db.session import get_db
from app.core import security
from app.core.config import settings
from app.models.models import User
from app.schemas.user import UserCreate, UserOut, Token
from app.services.zep_service import create_zep_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/signup", response_model=Token)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Signup request: email={user_in.email}, full_name={user_in.full_name}")
    
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"User created: id={db_user.id}, email={db_user.email}")
    
    # Create user in Zep Cloud for profiling and get thread_id
    zep_user, thread_id = create_zep_user(
        user_id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name
    )
    
    # Store thread_id if created successfully
    if thread_id:
        db_user.zep_thread_id = thread_id
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Thread created for user {db_user.id}: {thread_id}")
    
    # Return access token for automatic login
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            db_user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
