from typing import Optional, List
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOnboarding(BaseModel):
    gender: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None
    country: Optional[str] = None
    daily_style: Optional[str] = None
    color_preferences: List[str] = []
    fit_preference: Optional[str] = None
    price_comfort: Optional[str] = None
    buying_priorities: List[str] = []
    clothing_description: Optional[str] = None
    styled_combinations: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None

class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None
    country: Optional[str] = None
    daily_style: Optional[str] = None
    color_preferences: List[str] = []
    fit_preference: Optional[str] = None
    price_comfort: Optional[str] = None
    buying_priorities: List[str] = []
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    onboarding_completed: bool = False

    class Config:
        from_attributes = True
