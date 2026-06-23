"""用户相关 Pydantic Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """用户注册请求。"""
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    display_name: Optional[str] = Field(None, max_length=128, description="显示名")


class UserLogin(BaseModel):
    """用户登录请求。"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应。"""
    id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: str = "member"
    is_active: bool = True
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """令牌响应。"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
