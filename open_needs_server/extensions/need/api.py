from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete

from open_needs_server.extensions.base import ONSExtension, OnsExtensionException
from open_needs_server.extensions.project.models import ProjectModel

from .models import NeedModel
from .schemas import NeedReturnSchema, NeedCreateSchema, NeedUpdateSchema


async def get_need(ext: ONSExtension, db: AsyncSession, need_id: int):
    result = await db.execute(select(NeedModel).filter(NeedModel.id == need_id))
    return result.scalars().first()


async def get_needs(
    ext: ONSExtension, db: AsyncSession, skip: int = 0, limit: int = 100
):
    ext.fire_event("need_read", None)
    result = await db.execute(select(NeedModel).offset(skip).limit(limit))
    result = ext.fire_event("need_read_done", result)
    return result.scalars().all()


async def create_need(ext: ONSExtension, db: AsyncSession, need: NeedReturnSchema):
    project_id = need["project_id"]
    result = await db.execute(
        select(ProjectModel).filter(ProjectModel.id == project_id)
    )
    db_project = result.scalars().first()

    if not db_project:
        raise OnsApiNeedException(f"Referenced project_id {project_id} not found")

    data = ext.fire_event("need_create", {"need": need, "project": db_project})
    need = data["need"]

    cursor = await db.execute(insert(NeedModel).values(**need).returning(NeedModel.id))
    await db.commit()
    need_id = cursor.fetchone()[0]

    need = ext.fire_event("need_create_done", need)

    return {**need, "id": need_id}


async def update_need(
    ext: ONSExtension, db: AsyncSession, need_id: int, need: NeedUpdateSchema
) -> NeedModel:
    need = ext.fire_event("need_update", need)

    query = select(NeedModel).where(NeedModel.id == need_id)
    result = await db.execute(query)
    db_need = result.scalar_one()

    for key, value in need.items():
        if value is not None:
            setattr(db_need, key, value)
    await db.commit()

    need = ext.fire_event("need_update_done", db_need.to_dict())
    return need


async def delete_need(ext: ONSExtension, db: AsyncSession, need_id: int) -> NeedModel:
    query = select(NeedModel).where(NeedModel.id == need_id)
    db_need = await db.execute(query)
    db_need = db_need.scalar()
    if not db_need:
        raise OnsNeedNotFound(f"Unknown need id: {need_id}")

    ext.fire_event("need_delete", db_need.to_dict())

    query = delete(NeedModel).where(NeedModel.id == need_id)
    await db.execute(query)
    await db.commit()

    ext.fire_event("need_delete_done", db_need.to_dict())

    return db_need


class OnsApiNeedException(BaseException):
    pass


class OnsNeedNotFound(OnsExtensionException):
    """A requested object could not be found"""
