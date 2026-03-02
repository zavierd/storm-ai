from __future__ import annotations

import logging
from dataclasses import dataclass

from app.clients.base_client import BaseAIClient, EngineType

logger = logging.getLogger(__name__)


@dataclass
class EngineEntry:
    engine_type: EngineType
    client: BaseAIClient
    label: str
    is_default: bool = False


class EngineManager:
    """多引擎管理器，支持注册、切换、按类型获取"""

    def __init__(self):
        self._engines: dict[str, EngineEntry] = {}
        self._default_key: str | None = None

    def register(
        self,
        key: str,
        client: BaseAIClient,
        label: str = "",
        is_default: bool = False,
    ) -> None:
        entry = EngineEntry(
            engine_type=client.engine_type,
            client=client,
            label=label or key,
            is_default=is_default,
        )
        self._engines[key] = entry
        if is_default or self._default_key is None:
            self._default_key = key
        logger.info("注册引擎: %s (%s)%s", key, client.engine_type.value, " [默认]" if is_default else "")

    def get(self, key: str | None = None) -> BaseAIClient:
        """获取指定引擎，None 返回默认引擎"""
        target = key or self._default_key
        if not target or target not in self._engines:
            raise KeyError(f"引擎未注册: {target}")
        return self._engines[target].client

    def get_default(self) -> BaseAIClient:
        return self.get(None)

    def has(self, key: str) -> bool:
        return key in self._engines

    def list_engines(self) -> list[dict]:
        return [
            {
                "key": k,
                "type": e.engine_type.value,
                "label": e.label,
                "is_default": e.is_default,
            }
            for k, e in self._engines.items()
        ]

    @property
    def default_key(self) -> str | None:
        return self._default_key


engine_manager = EngineManager()
