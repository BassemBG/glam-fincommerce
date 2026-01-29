"""Schemas for profile brands API."""

from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, HttpUrl


class ProfileBrandCreate(BaseModel):
    """Request schema for creating/updating a profile brand."""
    brand_name: str
    office_email: Optional[str] = None
    brand_type: Optional[str] = None
    brand_website: Optional[str] = None
    instagram_link: Optional[str] = None
    brand_logo_url: Optional[str] = None
    description: Optional[str] = None


class ProfileBrandUpdate(BaseModel):
    """Schema for partial updates to a profile brand."""
    brand_name: Optional[str] = None
    brand_website: Optional[str] = None
    instagram_link: Optional[str] = None
    brand_logo_url: Optional[str] = None
    description: Optional[str] = None


class ProfileBrandResponse(BaseModel):
    """Response schema for a profile brand."""
    id: str
    brand_id: str
    brand_name: str
    office_email: Optional[str] = None
    brand_type: Optional[str] = None
    brand_website: Optional[str] = None
    instagram_link: Optional[str] = None
    brand_logo_url: Optional[str] = None
    description: Optional[str] = None
    brand_metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileBrandSearchResponse(BaseModel):
    """Response schema for brand search results."""
    brands: list[ProfileBrandResponse]
    count: int


class ProfileBrandListResponse(BaseModel):
    """Response schema for listing profile brands."""
    brands: list[ProfileBrandResponse]
    total: int

