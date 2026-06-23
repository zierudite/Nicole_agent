"""AuthService — 认证服务。

处理用户注册、登录、JWT 令牌生成与验证。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """认证与授权服务。"""

    def __init__(
        self,
        user_repo=None,
        secret_key: str = "default-secret-key",
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60 * 24,  # 24h
    ):
        self.user_repo = user_repo
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire_minutes

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None,
    ) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=self.access_token_expire)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except JWTError:
            return None

    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        """验证用户凭据并返回 token。"""
        if not self.user_repo:
            logger.error("user_repo not configured")
            return None

        user = await self.user_repo.get_by_username(username)
        if not user or not self.verify_password(password, user.get("password_hash", "")):
            return None

        token = self.create_access_token({"sub": user["id"], "role": user.get("role", "member")})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {k: v for k, v in user.items() if k != "password_hash"},
        }

    async def register(
        self, username: str, password: str, email: Optional[str] = None,
    ) -> Optional[dict]:
        """注册新用户。"""
        if not self.user_repo:
            return None

        existing = await self.user_repo.get_by_username(username)
        if existing:
            return None

        user = await self.user_repo.create({
            "username": username,
            "password_hash": self.hash_password(password),
            "email": email,
            "role": "member",
        })
        return {k: v for k, v in user.items() if k != "password_hash"}
