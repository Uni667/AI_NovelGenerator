import os
import logging

logger = logging.getLogger(__name__)


def get_file_access_flag() -> bool:
    """动态获取 Feature Flag 状态。"""
    # 优先读取环境变量，其次从动态配置中获取
    env_flag = os.getenv("ALLOW_LOCAL_FILE_ACCESS", "").lower()
    if env_flag in ("true", "false"):
        return env_flag == "true"
    
    try:
        from backend.app.services.local_library_config import get_local_library_config
        config = get_local_library_config()
        return config.get("allow_local_file_access", False)
    except Exception:
        return False


def _get_extension(filepath: str) -> str:
    """安全提取小写后缀名，特殊处理无其他后缀的隐藏文件（如 .env）。"""
    basename = os.path.basename(filepath.lower())
    if basename.startswith('.') and '.' not in basename[1:]:
        return basename
    _, ext = os.path.splitext(basename)
    return ext


def is_safe_extension(filename: str, allowed_extensions: list[str]) -> bool:
    """检查文件后缀是否在允许的白名单中。"""
    ext = _get_extension(filename)
    return ext in allowed_extensions


def resolve_safe_path(base_dir: str, target_path: str) -> str:
    """
    安全解析目标路径，防止目录穿越。
    在 Windows 下校验盘符、UNC，防软链接跳出。
    """
    if not get_file_access_flag():
        raise PermissionError("本地文件访问功能已禁用(Feature Flag ALLOW_LOCAL_FILE_ACCESS 为 false)。")

    if not base_dir:
        raise ValueError("安全校验失败：根目录为空。")

    # 规范化路径为物理绝对路径 (会展开软链接)
    abs_base = os.path.realpath(base_dir)
    
    if os.path.isabs(target_path):
        abs_target = os.path.realpath(target_path)
    else:
        abs_target = os.path.realpath(os.path.join(abs_base, target_path))

    # 判断 target 是否在 base 的子目录下
    try:
        common_path = os.path.commonpath([abs_base, abs_target])
    except ValueError:
        # 不同盘符情况下会抛出 ValueError (如 C: 与 D:)
        raise PermissionError(f"安全警报：拒绝跨盘符访问白名单目录外的路径: {abs_target}")

    if common_path != abs_base:
        raise PermissionError(f"安全警报：拒绝访问白名单目录外的路径: {abs_target}")

    return abs_target


def resolve_source_path(target_path: str) -> str:
    """解析并校验小说原文目录下的文件路径。"""
    from backend.app.services.local_library_config import get_local_library_config
    config = get_local_library_config()
    base_dir = config.get("source_dir", "")
    if not base_dir:
        raise ValueError("小说原文目录(source_dir)尚未配置。")
    return resolve_safe_path(base_dir, target_path)


def resolve_essence_path(target_path: str) -> str:
    """解析并校验精华输出目录下的文件路径。"""
    from backend.app.services.local_library_config import get_local_library_config
    config = get_local_library_config()
    base_dir = config.get("essence_dir", "")
    if not base_dir:
        raise ValueError("精华输出目录(essence_dir)尚未配置。")
    return resolve_safe_path(base_dir, target_path)


def assert_read_allowed(filepath: str):
    """校验是否可读，防穿越且属于允许的白名单目录。"""
    if not get_file_access_flag():
        raise PermissionError("本地文件读取被禁用(ALLOW_LOCAL_FILE_ACCESS is false)。")

    from backend.app.services.local_library_config import get_local_library_config
    config = get_local_library_config()
    
    # 动态汇聚所有可读白名单根目录
    allowed_dirs = [
        config.get("source_dir"),
        config.get("essence_dir"),
        config.get("cache_dir"),
    ]
    allowed_dirs = [os.path.realpath(d) for d in allowed_dirs if d]
    allowed_extensions = config.get("allowed_extensions", [".txt", ".md", ".epub", ".docx"])

    abs_path = os.path.realpath(filepath)
    
    # 1. 拦截敏感扩展名（黑名单）
    ext = _get_extension(abs_path)
    if ext in (".env", ".db", ".sqlite", ".sqlite3", ".key", ".pem", ".pfx", ".crt", ".log"):
        raise PermissionError(f"安全警报：黑名单文件类型拒绝读取(restricted extension): {abs_path}")

    # 2. 校验文件扩展名白名单
    if not is_safe_extension(abs_path, allowed_extensions):
        raise PermissionError(f"安全警报：拒绝读取不支持的文件类型(unsupported extension): {abs_path}")

    # 3. 校验目录越界
    in_whitelist = False
    for base_dir in allowed_dirs:
        try:
            if os.path.commonpath([base_dir, abs_path]) == base_dir:
                in_whitelist = True
                break
        except ValueError:
            continue

    if not in_whitelist:
        raise PermissionError(f"安全警报：文件路径不在可读白名单目录中: {abs_path}")


def assert_write_allowed(filepath: str):
    """校验是否可写，防穿越且属于允许的白名单目录。"""
    if not get_file_access_flag():
        raise PermissionError("本地文件写入被禁用(ALLOW_LOCAL_FILE_ACCESS is false)。")

    from backend.app.services.local_library_config import get_local_library_config
    config = get_local_library_config()
    
    # 动态汇聚所有可写白名单目录（一般仅限精华区、缓存区、日志区）
    allowed_dirs = [
        config.get("essence_dir"),
        config.get("cache_dir"),
        config.get("log_dir"),
    ]
    allowed_dirs = [os.path.realpath(d) for d in allowed_dirs if d]

    abs_path = os.path.realpath(filepath)

    # 1. 拦截敏感扩展名（黑名单）
    ext = _get_extension(abs_path)
    if ext in (".env", ".db", ".sqlite", ".sqlite3", ".key", ".pem", ".pfx", ".crt"):
        raise PermissionError(f"安全警报：黑名单文件类型拒绝写入: {abs_path}")

    # 2. 校验目录越界
    in_whitelist = False
    for base_dir in allowed_dirs:
        try:
            if os.path.commonpath([base_dir, abs_path]) == base_dir:
                in_whitelist = True
                break
        except ValueError:
            continue

    if not in_whitelist:
        raise PermissionError(f"安全警报：文件写入路径不在白名单目录中: {abs_path}")
