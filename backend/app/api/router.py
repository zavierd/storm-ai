from __future__ import annotations

from fastapi import APIRouter

from app.api import auth, credits, engines, health, interior_ai, projects, super_ai, toolbox
from app.models.common import FeatureInfo, FeatureListResponse
from app.prompts.registry import registry

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(credits.router)
api_router.include_router(projects.router)
api_router.include_router(engines.router)
api_router.include_router(super_ai.router)
api_router.include_router(interior_ai.router)
api_router.include_router(toolbox.router)


@api_router.get("/features", response_model=FeatureListResponse, tags=["功能列表"])
async def list_features(category: str | None = None):
    """获取所有已注册的 AI 功能列表"""
    features = registry.list_features(category=category)
    return FeatureListResponse(
        features=[
            FeatureInfo(
                key=f.feature_key,
                name=f.name,
                category=f.category,
                description=f.description,
                input_type=f.input_type,
                supports_mask=f.supports_mask,
            )
            for f in features
        ]
    )


# 健康检查挂在根路径
root_router = APIRouter()
root_router.include_router(health.router)
