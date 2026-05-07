from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginForm(BaseModel):
    username: str
    password: str


class URLCreate(BaseModel):
    original_url: str


class URLOut(BaseModel):
    id: int
    original_url: str
    short_code: str
    clicks: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
