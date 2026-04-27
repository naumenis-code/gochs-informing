#!/usr/bin/env python3
"""
API эндпоинты для управления группами контактов
Соответствует ТЗ, раздел 10: Контактная база — группы

Функционал:
- CRUD операции с группами
- Управление участниками (добавление/удаление)
- Получение списка для обзвона
- Массовые операции
- Статистика

Группы используются для:
- Организации контактов по отделам
- Массового обзвона
- Фильтрации и поиска
"""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА ГРУПП
# ============================================================================

@router.get("/")
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_system: Optional[bool] = Query(None),
    has_members: Optional[bool] = Query(None),
    sort_field: str = Query("name"),
    sort_direction: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка групп с фильтрацией и пагинацией
    
    Доступ: admin, operator, viewer
    """
    conditions = ["g.is_archived = false"]
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if search:
        conditions.append("(g.name ILIKE :s OR g.description ILIKE :s)")
        params["s"] = f"%{search}%"
    if is_active is not None:
        conditions.append("g.is_active = :active")
        params["active"] = is_active
    if is_system is not None:
        conditions.append("g.is_system = :sys")
        params["sys"] = is_system
    if has_members is not None:
        if has_members:
            conditions.append("g.member_count > 0")
        else:
            conditions.append("g.member_count = 0")
    
    where = " AND ".join(conditions)
    
    allowed_sorts = ["name", "member_count", "created_at"]
    if sort_field not in allowed_sorts:
        sort_field = "name"
    sort_dir = "DESC" if sort_direction.lower() == "desc" else "ASC"
    
    try:
        # Общее количество
        r = await db.execute(text(f"SELECT COUNT(*) FROM contact_groups g WHERE {where}"), params)
        total = r.scalar() or 0
        
        # Данные
        r = await db.execute(
            text(f"""
                SELECT g.* FROM contact_groups g
                WHERE {where}
                ORDER BY {sort_field} {sort_dir}
                LIMIT :limit OFFSET :offset
            """),
            params
        )
        
        items = []
        for row in r.fetchall():
            items.append({
                "id": str(row.id),
                "name": row.name,
                "description": row.description,
                "color": row.color or "#3498db",
                "is_active": row.is_active if row.is_active is not None else True,
                "is_archived": row.is_archived or False,
                "is_system": row.is_system or False,
                "member_count": row.member_count or 0,
                "total_member_count": row.member_count or 0,
                "default_priority": 5,
                "max_retries": 3,
                "created_by": str(row.created_by) if row.created_by else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if hasattr(row, 'updated_at') and row.updated_at else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "has_prev": page > 1
        }
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================================
# ПОЛУЧЕНИЕ ГРУППЫ ПО ID
# ============================================================================

@router.get("/{group_id}")
async def get_group(
    group_id: str,
    include_members: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение группы по ID с возможностью загрузки участников"""
    r = await db.execute(
        text("SELECT * FROM contact_groups WHERE id=:id AND is_archived=false"),
        {"id": group_id}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    
    # Подсчет типов номеров
    mobile_count = 0
    internal_count = 0
    members = []
    
    if include_members:
        try:
            mr = await db.execute(
                text("""
                    SELECT c.id, c.full_name, c.department, c.position, 
                           c.mobile_number, c.internal_number, c.email, c.is_active,
                           cgm.role, cgm.priority, cgm.added_at
                    FROM contacts c
                    JOIN contact_group_members cgm ON c.id=cgm.contact_id
                    WHERE cgm.group_id=:gid AND cgm.is_active=true AND c.is_archived=false
                    ORDER BY cgm.priority ASC, c.full_name ASC
                    LIMIT 100
                """),
                {"gid": group_id}
            )
            
            for m in mr.fetchall():
                if m.mobile_number:
                    mobile_count += 1
                if m.internal_number:
                    internal_count += 1
                members.append({
                    "contact_id": str(m.id),
                    "contact_name": m.full_name,
                    "department": m.department,
                    "position": m.position,
                    "mobile_number": m.mobile_number,
                    "internal_number": m.internal_number,
                    "email": m.email,
                    "is_active": m.is_active,
                    "role": m.role,
                    "priority": m.priority or 5,
                    "note": None,
                    "added_at": m.added_at.isoformat() if m.added_at else None,
                    "added_by": None
                })
        except Exception as e:
            logger.warning(f"Error loading members: {e}")
    
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "color": row.color or "#3498db",
        "is_active": row.is_active if row.is_active is not None else True,
        "is_archived": row.is_archived or False,
        "is_system": row.is_system or False,
        "member_count": row.member_count or 0,
        "total_member_count": row.member_count or 0,
        "mobile_members_count": mobile_count,
        "internal_members_count": internal_count,
        "default_priority": 5,
        "max_retries": 3,
        "created_by": str(row.created_by) if row.created_by else None,
        "updated_by": str(row.updated_by) if hasattr(row, 'updated_by') and row.updated_by else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if hasattr(row, 'updated_at') and row.updated_at else None,
        "members": members,
        "members_by_department": [],
        "active_members": len([m for m in members if m["is_active"]]),
        "inactive_members": len([m for m in members if not m["is_active"]])
    }


# ============================================================================
# СОЗДАНИЕ ГРУППЫ
# ============================================================================

@router.post("/", status_code=201)
async def create_group(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание новой группы
    
    Доступ: admin, operator
    Обязательное поле: name
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="Название группы обязательно")
    
    # Проверка уникальности
    r = await db.execute(
        text("SELECT id FROM contact_groups WHERE name=:n AND is_archived=false"),
        {"n": data["name"]}
    )
    if r.fetchone():
        raise HTTPException(status_code=409, detail="Группа с таким названием уже существует")
    
    try:
        r = await db.execute(
            text("""
                INSERT INTO contact_groups (name, description, color, created_by)
                VALUES (:n, :d, :c, :cb)
                RETURNING id, created_at
            """),
            {
                "n": data["name"],
                "d": data.get("description"),
                "c": data.get("color", "#3498db"),
                "cb": current_user.get("id")
            }
        )
        row = r.fetchone()
        
        # Добавляем контакты если указаны
        contact_ids = data.get("contact_ids", [])
        if contact_ids:
            for cid in contact_ids:
                try:
                    await db.execute(
                        text("""
                            INSERT INTO contact_group_members (contact_id, group_id, added_by)
                            VALUES (:cid, :gid, :uid)
                            ON CONFLICT (contact_id, group_id) DO NOTHING
                        """),
                        {"cid": cid, "gid": row.id, "uid": current_user.get("id")}
                    )
                except Exception:
                    pass
            
            # Обновляем счетчик
            r2 = await db.execute(
                text("SELECT COUNT(*) FROM contact_group_members WHERE group_id=:gid AND is_active=true"),
                {"gid": row.id}
            )
            member_count = r2.scalar() or 0
            await db.execute(
                text("UPDATE contact_groups SET member_count=:mc WHERE id=:gid"),
                {"mc": member_count, "gid": row.id}
            )
        
        await db.commit()
        
        logger.info(f"Создана группа: {data['name']}")
        
        return {
            "id": str(row.id),
            "name": data["name"],
            "description": data.get("description"),
            "color": data.get("color", "#3498db"),
            "is_active": True,
            "is_archived": False,
            "is_system": False,
            "member_count": len(contact_ids),
            "total_member_count": len(contact_ids),
            "default_priority": 5,
            "max_retries": 3,
            "created_by": current_user.get("id"),
            "created_at": row.created_at.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating group: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания: {str(e)}")


# ============================================================================
# ОБНОВЛЕНИЕ ГРУППЫ
# ============================================================================

@router.patch("/{group_id}")
async def update_group(
    group_id: str,
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновление группы (admin, operator)"""
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    r = await db.execute(text("SELECT * FROM contact_groups WHERE id=:id AND is_archived=false"), {"id": group_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Группа не найдена")
    
    updates = []
    params = {"id": group_id}
    
    for field in ["name", "description", "color", "is_active"]:
        if field in data and data[field] is not None:
            updates.append(f"{field}=:{field}")
            params[field] = data[field]
    
    if updates:
        await db.execute(text(f"UPDATE contact_groups SET {', '.join(updates)} WHERE id=:id"), params)
        await db.commit()
    
    return await get_group(group_id, False, db, current_user)


# ============================================================================
# УДАЛЕНИЕ/АРХИВИРОВАНИЕ ГРУППЫ
# ============================================================================

@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    hard_delete: bool = Query(False),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление группы
    
    - hard_delete=False: архивирование
    - hard_delete=True: полное удаление (только admin)
    """
    r = await db.execute(text("SELECT is_system FROM contact_groups WHERE id=:id"), {"id": group_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    if row.is_system:
        raise HTTPException(status_code=400, detail="Нельзя удалить системную группу")
    
    if hard_delete and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только администратор может полностью удалять")
    
    if hard_delete:
        await db.execute(text("DELETE FROM contact_group_members WHERE group_id=:id"), {"id": group_id})
        await db.execute(text("DELETE FROM contact_groups WHERE id=:id"), {"id": group_id})
        msg = "Группа удалена"
    else:
        await db.execute(text("UPDATE contact_groups SET is_archived=true, is_active=false WHERE id=:id"), {"id": group_id})
        msg = "Группа архивирована"
    
    await db.commit()
    return {"message": msg, "success": True}


# ============================================================================
# УПРАВЛЕНИЕ УЧАСТНИКАМИ
# ============================================================================

@router.post("/{group_id}/members")
async def add_members(
    group_id: str,
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Добавление контактов в группу
    
    Доступ: admin, operator
    data: {"contact_ids": ["uuid1", "uuid2", ...]}
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    contact_ids = data.get("contact_ids", [])
    if not contact_ids:
        raise HTTPException(status_code=400, detail="Укажите contact_ids")
    
    added = 0
    skipped = 0
    errors = []
    
    for cid in contact_ids:
        try:
            await db.execute(
                text("""
                    INSERT INTO contact_group_members (contact_id, group_id, added_by)
                    VALUES (:cid, :gid, :uid)
                    ON CONFLICT (contact_id, group_id) DO UPDATE SET is_active=true, removed_at=NULL
                """),
                {"cid": cid, "gid": group_id, "uid": current_user.get("id")}
            )
            added += 1
        except Exception as e:
            errors.append({"contact_id": cid, "error": str(e)})
    
    # Обновляем счетчик
    r = await db.execute(
        text("SELECT COUNT(*) FROM contact_group_members WHERE group_id=:gid AND is_active=true"),
        {"gid": group_id}
    )
    count = r.scalar() or 0
    await db.execute(text("UPDATE contact_groups SET member_count=:mc WHERE id=:gid"), {"mc": count, "gid": group_id})
    await db.commit()
    
    return {
        "total_processed": len(contact_ids),
        "success_count": added,
        "error_count": len(errors),
        "errors": errors,
        "message": f"Добавлено: {added}"
    }


@router.delete("/{group_id}/members")
async def remove_members(
    group_id: str,
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удаление контактов из группы"""
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    contact_ids = data.get("contact_ids", [])
    if not contact_ids:
        raise HTTPException(status_code=400, detail="Укажите contact_ids")
    
    for cid in contact_ids:
        await db.execute(
            text("UPDATE contact_group_members SET is_active=false, removed_at=NOW() WHERE contact_id=:cid AND group_id=:gid"),
            {"cid": cid, "gid": group_id}
        )
    
    # Обновляем счетчик
    r = await db.execute(
        text("SELECT COUNT(*) FROM contact_group_members WHERE group_id=:gid AND is_active=true"),
        {"gid": group_id}
    )
    count = r.scalar() or 0
    await db.execute(text("UPDATE contact_groups SET member_count=:mc WHERE id=:gid"), {"mc": count, "gid": group_id})
    await db.commit()
    
    return {"message": f"Удалено: {len(contact_ids)}", "success": True}


# ============================================================================
# СПИСОК ДЛЯ ОБЗВОНА
# ============================================================================

@router.get("/{group_id}/dialer-list")
async def get_dialer_list(
    group_id: str,
    prefer_mobile: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка для обзвона
    
    Доступ: admin, operator
    Возвращает контакты с номерами телефонов, отсортированные по приоритету
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    try:
        r = await db.execute(
            text("""
                SELECT c.id, c.full_name, c.mobile_number, c.internal_number, c.department,
                       COALESCE(cgm.priority, 5) as priority
                FROM contacts c
                JOIN contact_group_members cgm ON c.id=cgm.contact_id
                WHERE cgm.group_id=:gid AND cgm.is_active=true 
                  AND c.is_active=true AND c.is_archived=false
                  AND (c.mobile_number IS NOT NULL OR c.internal_number IS NOT NULL)
                ORDER BY priority ASC, c.full_name ASC
            """),
            {"gid": group_id}
        )
        
        contacts = []
        for row in r.fetchall():
            phone = row.mobile_number if (prefer_mobile and row.mobile_number) else (row.internal_number or row.mobile_number)
            contacts.append({
                "contact_id": str(row.id),
                "name": row.full_name,
                "phone": phone,
                "department": row.department,
                "priority": row.priority
            })
        
        group = await db.execute(text("SELECT name FROM contact_groups WHERE id=:id"), {"id": group_id})
        group_name = group.fetchone().name if group.fetchone() else "Группа"
        
        return {
            "group_id": group_id,
            "group_name": group_name,
            "total_contacts": len(contacts),
            "contacts": contacts
        }
        
    except Exception as e:
        logger.error(f"Dialer list error: {e}")
        return {"group_id": group_id, "group_name": "Группа", "total_contacts": 0, "contacts": []}


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get("/stats/summary")
async def get_group_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Статистика по группам"""
    try:
        r = await db.execute(text("SELECT COUNT(*) FROM contact_groups WHERE is_archived=false"))
        total = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM contact_groups WHERE is_active=true AND is_archived=false"))
        active = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM contact_groups WHERE is_system=true AND is_archived=false"))
        system = r.scalar() or 0
        
        r = await db.execute(text("SELECT AVG(member_count) FROM contact_groups WHERE is_archived=false"))
        avg_members = round(r.scalar() or 0, 1)
        
        # Самая большая группа
        r = await db.execute(
            text("SELECT name, member_count FROM contact_groups WHERE is_archived=false ORDER BY member_count DESC LIMIT 1")
        )
        largest = r.fetchone()
        
        return {
            "total_groups": total,
            "active_groups": active,
            "system_groups": system,
            "user_groups": total - system,
            "archived_groups": 0,
            "total_memberships": 0,
            "avg_members_per_group": avg_members,
            "groups_without_members": 0,
            "largest_group": {"name": largest.name, "count": largest.member_count} if largest else None
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total_groups": 0, "active_groups": 0, "system_groups": 0, "user_groups": 0}
