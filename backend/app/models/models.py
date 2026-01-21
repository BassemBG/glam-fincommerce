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
    age: Optional[int] = None
    education: Optional[str] = None  # Where they study
    daily_style: Optional[str] = None  # e.g., "modern chic", "sport", "classic"
    color_preferences: List[str] = Field(default=[], sa_column=Column(JSON))  # ["black/white/grey", "bright colors", ...]
    fit_preference: Optional[str] = None  # "tight", "regular", "loose", "depends"
    price_comfort: Optional[str] = None  # "low", "medium", "high", "depends"
    buying_priorities: List[str] = Field(default=[], sa_column=Column(JSON))  # ["comfort", "style", "price", ...]
    clothing_description: Optional[str] = None  # Description of their clothes
    styled_combinations: Optional[str] = None  # Description of past styled combinations
    onboarding_completed: bool = Field(default=False)
    
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
