"""
API endpoints for user-curated brand profiles.
Separate from brand ingestion - focused on profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_db
from app.models.models import ProfileBrand, Brand
from app.schemas.profile_brands import (
    ProfileBrandCreate,
    ProfileBrandUpdate,
    ProfileBrandResponse,
    ProfileBrandSearchResponse,
    ProfileBrandListResponse
)
from app.services.profile_brands_service import ProfileBrandsService
from app.api.brand_auth import get_current_brand

router = APIRouter(prefix="/profile-brands", tags=["profile-brands"])


@router.get("/me", response_model=ProfileBrandResponse)
async def get_current_brand_profile(
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """
    Get the authenticated brand's own profile.
    Returns pre-filled profile data for editing.
    """
    service = ProfileBrandsService(db)
    profile = service.get_or_create_brand_profile(
        brand_id=current_brand.id,
        brand_name=current_brand.brand_name,
        office_email=current_brand.office_email,
        brand_type=current_brand.brand_type,
        brand_website=current_brand.website_url,
    )
    return profile


@router.put("/me", response_model=ProfileBrandResponse)
async def update_current_brand_profile(
    payload: ProfileBrandUpdate,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """
    Update the authenticated brand's own profile.
    Only editable fields can be changed (name, bio, links, logo).
    Email and brand type are read-only.
    """
    service = ProfileBrandsService(db)
    service.get_or_create_brand_profile(
        brand_id=current_brand.id,
        brand_name=current_brand.brand_name,
        office_email=current_brand.office_email,
        brand_type=current_brand.brand_type,
        brand_website=current_brand.website_url,
    )
    updated_profile = service.update_brand_profile(
        brand_id=current_brand.id,
        brand_name=payload.brand_name,
        brand_website=payload.brand_website,
        instagram_link=payload.instagram_link,
        brand_logo_url=payload.brand_logo_url,
        description=payload.description,
    )
    if not updated_profile:
        raise HTTPException(status_code=404, detail="Brand profile not found.")
    return updated_profile


@router.post("/", response_model=ProfileBrandResponse)
async def create_or_update_profile_brand(
    payload: ProfileBrandCreate,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """
    Create or update a brand profile.
    If brand_name exists, updates the profile; otherwise creates a new one.
    [DEPRECATED] Use PUT /me for authenticated brand profile updates instead.
    """
    service = ProfileBrandsService(db)
    brand = service.upsert_profile_brand(
        brand_name=payload.brand_name,
        brand_website=payload.brand_website,
        instagram_link=payload.instagram_link,
        brand_logo_url=payload.brand_logo_url,
        description=payload.description,
    )
    return brand


@router.get("/{brand_id}", response_model=ProfileBrandResponse)
async def get_profile_brand_by_id(
    brand_id: str,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """Fetch a brand profile by ID."""
    service = ProfileBrandsService(db)
    brand = service.get_profile_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found.")
    return brand


@router.get("/name/{brand_name}", response_model=ProfileBrandResponse)
async def get_profile_brand_by_name(
    brand_name: str,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """Fetch a brand profile by exact brand name."""
    service = ProfileBrandsService(db)
    brand = service.get_profile_brand_by_name(brand_name)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found.")
    return brand


@router.get("/", response_model=ProfileBrandListResponse)
async def list_profile_brands(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """List all brand profiles with pagination."""
    service = ProfileBrandsService(db)
    brands = service.list_profile_brands(limit=limit, offset=offset)
    return {"brands": brands, "total": len(brands)}


@router.post("/search", response_model=ProfileBrandSearchResponse)
async def search_profile_brands(
    query: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """
    Search brand profiles by semantic similarity to query description.
    Uses cosine similarity over embeddings.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    service = ProfileBrandsService(db)
    brands = service.search_by_description(query.strip(), limit=limit)
    return {"brands": brands, "count": len(brands)}


@router.patch("/{brand_id}", response_model=ProfileBrandResponse)
async def update_profile_brand(
    brand_id: str,
    payload: ProfileBrandUpdate,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """Partially update a brand profile."""
    service = ProfileBrandsService(db)
    brand = service.get_profile_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found.")
    
    # Update only provided fields
    if payload.brand_website is not None:
        brand.brand_website = payload.brand_website
    if payload.instagram_link is not None:
        brand.instagram_link = payload.instagram_link
    if payload.brand_logo_url is not None:
        brand.brand_logo_url = payload.brand_logo_url
    if payload.description is not None:
        brand.description = payload.description
    
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.delete("/{brand_id}")
async def delete_profile_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """Delete a brand profile."""
    service = ProfileBrandsService(db)
    brand = service.get_profile_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found.")
    
    db.delete(brand)
    db.commit()
    return {"message": "Brand profile deleted successfully."}


@router.post("/search", response_model=ProfileBrandSearchResponse)
async def search_profile_brands(
    query: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """
    Search brand profiles by semantic similarity to query description.
    Uses cosine similarity over embeddings.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    service = ProfileBrandsService(db)
    brands = service.search_by_description(query.strip(), limit=limit)
    return {"brands": brands, "count": len(brands)}


@router.patch("/{brand_id}", response_model=ProfileBrandResponse)
async def update_profile_brand(
    brand_id: str,
    payload: ProfileBrandUpdate,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """Partially update a brand profile."""
    service = ProfileBrandsService(db)
    brand = service.get_profile_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found.")
    
    # Update only provided fields
    if payload.brand_website is not None:
        brand.brand_website = payload.brand_website
    if payload.instagram_link is not None:
        brand.instagram_link = payload.instagram_link
    if payload.brand_logo_url is not None:
        brand.brand_logo_url = payload.brand_logo_url
    if payload.description is not None:
        brand.description = payload.description
    
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.delete("/{brand_id}")
async def delete_profile_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_brand: Brand = Depends(get_current_brand)
):
    """Delete a brand profile."""
    service = ProfileBrandsService(db)
    brand = service.get_profile_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found.")
    
    db.delete(brand)
    db.commit()
    return {"message": "Brand profile deleted successfully."}
