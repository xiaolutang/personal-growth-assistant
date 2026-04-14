"""用户与认证模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """用户基础模型"""

    username: str
    email: str


class User(UserBase):
    """完整用户模型 - 对应 users 表"""

    id: str
    hashed_password: str  # 仅内部使用，不返回给前端
    is_active: bool = True
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserResponse(BaseModel):
    """用户响应模型 - 不含 hashed_password"""

    id: str
    username: str
    email: str
    is_active: bool
    onboarding_completed: bool = False
    created_at: datetime


class UserCreate(BaseModel):
    """注册请求模型"""

    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """登录请求模型"""

    username: str
    password: str


class UserUpdate(BaseModel):
    """用户信息更新请求模型"""

    onboarding_completed: Optional[bool] = None


class Token(BaseModel):
    """Token 响应模型"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 604800  # 7天，单位秒
    user: UserResponse


class DefaultDataClaimResult(BaseModel):
    """`_default` 历史数据认领结果"""

    claimed: bool
    reason: str = ""
    sqlite_entries_claimed: int = 0
    markdown_files_copied: int = 0
    markdown_files_skipped: int = 0
    session_count_claimed: int = 0


class TokenData(BaseModel):
    """JWT payload 结构"""

    sub: str  # user_id
    exp: int  # 过期时间戳
