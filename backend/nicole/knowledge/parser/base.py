"""解析器基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParserResult:
    """解析结果。"""
    text: str
    file_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    pages: List[Dict] = field(default_factory=list)

    def __repr__(self):
        return (
            f"ParserResult(type={self.file_type}, "
            f"text_len={len(self.text)}, pages={len(self.pages)})"
        )


class BaseParser(ABC):
    """解析器基类。所有具体解析器继承此类。"""

    @abstractmethod
    async def parse(self, file_path: str) -> Optional[ParserResult]:
        """解析文件并返回结果。"""
        ...

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """返回支持的文件扩展名列表。"""
        ...

    def validate_file(self, file_path: str) -> bool:
        """验证文件是否存在且可读。"""
        from pathlib import Path
        p = Path(file_path)
        return p.exists() and p.is_file()
