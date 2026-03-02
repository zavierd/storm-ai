from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_id
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["项目"])


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class UpdateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.get("")
async def list_projects(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    records = await project_service.list_projects(user_id=user_id, limit=limit, offset=offset)
    return {"success": True, "records": records, "count": len(records)}


@router.post("")
async def create_project(
    request_body: CreateProjectRequest,
    user_id: str = Depends(get_current_user_id),
):
    record = await project_service.create_project(user_id=user_id, name=request_body.name)
    return {"success": True, "record": record}


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    request_body: UpdateProjectRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        record = await project_service.update_project(
            user_id=user_id,
            project_id=project_id,
            name=request_body.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "record": record}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
):
    record = await project_service.get_project(user_id=user_id, project_id=project_id)
    if not record:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"success": True, "record": record}


@router.get("/{project_id}/generations")
async def list_project_generations(
    project_id: str,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    project = await project_service.get_project(user_id=user_id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    records = await project_service.list_project_generations(
        user_id=user_id,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "project": project,
        "records": records,
        "count": len(records),
    }

