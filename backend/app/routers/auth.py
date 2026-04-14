"""认证路由 - 注册/登录/登出/me"""

import logging

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.models.user import (
    DefaultDataClaimResult,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token,
)
from app.infrastructure.storage.user_storage import UserStorage, verify_password
from app.services.auth_service import (
    auto_claim_default_user_data,
    create_access_token,
    get_current_user_from_token,
)
from app.routers.deps import get_current_user, get_storage, get_user_storage

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()
logger = logging.getLogger(__name__)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(
    user_data: UserCreate,
    user_storage: UserStorage = Depends(get_user_storage),
):
    """注册新用户"""
    try:
        user = user_storage.create_user(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        onboarding_completed=user.onboarding_completed,
        created_at=user.created_at,
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    user_storage: UserStorage = Depends(get_user_storage),
    storage=Depends(get_storage),
):
    """用户登录，返回 access token"""
    user = user_storage.get_by_username(credentials.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已停用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    claim_result = auto_claim_default_user_data(
        user,
        user_storage=user_storage,
        sync_service=storage,
    )
    logger.info(
        "Auto-claim result for user %s: claimed=%s reason=%s sqlite_entries_claimed=%s markdown_files_copied=%s markdown_files_skipped=%s session_count_claimed=%s",
        user.id,
        claim_result.claimed,
        claim_result.reason,
        claim_result.sqlite_entries_claimed,
        claim_result.markdown_files_copied,
        claim_result.markdown_files_skipped,
        claim_result.session_count_claimed,
    )

    access_token = create_access_token(user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_DAYS * 86400,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            onboarding_completed=user.onboarding_completed,
            created_at=user.created_at,
        ),
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """登出（前端清除 token）"""
    return {"message": "logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_storage: UserStorage = Depends(get_user_storage),
):
    """获取当前用户信息"""
    user = get_current_user_from_token(credentials.credentials, user_storage)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        onboarding_completed=user.onboarding_completed,
        created_at=user.created_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    update_data: UserUpdate,
    user=Depends(get_current_user),
    user_storage: UserStorage = Depends(get_user_storage),
):
    """更新当前用户信息（onboarding_completed 等）"""
    if update_data.onboarding_completed is not None:
        user_storage.update_onboarding_completed(
            user.id, update_data.onboarding_completed
        )
        user = user_storage.get_by_id(user.id)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        onboarding_completed=user.onboarding_completed,
        created_at=user.created_at,
    )


@router.post("/claim-default-data", response_model=DefaultDataClaimResult)
async def claim_default_data(
    user=Depends(get_current_user),
    storage=Depends(get_storage),
):
    """显式将 `_default` 历史数据认领到当前用户"""
    return storage.claim_default_data(user)
