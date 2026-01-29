from fastapi import APIRouter, HTTPException, Depends

from app.schemas.profile_qdrant import ProfileIngestRequest, ProfileResponse, ProfileListResponse
from app.services.profile_qdrant_service import ProfileQdrantService
from app.api.brand_auth import get_current_brand
from app.models.models import Brand

router = APIRouter(prefix="/brands/profile", tags=["brands-profile"])
service = ProfileQdrantService()


@router.post("/ingest", response_model=ProfileResponse)
async def ingest_profile(payload: ProfileIngestRequest, current_brand: Brand = Depends(get_current_brand)):
    try:
        profile = service.upsert_profile(
            brand_name=payload.brand_name,
            brand_website=str(payload.brand_website) if payload.brand_website else None,
            instagram_link=str(payload.instagram_link) if payload.instagram_link else None,
            brand_logo_url=str(payload.brand_logo_url) if payload.brand_logo_url else None,
            description=payload.description,
        )
        return profile
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/list", response_model=ProfileListResponse)
async def list_profiles(current_brand: Brand = Depends(get_current_brand)):
    try:
        profiles = service.list_profiles()
        return {"profiles": profiles, "total": len(profiles)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{brand_name}", response_model=ProfileResponse)
async def get_profile(brand_name: str, current_brand: Brand = Depends(get_current_brand)):
    try:
        profile = service.get_profile(brand_name)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not profile:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return profile
