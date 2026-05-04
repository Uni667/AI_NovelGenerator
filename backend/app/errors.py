"""统一 API 错误码和异常。"""

from fastapi import HTTPException


# ── 错误码常量 ──

AUTH_REQUIRED = "AUTH_REQUIRED"
PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
PROJECT_FORBIDDEN = "PROJECT_FORBIDDEN"
API_CREDENTIAL_NOT_FOUND = "API_CREDENTIAL_NOT_FOUND"
API_CREDENTIAL_DISABLED = "API_CREDENTIAL_DISABLED"
MODEL_PROFILE_NOT_FOUND = "MODEL_PROFILE_NOT_FOUND"
MODEL_PROFILE_DISABLED = "MODEL_PROFILE_DISABLED"
MODEL_TYPE_MISMATCH = "MODEL_TYPE_MISMATCH"
MODEL_CALL_FAILED = "MODEL_CALL_FAILED"
API_KEY_DECRYPT_FAILED = "API_KEY_DECRYPT_FAILED"
LEGACY_CONFIG_REMOVED = "LEGACY_CONFIG_REMOVED"


# ── 异常类 ──

def api_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        }
    )


def auth_required() -> HTTPException:
    return api_error(401, AUTH_REQUIRED, "请先登录。")


def project_not_found() -> HTTPException:
    return api_error(404, PROJECT_NOT_FOUND, "项目不存在或你没有权限访问。")


def project_forbidden() -> HTTPException:
    return api_error(403, PROJECT_FORBIDDEN, "你没有权限访问该项目。")


def credential_not_found() -> HTTPException:
    return api_error(404, API_CREDENTIAL_NOT_FOUND, "API 凭证不存在。")


def credential_disabled() -> HTTPException:
    return api_error(400, API_CREDENTIAL_DISABLED, "API 凭证已被禁用。")


def model_profile_not_found() -> HTTPException:
    return api_error(404, MODEL_PROFILE_NOT_FOUND, "模型配置不存在。")


def model_profile_disabled() -> HTTPException:
    return api_error(400, MODEL_PROFILE_DISABLED, "模型配置已被禁用。")


def model_type_mismatch(expected: str, actual: str) -> HTTPException:
    return api_error(400, MODEL_TYPE_MISMATCH,
                     f"模型类型不匹配：需要 {expected} 类型，但选择的是 {actual} 类型。")


def model_call_failed(detail: str) -> HTTPException:
    return api_error(502, MODEL_CALL_FAILED, f"模型调用失败: {detail}")


def api_key_decrypt_failed() -> HTTPException:
    return api_error(500, API_KEY_DECRYPT_FAILED,
                     "API Key 解密失败，请重新填写 API Key。")
