from datetime import timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.db.session import get_db
from app.core import security
from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.models import Brand
from app.schemas.brand_auth import BrandCreate, BrandOut
from app.schemas.user import Token
from app.services.profile_brands_service import ProfileBrandsService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/signup", response_model=Token)
def brand_signup(brand_in: BrandCreate, db: Session = Depends(get_db)):
    existing = db.query(Brand).filter(Brand.office_email == brand_in.office_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A brand with this email already exists")

    existing_name = db.query(Brand).filter(Brand.brand_name == brand_in.brand_name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="A brand with this name already exists")

    hashed_password = security.get_password_hash(brand_in.password)

    brand = Brand(
        brand_name=brand_in.brand_name,
        office_email=brand_in.office_email,
        brand_type=brand_in.brand_type,
        hashed_password=hashed_password,
        website_url=brand_in.website_url,
        logo_url=brand_in.logo_url,
    )

    db.add(brand)
    db.commit()
    db.refresh(brand)

    # Auto-create brand profile with sign-up data
    profile_service = ProfileBrandsService(db)
    try:
        profile_service.get_or_create_brand_profile(
            brand_id=brand.id,
            brand_name=brand.brand_name,
            office_email=brand.office_email,
            brand_type=brand.brand_type,
            brand_website=brand.website_url,
            description=None  # No description at signup time
        )
    except Exception as e:
        logger.warning(f"Failed to auto-create profile for brand {brand.id}: {e}")
        # Don't fail signup if profile creation fails

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            brand.id, expires_delta=access_token_expires, role="brand"
        ),
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token)
def brand_login(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    brand = db.query(Brand).filter(Brand.office_email == form_data.username).first()
    if not brand:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    try:
        if not security.verify_password(form_data.password, brand.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            brand.id, expires_delta=access_token_expires, role="brand"
        ),
        "token_type": "bearer",
    }


def get_current_brand(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> Brand:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        brand_id: str = payload.get("sub")
        role: str | None = payload.get("role")
        if not brand_id or role != "brand":
            raise HTTPException(status_code=403, detail="Brand credentials required")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=401, detail="Brand not found")
    return brand


@router.get("/me", response_model=BrandOut)
def brand_me(current_brand: Brand = Depends(get_current_brand)):
    return current_brand
