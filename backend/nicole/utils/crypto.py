"""CryptoUtils — 加密工具。

提供密码哈希、Token 签名、数据加解密等功能。
参考 Keji-agent 的安全设计。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional


class CryptoUtils:
    """加密工具类。"""

    @staticmethod
    def generate_salt(length: int = 32) -> str:
        """生成随机盐值。"""
        return secrets.token_hex(length)

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """密码哈希（带盐值）。

        Returns:
            (hash, salt) 元组
        """
        salt = salt or CryptoUtils.generate_salt()
        hash_value = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return hash_value.hex(), salt

    @staticmethod
    def verify_password(password: str, hash_value: str, salt: str) -> bool:
        """验证密码。"""
        computed, _ = CryptoUtils.hash_password(password, salt)
        return hmac.compare_digest(computed, hash_value)

    @staticmethod
    def generate_api_key() -> str:
        """生成 API Key。"""
        return f"nm_{secrets.token_urlsafe(32)}"

    @staticmethod
    def generate_secret_key(length: int = 64) -> str:
        """生成密钥。"""
        return secrets.token_hex(length)

    @staticmethod
    def md5(data: str) -> str:
        """计算 MD5 哈希。"""
        return hashlib.md5(data.encode("utf-8")).hexdigest()

    @staticmethod
    def sha256(data: str) -> str:
        """计算 SHA-256 哈希。"""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def mask_sensitive(value: str, visible_chars: int = 4) -> str:
        """脱敏处理。"""
        if len(value) <= visible_chars:
            return value
        return value[:visible_chars] + "*" * (len(value) - visible_chars)
