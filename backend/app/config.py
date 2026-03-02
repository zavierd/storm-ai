from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Swiftask 中转站
    swiftask_api_key: str = Field(default="", description="Swiftask API 密钥")
    swiftask_default_model: str = Field(default="nano_banana_pro", description="Swiftask 默认模型 slug")

    # Google Gemini 直连（可选）
    gemini_api_key: str = Field(default="", description="Gemini API 密钥")
    gemini_model_name: str = Field(default="gemini-2.0-flash-exp", description="Gemini 模型名称")

    # Vertex AI 渠道（可选，默认仅按请求 channel=vertex 启用）
    vertex_enabled: bool = Field(
        default=False,
        description="启用 Vertex 渠道注册（仅在请求指定 channel=vertex 或显式默认开关时使用）",
    )
    vertex_as_default: bool = Field(
        default=False,
        description="显式启用后，Vertex 接管默认推理与生图引擎",
    )
    vertex_model_name: str = Field(
        default="gemini-3.1-flash-image-preview",
        description="Vertex 默认模型名称",
    )
    vertex_project_id: str = Field(default="", description="Vertex master 账号的项目 ID")
    vertex_location: str = Field(default="us-central1", description="Vertex master 账号区域")
    vertex_adc_path: str = Field(default="", description="Vertex master 账号 ADC JSON 路径（可选）")
    vertex_default_account: str = Field(
        default="master",
        description="Vertex 默认账号（请求未传 vertex_account 时生效）",
    )
    vertex_accounts_json: str = Field(
        default="",
        description="Vertex 多账号配置 JSON（键为账号名）",
    )
    vertex_accounts_file: str = Field(
        default="",
        description="Vertex 多账号配置文件路径（可选，JSON）",
    )

    # NewAPI 分发站（可选）
    newapi_api_key: str = Field(default="", description="NewAPI 分发站 API 密钥")
    newapi_base_url: str = Field(default="https://zapi.aicc0.com/v1", description="NewAPI 分发站基础 URL")
    newapi_default_model: str = Field(default="gpt-4o", description="NewAPI 默认模型（兼容 fallback）")
    newapi_reasoning_model: str = Field(default="gemini-3-flash", description="NewAPI 推理模型")
    newapi_generation_model: str = Field(default="grok-imagine-1.0", description="NewAPI 生图模型（走 /images/generations）")
    newapi_as_default: bool = Field(
        default=False,
        description="为 true 且 NEWAPI_API_KEY 存在时，NewAPI 作为默认推理与生图引擎",
    )

    # Venice AI（可选，OpenAI 兼容）
    venice_api_key: str = Field(default="", description="Venice AI API 密钥")
    venice_base_url: str = Field(default="https://api.venice.ai/api/v1", description="Venice AI 基础 URL")
    venice_default_model: str = Field(default="venice-uncensored", description="Venice 默认模型")
    venice_generation_model: str = Field(
        default="nano-banana-2",
        description="Venice 生图模型（走原生 /image/generate 端点）",
    )
    venice_as_reasoning: bool = Field(
        default=False,
        description="为 true 且 VENICE_API_KEY 存在时，将推理客户端切换到 Venice（不影响生图）",
    )
    venice_as_generation: bool = Field(
        default=False,
        description="为 true 且 VENICE_API_KEY 存在时，Venice 作为默认生图引擎（与 NEWAPI_AS_DEFAULT 互斥）",
    )

    # 数据库
    database_url: str = Field(default="", description="PostgreSQL 连接串")
    jwt_secret: str = Field(default="storm-ai-secret-change-me-in-production", description="JWT 签名密钥")

    max_image_size_mb: int = Field(default=10, description="最大图片大小(MB)")
    max_retries: int = Field(default=3, description="最大重试次数")
    log_level: str = Field(default="INFO", description="日志级别")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"], description="允许的跨域来源"
    )
    backend_public_url: str = Field(
        default="http://localhost:8000",
        description="后端对外可访问基地址，用于拼接生成图片静态URL",
    )
    credits_default_generation_cost: float = Field(
        default=10.0,
        description="生成接口默认积分消耗（当功能未配置单独费率时使用）",
    )
    credits_feature_rates_json: str = Field(
        default="",
        description='按 feature_key 覆盖费率的 JSON，例如 {"banana-pro-edit":12,"toolbox-t2i":8}',
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
