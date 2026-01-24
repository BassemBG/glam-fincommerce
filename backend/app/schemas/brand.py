from typing import List, Optional
from pydantic import BaseModel


class BrandPriceRange(BaseModel):
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: Optional[str] = None


class BrandStyleGroup(BaseModel):
    style_name: Optional[str] = None
    product_types: List[str] = []
    price_range: Optional[BrandPriceRange] = None
    aesthetic_keywords: List[str] = []
    target_demographic: Optional[str] = None
    sustainability_score: Optional[float] = None


class BrandProfile(BaseModel):
    brand_name: Optional[str] = None
    style_groups: List[BrandStyleGroup] = []
    num_styles: Optional[int] = None
    point_ids: Optional[List[str]] = None
    source: Optional[str] = None


class BrandIngestRequest(BaseModel):
    url: Optional[str] = None
    brand_name: Optional[str] = None


class BrandIngestResponse(BrandProfile):
    pass


class BrandListResponse(BaseModel):
    brands: List[BrandProfile]
