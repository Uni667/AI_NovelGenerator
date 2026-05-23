"""
Invocation Logger Service — 处理大模型调用日志与状态。
"""

import datetime
import logging
import uuid
from dataclasses import dataclass

from backend.app.database import get_db

logger = logging.getLogger(__name__)


def mark_used(user_id: str, cred_id: str = "", profile_id: str = "") -> None:
    """标记 API 和模型最近使用时间。"""
    now = datetime.datetime.now().isoformat()
    logger.info("ModelRuntime mark_used [user=%s cred=%s profile=%s]", user_id, cred_id, profile_id)
    with get_db() as conn:
        if cred_id:
            conn.execute(
                "UPDATE api_credential SET last_used_at=?, updated_at=? WHERE id=? AND user_id=?",
                (now, now, cred_id, user_id),
            )
        if profile_id:
            conn.execute(
                "UPDATE model_profile SET last_used_at=?, updated_at=? WHERE id=? AND user_id=?",
                (now, now, profile_id, user_id),
            )


def update_health(profile_id: str, status: str, message: str = "") -> None:
    """更新模型配置的健康状态。"""
    now = datetime.datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE model_profile SET health_status=?, last_error=?, updated_at=? WHERE id=?",
            (status, message[:500], now, profile_id),
        )


def log_invocation(
    user_id: str,
    cfg: any,  # RuntimeConfig
    input_chars: int = 0,
    output_chars: int = 0,
    latency_ms: int = 0,
    success: bool = True,
    error_code: str = "",
    error_message: str = "",
    project_id: str = "",
    task_id: str = "",
) -> None:
    """记录模型调用日志。"""
    log_id = uuid.uuid4().hex
    now = datetime.datetime.now().isoformat()
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO model_invocation_log
                   (id, user_id, project_id, task_id, api_credential_id,
                    model_profile_id, provider, model, purpose,
                    input_chars, output_chars, latency_ms,
                    success, error_code, error_message, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    log_id,
                    user_id,
                    project_id or "",
                    task_id or "",
                    getattr(cfg, "api_credential_id", ""),
                    getattr(cfg, "model_profile_id", ""),
                    getattr(cfg, "provider", ""),
                    getattr(cfg, "model", ""),
                    getattr(cfg, "purpose", ""),
                    input_chars,
                    output_chars,
                    latency_ms,
                    1 if success else 0,
                    error_code,
                    error_message,
                    now,
                ),
            )
    except Exception:
        logger.warning("Failed to log invocation", exc_info=True)
