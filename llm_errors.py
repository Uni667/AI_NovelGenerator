from __future__ import annotations

from dataclasses import asdict, dataclass
from json import JSONDecodeError
from typing import Any


@dataclass
class LLMErrorInfo:
    code: str
    category: str
    user_message: str
    detail: str
    retryable: bool
    status_code: int | None = None
    exception_type: str = ""
    provider: str = ""
    model_name: str = ""
    base_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LLMInvocationError(RuntimeError):
    def __init__(self, info: LLMErrorInfo, operation_name: str = "", step: str | None = None):
        self.info = info
        self.operation_name = operation_name
        self.step = step
        prefix = f"{operation_name}失败：" if operation_name else ""
        super().__init__(f"{prefix}{info.user_message}")

    def to_payload(self) -> dict[str, Any]:
        payload = self.info.to_dict()
        payload["message"] = str(self)
        if self.operation_name:
            payload["operation"] = self.operation_name
        if self.step:
            payload["step"] = self.step
        return payload


def coerce_error_info(value: Any) -> LLMErrorInfo | None:
    if value is None:
        return None
    if isinstance(value, LLMErrorInfo):
        return value
    if isinstance(value, dict):
        return LLMErrorInfo(
            code=str(value.get("code", "unknown_error")),
            category=str(value.get("category", "unknown")),
            user_message=str(value.get("user_message", "模型调用失败，请稍后重试。")),
            detail=str(value.get("detail", value.get("message", "未知错误"))),
            retryable=bool(value.get("retryable", False)),
            status_code=value.get("status_code"),
            exception_type=str(value.get("exception_type", "")),
            provider=str(value.get("provider", "")),
            model_name=str(value.get("model_name", "")),
            base_url=str(value.get("base_url", "")),
        )
    return None


def build_empty_response_error(
    *,
    provider: str = "",
    model_name: str = "",
    base_url: str = "",
) -> LLMErrorInfo:
    return LLMErrorInfo(
        code="empty_response",
        category="parse_failure",
        user_message="模型没有返回有效内容，请稍后重试；如果持续出现，请检查模型配置或切换模型。",
        detail="LLM returned empty content after cleanup.",
        retryable=True,
        exception_type="EmptyResponse",
        provider=provider,
        model_name=model_name,
        base_url=_sanitize_base_url(base_url),
    )


def classify_llm_exception(
    exc: BaseException,
    *,
    provider: str = "",
    model_name: str = "",
    base_url: str = "",
) -> LLMErrorInfo:
    exc_type = exc.__class__.__name__
    detail = _safe_exception_detail(exc)
    lowered = detail.lower()
    status_code = _extract_status_code(exc)

    if isinstance(exc, JSONDecodeError) or any(token in exc_type.lower() for token in ("decode", "validation")):
        return _build_info(
            code="parse_failure",
            category="parse_failure",
            user_message="模型返回内容解析失败，请稍后重试；如果持续出现，请检查模型输出格式。",
            detail=detail,
            retryable=False,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if isinstance(exc, ValueError) and any(token in lowered for token in ("api key", "base url", "model", "interface_format", "接口", "配置")):
        return _build_info(
            code="config_missing",
            category="config_missing",
            user_message="模型配置缺失或无效，请检查模型名称、Base URL 和 API Key。",
            detail=detail,
            retryable=False,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if status_code in {401, 403} or "authentication" in exc_type.lower() or "unauthorized" in lowered or "invalid api key" in lowered:
        return _build_info(
            code="auth_failed",
            category="auth_failed",
            user_message="模型服务认证失败，请检查 API Key、账号权限或服务商控制台设置。",
            detail=detail,
            retryable=False,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if status_code == 429 or "rate limit" in lowered:
        return _build_info(
            code="rate_limited",
            category="provider_4xx",
            user_message="模型服务限流了，请稍后重试，或降低并发后再试。",
            detail=detail,
            retryable=True,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if _looks_like_timeout(exc_type, lowered):
        return _build_info(
            code="timeout",
            category="timeout",
            user_message="模型服务响应超时，请稍后重试，或适当调大超时时间。",
            detail=detail,
            retryable=True,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if status_code is not None and 400 <= status_code < 500:
        return _build_info(
            code="provider_4xx",
            category="provider_4xx",
            user_message="模型服务拒绝了这次请求，请检查模型名称、请求参数或账号配额。",
            detail=detail,
            retryable=status_code in {408, 409, 429},
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if status_code is not None and status_code >= 500:
        return _build_info(
            code="provider_5xx",
            category="provider_5xx",
            user_message="模型服务暂时异常，请稍后重试。",
            detail=detail,
            retryable=True,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if _looks_like_stream_error(exc_type, lowered):
        return _build_info(
            code="stream_interrupted",
            category="stream_interrupted",
            user_message="模型服务连接在传输过程中被中断，请稍后重试。",
            detail=detail,
            retryable=True,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    if _looks_like_network_error(exc_type, lowered):
        return _build_info(
            code="network_error",
            category="network_error",
            user_message="无法连接到模型服务，请检查 Base URL、网络连通性或代理设置。",
            detail=detail,
            retryable=True,
            status_code=status_code,
            exc_type=exc_type,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
        )

    return _build_info(
        code="provider_error",
        category="provider_error",
        user_message="模型服务调用失败，请查看后端日志中的详细错误。",
        detail=detail,
        retryable=False,
        status_code=status_code,
        exc_type=exc_type,
        provider=provider,
        model_name=model_name,
        base_url=base_url,
    )


def _build_info(
    *,
    code: str,
    category: str,
    user_message: str,
    detail: str,
    retryable: bool,
    status_code: int | None,
    exc_type: str,
    provider: str,
    model_name: str,
    base_url: str,
) -> LLMErrorInfo:
    return LLMErrorInfo(
        code=code,
        category=category,
        user_message=user_message,
        detail=detail,
        retryable=retryable,
        status_code=status_code,
        exception_type=exc_type,
        provider=provider,
        model_name=model_name,
        base_url=_sanitize_base_url(base_url),
    )


def _extract_status_code(exc: BaseException) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _safe_exception_detail(exc: BaseException) -> str:
    detail = str(exc).strip() or exc.__class__.__name__
    response = getattr(exc, "response", None)
    response_text = getattr(response, "text", None)
    if callable(response_text):
        try:
            response_text = response_text()
        except Exception:
            response_text = None
    if response_text:
        response_text = str(response_text).strip()
        if response_text and response_text not in detail:
            detail = f"{detail} | response={response_text[:500]}"
    return detail


def _looks_like_timeout(exc_type: str, lowered: str) -> bool:
    return "timeout" in exc_type.lower() or any(
        token in lowered
        for token in ("timed out", "timeout", "read timeout", "request timed out")
    )


def _looks_like_network_error(exc_type: str, lowered: str) -> bool:
    return any(
        token in exc_type.lower()
        for token in ("apiconnectionerror", "connecterror", "networkerror")
    ) or any(
        token in lowered
        for token in (
            "connection error",
            "connect error",
            "connection refused",
            "name or service not known",
            "temporary failure in name resolution",
            "network is unreachable",
            "nodename nor servname provided",
            "ssl",
            "certificate verify failed",
            "dns",
            "proxy error",
        )
    )


def _looks_like_stream_error(exc_type: str, lowered: str) -> bool:
    return any(
        token in exc_type.lower()
        for token in ("remoteprotocolerror", "readerror", "protocolerror", "assertionerror")
    ) or any(
        token in lowered
        for token in (
            "server disconnected",
            "stream closed",
            "remote protocol error",
            "peer closed connection",
            "syncbytestream",
        )
    )


def _sanitize_base_url(base_url: str) -> str:
    return (base_url or "").strip().rstrip("/")
