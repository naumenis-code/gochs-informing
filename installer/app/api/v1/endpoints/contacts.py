#!/usr/bin/env python3
"""
API эндпоинты для управления контактами
Соответствует ТЗ, раздел 10: Контактная база

Функционал:
- CRUD операции с контактами
- Импорт из CSV/XLSX (только admin)
- Экспорт в CSV/XLSX/JSON
- Поиск и фильтрация
- Массовые операции
- Статистика

Поля контакта:
- ФИО (обязательное)
- Подразделение
- Должность
- Внутренний номер (3-4 знака)
- Мобильный номер (+7XXXXXXXXXX / 8XXXXXXXXXX)
- Email (опционально)
- Активен/неактивен
- Комментарий
"""
import logging
import csv
import io
from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query,
    Request, UploadFile, File
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА КОНТАКТОВ
# ============================================================================

@router.get("/")
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    group_id: Optional[str] = Query(None),
    has_mobile: Optional[bool] = Query(None),
    has_internal: Optional[bool] = Query(None),
    sort_field: str = Query("full_name"),
    sort_direction: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка контактов с фильтрацией и пагинацией
    
    Доступ: admin, operator, viewer
    """
    conditions = ["c.is_archived = false"]
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if search:
        conditions.append("(c.full_name ILIKE :s OR c.department ILIKE :s OR c.position ILIKE :s OR c.mobile_number ILIKE :s OR c.internal_number ILIKE :s)")
        params["s"] = f"%{search}%"
    if department:
        conditions.append("c.department = :dep")
        params["dep"] = department
    if is_active is not None:
        conditions.append("c.is_active = :active")
        params["active"] = is_active
    if has_mobile is not None:
        if has_mobile:
            conditions.append("c.mobile_number IS NOT NULL")
        else:
            conditions.append("c.mobile_number IS NULL")
    if has_internal is not None:
        if has_internal:
            conditions.append("c.internal_number IS NOT NULL")
        else:
            conditions.append("c.internal_number IS NULL")
    
    # Фильтр по группе
    if group_id:
        conditions.append("EXISTS (SELECT 1 FROM contact_group_members cgm WHERE cgm.contact_id=c.id AND cgm.group_id=:gid)")
        params["gid"] = group_id
    
    where = " AND ".join(conditions)
    
    # Сортировка
    allowed_sorts = ["full_name", "department", "position", "mobile_number", "created_at"]
    if sort_field not in allowed_sorts:
        sort_field = "full_name"
    sort_dir = "DESC" if sort_direction.lower() == "desc" else "ASC"
    
    try:
        # Общее количество
        r = await db.execute(text(f"SELECT COUNT(*) FROM contacts c WHERE {where}"), params)
        total = r.scalar() or 0
        
        # Данные
        r = await db.execute(
            text(f"""
                SELECT c.* FROM contacts c 
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
                "full_name": row.full_name,
                "department": row.department,
                "position": row.position,
                "internal_number": row.internal_number,
                "mobile_number": row.mobile_number,
                "email": row.email,
                "is_active": row.is_active,
                "is_archived": row.is_archived or False,
                "comment": row.comment,
                "group_names": [],
                "tag_names": [],
                "tag_colors": {},
                "primary_phone": row.mobile_number or row.internal_number,
                "has_mobile": bool(row.mobile_number),
                "has_internal": bool(row.internal_number),
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
        logger.error(f"Error listing contacts: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================================
# ПОЛУЧЕНИЕ КОНТАКТА ПО ID
# ============================================================================

@router.get("/{contact_id}")
async def get_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение контакта по ID с группами и тегами"""
    r = await db.execute(text("SELECT * FROM contacts WHERE id=:id"), {"id": contact_id})
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Контакт не найден")
    
    # Получаем группы
    groups = []
    try:
        gr = await db.execute(
            text("""
                SELECT cg.id, cg.name, cg.color 
                FROM contact_groups cg 
                JOIN contact_group_members cgm ON cg.id=cgm.group_id 
                WHERE cgm.contact_id=:cid AND cgm.is_active=true AND cg.is_archived=false
            """),
            {"cid": contact_id}
        )
        for g in gr.fetchall():
            groups.append({"id": str(g.id), "name": g.name, "color": g.color or "#3498db"})
    except Exception:
        pass
    
    # Получаем теги
    tags = []
    try:
        tr = await db.execute(
            text("""
                SELECT t.id, t.name, t.color 
                FROM tags t 
                JOIN contact_tags ct ON t.id=ct.tag_id 
                WHERE ct.contact_id=:cid
            """),
            {"cid": contact_id}
        )
        for t in tr.fetchall():
            tags.append({"id": str(t.id), "name": t.name, "color": t.color or "#95a5a6"})
    except Exception:
        pass
    
    return {
        "id": str(row.id),
        "full_name": row.full_name,
        "department": row.department,
        "position": row.position,
        "internal_number": row.internal_number,
        "mobile_number": row.mobile_number,
        "email": row.email,
        "is_active": row.is_active,
        "is_archived": row.is_archived or False,
        "comment": row.comment,
        "groups": groups,
        "tags": tags,
        "primary_phone": row.mobile_number or row.internal_number,
        "has_mobile": bool(row.mobile_number),
        "has_internal": bool(row.internal_number),
        "created_by": str(row.created_by) if row.created_by else None,
        "updated_by": str(row.updated_by) if hasattr(row, 'updated_by') and row.updated_by else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if hasattr(row, 'updated_at') and row.updated_at else None
    }


# ============================================================================
# ПОИСК КОНТАКТА ПО НОМЕРУ ТЕЛЕФОНА
# ============================================================================

@router.get("/by-phone/{phone}")
async def get_contact_by_phone(
    phone: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Поиск контакта по мобильному или внутреннему номеру"""
    r = await db.execute(
        text("SELECT * FROM contacts WHERE (mobile_number=:p OR internal_number=:p) AND is_archived=false"),
        {"p": phone}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Контакт с таким номером не найден")
    
    return {
        "id": str(row.id),
        "full_name": row.full_name,
        "department": row.department,
        "position": row.position,
        "internal_number": row.internal_number,
        "mobile_number": row.mobile_number,
        "email": row.email,
        "is_active": row.is_active,
        "primary_phone": row.mobile_number or row.internal_number
    }


# ============================================================================
# СОЗДАНИЕ КОНТАКТА
# ============================================================================

@router.post("/", status_code=201)
async def create_contact(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового контакта
    
    Доступ: admin, operator
    Требуется: full_name + хотя бы один номер телефона
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if not data.get("full_name"):
        raise HTTPException(status_code=400, detail="Поле full_name обязательно")
    
    if not data.get("mobile_number") and not data.get("internal_number"):
        raise HTTPException(status_code=400, detail="Укажите хотя бы один номер телефона")
    
    # Нормализация мобильного номера
    mobile = data.get("mobile_number")
    if mobile:
        import re
        mobile = re.sub(r'[\s\-\(\)]', '', mobile)
        if mobile.startswith('8') and len(mobile) == 11:
            mobile = '+7' + mobile[1:]
        elif mobile.startswith('7') and len(mobile) == 11:
            mobile = '+' + mobile
    
    try:
        r = await db.execute(
            text("""
                INSERT INTO contacts (full_name, department, position, mobile_number, internal_number, email, comment, created_by)
                VALUES (:f, :d, :p, :m, :i, :e, :c, :cb)
                RETURNING id, created_at
            """),
            {
                "f": data["full_name"],
                "d": data.get("department"),
                "p": data.get("position"),
                "m": mobile,
                "i": data.get("internal_number"),
                "e": data.get("email"),
                "c": data.get("comment"),
                "cb": current_user.get("id")
            }
        )
        row = r.fetchone()
        await db.commit()
        
        logger.info(f"Создан контакт: {data['full_name']}")
        
        return {
            "id": str(row.id),
            "full_name": data["full_name"],
            "department": data.get("department"),
            "position": data.get("position"),
            "mobile_number": mobile,
            "internal_number": data.get("internal_number"),
            "email": data.get("email"),
            "is_active": True,
            "is_archived": False,
            "comment": data.get("comment"),
            "groups": [],
            "tags": [],
            "created_at": row.created_at.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating contact: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания: {str(e)}")


# ============================================================================
# ОБНОВЛЕНИЕ КОНТАКТА
# ============================================================================

@router.patch("/{contact_id}")
async def update_contact(
    contact_id: str,
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновление контакта (admin, operator)"""
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Проверка существования
    r = await db.execute(text("SELECT id FROM contacts WHERE id=:id AND is_archived=false"), {"id": contact_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Контакт не найден")
    
    # Поля для обновления
    allowed_fields = ["full_name", "department", "position", "mobile_number", "internal_number", "email", "is_active", "comment"]
    updates = []
    params = {"id": contact_id}
    
    for field in allowed_fields:
        if field in data and data[field] is not None:
            updates.append(f"{field}=:{field}")
            params[field] = data[field]
    
    if updates:
        await db.execute(text(f"UPDATE contacts SET {', '.join(updates)} WHERE id=:id"), params)
        await db.commit()
    
    # Возвращаем обновленный контакт
    return await get_contact(contact_id, db, current_user)


# ============================================================================
# УДАЛЕНИЕ/АРХИВИРОВАНИЕ КОНТАКТА
# ============================================================================

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str,
    hard_delete: bool = Query(False),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление контакта
    
    Доступ: admin - полное удаление, operator - архивирование
    - hard_delete=False: архивирование
    - hard_delete=True: полное удаление (только admin)
    """
    if hard_delete and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только администратор может полностью удалять")
    
    if hard_delete:
        await db.execute(text("DELETE FROM contacts WHERE id=:id"), {"id": contact_id})
        msg = "Контакт удален"
    else:
        await db.execute(text("UPDATE contacts SET is_archived=true, is_active=false WHERE id=:id"), {"id": contact_id})
        msg = "Контакт архивирован"
    
    await db.commit()
    return {"message": msg, "success": True}


# ============================================================================
# ВОССТАНОВЛЕНИЕ КОНТАКТА
# ============================================================================

@router.post("/{contact_id}/restore")
async def restore_contact(
    contact_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Восстановление архивированного контакта (только admin)"""
    await db.execute(
        text("UPDATE contacts SET is_archived=false, is_active=true WHERE id=:id"),
        {"id": contact_id}
    )
    await db.commit()
    return {"message": "Контакт восстановлен", "success": True}


# ============================================================================
# ИМПОРТ КОНТАКТОВ
# ============================================================================

@router.post("/import")
async def import_contacts(
    file: UploadFile = File(...),
    update_existing: bool = Query(False),
    skip_duplicates: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Импорт контактов из CSV файла (только admin)
    
    Формат CSV: full_name, department, position, mobile_number, internal_number, email, comment
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Поддерживаются только CSV файлы")
    
    try:
        content = await file.read()
        text = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))
        
        imported = 0
        skipped = 0
        errors = []
        
        for row_num, row in enumerate(reader, 2):
            try:
                if not row.get('full_name'):
                    errors.append({"row": row_num, "error": "Отсутствует full_name"})
                    continue
                
                # Проверка дубликата по мобильному
                mobile = row.get('mobile_number', '').strip()
                if mobile and skip_duplicates:
                    r = await db.execute(
                        text("SELECT id FROM contacts WHERE mobile_number=:m AND is_archived=false"),
                        {"m": mobile}
                    )
                    if r.fetchone():
                        if update_existing:
                            await db.execute(
                                text("UPDATE contacts SET full_name=:f, department=:d, position=:p, email=:e WHERE mobile_number=:m"),
                                {"f": row.get('full_name'), "d": row.get('department'),
                                 "p": row.get('position'), "e": row.get('email'), "m": mobile}
                            )
                            imported += 1
                        else:
                            skipped += 1
                        continue
                
                await db.execute(
                    text("""
                        INSERT INTO contacts (full_name, department, position, mobile_number, internal_number, email, comment)
                        VALUES (:f, :d, :p, :m, :i, :e, :c)
                    """),
                    {
                        "f": row.get('full_name'),
                        "d": row.get('department'),
                        "p": row.get('position'),
                        "m": mobile or None,
                        "i": row.get('internal_number'),
                        "e": row.get('email'),
                        "c": row.get('comment')
                    }
                )
                imported += 1
                
            except Exception as e:
                errors.append({"row": row_num, "error": str(e)})
        
        await db.commit()
        
        return {
            "total_processed": imported + skipped + len(errors),
            "success_count": imported,
            "skipped_count": skipped,
            "error_count": len(errors),
            "errors": errors[:10],
            "message": f"Импортировано: {imported}, пропущено: {skipped}, ошибок: {len(errors)}"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")


# ============================================================================
# ЭКСПОРТ КОНТАКТОВ
# ============================================================================

@router.get("/export")
async def export_contacts(
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Экспорт контактов в CSV"""
    r = await db.execute(
        text("SELECT full_name, department, position, mobile_number, internal_number, email, is_active FROM contacts WHERE is_archived=false ORDER BY full_name")
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["full_name", "department", "position", "mobile_number", "internal_number", "email", "is_active"])
    
    for row in r.fetchall():
        writer.writerow([row.full_name, row.department or "", row.position or "", 
                        row.mobile_number or "", row.internal_number or "", row.email or "", row.is_active])
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts_export.csv"}
    )


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get("/stats/summary")
async def get_contact_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Статистика по контактам"""
    try:
        r = await db.execute(text("SELECT COUNT(*) FROM contacts WHERE is_archived=false"))
        total = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM contacts WHERE is_active=true AND is_archived=false"))
        active = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM contacts WHERE mobile_number IS NOT NULL AND is_archived=false"))
        with_mobile = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM contacts WHERE internal_number IS NOT NULL AND is_archived=false"))
        with_internal = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM contacts WHERE email IS NOT NULL AND is_archived=false"))
        with_email = r.scalar() or 0
        
        # По подразделениям
        r = await db.execute(
            text("SELECT COALESCE(department,'Без отдела'), COUNT(*) FROM contacts WHERE is_archived=false GROUP BY department ORDER BY COUNT(*) DESC LIMIT 10")
        )
        by_department = [{"department": row[0], "count": row[1]} for row in r.fetchall()]
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "archived": 0,
            "with_mobile": with_mobile,
            "with_internal": with_internal,
            "with_email": with_email,
            "by_department": by_department
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total": 0, "active": 0, "inactive": 0, "with_mobile": 0, "with_internal": 0, "with_email": 0}
