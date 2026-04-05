from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin, get_optional_admin
from app.db.session import get_db
from app.models import AdminUser, Template, TemplateStatus, TemplateVersion
from app.rules_engine.template_schema import DEFAULT_TEMPLATE_BLOCKS, TemplateRules
from app.services.audit import log_admin_action

router = APIRouter()


class TemplateCreateRequest(BaseModel):
    university_id: int
    name: str
    type_work: str
    year: str


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    university_id: int | None = None
    type_work: str | None = None
    year: str | None = None
    active: bool | None = None


class TemplateVersionCreateRequest(BaseModel):
    rules: TemplateRules


@router.get("")
async def list_templates(
    university_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser | None = Depends(get_optional_admin),
) -> list[dict]:
    stmt = select(Template).order_by(Template.id)
    if admin is None:
        stmt = stmt.where(
            Template.status == TemplateStatus.published,
            Template.active.is_(True),
        )
    if university_id:
        stmt = stmt.where(Template.university_id == university_id)
    rows = list(await db.scalars(stmt))

    if not rows:
        return []

    template_ids = [r.id for r in rows]
    latest_sq = (
        select(
            TemplateVersion.template_id,
            func.max(TemplateVersion.id).label("vid"),
        )
        .where(TemplateVersion.template_id.in_(template_ids))
        .group_by(TemplateVersion.template_id)
    )
    ver_rows = await db.execute(latest_sq)
    ver_map = {r.template_id: r.vid for r in ver_rows}

    return [
        {
            "id": r.id,
            "university_id": r.university_id,
            "name": r.name,
            "type_work": r.type_work,
            "year": r.year,
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "active": r.active,
            "latest_version_id": ver_map.get(r.id),
        }
        for r in rows
    ]


@router.post("")
async def create_template(
    payload: TemplateCreateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = Template(
        university_id=payload.university_id,
        name=payload.name,
        type_work=payload.type_work,
        year=payload.year,
        status=TemplateStatus.draft,
        active=True,
    )
    db.add(item)
    await db.flush()

    version = TemplateVersion(
        template_id=item.id,
        version_number=1,
        rules_json={"blocks": [b.model_dump() for b in DEFAULT_TEMPLATE_BLOCKS]},
        created_at=datetime.utcnow(),
        created_by_admin_id=current_admin.id,
    )
    db.add(version)

    await log_admin_action(
        db=db,
        admin_user_id=current_admin.id,
        action="template.create",
        entity_type="template",
        entity_id=str(item.id),
        diff={"after": payload.model_dump()},
    )
    await db.commit()
    return {"id": item.id, "version_id": version.id}


@router.get("/{template_id}/blocks")
async def get_template_blocks(template_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    version = await db.scalar(
        select(TemplateVersion)
        .where(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version_number.desc())
        .limit(1)
    )
    if not version:
        raise HTTPException(status_code=404, detail="Версия шаблона не найдена")
    return {
        "template_id": template_id,
        "version_id": version.id,
        "version_number": version.version_number,
        "blocks": version.rules_json.get("blocks", []),
    }


@router.post("/{template_id}/versions")
async def create_template_version(
    template_id: int,
    payload: TemplateVersionCreateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    last_ver = await db.scalar(
        select(func.max(TemplateVersion.version_number)).where(TemplateVersion.template_id == template_id)
    )
    next_ver = int(last_ver or 0) + 1
    version = TemplateVersion(
        template_id=template_id,
        version_number=next_ver,
        rules_json=payload.rules.model_dump(),
        created_at=datetime.utcnow(),
        created_by_admin_id=current_admin.id,
    )
    db.add(version)

    await log_admin_action(
        db=db,
        admin_user_id=current_admin.id,
        action="template.version.create",
        entity_type="template",
        entity_id=str(template_id),
        diff={"version_number": next_ver, "rules": payload.rules.model_dump()},
    )
    await db.commit()
    return {"template_id": template_id, "version_id": version.id, "version_number": next_ver}


@router.post("/{template_id}/publish")
async def publish_template(
    template_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    before = template.status.value if hasattr(template.status, "value") else template.status
    template.status = TemplateStatus.published

    after = template.status.value if hasattr(template.status, "value") else template.status
    await log_admin_action(
        db=db,
        admin_user_id=current_admin.id,
        action="template.publish",
        entity_type="template",
        entity_id=str(template_id),
        diff={"before": before, "after": after},
    )
    await db.commit()
    return {"template_id": template_id, "status": after}


@router.get("/{template_id}")
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return {
        "id": template.id,
        "university_id": template.university_id,
        "name": template.name,
        "type_work": template.type_work,
        "year": template.year,
        "status": template.status.value if hasattr(template.status, "value") else template.status,
        "active": template.active,
    }


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    payload: TemplateUpdateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    before = {
        "name": template.name,
        "university_id": template.university_id,
        "type_work": template.type_work,
        "year": template.year,
        "active": template.active,
    }

    if payload.name is not None:
        template.name = payload.name
    if payload.university_id is not None:
        template.university_id = payload.university_id
    if payload.type_work is not None:
        template.type_work = payload.type_work
    if payload.year is not None:
        template.year = payload.year
    if payload.active is not None:
        template.active = payload.active

    after = {
        "name": template.name,
        "university_id": template.university_id,
        "type_work": template.type_work,
        "year": template.year,
        "active": template.active,
    }

    await log_admin_action(
        db=db,
        admin_user_id=current_admin.id,
        action="template.update",
        entity_type="template",
        entity_id=str(template_id),
        diff={"before": before, "after": after},
    )
    await db.commit()
    return {"id": template.id, "status": "updated"}
