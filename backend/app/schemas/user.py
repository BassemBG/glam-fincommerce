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
    age: Optional[int] = None
    education: Optional[str] = None
    daily_style: Optional[str] = None
    color_preferences: List[str] = []
    fit_preference: Optional[str] = None
    price_comfort: Optional[str] = None
    buying_priorities: List[str] = []
    clothing_description: Optional[str] = None
    styled_combinations: Optional[str] = None

class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None
    daily_style: Optional[str] = None
    color_preferences: List[str] = []
    fit_preference: Optional[str] = None
    price_comfort: Optional[str] = None
    buying_priorities: List[str] = []
    onboarding_completed: bool = False

    class Config:
        from_attributes = True
