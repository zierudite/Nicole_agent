"""FileService — 文件服务。

管理文件上传、存储、元数据、文档解析触发。
对象存储使用本地文件系统（替代 MinIO/S3）。
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

UPLOAD_BASE = "data/uploads"
SAVES_BASE = "data/saves"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


class FileService:
    """文件服务。管理文件的存储和元数据。"""

    def __init__(self, file_repo=None, knowledge_service=None):
        self.file_repo = file_repo
        self.knowledge_service = knowledge_service
        self._ensure_dirs()

    def _ensure_dirs(self):
        Path(UPLOAD_BASE).mkdir(parents=True, exist_ok=True)
        Path(SAVES_BASE).mkdir(parents=True, exist_ok=True)

    async def upload(
        self, user_id: str, file_data: bytes, filename: str,
        mime_type: str = "",
    ) -> Dict:
        """上传文件。"""
        if len(file_data) > MAX_FILE_SIZE:
            raise ValueError(f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

        file_id = str(uuid.uuid4())
        md5 = hashlib.md5(file_data).hexdigest()
        ext = Path(filename).suffix.lower()
        storage_dir = Path(UPLOAD_BASE) / file_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_path = storage_dir / filename

        storage_path.write_bytes(file_data)

        file_record = {
            "id": file_id,
            "user_id": user_id,
            "filename": filename,
            "storage_path": str(storage_path),
            "size": len(file_data),
            "mime_type": mime_type or self._guess_mime(ext),
            "md5_hash": md5,
        }

        if self.file_repo:
            created = await self.file_repo.create(file_record)
        else:
            created = file_record

        logger.info(f"File uploaded: {filename} ({len(file_data)} bytes) -> {storage_path}")
        return created

    async def get(self, file_id: str) -> Optional[Dict]:
        """获取文件元数据。"""
        if self.file_repo:
            return await self.file_repo.get(file_id)
        return None

    async def read_content(self, file_id: str) -> Optional[bytes]:
        """读取文件内容。"""
        record = await self.get(file_id)
        if not record:
            return None
        path = Path(record["storage_path"])
        if path.exists():
            return path.read_bytes()
        return None

    async def list_by_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        """列出用户的文件。"""
        if self.file_repo:
            return await self.file_repo.list_by_user(user_id, limit=limit)
        return []

    async def delete(self, file_id: str) -> bool:
        """删除文件（含物理文件）。"""
        record = await self.get(file_id)
        if not record:
            return False

        path = Path(record["storage_path"])
        if path.exists():
            path.unlink()
        # 删除空目录
        parent = path.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

        if self.file_repo:
            return await self.file_repo.delete(file_id)
        return True

    async def parse_and_index(
        self, file_id: str, knowledge_base_id: str,
    ) -> Dict:
        """解析文件并索引到知识库。"""
        record = await self.get(file_id)
        if not record:
            return {"status": "error", "message": "File not found"}

        if self.knowledge_service:
            result = await self.knowledge_service.upload_and_index(
                record["storage_path"], knowledge_base_id,
            )
            # 更新文件状态
            if self.file_repo:
                await self.file_repo.update(file_id, {"is_parsed": True})
            return result

        return {"status": "error", "message": "Knowledge service not configured"}

    @staticmethod
    def _guess_mime(ext: str) -> str:
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".md": "text/markdown",
            ".txt": "text/plain",
        }
        return mime_map.get(ext, "application/octet-stream")

    @staticmethod
    def get_save_path(user_id: str, filename: str) -> str:
        """获取用户保存文件的路径。"""
        save_dir = Path(SAVES_BASE) / user_id
        save_dir.mkdir(parents=True, exist_ok=True)
        return str(save_dir / filename)
