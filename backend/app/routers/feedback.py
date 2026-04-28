"""用户反馈 API 路由

支持 general 和 agent 两种反馈类型。
- general: 通用反馈（原有逻辑不变）
- agent: Agent 回复反馈，支持 message_id / reason / detail

负面反馈自动创建 Issue（通过 log-service）。
Agent 负面反馈可导出到 Golden Dataset 的 bad case 目录。
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from typing_extensions import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints, model_validator

from app.core.config import get_settings
from app.routers.deps import get_current_user, get_storage
from app.models.user import User
from log_service_sdk import report_issue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

Severity = Literal["low", "medium", "high", "critical"]
FeedbackType = Literal["general", "agent"]
NonEmptyTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# 远程状态 → 本地状态映射
_REMOTE_STATUS_MAP: dict[str, str] = {
    "pending": "reported",
    "in_progress": "in_progress",
    "resolved": "resolved",
}

# 负面 reason 列表 —— 匹配这些 reason 的反馈视为 👎 负面
_NEGATIVE_REASONS: frozenset[str] = frozenset({
    "理解错了",
    "操作不正确",
    "信息不准确",
    "不相关",
    "不完整",
    "格式错误",
    "other_negative",
})


# ── Request / Response Models ──


class FeedbackRequest(BaseModel):
    """前端反馈请求"""

    title: NonEmptyTitle
    description: str | None = None
    severity: Severity = "medium"
    feedback_type: FeedbackType = "general"
    message_id: str | None = None
    reason: str | None = None
    detail: str | None = None

    @model_validator(mode="after")
    def _validate_agent_fields(self) -> "FeedbackRequest":
        """Agent 反馈必须提供 message_id"""
        if self.feedback_type == "agent" and not self.message_id:
            raise ValueError("agent 反馈必须提供 message_id")
        return self


class FeedbackResponse(BaseModel):
    """反馈提交响应"""

    success: bool
    feedback: dict[str, Any]


class FeedbackItem(BaseModel):
    """单条反馈记录"""

    id: int
    user_id: str
    title: str
    description: str | None = None
    severity: str = "medium"
    log_service_issue_id: int | None = None
    status: str = "pending"
    created_at: str
    updated_at: str | None = None
    feedback_type: str = "general"
    message_id: str | None = None
    reason: str | None = None
    detail: str | None = None


class FeedbackListResponse(BaseModel):
    """反馈列表响应"""

    items: list[FeedbackItem]
    total: int


class FeedbackSyncResponse(BaseModel):
    """反馈同步响应"""

    synced_count: int
    updated_count: int
    items: list[FeedbackItem]
    total: int


# ── Langfuse trace 标记（可选）──


def _langfuse_score_trace(message_id: str, score: float, reason: str | None = None) -> None:
    """尝试对 Langfuse 中的对应 trace 打分。

    仅在 LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY 均已设置时启用。
    如果 langfuse 包未安装或配置不完整，静默跳过。
    """
    try:
        from langfuse import Langfuse

        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
        if not public_key or not secret_key:
            return

        host = os.environ.get("LANGFUSE_HOST", "http://localhost:3010").strip()
        langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

        # message_id 作为 trace_id 来标记评分
        langfuse.score(
            trace_id=message_id,
            name="user_feedback",
            value=score,
            comment=reason,
        )
        logger.info("Langfuse trace %s 已标记评分 %.1f", message_id, score)
    except ImportError:
        logger.debug("langfuse 包未安装，跳过 trace 标记")
    except Exception:
        logger.warning("Langfuse trace 标记失败", exc_info=True)


# ── Bad Case 导出 ──


def export_to_golden_dataset(feedback: dict[str, Any]) -> Path | None:
    """将负面 Agent 反馈导出为 Golden Dataset 的 bad case。

    输出到 {DATA_DIR}/eval_transcripts/bad_cases/{message_id}_{timestamp}.json

    Returns:
        导出文件路径，如果不符合导出条件则返回 None。
    """
    # 仅导出 agent 类型的负面反馈
    if feedback.get("feedback_type") != "agent":
        return None
    if not feedback.get("message_id"):
        return None

    reason = feedback.get("reason", "")
    if reason not in _NEGATIVE_REASONS:
        return None

    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)
    bad_cases_dir = data_dir / "eval_transcripts" / "bad_cases"
    bad_cases_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"{feedback['message_id']}_{ts}.json"
    filepath = bad_cases_dir / filename

    export_data = {
        "feedback_id": feedback["id"],
        "message_id": feedback["message_id"],
        "reason": reason,
        "detail": feedback.get("detail"),
        "title": feedback["title"],
        "description": feedback.get("description"),
        "user_id": feedback["user_id"],
        "created_at": feedback.get("created_at"),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    filepath.write_text(json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Bad case 已导出到 %s", filepath)
    return filepath


# ── 后台任务 ──


async def _report_to_log_service(
    feedback_id: int,
    title: str,
    description: str | None,
    severity: str,
) -> None:
    """后台任务：异步上报到 log-service"""
    settings = get_settings()
    storage = get_storage()

    try:
        issue = await asyncio.to_thread(
            report_issue,
            settings.LOG_SERVICE_URL,
            title,
            "personal-growth-assistant",
            description=description,
            severity=severity,
            component="frontend",
        )
        remote_id = issue.get("id")
        if storage and storage.sqlite:
            storage.sqlite.update_feedback_status(
                feedback_id, "reported", log_service_issue_id=remote_id
            )
        logger.info("反馈 %d 已上报到 log-service，远程 ID: %s", feedback_id, remote_id)
    except Exception:
        logger.warning("反馈 %d 上报 log-service 失败，保留 pending 状态", feedback_id, exc_info=True)


async def _auto_create_issue_for_negative(
    feedback_id: int,
    feedback: dict[str, Any],
) -> None:
    """后台任务：负面反馈自动创建 Issue。

    条件：feedback_type == "agent" 且 reason 属于负面列表。
    """
    reason = feedback.get("reason", "")
    if reason not in _NEGATIVE_REASONS:
        return

    settings = get_settings()
    storage = get_storage()

    title = f"[Agent Bad Case] {reason} - {feedback.get('title', '')}"
    description_parts = [
        f"反馈 ID: {feedback_id}",
        f"Message ID: {feedback.get('message_id', 'N/A')}",
        f"Reason: {reason}",
        f"Detail: {feedback.get('detail') or 'N/A'}",
        f"User: {feedback.get('user_id', 'N/A')}",
        f"Created: {feedback.get('created_at', 'N/A')}",
    ]
    description = "\n".join(description_parts)

    try:
        issue = await asyncio.to_thread(
            report_issue,
            settings.LOG_SERVICE_URL,
            title,
            "personal-growth-assistant",
            description=description,
            severity="medium",
            component="backend",
        )
        remote_id = issue.get("id")
        if storage and storage.sqlite:
            storage.sqlite.update_feedback_status(
                feedback_id, "reported", log_service_issue_id=remote_id
            )
        logger.info("负面反馈 %d 自动创建 Issue，远程 ID: %s", feedback_id, remote_id)
    except Exception:
        logger.warning("负面反馈 %d 自动创建 Issue 失败", feedback_id, exc_info=True)


# ── API Endpoints ──


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
) -> FeedbackResponse:
    """提交反馈：本地先写入，后台异步上报 log-service。

    支持两种反馈类型：
    - general: 通用反馈（原有逻辑）
    - agent: Agent 回复反馈（需 message_id）

    Agent 负面反馈会：
    1. 自动创建 Issue（medium severity）
    2. 标记 Langfuse trace 评分（可选）
    3. 导出到 Golden Dataset bad case 目录
    """
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    # 1. 本地写入
    feedback = storage.sqlite.create_feedback(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        feedback_type=payload.feedback_type,
        message_id=payload.message_id,
        reason=payload.reason,
        detail=payload.detail,
    )

    if payload.feedback_type == "agent":
        # 2a. Agent 反馈：Langfuse trace 标记（后台）
        if payload.message_id:
            reason = payload.reason or ""
            score = 0.0 if reason in _NEGATIVE_REASONS else 1.0
            asyncio.get_event_loop().run_in_executor(
                None, _langfuse_score_trace, payload.message_id, score, reason
            )

        # 2b. 负面反馈自动创建 Issue + 导出 bad case
        reason = payload.reason or ""
        if reason in _NEGATIVE_REASONS:
            asyncio.create_task(
                _auto_create_issue_for_negative(
                    feedback_id=feedback["id"],
                    feedback=feedback,
                )
            )
            # 导出 bad case（同步，快速操作）
            try:
                export_to_golden_dataset(feedback)
            except Exception:
                logger.warning("导出 bad case 失败", exc_info=True)
    else:
        # 2c. 通用反馈：后台异步上报 log-service（原有逻辑）
        asyncio.create_task(
            _report_to_log_service(
                feedback_id=feedback["id"],
                title=payload.title,
                description=payload.description,
                severity=payload.severity,
            )
        )

    return FeedbackResponse(success=True, feedback=feedback)


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedbacks(
    user: User = Depends(get_current_user),
) -> FeedbackListResponse:
    """获取当前用户的反馈列表"""
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    items = storage.sqlite.list_feedbacks_by_user(user.id)
    return FeedbackListResponse(
        items=[FeedbackItem(**item) for item in items],
        total=len(items),
    )


@router.get("/feedback/{feedback_id}", response_model=FeedbackItem)
async def get_feedback(
    feedback_id: int,
    user: User = Depends(get_current_user),
) -> FeedbackItem:
    """获取单条反馈详情"""
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    feedback = storage.sqlite.get_feedback_by_id(feedback_id, user.id)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    return FeedbackItem(**feedback)


@router.post("/feedback/sync", response_model=FeedbackSyncResponse)
async def sync_feedbacks(
    user: User = Depends(get_current_user),
) -> FeedbackSyncResponse:
    """同步反馈状态：从 log-service 拉取远程 issue 状态并更新本地"""
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    # 获取有远程 issue_id 的反馈
    feedbacks = storage.sqlite.list_feedbacks_with_issue_id(user.id)
    if not feedbacks:
        # 无需同步，返回完整列表
        all_items = storage.sqlite.list_feedbacks_by_user(user.id)
        return FeedbackSyncResponse(
            synced_count=0,
            updated_count=0,
            items=[FeedbackItem(**item) for item in all_items],
            total=len(all_items),
        )

    settings = get_settings()
    synced_count = 0
    updated_count = 0

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        for fb in feedbacks:
            remote_id = fb["log_service_issue_id"]
            try:
                resp = await http_client.get(
                    f"{settings.LOG_SERVICE_URL}/api/issues/{remote_id}"
                )
                if resp.status_code != 200:
                    # 404/超时/其他错误：该条 status 和 updated_at 均不变
                    continue

                remote_data = resp.json()
                remote_status = remote_data.get("status", "")
                local_status = _REMOTE_STATUS_MAP.get(remote_status)

                if local_status is None:
                    # 未知 status：保持原状态不更新
                    continue

                synced_count += 1

                if fb["status"] != local_status:
                    # 状态实际变更 → 更新 status + updated_at
                    updated_at = datetime.now(timezone.utc).isoformat()
                    storage.sqlite.sync_feedback_status(fb["id"], local_status, updated_at)
                    updated_count += 1
                elif fb.get("updated_at") is None:
                    # 首次同步（updated_at 为 null）→ 写入 updated_at
                    updated_at = datetime.now(timezone.utc).isoformat()
                    storage.sqlite.sync_feedback_status(fb["id"], local_status, updated_at)
                # else: 状态未变更且非首次 → 不更新
            except (httpx.TimeoutException, httpx.HTTPError):
                # 单条超时/网络错误：跳过，其他继续
                continue
            except Exception:
                logger.warning("同步反馈 %d 远程 issue %d 异常", fb["id"], remote_id, exc_info=True)
                continue

    # 返回同步后的完整列表
    all_items = storage.sqlite.list_feedbacks_by_user(user.id)
    return FeedbackSyncResponse(
        synced_count=synced_count,
        updated_count=updated_count,
        items=[FeedbackItem(**item) for item in all_items],
        total=len(all_items),
    )
