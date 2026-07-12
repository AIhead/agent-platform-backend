from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class RegisterRequest(BaseModel):
    account: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    account: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: str
    account: str
    nickname: str
    avatar: str = ""
    isMember: bool = False
    memberExpireAt: Optional[int] = None

    class Config:
        from_attributes = True
