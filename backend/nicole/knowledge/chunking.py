"""文档分块策略。

提供多种分块策略: 语义分块、递归字符分块、固定大小分块。
参考 Yuxi 的 chunking 策略 + RAGflow 的分块思路。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChunkStrategy(str, Enum):
    """分块策略枚举。"""
    RECURSIVE = "recursive"           # 递归字符分块 (默认)
    FIXED_SIZE = "fixed_size"         # 固定大小分块
    SEMANTIC = "semantic"             # 语义分块 (按标题/段落)
    MARKDOWN_HEADER = "markdown_header"  # 按Markdown标题分块


@dataclass
class Chunk:
    """单个文档块。"""
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0


@dataclass
class ChunkConfig:
    """分块配置。"""
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    chunk_size: int = 512            # 每块目标字符数
    chunk_overlap: int = 128          # 块间重叠字符数
    min_chunk_size: int = 50          # 最小块大小
    separators: List[str] = field(
        default_factory=lambda: ["\n\n", "\n", "。", ".", " ", ""]
    )


class Chunker:
    """文档分块器。支持多种分块策略。"""

    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """根据配置的策略执行分块。"""
        strategy_map = {
            ChunkStrategy.RECURSIVE: self._recursive_chunk,
            ChunkStrategy.FIXED_SIZE: self._fixed_size_chunk,
            ChunkStrategy.SEMANTIC: self._semantic_chunk,
            ChunkStrategy.MARKDOWN_HEADER: self._markdown_header_chunk,
        }
        strategy = self.config.strategy
        chunker = strategy_map.get(strategy, self._recursive_chunk)
        chunks = chunker(text, metadata or {})
        logger.info(f"Chunked into {len(chunks)} chunks (strategy={strategy.value})")
        return chunks

    def _recursive_chunk(self, text: str, metadata: Dict) -> List[Chunk]:
        """递归字符分块。

        按优先级依次尝试分隔符切割，直到块大小满足要求。
        参考 LangChain 的 RecursiveCharacterTextSplitter 思路。
        """
        chunks = []
        self._recursive_split(
            text, self.config.separators, 0, chunks, metadata
        )
        return self._apply_overlap(chunks)

    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        sep_idx: int,
        chunks: List[Chunk],
        metadata: Dict,
    ):
        if len(text) <= self.config.chunk_size:
            chunks.append(Chunk(
                content=text,
                chunk_index=len(chunks),
                metadata=metadata,
                token_count=len(text),
            ))
            return

        if sep_idx >= len(separators):
            # 没有更多分隔符，直接切分
            for i in range(0, len(text), self.config.chunk_size):
                chunk_text = text[i : i + self.config.chunk_size]
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunks.append(Chunk(
                        content=chunk_text,
                        chunk_index=len(chunks),
                        metadata=metadata,
                        token_count=len(chunk_text),
                    ))
            return

        separator = separators[sep_idx]
        if not separator:
            self._recursive_split(text, separators, sep_idx + 1, chunks, metadata)
            return

        parts = text.split(separator)
        if len(parts) == 1:
            self._recursive_split(text, separators, sep_idx + 1, chunks, metadata)
            return

        current = ""
        for part in parts:
            candidate = current + (separator if current else "") + part
            if len(candidate) <= self.config.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(Chunk(
                        content=current,
                        chunk_index=len(chunks),
                        metadata=metadata,
                        token_count=len(current),
                    ))
                current = part

        if current:
            chunks.append(Chunk(
                content=current,
                chunk_index=len(chunks),
                metadata=metadata,
                token_count=len(current),
            ))

    def _fixed_size_chunk(self, text: str, metadata: Dict) -> List[Chunk]:
        """固定大小分块 (简单按字符数切分)。"""
        chunks = []
        for i in range(0, len(text), self.config.chunk_size):
            chunk_text = text[i : i + self.config.chunk_size]
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    content=chunk_text,
                    chunk_index=len(chunks),
                    metadata=metadata,
                    token_count=len(chunk_text),
                ))
        return self._apply_overlap(chunks)

    def _semantic_chunk(self, text: str, metadata: Dict) -> List[Chunk]:
        """语义分块: 按段落 (连续双换行) 和语义边界分块。"""
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            candidate = current + ("\n\n" if current else "") + para
            if len(candidate) <= self.config.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(Chunk(
                        content=current,
                        chunk_index=len(chunks),
                        metadata=metadata,
                        token_count=len(current),
                    ))
                current = para

        if current and len(current) >= self.config.min_chunk_size:
            chunks.append(Chunk(
                content=current,
                chunk_index=len(chunks),
                metadata=metadata,
                token_count=len(current),
            ))

        return self._apply_overlap(chunks)

    def _markdown_header_chunk(self, text: str, metadata: Dict) -> List[Chunk]:
        """按 Markdown 标题层级分块。"""
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        sections = header_pattern.split(text)

        chunks = []
        current_header = ""
        current_content = ""

        # sections 格式: [before_first_header, level1, title1, content1, level2, title2, ...]
        i = 0
        while i < len(sections):
            section = sections[i].strip()
            if not section:
                i += 1
                continue

            # 检查是否是标题行
            if i + 1 < len(sections) and re.match(r"^#{1,6}$", sections[i]):
                level = len(sections[i])
                title = sections[i + 1].strip()
                if current_header:
                    chunks.append(Chunk(
                        content=f"{current_header}\n\n{current_content}".strip(),
                        chunk_index=len(chunks),
                        metadata={**metadata, "header": current_header},
                    ))
                current_header = "#" * level + " " + title
                current_content = ""
                i += 2
            else:
                current_content += section + "\n"
                i += 1

        if current_header or current_content:
            content = (
                f"{current_header}\n\n{current_content}".strip()
                if current_header
                else current_content.strip()
            )
            if len(content) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    content=content,
                    chunk_index=len(chunks),
                    metadata={**metadata, "header": current_header},
                ))

        return self._apply_overlap(chunks)

    def _apply_overlap(self, chunks: List[Chunk]) -> List[Chunk]:
        """在块之间应用重叠。"""
        if self.config.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        overlapped = []
        for i, chunk in enumerate(chunks):
            if i > 0 and self.config.chunk_overlap > 0:
                prev = chunks[i - 1].content
                overlap_text = prev[-self.config.chunk_overlap :]
                chunk.content = overlap_text + chunk.content

            overlapped.append(chunk)

        return overlapped

    def chunk_batch(
        self,
        documents: List[Dict[str, str]],
    ) -> List[List[Chunk]]:
        """批量分块多个文档。"""
        results = []
        for doc in documents:
            text = doc.get("content", "")
            metadata = doc.get("metadata", {})
            chunks = self.chunk(text, metadata)
            results.append(chunks)
        return results
