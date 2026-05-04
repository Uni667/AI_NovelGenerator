"""加密工具：AES-256-GCM 加密存储 API Key。"""

import base64
import hashlib
import hmac
import os

_ENV_KEY = os.getenv("API_SECRET_ENCRYPTION_KEY", "")
_SALT = b"ai_novel_generator_salt_v1"


def _derive_aes_key() -> bytes:
    """从环境变量 API_SECRET_ENCRYPTION_KEY 派生 AES-256 密钥。"""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    if not _ENV_KEY:
        raise RuntimeError("API_SECRET_ENCRYPTION_KEY 环境变量未设置，请联系管理员配置后重试")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100_000,
        backend=default_backend(),
    )
    return kdf.derive(_ENV_KEY.encode("utf-8"))


def _aesgcm():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(_derive_aes_key())


def encrypt_api_key(api_key: str) -> str:
    """AES-256-GCM 加密，输出 base64(nonce + ciphertext + tag)。"""
    aesgcm = _aesgcm()
    nonce = os.urandom(12)  # 96-bit IV
    ciphertext = aesgcm.encrypt(nonce, api_key.encode("utf-8"), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode("utf-8")


def decrypt_api_key(encrypted: str) -> str:
    """AES-256-GCM 解密。解密失败时抛出明确异常（方便上层提示密钥变更）。"""
    from cryptography.exceptions import InvalidTag

    aesgcm = _aesgcm()
    try:
        raw = base64.b64decode(encrypted.encode("utf-8"))
    except Exception:
        raise ValueError("API 配置密文格式异常，可能是加密密钥发生变化，请重新填写 API Key")
    if len(raw) < 13:
        raise ValueError("API 配置密文长度异常，可能是加密密钥发生变化，请重新填写 API Key")
    nonce = raw[:12]
    ciphertext = raw[12:]
    try:
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except InvalidTag:
        raise ValueError("API 配置解密失败：当前加密密钥与保存时的密钥不一致，请重新填写 API Key")


def hash_api_key(api_key: str) -> str:
    """HMAC-SHA256 fingerprint for duplicate detection. Not reversible."""
    key = (_ENV_KEY or "missing-encryption-key").encode("utf-8")
    return hmac.new(key, api_key.encode("utf-8"), hashlib.sha256).hexdigest()


def last4(value: str) -> str:
    """取最后 4 个有效字符。"""
    v = (value or "").strip()
    if len(v) <= 4:
        return v
    return v[-4:]


def mask_key(key: str) -> str:
    """脱敏显示：前缀 4 字符 + **** + 后缀 4 字符。"""
    k = (key or "").strip()
    if len(k) <= 8:
        return "*" * len(k)
    return k[:4] + "*" * (len(k) - 8) + k[-4:]


def mask_api_key(key: str) -> str:
    """脱敏显示 API Key：如 sk-a***c1234。"""
    k = (key or "").strip()
    if not k:
        return "未配置"
    if len(k) <= 7:
        return k[:1] + "***"
    # 取前缀前 3 个字符 + *** + 末尾 4 个字符
    return k[:3] + "***" + k[-4:]


encrypt_secret = encrypt_api_key
decrypt_secret = decrypt_api_key
hash_secret = hash_api_key
mask_secret = mask_api_key
