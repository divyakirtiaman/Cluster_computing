"""
Pydantic Schemas for User authentication and profiles
"""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str
    preferred_genres: List[str] = Field(default_factory=list)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


class UserResponse(UserBase):
    id: str
    is_active: bool = True
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
