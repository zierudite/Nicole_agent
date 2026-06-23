"""DocumentParser — 文档解析管理器。

自动检测文件类型并路由到对应解析器。
支持多层解析引擎: MinerU (高精度) > 专用库 > 基础文本提取。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import BaseParser, ParserResult
from .pdf import PDFParser
from .docx import DOCXParser
from .pptx import PPTXParser

logger = logging.getLogger(__name__)


class DocumentParser:
    """文档解析管理器。自动路由文件到合适的解析器。"""

    PARSER_MAP: Dict[str, Type[BaseParser]] = {
        ".pdf": PDFParser,
        ".docx": DOCXParser,
        ".doc": DOCXParser,
        ".pptx": PPTXParser,
        ".ppt": PPTXParser,
    }

    def __init__(
        self,
        use_mineru: bool = False,
        use_paddlex: bool = False,
        use_rapidocr: bool = False,
        mineru_config: Optional[Dict] = None,
    ):
        self.use_mineru = use_mineru
        self.use_paddlex = use_paddlex
        self.use_rapidocr = use_rapidocr
        self.mineru_config = mineru_config or {}

    async def parse(self, file_path: str) -> Optional[ParserResult]:
        """解析文件。自动检测类型并路由。"""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        ext = path.suffix.lower()
        logger.info(f"Parsing: {file_path} (type={ext})")

        # 1. MinerU 高精度 PDF 解析
        if self.use_mineru and ext == ".pdf":
            from .mineru_adapter import MinerUAdapter
            try:
                adapter = MinerUAdapter(**self.mineru_config)
                result = await adapter.parse(file_path)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"MinerU failed: {e}")

        # 2. 专用解析器
        parser_cls = self.PARSER_MAP.get(ext)
        if parser_cls:
            try:
                parser = parser_cls(
                    use_paddlex=self.use_paddlex,
                    use_rapidocr=self.use_rapidocr,
                )
                return await parser.parse(file_path)
            except Exception as e:
                logger.warning(f"Parser {parser_cls.__name__} failed: {e}")

        # 3. 降级: 纯文本读取
        return await self._fallback_parse(file_path)

    async def parse_batch(self, file_paths: List[str]) -> List[ParserResult]:
        """批量解析。"""
        results = []
        for fp in file_paths:
            result = await self.parse(fp)
            if result:
                results.append(result)
        logger.info(f"Batch parsed {len(results)}/{len(file_paths)}")
        return results

    async def _fallback_parse(self, file_path: str) -> Optional[ParserResult]:
        """降级解析: 尝试以纯文本读取。"""
        path = Path(file_path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return ParserResult(
                text=text,
                file_type=path.suffix.lower(),
                metadata={"filename": path.name, "size": path.stat().st_size},
            )
        except Exception as e:
            logger.error(f"Fallback parse failed: {e}")
            return None
