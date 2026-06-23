"""FileStore — 本地文件存储管理。

封装本地文件系统的读写操作，替代 MinIO/S3。
提供文件路径管理、分片存储、安全路径验证。
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class FileStoreSettings(BaseSettings):
    """文件存储配置。"""
    upload_dir: str = Field(default="data/uploads", validation_alias="UPLOAD_DIR")
    saves_dir: str = Field(default="data/saves", validation_alias="SAVES_DIR")
    sandbox_dir: str = Field(default="data/sandbox", validation_alias="SANDBOX_DIR")
    max_file_size: int = Field(default=100 * 1024 * 1024, validation_alias="MAX_FILE_SIZE")  # 100MB
    allowed_extensions: str = Field(
        default=".pdf,.docx,.doc,.pptx,.ppt,.png,.jpg,.jpeg,.md,.txt,.csv",
        validation_alias="ALLOWED_EXTENSIONS",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


class FileStore:
    """本地文件存储管理。

    职责:
    - 安全文件路径管理（防止路径穿越）
    - 分片目录存储
    - 文件类型验证
    - MD5 完整性校验
    参考 Yuxi 的存储管理 + Keji-agent 的工作区设计。
    """

    def __init__(self, settings: Optional[FileStoreSettings] = None):
        self.settings = settings or FileStoreSettings()
        self.allowed_exts = set(self.settings.allowed_extensions.split(","))
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保存储目录存在。"""
        for d in [self.settings.upload_dir, self.settings.saves_dir, self.settings.sandbox_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)

    # ── 路径安全 ──

    def safe_path(self, base_dir: str, relative_path: str) -> Path:
        """安全的路径拼接，防止路径穿越攻击。

        Args:
            base_dir: 基础目录
            relative_path: 相对路径

        Returns:
            安全的绝对路径

        Raises:
            ValueError: 如果解析后的路径超出 base_dir 范围
        """
        base = Path(base_dir).resolve()
        target = (base / relative_path).resolve()
        if not str(target).startswith(str(base)):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return target

    def validate_extension(self, filename: str) -> bool:
        """验证文件扩展名是否允许。"""
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_exts:
            logger.warning(f"File type not allowed: {ext}")
            return False
        return True

    # ── 文件操作 ──

    async def save(
        self,
        data: bytes,
        filename: str,
        sub_dir: str = "",
        base_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """保存文件到本地存储。

        Args:
            data: 文件二进制数据
            filename: 文件名
            sub_dir: 子目录 (如用户 ID)
            base_dir: 基础目录 (默认 upload_dir)

        Returns:
            文件元数据字典
        """
        if not self.validate_extension(filename):
            raise ValueError(f"File type not allowed: {filename}")

        if len(data) > self.settings.max_file_size:
            raise ValueError(f"File too large: {len(data)} > {self.settings.max_file_size}")

        base = base_dir or self.settings.upload_dir
        file_id = str(uuid.uuid4())
        md5 = hashlib.md5(data).hexdigest()

        # 分片存储: base/sub_dir/file_id/filename
        rel_dir = str(Path(sub_dir) / file_id) if sub_dir else file_id
        target_dir = self.safe_path(base, rel_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / filename
        target_path.write_bytes(data)

        record = {
            "id": file_id,
            "filename": filename,
            "storage_path": str(target_path),
            "size": len(data),
            "md5_hash": md5,
            "base_dir": base,
            "relative_path": str(Path(rel_dir) / filename),
        }

        logger.info(f"File saved: {filename} ({len(data)} bytes) -> {target_path}")
        return record

    async def read(self, storage_path: str) -> Optional[bytes]:
        """读取文件内容。"""
        path = Path(storage_path)
        if path.exists() and path.is_file():
            return path.read_bytes()
        logger.warning(f"File not found: {storage_path}")
        return None

    async def delete(self, storage_path: str) -> bool:
        """删除文件及空目录。"""
        path = Path(storage_path)
        if not path.exists():
            return False

        path.unlink()
        # 移除空父目录
        parent = path.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
        logger.info(f"File deleted: {storage_path}")
        return True

    async def copy(
        self, src_path: str, dest_sub_dir: str, new_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """复制文件到新位置。"""
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"Source not found: {src_path}")

        data = src.read_bytes()
        filename = new_filename or src.name
        return await self.save(data, filename, dest_sub_dir)

    # ── 文件查询 ──

    async def get_info(self, storage_path: str) -> Optional[Dict]:
        """获取文件信息。"""
        path = Path(storage_path)
        if not path.exists():
            return None
        stat = path.stat()
        return {
            "path": str(path),
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "extension": path.suffix.lower(),
        }

    def list_dir(self, sub_dir: str = "", base_dir: Optional[str] = None) -> List[str]:
        """列出目录中的文件。"""
        base = base_dir or self.settings.upload_dir
        target = self.safe_path(base, sub_dir)
        if not target.exists():
            return []
        return [str(f.relative_to(Path(base))) for f in target.iterdir() if f.is_file()]

    # ── 沙盒文件操作 ──

    def get_sandbox_path(self, user_id: str, filename: str = "") -> str:
        """获取用户沙盒路径。"""
        sandbox_dir = Path(self.settings.sandbox_dir) / user_id
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        if filename:
            return str(sandbox_dir / filename)
        return str(sandbox_dir)

    # ── 工具方法 ──

    def get_storage_path(self, file_id: str, filename: str, sub_dir: str = "") -> str:
        """获取文件的存储路径（基于 ID 分片）。"""
        base = Path(self.settings.upload_dir)
        return str(base / sub_dir / file_id / filename)

    async def clear_temp(self, older_than_days: int = 7):
        """清理临时文件。"""
        import time
        now = time.time()
        threshold = now - older_than_days * 86400
        cleaned = 0

        for root, dirs, files in os.walk(self.settings.upload_dir):
            for f in files:
                path = Path(root) / f
                if path.stat().st_mtime < threshold:
                    path.unlink()
                    cleaned += 1

        logger.info(f"Cleaned {cleaned} temp files older than {older_than_days} days")
