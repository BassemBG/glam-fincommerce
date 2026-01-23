from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging
import secrets
from app.db.session import get_db
from app.core import security
from app.core.config import settings
from app.models.models import User
from app.schemas.user import UserCreate, UserOut, Token
from app.services.zep_service import create_zep_user
from app.api.user import get_current_user
from app.services.pinterest_service import (
    PinterestOAuthService,
    PinterestPersonaService
)

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

@router.get("/pinterest/login")
def pinterest_login():
    """Redirect user to Pinterest for OAuth authorization"""
    # Generate a random state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Get the Pinterest OAuth URL
    oauth_url = PinterestOAuthService.get_oauth_url(state)
    
    logger.info(f"Redirecting user to Pinterest OAuth: {oauth_url}")
    
    # Return the OAuth URL so frontend can redirect
    return {
        "oauth_url": oauth_url,
        "state": state
    }

@router.get("/pinterest/status")
def pinterest_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return whether the current user has a saved Pinterest token."""
    from app.models.models import PinterestToken

    token = db.query(PinterestToken).filter(PinterestToken.user_id == current_user.id).first()
    return {
        "connected": bool(token),
        "synced_at": token.synced_at.isoformat() if token and token.synced_at else None,
    }

@router.get("/pinterest/callback")
def pinterest_callback(
    code: str,
    state: str = None,
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Handle Pinterest OAuth callback.
    
    Query params:
    - code: Authorization code from Pinterest
    - state: CSRF token
    - user_id: Current user's ID (passed from frontend)
    """
    try:
        logger.info(f"Pinterest callback received with code and state")
        
        # If user_id not provided, try to extract from JWT token
        if not user_id:
            logger.error("user_id not provided in callback. Frontend must pass user_id.")
            raise HTTPException(
                status_code=400,
                detail="Missing user_id. Please ensure you're logged in."
            )
        
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Exchange code for access token
        token_data = PinterestOAuthService.exchange_code_for_token(code)
        
        # Save token to database
        from app.models.models import PinterestToken
        PinterestOAuthService.save_token_to_db(user_id, token_data, db)
        
        logger.info(f"✓ Pinterest token saved for user {user_id}")
        
        # Now sync the Pinterest data
        persona_service = PinterestPersonaService(db)
        sync_result = persona_service.sync_user_pinterest_data(
            user_id=user_id,
            access_token=token_data.get("access_token")
        )
        
        logger.info(f"✓ Pinterest data synced for user {user_id}")
        
        # Return success response (don't redirect - let frontend handle it)
        return {
            "success": True,
            "message": "Pinterest connected and data synced",
            "boards_count": sync_result.get('boards_count', 0),
            "pins_count": sync_result.get('pins_count', 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pinterest callback error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Authorization failed: {str(e)}"
        )


@router.post("/pinterest/sync")
def sync_pinterest_data(user_id: str, db: Session = Depends(get_db)):
    """
    Sync Pinterest boards and pins for authenticated user.
    This should be called after user has authorized Pinterest.
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Pinterest token for this user
        from app.models.models import PinterestToken
        pinterest_token = db.query(PinterestToken).filter(
            PinterestToken.user_id == user_id
        ).first()
        
        if not pinterest_token:
            raise HTTPException(
                status_code=400,
                detail="Pinterest not connected. Please authorize first."
            )
        
        # Check if token is expired
        from datetime import datetime
        if pinterest_token.expires_at and pinterest_token.expires_at < datetime.utcnow():
            logger.warning(f"Pinterest token expired for user {user_id}")
            raise HTTPException(
                status_code=400,
                detail="Pinterest token expired. Please reconnect."
            )
        
        # Sync Pinterest data
        persona_service = PinterestPersonaService(db)
        result = persona_service.sync_user_pinterest_data(
            user_id=user_id,
            access_token=pinterest_token.access_token
        )
        
        logger.info(f"Successfully synced Pinterest data for user {user_id}")
        
        return {
            "success": True,
            "message": "Pinterest data synced successfully",
            "data": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing Pinterest data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Pinterest data: {str(e)}"
        )
