from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """功能配置"""

    feature_key: str
    name: str
    category: str
    template_path: str
    description: str = ""
    input_type: Literal["single_image", "multi_image", "text_only"] = "single_image"
    supports_mask: bool = False


class FeatureRegistry:
    """功能注册表，管理所有 AI 功能的配置"""

    def __init__(self):
        self._features: dict[str, FeatureConfig] = {}

    def register(self, feature_config: FeatureConfig) -> None:
        """注册功能配置"""
        self._features[feature_config.feature_key] = feature_config
        logger.info("注册功能: %s (%s)", feature_config.feature_key, feature_config.name)

    def get(self, feature_key: str) -> FeatureConfig:
        """获取功能配置"""
        config = self._features.get(feature_key)
        if not config:
            raise KeyError(f"功能未注册: {feature_key}")
        return config

    def list_features(self, category: str | None = None) -> list[FeatureConfig]:
        """列出功能，可按分类过滤"""
        features = list(self._features.values())
        if category:
            features = [f for f in features if f.category == category]
        return features

    def feature(
        self,
        feature_key: str,
        name: str,
        category: str,
        template_path: str,
        description: str = "",
        input_type: Literal["single_image", "multi_image", "text_only"] = "single_image",
        supports_mask: bool = False,
    ) -> Callable:
        """装饰器：在 Service 方法上标注功能配置并自动注册"""
        config = FeatureConfig(
            feature_key=feature_key,
            name=name,
            category=category,
            template_path=template_path,
            description=description,
            input_type=input_type,
            supports_mask=supports_mask,
        )
        self.register(config)

        def decorator(func: Callable) -> Callable:
            func._feature_config = config  # type: ignore[attr-defined]
            return func

        return decorator


# 全局单例
registry = FeatureRegistry()
