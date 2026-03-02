from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.exceptions import PromptRenderError

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptEngine:
    """基于 Jinja2 的提示词模板渲染引擎"""

    def __init__(self, templates_dir: Path | str | None = None):
        self._templates_dir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self._templates_dir.mkdir(parents=True, exist_ok=True)

        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )
        logger.info("PromptEngine 初始化完成，模板目录: %s", self._templates_dir)

    def render(self, template_path: str, **kwargs) -> str:
        """渲染指定模板"""
        try:
            template = self._env.get_template(template_path)
            return template.render(**kwargs)
        except TemplateNotFound as e:
            raise PromptRenderError(
                message=f"模板未找到: {template_path}", detail=str(e)
            ) from e
        except Exception as e:
            raise PromptRenderError(
                message=f"模板渲染失败: {template_path}", detail=str(e)
            ) from e

    def list_templates(self) -> list[str]:
        """列出所有可用模板"""
        return self._env.list_templates()
