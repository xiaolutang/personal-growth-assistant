"""认证服务 - JWT 创建/验证、用户认证"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.user import DefaultDataClaimResult, User, UserResponse, TokenData

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """内存 Token 黑名单（基于 jti），协程安全"""

    CLEANUP_INTERVAL = 600  # 10 分钟

    def __init__(self):
        # _entries: dict[jti, exp_timestamp]
        self._entries: dict[str, int] = {}
        self._cleanup_task: asyncio.Task | None = None

    def add(self, jti: str, exp: int) -> None:
        """将 jti 加入黑名单"""
        self._entries[jti] = exp

    def is_blacklisted(self, jti: str) -> bool:
        """检查 jti 是否在黑名单中"""
        return jti in self._entries

    def cleanup_expired(self) -> int:
        """清理过期记录，返回清理数量"""
        now = int(time.time())
        expired_jtis = [jti for jti, exp in self._entries.items() if exp <= now]
        for jti in expired_jtis:
            del self._entries[jti]
        return len(expired_jtis)

    async def start_cleanup_task(self) -> None:
        """启动定时清理任务"""
        if self._cleanup_task is not None and not self._cleanup_task.cancelled():
            return
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self) -> None:
        """定时清理循环"""
        try:
            while True:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                removed = self.cleanup_expired()
                if removed > 0:
                    logger.info("TokenBlacklist cleanup: removed %d expired entries", removed)
        except asyncio.CancelledError:
            pass

    def stop_cleanup_task(self) -> None:
        """取消清理任务"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            self._cleanup_task = None


# 模块级单例
token_blacklist = TokenBlacklist()


def create_access_token(user_id: str) -> str:
    """创建 JWT access token"""
    settings = get_settings()
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET 环境变量未设置，应用无法启动")
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    """解码并验证 JWT token"""
    settings = get_settings()
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    return TokenData(sub=payload["sub"], exp=payload["exp"], jti=payload.get("jti"))


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

    # 检查黑名单
    if token_data.jti and token_blacklist.is_blacklisted(token_data.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已失效",
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
