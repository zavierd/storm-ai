from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class EngineType(str, Enum):
    GEMINI_DIRECT = "gemini_direct"
    SWIFTASK = "swiftask"
    NEWAPI = "newapi"
    VENICE = "venice"
    VERTEX = "vertex"


@dataclass
class GenerationResult:
    """所有引擎的统一生成结果"""

    images: list[bytes] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    raw_response: dict = field(default_factory=dict)


class BaseAIClient(ABC):
    """AI 引擎客户端抽象基类，所有引擎必须实现"""

    engine_type: EngineType

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
        config: dict | None = None,
    ) -> GenerationResult:
        """图文混合生成"""
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        image_urls: list[str] | None = None,
    ) -> str:
        """纯文本生成"""
        ...

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """列出该引擎下可用模型"""
        ...
