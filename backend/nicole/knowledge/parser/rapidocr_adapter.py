"""RapidOCR 适配器。

RapidOCR 是基于 ONNX Runtime 的轻量级 OCR 引擎，
无需 GPU，适合 CPU 环境快速部署。
参考 Yuxi 的 RapidOCR 集成。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseParser, ParserResult

logger = logging.getLogger(__name__)


class RapidOCRAdapter(BaseParser):
    """RapidOCR 轻量 OCR 适配器。

    安装: pip install rapidocr-onnxruntime
    纯 CPU 推理，速度快，适合轻量部署。
    """

    def __init__(self, lang: str = "ch"):
        self.lang = lang

    def supported_extensions(self) -> List[str]:
        return [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]

    async def parse(self, file_path: str) -> Optional[ParserResult]:
        """对图像执行 OCR 识别。"""
        if not self.validate_file(file_path):
            return None

        path = Path(file_path)
        metadata = {"filename": path.name, "size": path.stat().st_size}

        try:
            text = await self._ocr(file_path)
            if text:
                return ParserResult(
                    text=text,
                    file_type=path.suffix.lower(),
                    metadata={**metadata, "engine": "rapidocr"},
                )
        except Exception as e:
            logger.error(f"RapidOCR failed: {e}")

        return None

    async def _ocr(self, file_path: str) -> Optional[str]:
        """执行 OCR 并返回文本。"""
        try:
            from rapidocr_onnxruntime import RapidOCR

            engine = RapidOCR()
            result, elapse = engine(file_path)

            if not result:
                return None

            text_parts = []
            for line in result:
                box = line[0]
                text = line[1]
                score = line[2]
                if score and score > 0.5:
                    text_parts.append(text)

            return "\n".join(text_parts)

        except ImportError:
            logger.warning("rapidocr-onnxruntime not installed")
        except Exception as e:
            logger.warning(f"RapidOCR inference failed: {e}")

        return None

    async def ocr_batch(
        self, file_paths: List[str]
    ) -> List[Optional[str]]:
        """批量 OCR。"""
        results = []
        for fp in file_paths:
            text = await self._ocr(fp)
            results.append(text)
        return results
