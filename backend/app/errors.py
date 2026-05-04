"""统一 API 错误码和用户提示。"""

from fastapi import HTTPException


AUTH_REQUIRED = "AUTH_REQUIRED"
PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
PROJECT_FORBIDDEN = "PROJECT_FORBIDDEN"
API_CREDENTIAL_NOT_FOUND = "API_CREDENTIAL_NOT_FOUND"
API_CREDENTIAL_IN_USE = "API_CREDENTIAL_IN_USE"
API_CREDENTIAL_DISABLED = "API_CREDENTIAL_DISABLED"
MODEL_PROFILE_NOT_FOUND = "MODEL_PROFILE_NOT_FOUND"
MODEL_PROFILE_DISABLED = "MODEL_PROFILE_DISABLED"
MODEL_TYPE_MISMATCH = "MODEL_TYPE_MISMATCH"
MODEL_CALL_FAILED = "MODEL_CALL_FAILED"
API_KEY_DECRYPT_FAILED = "API_KEY_DECRYPT_FAILED"
API_KEY_INVALID = "API_KEY_INVALID"
BASE_URL_INVALID = "BASE_URL_INVALID"
MODEL_NAME_INVALID = "MODEL_NAME_INVALID"
MODEL_CONFIG_INVALID = "MODEL_CONFIG_INVALID"
MODEL_CONFIG_INCOMPLETE = "MODEL_CONFIG_INCOMPLETE"
SERVER_INTERFACE_NOT_FOUND = "SERVER_INTERFACE_NOT_FOUND"
LEGACY_CONFIG_REMOVED = "LEGACY_CONFIG_REMOVED"


def api_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
        },
    )


def auth_required() -> HTTPException:
    return api_error(401, AUTH_REQUIRED, "请先登录。")


def project_not_found() -> HTTPException:
    return api_error(404, PROJECT_NOT_FOUND, "项目不存在或你没有权限访问。")


def project_forbidden() -> HTTPException:
    return api_error(403, PROJECT_FORBIDDEN, "你没有权限访问该项目。")


def credential_not_found() -> HTTPException:
    return api_error(404, API_CREDENTIAL_NOT_FOUND, "API 凭证不存在。")


def credential_in_use(count: int | None = None) -> HTTPException:
    details = {"count": count} if count is not None else {}
    return api_error(
        400,
        API_CREDENTIAL_IN_USE,
        "这个模型服务账号正在被模型配置使用。你可以选择同时删除关联模型配置。",
        details,
    )


def credential_disabled() -> HTTPException:
    return api_error(400, API_CREDENTIAL_DISABLED, "API 凭证已被禁用。")


def model_profile_not_found() -> HTTPException:
    return api_error(404, MODEL_PROFILE_NOT_FOUND, "模型配置不存在。")


def model_profile_disabled() -> HTTPException:
    return api_error(400, MODEL_PROFILE_DISABLED, "模型配置已被禁用。")


def model_type_mismatch(expected: str, actual: str) -> HTTPException:
    return api_error(400, MODEL_TYPE_MISMATCH, f"模型类型不匹配：需要 {expected}，但当前是 {actual}。")


def model_call_failed(detail: str) -> HTTPException:
    return api_error(502, MODEL_CALL_FAILED, f"模型调用失败：{detail}")


def api_key_decrypt_failed() -> HTTPException:
    return api_error(500, API_KEY_DECRYPT_FAILED, "API Key 读取失败，请重新填写后再试。")


def api_key_invalid() -> HTTPException:
    return api_error(400, API_KEY_INVALID, "测试失败，请检查 API Key 和服务商是否匹配。")


def base_url_invalid() -> HTTPException:
    return api_error(400, BASE_URL_INVALID, "服务地址配置异常，请点击修复旧配置或清空后重配。")


def model_name_invalid() -> HTTPException:
    return api_error(400, MODEL_NAME_INVALID, "模型名配置异常，请清空后重新配置。")


def model_config_invalid() -> HTTPException:
    return api_error(400, MODEL_CONFIG_INVALID, "当前模型配置不完整，建议清空后重新配置。")


def model_config_incomplete() -> HTTPException:
    return api_error(400, MODEL_CONFIG_INCOMPLETE, "当前模型配置不完整，建议清空后重新配置。")


def server_interface_not_found() -> HTTPException:
    return api_error(404, SERVER_INTERFACE_NOT_FOUND, "服务器接口未找到，请重新部署后再试。")
