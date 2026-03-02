"""
系统提示词管理器
每个功能有独立的系统提示词（.md文件），定义该功能的整体行为、风格、质量标准。
系统提示词是功能独立存在的核心价值。
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS_DIR = Path(__file__).parent / "system_prompts"


class SystemPromptManager:
    """管理各功能的系统提示词，支持热加载"""

    def __init__(self, prompts_dir: Path | str | None = None):
        self._dir = Path(prompts_dir) if prompts_dir else SYSTEM_PROMPTS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, str] = {}
        self._load_all()

    def _load_all(self) -> None:
        for f in self._dir.glob("*.md"):
            key = f.stem
            self._cache[key] = f.read_text(encoding="utf-8").strip()
        logger.info("加载了 %d 个系统提示词: %s", len(self._cache), list(self._cache.keys()))

    def get(self, feature_key: str) -> str | None:
        """获取功能的系统提示词，无则返回 None"""
        return self._cache.get(feature_key)

    def set(self, feature_key: str, content: str) -> None:
        """设置/更新功能的系统提示词（同时写入文件）"""
        self._cache[feature_key] = content.strip()
        path = self._dir / f"{feature_key}.md"
        path.write_text(content.strip(), encoding="utf-8")
        logger.info("更新系统提示词: %s", feature_key)

    def list_features(self) -> list[dict]:
        return [
            {"feature_key": k, "has_system_prompt": True, "length": len(v)}
            for k, v in self._cache.items()
        ]

    def reload(self) -> None:
        self._cache.clear()
        self._load_all()


system_prompt_manager = SystemPromptManager()
