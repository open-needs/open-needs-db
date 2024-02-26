from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete

from open_needs_server.extensions.base import ONSExtension, OnsExtensionException
from open_needs_server.extensions.domain.api import get_domain

from .models import ProjectModel
from .schemas import ProjectSchema


async def get_project(db: AsyncSession, project_id: int):
    result = await db.execute(
        select(ProjectModel).filter(ProjectModel.id == project_id)
    )
    return result.scalars().first()


async def get_project_by_title(db: AsyncSession, project_title: int):
    result = await db.execute(
        select(ProjectModel).filter(ProjectModel.title == project_title)
    )
    return result.scalars().first()


async def get_projects(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(ProjectModel).offset(skip).limit(limit))
    return result.scalars().all()


async def create_project(db: AsyncSession, project: ProjectSchema):
    domains_db = []
    for domain_id in project["domains"]:
        domain_db = await get_domain(db, domain_id)
        if not domain_db:
            raise HTTPException(404, detail=f"Unknown domain id: {domain_id}")
        domains_db.append(domain_db)


    project = {
        "title": project["title"],
        "organization_id": project["organization_id"]
    }
    cursor = await db.execute(insert(ProjectModel).values(**project).returning(ProjectModel.id))
    await db.commit()
    project_id = cursor.fetchone()[0]
    project_db = await get_project(db, project_id)
    project_db.domains = domains_db
    await db.commit()

    return project_db


# Project specific
async def get_organization_project_by_title(
    db: AsyncSession, organization_id: int, project_title: int
):
    result = await db.execute(
        select(ProjectModel).filter(
            ProjectModel.title == project_title,
            ProjectModel.organization_id == organization_id,
        )
    )
    return result.scalars().first()


async def update_project(
    ext: ONSExtension,
    db: AsyncSession,
    project_id: int,
    project: ProjectSchema,
) -> ProjectModel:
    project = ext.fire_event("project_update", project)
    query = select(ProjectModel).where(ProjectModel.id == project_id)
    result = await db.execute(query)
    db_project = result.scalar_one()

    for key, value in project.items():
        setattr(db_project, key, value)
    await db.commit()

    project = ext.fire_event("project_update_done", db_project.to_dict())
    return project


async def delete_project(
    ext: ONSExtension, db: AsyncSession, project_id: int
) -> ProjectModel:
    query = select(ProjectModel).where(ProjectModel.id == project_id)
    db_project = await db.execute(query)
    db_project = db_project.scalar()
    if not db_project:
        raise OnsProjectNotFound(f"Unknown project id: {project_id}")

    ext.fire_event("project_delete", db_project.to_dict())

    query = delete(ProjectModel).where(ProjectModel.id == project_id)
    await db.execute(query)
    await db.commit()

    ext.fire_event("project_delete_done", db_project.to_dict())

    return db_project


class OnsProjectNotFound(OnsExtensionException):
    """A requested object could not be found"""

    pass
