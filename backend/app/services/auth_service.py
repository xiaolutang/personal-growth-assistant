"""认证服务 - JWT 创建/验证、用户认证"""

import jwt
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.user import DefaultDataClaimResult, User, UserResponse, TokenData


def create_access_token(user_id: str) -> str:
    """创建 JWT access token"""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    """解码并验证 JWT token"""
    settings = get_settings()
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    return TokenData(sub=payload["sub"], exp=payload["exp"])


def get_current_user_from_token(token: str, user_storage) -> User:
    """验证 token 并返回用户。失败抛 HTTPException"""
    try:
        token_data = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_storage.get_by_id(token_data.sub)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已停用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def auto_claim_default_user_data(user: User, user_storage, sync_service) -> DefaultDataClaimResult:
    """在单用户迁移场景下自动认领 `_default` 历史数据"""
    try:
        if user_storage.count_users() != 1:
            return DefaultDataClaimResult(claimed=False, reason="multiple_users")
    except Exception:
        return DefaultDataClaimResult(claimed=False, reason="user_count_unavailable")

    if sync_service.sqlite is not None and sync_service.sqlite.count_entries(user_id=user.id) > 0:
        return DefaultDataClaimResult(claimed=False, reason="target_already_has_entries")

    return sync_service.claim_default_data(user)
