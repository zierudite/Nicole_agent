"""Helpers — 通用工具函数。

参考 Yuxi 的 utils + Keji-agent 的辅助函数。
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, TypeVar

T = TypeVar("T")


def slugify(text: str) -> str:
    """将文本转为 URL 友好的 slug。"""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """截断文本到指定长度。"""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + suffix


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


def generate_trace_id() -> str:
    """生成 Trace ID。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = uuid.uuid4().hex[:8]
    return f"nm_{timestamp}_{random_part}"


def safe_get(data: Optional[Dict], *keys: str, default: Any = None) -> Any:
    """安全地获取嵌套字典值。"""
    if data is None:
        return default
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
    return current if current is not None else default


def parse_structured_response(content: str) -> Optional[Dict]:
    """从 LLM 响应中解析 JSON。

    处理常见的 Markdown 代码块包裹：
    ```json\n{...}\n```
    ```\n{...}\n```
    """
    if not content:
        return None
    content = content.strip()
    # 移除 ```json 或 ``` 包裹
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """将列表分块。"""
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def now_iso() -> str:
    """返回当前 ISO 格式时间字符串。"""
    return datetime.now(timezone.utc).isoformat()


def deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并两个字典。覆盖 base 中的值。"""
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class TimingContext:
    """计时上下文管理器。用于性能测量。"""

    def __init__(self, name: str = ""):
        self.name = name
        self.start: Optional[float] = None
        self.elapsed: Optional[float] = None

    def __enter__(self):
        import time
        self.start = time.time()
        return self

    def __exit__(self, *args):
        import time
        self.elapsed = time.time() - self.start

    def __str__(self):
        return f"{self.name}: {self.elapsed:.3f}s" if self.name else f"{self.elapsed:.3f}s"
