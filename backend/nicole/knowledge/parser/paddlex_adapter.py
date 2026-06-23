"""PaddleX OCR 适配器。

PaddleX 是百度 PaddlePaddle 生态的 OCR 与版面分析工具。
参考 Yuxi 的 PaddleX 集成。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseParser, ParserResult

logger = logging.getLogger(__name__)


class PaddleXAdapter(BaseParser):
    """PaddleX OCR / 版面分析适配器。

    安装: pip install paddlex paddlepaddle
    用于图像中的文字识别和文档版面分析。
    """

    def __init__(
        self,
        ocr_model: str = "PP-OCRv4",
        layout_model: str = "PP-Layout",
        lang: str = "ch",
    ):
        self.ocr_model = ocr_model
        self.layout_model = layout_model
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
            result = await self._ocr_image(file_path, metadata)
            return result
        except Exception as e:
            logger.error(f"PaddleX OCR failed: {e}")
            return None

    async def _ocr_image(
        self, file_path: str, base_meta: Dict
    ) -> Optional[ParserResult]:
        """对单张图片执行 OCR。"""
        try:
            from paddlex import create_model

            model = create_model(self.ocr_model)
            output = model.predict(file_path, batch_size=1)

            text_parts = []
            for res in output:
                for item in res:
                    text = item.get("text", "")
                    score = item.get("score", 0)
                    if text and score > 0.5:
                        text_parts.append(text)

            full_text = "\n".join(text_parts)
            return ParserResult(
                text=full_text,
                file_type=Path(file_path).suffix.lower(),
                metadata={**base_meta, "engine": f"paddlex_{self.ocr_model}"},
            )

        except ImportError:
            logger.warning("paddlex not installed")
        return None

    async def analyze_layout(self, file_path: str) -> Dict:
        """版面分析 (识别标题、段落、表格等区域)。"""
        try:
            from paddlex import create_model

            model = create_model(self.layout_model)
            output = model.predict(file_path)
            regions = []
            for res in output:
                regions.append(res)
            return {"regions": regions}
        except ImportError:
            logger.warning("paddlex layout model not available")
            return {"regions": []}
