"""认证工具：密码哈希 + JWT 编解码（纯 stdlib，避免 Python 3.14 无 wheel 问题）

设计：
- 密码哈希：PBKDF2-HMAC-SHA256, 600_000 iterations, 16-byte salt, 32-byte key
  （OWASP 2023 推荐配置；bcrypt 在 Py 3.14 上无 wheel，PBKDF2 够用）
- 存储格式：`pbkdf2_sha256$600000$<salt_b64>$<hash_b64>`
  自描述算法 + iterations + salt + hash，将来切算法可读旧字段
- JWT：HS256 自实现（PyJWT 在 Py 3.14 上无 wheel）
  header.payload.signature 三段式，签名 HMAC-SHA256
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

# ===== 密码哈希 =====

_HASH_ALG = "pbkdf2_sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16
_KEY_BYTES = 32


def hash_password(plain: str) -> str:
    """生成可存储的密码哈希字符串。"""
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS, dklen=_KEY_BYTES)
    return f"{_HASH_ALG}${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(plain: str, stored: str) -> bool:
    """验证明文密码 vs 存储哈希。"""
    try:
        alg, iters, salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        return False
    if alg != _HASH_ALG:
        return False
    try:
        iters_i = int(iters)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, Exception):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iters_i, dklen=len(expected))
    return hmac.compare_digest(dk, expected)


# ===== JWT (HS256) =====

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def create_jwt(payload: dict[str, Any], secret: str, expires_seconds: int = 86400) -> str:
    """签发 JWT (HS256)。默认 24h 过期。"""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    body = dict(payload)
    body["iat"] = now
    body["exp"] = now + expires_seconds
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(body, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode("utf-8"), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def decode_jwt(token: str, secret: str) -> dict[str, Any] | None:
    """解码 JWT 并验证签名 + 过期时间。失败返回 None。"""
    try:
        h, p, s = token.split(".")
    except ValueError:
        return None
    expected_sig = hmac.new(secret.encode("utf-8"), f"{h}.{p}".encode(), hashlib.sha256).digest()
    actual_sig = _b64url_decode(s)
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None
    try:
        payload = json.loads(_b64url_decode(p))
    except (ValueError, json.JSONDecodeError):
        return None
    if "exp" in payload and int(payload["exp"]) < int(time.time()):
        return None
    return payload
