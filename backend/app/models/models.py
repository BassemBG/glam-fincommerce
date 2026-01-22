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
    created_by: str = Field(default="user", max_length=20)
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
