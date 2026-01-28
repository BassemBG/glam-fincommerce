from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl

class ProfileIngestRequest(BaseModel):
    brand_name: str
    brand_website: Optional[HttpUrl] = None
    instagram_link: Optional[HttpUrl] = None
    brand_logo_url: Optional[HttpUrl] = None
    description: Optional[str] = None


class ProfileResponse(BaseModel):
    id: str
    brand_name: str
    brand_website: Optional[str] = None
    instagram_link: Optional[str] = None
    brand_logo_url: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProfileListResponse(BaseModel):
    profiles: List[ProfileResponse]
    total: int
