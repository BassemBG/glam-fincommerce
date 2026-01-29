from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy import String, Text

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = None
    full_body_image: Optional[str] = None
    style_profile: Dict = Field(default={}, sa_column=Column(JSON))
    
    # Zep Cloud integration
    zep_thread_id: Optional[str] = None  # Thread ID for storing onboarding data in Zep
    
    # Onboarding profile fields
    gender: Optional[str] = None  # "male", "female", "neutral", "other"
    age: Optional[int] = None
    education: Optional[str] = None  # Where they study
    country: Optional[str] = None  # User's country for localized search
    daily_style: Optional[str] = None  # e.g., "modern chic", "sport", "classic"
    color_preferences: List[str] = Field(default=[], sa_column=Column(JSON))  # ["black/white/grey", "bright colors", ...]
    fit_preference: Optional[str] = None  # "tight", "regular", "loose", "depends"
    price_comfort: Optional[str] = None  # "low", "medium", "high", "depends"
    buying_priorities: List[str] = Field(default=[], sa_column=Column(JSON))  # ["comfort", "style", "price", ...]
    clothing_description: Optional[str] = None  # Description of their clothes
    styled_combinations: Optional[str] = None  # Description of past styled combinations
    onboarding_completed: bool = Field(default=False)
    
    # Financial constraints for AI Stylist
    budget_limit: Optional[float] = Field(default=None)
    min_budget: Optional[float] = Field(default=None)
    max_budget: Optional[float] = Field(default=None)
    currency: str = Field(default="TND", max_length=10)
    wallet_balance: float = Field(default=0.0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Brand(SQLModel, table=True):
    __tablename__ = "brands"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    brand_name: str = Field(index=True, unique=True, nullable=False, max_length=255)
    office_email: str = Field(index=True, unique=True, nullable=False, max_length=255)
    brand_type: str = Field(nullable=False, max_length=50)  # local | international
    hashed_password: str = Field(nullable=False)
    website_url: Optional[str] = Field(default=None, max_length=500)
    logo_url: Optional[str] = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ClothingItem(SQLModel, table=True):
    __tablename__ = "clothing_items"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    category: str = Field(max_length=50)
    sub_category: Optional[str] = Field(default=None, max_length=50)
    body_region: str = Field(default="top", max_length=50)
    image_url: str
    mask_url: Optional[str] = None
    metadata_json: Dict = Field(default={}, sa_column=Column("metadata", JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Outfit(SQLModel, table=True):
    __tablename__ = "outfits"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: Optional[str] = Field(default=None, max_length=255)
    occasion: Optional[str] = Field(default=None, max_length=100)
    vibe: Optional[str] = Field(default=None, max_length=100)
    items: str = Field(default="[]", sa_column=Column(Text))  # JSON string of item IDs
    score: float = Field(default=0.0)
    reasoning: Optional[str] = None
    tryon_image_url: Optional[str] = None
    description: Optional[str] = None
    style_tags: Optional[str] = Field(default="[]", sa_column=Column(Text))  # JSON string of tags
    created_by: str = Field(default="user", max_length=20)
    # New fields added below
    qdrant_vector_id: Optional[str] = Field(default=None, index=True)
    qdrant_payload: Dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ClothingIngestionHistory(SQLModel, table=True):
    """Tracks all clothing item ingestions with full analysis data"""
    __tablename__ = "clothing_ingestion_history"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    clothing_item_id: Optional[str] = Field(foreign_key="clothing_items.id", default=None)
    
    # Clothing Analysis
    category: str = Field(max_length=50)
    sub_category: str = Field(max_length=100)
    body_region: str = Field(max_length=50)
    colors: List[str] = Field(default=[], sa_column=Column(JSON))
    material: str = Field(max_length=100)
    vibe: str = Field(max_length=50)
    season: str = Field(max_length=50)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    styling_tips: Optional[str] = Field(default=None, sa_column=Column(Text))
    estimated_brand_range: str = Field(max_length=50, default="unknown")
    care_instructions: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Body Analysis (if provided)
    gender_presentation: Optional[str] = Field(default=None, max_length=50)
    body_type: Optional[str] = Field(default=None, max_length=50)
    skin_tone: Optional[str] = Field(default=None, max_length=50)
    estimated_height: Optional[str] = Field(default=None, max_length=50)
    body_confidence: Optional[float] = Field(default=None)
    
    # Brand Info
    detected_brand: str = Field(max_length=100, default="Unknown")
    brand_confidence: float = Field(default=0.0)
    brand_indicators: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Price Info
    price: Optional[float] = Field(default=None)
    price_range: str = Field(max_length=50, default="unknown")
    typical_brand_price: Optional[float] = Field(default=None)
    stores: List[str] = Field(default=[], sa_column=Column(JSON))
    purchase_date: Optional[datetime] = Field(default=None)
    
    # Embeddings & Qdrant
    embeddings: Optional[List[float]] = Field(default=None, sa_column=Column(JSON))
    qdrant_point_id: Optional[str] = Field(default=None, max_length=255)
    
    # Image Data
    image_url: str
    full_body_image_url: Optional[str] = Field(default=None)
    
    # Status & Timestamps
    status: str = Field(max_length=50, default="completed")  # pending, processing, completed, failed
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
class PinterestPin(SQLModel, table=True):
    """Stores Pinterest pins that have been filtered and indexed"""
    __tablename__ = "pinterest_pins"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    pin_id: str = Field(index=True)  # Pinterest pin ID
    board_name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    original_url: str  # Original Pinterest URL
    stored_url: str  # Our storage (S3/local) URL
    colors: List[str] = Field(default=[], sa_column=Column(JSON))
    style_tags: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Qdrant integration
    qdrant_point_id: Optional[str] = Field(default=None, index=True)
    qdrant_vector: Optional[List[float]] = Field(default=None, sa_column=Column(JSON))
    
    # Metadata
    metadata_json: Dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PinterestToken(SQLModel, table=True):
    __tablename__ = "pinterest_tokens"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True, unique=True)
    access_token: str = Field(nullable=False)
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
class ProfileBrand(SQLModel, table=True):
    __tablename__ = "profile_brands"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    brand_id: str = Field(foreign_key="brands.id", index=True, unique=True, nullable=False)
    brand_name: str = Field(index=True, nullable=False, max_length=255)
    office_email: Optional[str] = Field(default=None, max_length=255)
    brand_type: Optional[str] = Field(default=None, max_length=50)  # local | international (read-only)
    brand_website: Optional[str] = Field(default=None, max_length=500)
    instagram_link: Optional[str] = Field(default=None, max_length=500)
    brand_logo_url: Optional[str] = None
    description: Optional[str] = None  # Bio/short description
    brand_metadata: Dict = Field(default={}, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)