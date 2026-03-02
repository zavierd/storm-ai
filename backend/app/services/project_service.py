from __future__ import annotations

from sqlalchemy import func, select

from app.database import get_session
from app.models.db_models import GenerationHistory, Project


def _normalize_name(name: str | None) -> str:
    value = (name or "").strip()
    return value[:120] if value else "未命名项目"


async def get_or_create_default_project(user_id: str) -> dict:
    async with get_session() as session:
        result = await session.execute(
            select(Project).where(
                Project.user_id == user_id,
                Project.is_default.is_(True),
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            project = Project(
                user_id=user_id,
                name="未命名项目",
                is_default=True,
            )
            session.add(project)
            await session.flush()
        return {
            "id": project.id,
            "name": project.name,
            "cover_image_url": project.cover_image_url,
            "is_default": project.is_default,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }


async def resolve_project_id(user_id: str, project_id: str | None) -> str:
    if project_id:
        async with get_session() as session:
            result = await session.execute(
                select(Project.id).where(
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
            )
            existed = result.scalar_one_or_none()
            if not existed:
                raise ValueError("项目不存在或无权限")
            return project_id
    default_project = await get_or_create_default_project(user_id)
    return default_project["id"]


async def create_project(user_id: str, name: str) -> dict:
    async with get_session() as session:
        project = Project(
            user_id=user_id,
            name=_normalize_name(name),
            is_default=False,
        )
        session.add(project)
        await session.flush()
        return {
            "id": project.id,
            "name": project.name,
            "cover_image_url": project.cover_image_url,
            "is_default": project.is_default,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "image_count": 0,
            "last_generated_at": None,
        }


async def update_project(user_id: str, project_id: str, name: str) -> dict:
    async with get_session() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("项目不存在或无权限")
        project.name = _normalize_name(name)
        await session.flush()
        return {
            "id": project.id,
            "name": project.name,
            "cover_image_url": project.cover_image_url,
            "is_default": project.is_default,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }


async def list_projects(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    async with get_session() as session:
        stmt = (
            select(
                Project,
                func.count(GenerationHistory.id).label("image_count"),
                func.max(GenerationHistory.created_at).label("last_generated_at"),
            )
            .outerjoin(GenerationHistory, GenerationHistory.project_id == Project.id)
            .where(Project.user_id == user_id)
            .group_by(Project.id)
            .order_by(Project.is_default.desc(), Project.updated_at.desc(), Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await session.execute(stmt)).all()
        return [
            {
                "id": project.id,
                "name": project.name,
                "cover_image_url": project.cover_image_url,
                "is_default": project.is_default,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "image_count": int(image_count or 0),
                "last_generated_at": last_generated_at.isoformat() if last_generated_at else None,
            }
            for project, image_count, last_generated_at in rows
        ]


async def get_project(user_id: str, project_id: str) -> dict | None:
    async with get_session() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            return None
        count_stmt = await session.execute(
            select(func.count(GenerationHistory.id)).where(
                GenerationHistory.user_id == user_id,
                GenerationHistory.project_id == project_id,
            )
        )
        image_count = count_stmt.scalar_one() or 0
        return {
            "id": project.id,
            "name": project.name,
            "cover_image_url": project.cover_image_url,
            "is_default": project.is_default,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "image_count": int(image_count),
        }


async def list_project_generations(
    user_id: str, project_id: str, limit: int = 20, offset: int = 0
) -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(GenerationHistory)
            .where(
                GenerationHistory.user_id == user_id,
                GenerationHistory.project_id == project_id,
            )
            .order_by(GenerationHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "project_id": r.project_id,
                "feature_key": r.feature_key,
                "prompt_text": r.prompt_text,
                "room_type": r.room_type,
                "result_image_url": r.result_image_url,
                "credits_cost": r.credits_cost,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

