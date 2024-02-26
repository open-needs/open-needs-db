from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete

from open_needs_server.extensions.base import ONSExtension, OnsExtensionException

from .models import DomainModel
from .schemas import DomainSchema


async def get_domain(db: AsyncSession, domain_id: int):
    result = await db.execute(select(DomainModel).filter(DomainModel.id == domain_id))
    return result.scalars().first()


async def get_domain_by_title(db: AsyncSession, domain_title: int):
    result = await db.execute(
        select(DomainModel).filter(DomainModel.title == domain_title)
    )
    return result.scalars().first()


async def get_domains(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(DomainModel).offset(skip).limit(limit))
    return result.scalars().all()


async def create_domain(db: AsyncSession, domain: DomainSchema):
    cursor = await db.execute(insert(DomainModel).values(**domain).returning(DomainModel.id))
    await db.commit()
    domain_id = cursor.fetchone()[0]
    return {**domain, "id": domain_id}


# Domain specific


async def get_organization_domain_by_title(
    db: AsyncSession, organization_id: int, domain_title: int
):
    result = await db.execute(
        select(DomainModel).filter(
            DomainModel.title == domain_title,
            DomainModel.organization_id == organization_id,
        )
    )
    return result.scalars().first()


async def update_domain(
    ext: ONSExtension,
    db: AsyncSession,
    domain_id: int,
    domain: DomainSchema,
) -> DomainModel:
    domain = ext.fire_event("domain_update", domain)
    query = select(DomainModel).where(DomainModel.id == domain_id)
    result = await db.execute(query)
    db_domain = result.scalar_one()

    for key, value in domain.items():
        setattr(db_domain, key, value)
    await db.commit()

    domain = ext.fire_event("domain_update_done", db_domain.to_dict())
    return domain


async def delete_domain(
    ext: ONSExtension, db: AsyncSession, domain_id: int
) -> DomainModel:
    query = select(DomainModel).where(DomainModel.id == domain_id)
    db_domain = await db.execute(query)
    db_domain = db_domain.scalar()
    if not db_domain:
        raise OnsDomainNotFound(f"Unknown domain id: {domain_id}")

    ext.fire_event("domain_delete", db_domain.to_dict())

    query = delete(DomainModel).where(DomainModel.id == domain_id)
    await db.execute(query)
    await db.commit()

    ext.fire_event("domain_delete_done", db_domain.to_dict())

    return db_domain


class OnsDomainNotFound(OnsExtensionException):
    """A requested object could not be found"""
