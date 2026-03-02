from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router, root_router
from app.clients.engine_manager import engine_manager
from app.clients.swiftask_client import SwiftaskClient, SwiftaskConfig
from app.config import get_settings
from app.middleware.error_handler import register_exception_handlers
from app.middleware.request_logger import RequestLoggerMiddleware
from app.prompts.engine import PromptEngine
from app.services.interior_ai_service import InteriorAIService
from app.services.pipeline import TwoStagePipeline
from app.services.super_ai_service import SuperAIService
from app.services.toolbox_service import ToolboxService

logger = logging.getLogger(__name__)


def _load_vertex_account_payload(settings) -> dict[str, dict[str, Any]]:
    """加载并合并 Vertex 账号池配置（文件 + JSON 字符串）。"""
    payload: dict[str, dict[str, Any]] = {}

    def _merge(raw: Any, source: str) -> None:
        if not isinstance(raw, dict):
            logger.warning("Vertex 账号配置格式无效（%s）：应为 JSON 对象", source)
            return
        for account, cfg in raw.items():
            if not isinstance(cfg, dict):
                logger.warning("Vertex 账号 %s 配置无效（%s）：应为对象", account, source)
                continue
            payload[str(account).strip()] = cfg

    if settings.vertex_accounts_file:
        file_path = Path(settings.vertex_accounts_file).expanduser()
        try:
            content = file_path.read_text(encoding="utf-8")
            _merge(json.loads(content), f"file={file_path}")
        except FileNotFoundError:
            logger.warning("VERTEX_ACCOUNTS_FILE 不存在: %s", file_path)
        except Exception as e:
            logger.warning("读取 VERTEX_ACCOUNTS_FILE 失败: %s", e)

    if settings.vertex_accounts_json:
        try:
            _merge(json.loads(settings.vertex_accounts_json), "VERTEX_ACCOUNTS_JSON")
        except Exception as e:
            logger.warning("解析 VERTEX_ACCOUNTS_JSON 失败: %s", e)

    return payload


def _build_vertex_configs(settings):
    from app.clients.vertex_client import VertexConfig

    payload = _load_vertex_account_payload(settings)

    # 顶层 master 配置兜底（兼容旧配置）
    if settings.vertex_project_id:
        master_seed = {
            "project_id": settings.vertex_project_id,
            "location": settings.vertex_location,
            "model_name": settings.vertex_model_name,
            "adc_path": settings.vertex_adc_path,
        }
        master_existing = payload.get("master", {})
        if not isinstance(master_existing, dict):
            master_existing = {}
        payload["master"] = {**master_seed, **master_existing}

    configs: dict[str, VertexConfig] = {}
    for account, cfg in payload.items():
        account_name = str(account).strip()
        if not account_name:
            continue

        project_id = str(cfg.get("project_id") or "").strip()
        if not project_id:
            logger.warning("跳过 Vertex 账号 %s：缺少 project_id", account_name)
            continue

        location = str(cfg.get("location") or settings.vertex_location or "us-central1").strip()
        model_name = str(cfg.get("model_name") or settings.vertex_model_name).strip() or settings.vertex_model_name
        credentials_path = (
            str(cfg.get("credentials_path") or cfg.get("adc_path") or "").strip()
            or None
        )
        if account_name == "master" and not credentials_path and settings.vertex_adc_path:
            credentials_path = settings.vertex_adc_path.strip() or None

        configs[account_name] = VertexConfig(
            account=account_name,
            project_id=project_id,
            location=location,
            model_name=model_name,
            credentials_path=credentials_path,
        )

    return configs


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    logger.info("正在初始化服务...")

    from app.database import init_db, close_db
    await init_db()

    prompt_engine = PromptEngine()

    # ---- 注册 AI 引擎 ----
    reasoning_client = None
    generation_client = None

    use_venice_generation = settings.venice_as_generation and bool(settings.venice_api_key)
    use_newapi_default = settings.newapi_as_default and bool(settings.newapi_api_key) and not use_venice_generation
    if settings.newapi_as_default and not settings.newapi_api_key:
        logger.warning("NEWAPI_AS_DEFAULT=true 但未配置 NEWAPI_API_KEY，回退到原有默认引擎逻辑")
    if settings.venice_as_generation and not settings.venice_api_key:
        logger.warning("VENICE_AS_GENERATION=true 但未配置 VENICE_API_KEY，回退到原有默认引擎逻辑")
    if use_venice_generation and settings.newapi_as_default:
        logger.info("VENICE_AS_GENERATION 优先，NEWAPI_AS_DEFAULT 降级为非默认")

    if settings.swiftask_api_key:
        gen_swiftask = SwiftaskClient(SwiftaskConfig(
            api_key=settings.swiftask_api_key,
            default_model=settings.swiftask_default_model,
        ))
        engine_manager.register(
            "swiftask", gen_swiftask,
            label="Swiftask 生图引擎",
            is_default=not use_newapi_default and not use_venice_generation,
        )
        if not use_newapi_default and not use_venice_generation:
            generation_client = gen_swiftask

        reasoning_swiftask = SwiftaskClient(SwiftaskConfig(
            api_key=settings.swiftask_api_key,
            default_model="gemini-3-pro",
        ))
        engine_manager.register("swiftask_reasoning", reasoning_swiftask, label="Swiftask 推理引擎")
        if not use_newapi_default:
            reasoning_client = reasoning_swiftask

    if settings.gemini_api_key:
        from app.clients.gemini_client import GeminiClient
        gemini = GeminiClient(api_key=settings.gemini_api_key, model_name=settings.gemini_model_name)
        engine_manager.register(
            "gemini_direct", gemini,
            label="Google Gemini 直连",
            is_default=not settings.swiftask_api_key and not use_newapi_default and not use_venice_generation,
        )
        if not generation_client:
            generation_client = gemini
        if not reasoning_client:
            reasoning_client = gemini

    if settings.newapi_api_key:
        from app.clients.newapi_client import NewAPIClient, NewAPIConfig
        if use_newapi_default:
            newapi_gen = NewAPIClient(NewAPIConfig(
                api_key=settings.newapi_api_key,
                base_url=settings.newapi_base_url,
                default_model=settings.newapi_generation_model,
            ))
            newapi_reason = NewAPIClient(NewAPIConfig(
                api_key=settings.newapi_api_key,
                base_url=settings.newapi_base_url,
                default_model=settings.newapi_reasoning_model,
            ))
            engine_manager.register("newapi", newapi_gen, label="NewAPI 生图引擎", is_default=True)
            engine_manager.register("newapi_reasoning", newapi_reason, label="NewAPI 推理引擎")
            generation_client = newapi_gen
            reasoning_client = newapi_reason
            logger.info(
                "NewAPI 默认模式：推理[%s] + 生图[%s]",
                settings.newapi_reasoning_model, settings.newapi_generation_model,
            )
        else:
            fallback_model = settings.newapi_default_model or settings.newapi_reasoning_model
            newapi = NewAPIClient(NewAPIConfig(
                api_key=settings.newapi_api_key,
                base_url=settings.newapi_base_url,
                default_model=fallback_model,
            ))
            engine_manager.register("newapi", newapi, label="NewAPI 分发站")
            if not reasoning_client:
                reasoning_client = newapi

    # ---- Venice AI（可选，原生生图 + OpenAI 兼容推理）----
    if settings.venice_api_key:
        from app.clients.venice_client import VeniceClient
        from app.clients.newapi_client import NewAPIConfig as _VeniceConfig

        venice_model = (
            settings.venice_generation_model if use_venice_generation
            else settings.venice_default_model
        )
        venice = VeniceClient(_VeniceConfig(
            api_key=settings.venice_api_key,
            base_url=settings.venice_base_url,
            default_model=venice_model,
        ))
        engine_manager.register(
            "venice", venice,
            label="Venice AI 生图引擎" if use_venice_generation else "Venice AI",
            is_default=use_venice_generation,
        )

        if use_venice_generation:
            generation_client = venice
            logger.info(
                "Venice 已接管生图引擎，模型: %s（原生 /image/generate）",
                venice_model,
            )

        if settings.venice_as_reasoning and reasoning_client:
            reasoning_client = venice
            logger.info("Venice 已接管推理客户端，模型: %s", venice_model)

    # ---- Vertex AI（可选，按 channel=vertex 触发；可选接管默认）----
    vertex_enabled = settings.vertex_enabled or settings.vertex_as_default
    if settings.vertex_as_default and not settings.vertex_enabled:
        logger.info("VERTEX_AS_DEFAULT=true，自动启用 Vertex 渠道注册")

    if vertex_enabled:
        from app.clients.vertex_client import VertexClient

        vertex_configs = _build_vertex_configs(settings)
        preferred_account = (settings.vertex_default_account or "master").strip() or "master"
        registered_accounts: list[str] = []

        for account, cfg in vertex_configs.items():
            key = f"vertex:{account}"
            try:
                engine_manager.register(
                    key,
                    VertexClient(cfg),
                    label=f"Vertex AI ({account})",
                )
                registered_accounts.append(account)
            except Exception as e:
                logger.error("注册 Vertex 账号失败（%s）: %s", account, e)

        if settings.vertex_as_default and registered_accounts:
            active_account = preferred_account
            if active_account not in registered_accounts:
                active_account = "master" if "master" in registered_accounts else registered_accounts[0]
                logger.warning(
                    "VERTEX_DEFAULT_ACCOUNT=%s 未注册，回退到 %s",
                    preferred_account,
                    active_account,
                )
            active_key = f"vertex:{active_account}"
            active_client = engine_manager.get(active_key)
            # 通过同 key 再注册一次，提升为默认引擎，避免改动 EngineManager 结构。
            engine_manager.register(
                active_key,
                active_client,
                label=f"Vertex AI ({active_account})",
                is_default=True,
            )
            reasoning_client = active_client
            generation_client = active_client
            logger.info("Vertex 已接管默认推理/生图引擎，账号: %s", active_account)
        elif not registered_accounts:
            logger.warning("Vertex 已启用但没有可用账号，需配置 master 或账号池 project_id")

    # ---- 创建两阶段管线 ----
    pipeline = None
    if reasoning_client and generation_client:
        pipeline = TwoStagePipeline(
            reasoning_client=reasoning_client,
            generation_client=generation_client,
            engine_manager=engine_manager,
            vertex_default_account=settings.vertex_default_account,
        )
        logger.info("两阶段管线就绪: 推理[%s] → 生图[%s]",
                     reasoning_client.engine_type.value, generation_client.engine_type.value)

    default_client = engine_manager.get_default()

    # ---- 初始化 Service ----
    super_ai_service = SuperAIService(default_client, prompt_engine)
    interior_ai_service = InteriorAIService(default_client, prompt_engine)
    toolbox_service = ToolboxService(default_client, prompt_engine)
    for service in (super_ai_service, interior_ai_service, toolbox_service):
        service.set_engine_manager(
            engine_manager=engine_manager,
            vertex_default_account=settings.vertex_default_account,
        )

    if pipeline:
        super_ai_service.set_pipeline(pipeline)
        interior_ai_service.set_pipeline(pipeline)
        toolbox_service.set_pipeline(pipeline)

    app.state.engine_manager = engine_manager
    app.state.pipeline = pipeline
    app.state.prompt_engine = prompt_engine
    app.state.super_ai_service = super_ai_service
    app.state.interior_ai_service = interior_ai_service
    app.state.toolbox_service = toolbox_service

    logger.info("服务初始化完成，默认引擎: %s, 管线: %s",
                engine_manager.default_key, "启用" if pipeline else "未启用")
    yield

    for entry in engine_manager._engines.values():
        if hasattr(entry.client, "close"):
            await entry.client.close()
    await close_db()
    logger.info("服务关闭")


app = FastAPI(
    title="风暴AI - 室内设计平台",
    description="两阶段管线：推理模型优化提示词 → 生图模型出图",
    version="0.4.0",
    lifespan=lifespan,
)

settings = get_settings()
generated_images_dir = Path(__file__).resolve().parent.parent / "generated_images"
generated_images_dir.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggerMiddleware)

register_exception_handlers(app)

app.mount("/generated-images", StaticFiles(directory=str(generated_images_dir)), name="generated-images")
app.include_router(root_router)
app.include_router(api_router)
