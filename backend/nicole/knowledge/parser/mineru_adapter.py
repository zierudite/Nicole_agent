"""MinerU 适配器。

MinerU 是 opendatalab 开源的高精度文档解析工具，
支持 PDF 中的公式、表格、图片、排版等复杂元素的精确提取。
参考 Yuxi 的 MinerU 集成。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseParser, ParserResult

logger = logging.getLogger(__name__)


class MinerUAdapter(BaseParser):
    """MinerU 高精度 PDF 解析适配器。

    通过调用 MinerU 的 API 或命令行进行解析。
    MinerU 安装: pip install magic-pdf[full]
    """

    def __init__(
        self,
        method: str = "auto",
        ocr: bool = True,
        lang: str = "ch",
        **kwargs,
    ):
        self.method = method
        self.ocr = ocr
        self.lang = lang
        self.extra_kwargs = kwargs

    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    async def parse(self, file_path: str) -> Optional[ParserResult]:
        """使用 MinerU 解析 PDF。"""
        if not self.validate_file(file_path):
            return None

        path = Path(file_path)
        metadata = {"filename": path.name, "size": path.stat().st_size}

        try:
            # 尝试通过 mineru API 解析
            result = await self._parse_via_api(file_path, metadata)
            if result:
                return result
        except Exception as e:
            logger.warning(f"MinerU API parse failed: {e}")

        # 降级: 通过命令行工具
        return await self._parse_via_cli(file_path, metadata)

    async def _parse_via_api(
        self, file_path: str, base_meta: Dict
    ) -> Optional[ParserResult]:
        """通过 MinerU Python API 解析。"""
        try:
            from mineru.pdf_extractor import PDFExtractor

            extractor = PDFExtractor(
                method=self.method,
                ocr=self.ocr,
                lang=self.lang,
                **self.extra_kwargs,
            )
            result = extractor.extract(file_path)

            text = result.get("text", "")
            pages = result.get("pages", [])

            logger.info(f"MinerU API parsed: {file_path}, {len(pages)} pages")
            return ParserResult(
                text=text,
                file_type="pdf",
                metadata={
                    **base_meta,
                    "engine": "mineru_api",
                    "pages": len(pages),
                },
                pages=pages,
            )

        except ImportError:
            logger.debug("mineru not installed via API")
        return None

    async def _parse_via_cli(
        self, file_path: str, base_meta: Dict
    ) -> Optional[ParserResult]:
        """通过 MinerU CLI 解析。"""
        import subprocess

        output_dir = Path(file_path).parent / f"{Path(file_path).stem}_mineru"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                "magic-pdf",
                "-p", file_path,
                "-o", str(output_dir),
            ]
            if self.ocr:
                cmd.append("--ocr")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.warning(f"MinerU CLI failed: {stderr.decode()[:200]}")
                return None

            # 读取输出文件
            md_file = output_dir / f"{Path(file_path).stem}.md"
            if md_file.exists():
                text = md_file.read_text(encoding="utf-8")
                return ParserResult(
                    text=text,
                    file_type="pdf",
                    metadata={**base_meta, "engine": "mineru_cli"},
                )

        except FileNotFoundError:
            logger.warning("MinerU CLI (magic-pdf) not found in PATH")
        except Exception as e:
            logger.warning(f"MinerU CLI failed: {e}")

        return None


# 需要在文件顶部添加 asyncio 导入
import asyncio
