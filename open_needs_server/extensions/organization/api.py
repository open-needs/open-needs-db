from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import load_only, joinedload

from open_needs_server.extensions.base import ONSExtension, OnsExtensionException

from .models import OrganizationModel
from open_needs_server.extensions.project.models import ProjectModel
from .schemas import OrganizationCreateSchema, OrganizationReturnSchema


async def get_organization(ext: ONSExtension, db: AsyncSession, organization_id: int):
    ext.fire_event("org_read", None)
    result = await db.execute(
        select(OrganizationModel).filter(OrganizationModel.id == organization_id)
    )
    result = result.scalars().first()
    result = ext.fire_event("org_read_done", result)
    return result


async def get_organization_by_title(
    ext: ONSExtension, db: AsyncSession, organization_title: int
):
    ext.fire_event("org_read", None)
    result = await db.execute(
        select(OrganizationModel).filter(OrganizationModel.title == organization_title)
    )
    result = result.scalars().first()
    result = ext.fire_event("org_read_done", result)
    return result


async def get_organizations(
    ext: ONSExtension, db: AsyncSession, skip: int = 0, limit: int = 100
):
    ext.fire_event("org_list_read", None)
    query = (
        select((OrganizationModel.id, OrganizationModel.title))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    result = result.all()

    final_result = ext.fire_event("org_list_read_done", result)
    return final_result


async def create_organization(
    ext: ONSExtension, db: AsyncSession, organization: OrganizationCreateSchema
):
    organization = ext.fire_event("org_create", organization)
    cursor = await db.execute(insert(OrganizationModel).values(**organization).returning(OrganizationModel.id))
    await db.commit()
    organization_id = cursor.fetchone()[0]
    new_organization = {**organization, "id": organization_id}
    new_organization = ext.fire_event("org_create_done", new_organization)
    return new_organization


async def update_organization(
    ext: ONSExtension,
    db: AsyncSession,
    organization_id: int,
    organization: OrganizationCreateSchema,
) -> OrganizationModel:
    organization = ext.fire_event("org_update", organization)

    query = select(OrganizationModel).where(OrganizationModel.id == organization_id)
    result = await db.execute(query)
    # db_organization = result.scalars().first()
    db_organization = result.scalar_one()

    for key, value in organization.items():
        setattr(db_organization, key, value)
    await db.commit()

    organization = ext.fire_event("org_update_done", db_organization.to_dict())
    return organization


async def delete_organization(
    ext: ONSExtension, db: AsyncSession, organization_id: int
) -> OrganizationModel:
    query = select(OrganizationModel).where(OrganizationModel.id == organization_id)
    db_organization = await db.execute(query)
    db_organization = db_organization.scalar()
    if not db_organization:
        raise OnsOrganizationNotFound(f"Unknown organization id: {organization_id}")

    ext.fire_event("org_delete", db_organization.to_dict())

    query = delete(OrganizationModel).where(OrganizationModel.id == organization_id)
    await db.execute(query)
    await db.commit()

    ext.fire_event("org_delete_done", db_organization.to_dict())

    return db_organization


class OnsOrganizationNotFound(OnsExtensionException):
    """A requested object could not be found"""
