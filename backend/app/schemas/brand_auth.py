from typing import Optional, Literal
from pydantic import BaseModel, EmailStr


BrandType = Literal["local", "international"]


class BrandCreate(BaseModel):
    brand_name: str
    office_email: EmailStr
    brand_type: BrandType
    password: str
    website_url: Optional[str] = None
    logo_url: Optional[str] = None


class BrandOut(BaseModel):
    id: str
    brand_name: str
    office_email: EmailStr
    brand_type: BrandType
    website_url: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True
