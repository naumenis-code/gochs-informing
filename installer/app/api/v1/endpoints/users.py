#!/usr/bin/env python3
"""
API эндпоинты для управления пользователями
Соответствует ТЗ, раздел 22: Роли пользователей

Роли:
- Администратор: полный доступ (CRUD, блокировка, сброс пароля)
- Оператор: только просмотр своего профиля
- Наблюдатель: только чтение

Функционал:
- CRUD пользователей (только admin)
- Смена пароля
- Блокировка/разблокировка
- Статистика по пользователям
"""
import logging
import hashlib
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

@router.get("/")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка пользователей с фильтрацией
    
    Доступ: admin - все, operator/viewer - только себя
    """
    if current_user["role"] != "admin":
        # Не-admin видят только себя
        r = await db.execute(
            text("SELECT id, email, username, full_name, role, is_active, last_login, created_at FROM users WHERE id=:id"),
            {"id": current_user["id"]}
        )
        row = r.fetchone()
        items = [{
            "id": str(row.id), "email": row.email, "username": row.username,
            "full_name": row.full_name, "role": row.role,
            "is_active": row.is_active,
            "last_login": row.last_login.isoformat() if row.last_login else None,
            "created_at": row.created_at.isoformat() if row.created_at else None
        }] if row else []
        return {"items": items, "total": len(items), "page": 1, "page_size": limit}
    
    # Админ видит всех с фильтрацией
    conditions = ["1=1"]
    params = {"limit": limit, "skip": skip}
    
    if role:
        conditions.append("role = :role")
        params["role"] = role
    if is_active is not None:
        conditions.append("is_active = :active")
        params["active"] = is_active
    if search:
        conditions.append("(full_name ILIKE :s OR email ILIKE :s OR username ILIKE :s)")
        params["s"] = f"%{search}%"
    
    where = " AND ".join(conditions)
    
    r = await db.execute(text(f"SELECT COUNT(*) FROM users WHERE {where}"), params)
    total = r.scalar() or 0
    
    r = await db.execute(
        text(f"SELECT id, email, username, full_name, role, is_active, last_login, created_at FROM users WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :skip"),
        params
    )
    
    items = []
    for row in r.fetchall():
        items.append({
            "id": str(row.id),
            "email": row.email,
            "username": row.username,
            "full_name": row.full_name,
            "role": row.role,
            "is_active": row.is_active,
            "last_login": row.last_login.isoformat() if row.last_login else None,
            "created_at": row.created_at.isoformat() if row.created_at else None
        })
    
    return {
        "items": items,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit
    }


# ============================================================================
# ПОЛУЧЕНИЕ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.get("/me")
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение своего профиля"""
    r = await db.execute(
        text("SELECT * FROM users WHERE id=:id"),
        {"id": current_user["id"]}
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return {
        "id": str(row.id),
        "email": row.email,
        "username": row.username,
        "full_name": row.full_name,
        "role": row.role,
        "is_active": row.is_active,
        "is_superuser": row.is_superuser,
        "last_login": row.last_login.isoformat() if row.last_login else None,
        "created_at": row.created_at.isoformat() if row.created_at else None
    }


# ============================================================================
# ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО ID
# ============================================================================

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение пользователя по ID (только admin)"""
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    r = await db.execute(
        text("SELECT * FROM users WHERE id=:id"),
        {"id": user_id}
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return {
        "id": str(row.id),
        "email": row.email,
        "username": row.username,
        "full_name": row.full_name,
        "role": row.role,
        "is_active": row.is_active,
        "is_superuser": row.is_superuser,
        "last_login": row.last_login.isoformat() if row.last_login else None,
        "login_attempts": row.login_attempts or 0,
        "created_at": row.created_at.isoformat() if row.created_at else None
    }


# ============================================================================
# СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.post("/", status_code=201)
async def create_user(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Создание нового пользователя
    
    Требует роль: admin
    
    Поля:
    - email: обязательное, уникальное
    - username: обязательное, уникальное, 3-100 символов
    - full_name: обязательное
    - password: обязательное, минимум 8 символов
    - role: admin/operator/viewer (по умолчанию operator)
    """
    # Проверка обязательных полей
    if not data.get("email") or not data.get("username") or not data.get("full_name") or not data.get("password"):
        raise HTTPException(status_code=400, detail="Обязательные поля: email, username, full_name, password")
    
    if len(data.get("password", "")) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен быть не менее 8 символов")
    
    # Проверка уникальности
    r = await db.execute(
        text("SELECT id FROM users WHERE email=:e OR username=:u"),
        {"e": data["email"], "u": data["username"]}
    )
    if r.fetchone():
        raise HTTPException(status_code=409, detail="Пользователь с таким email или username уже существует")
    
    # Создание
    password_hash = hashlib.sha256(data["password"].encode()).hexdigest()
    role = data.get("role", "operator")
    if role not in ("admin", "operator", "viewer"):
        role = "operator"
    
    r = await db.execute(
        text("""
            INSERT INTO users (email, username, full_name, hashed_password, role, is_active)
            VALUES (:e, :u, :f, :h, :r, true)
            RETURNING id, created_at
        """),
        {"e": data["email"], "u": data["username"], "f": data["full_name"], "h": password_hash, "r": role}
    )
    row = r.fetchone()
    await db.commit()
    
    logger.info(f"Создан пользователь: {data['username']} (роль: {role})")
    
    return {
        "id": str(row.id),
        "email": data["email"],
        "username": data["username"],
        "full_name": data["full_name"],
        "role": role,
        "is_active": True,
        "created_at": row.created_at.isoformat()
    }


# ============================================================================
# ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Обновление пользователя (только admin)"""
    r = await db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id})
    user = r.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Нельзя снять роль admin с последнего администратора
    if "role" in data and data["role"] != "admin" and user.role == "admin":
        r = await db.execute(text("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=true"))
        if r.scalar() <= 1:
            raise HTTPException(status_code=400, detail="Нельзя изменить роль последнего администратора")
    
    updates = []
    params = {"id": user_id}
    
    for field in ["email", "username", "full_name", "role", "is_active"]:
        if field in data and data[field] is not None:
            updates.append(f"{field}=:{field}")
            params[field] = data[field]
    
    if updates:
        await db.execute(text(f"UPDATE users SET {', '.join(updates)} WHERE id=:id"), params)
        await db.commit()
    
    # Возвращаем обновленного пользователя
    r = await db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id})
    row = r.fetchone()
    
    return {
        "id": str(row.id), "email": row.email, "username": row.username,
        "full_name": row.full_name, "role": row.role, "is_active": row.is_active
    }


# ============================================================================
# УДАЛЕНИЕ/ДЕАКТИВАЦИЯ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Удаление пользователя (только admin)
    
    - hard_delete=False: деактивация (мягкое удаление)
    - hard_delete=True: полное удаление из БД
    """
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    
    if hard_delete:
        await db.execute(text("DELETE FROM users WHERE id=:id"), {"id": user_id})
    else:
        await db.execute(text("UPDATE users SET is_active=false WHERE id=:id"), {"id": user_id})
    
    await db.commit()
    return {"message": "Пользователь удален" if hard_delete else "Пользователь деактивирован", "success": True}


# ============================================================================
# СМЕНА ПАРОЛЯ
# ============================================================================

@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Сброс пароля (только admin)"""
    new_password = data.get("new_password", "User123!")
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    
    await db.execute(
        text("UPDATE users SET hashed_password=:h, force_password_change=true WHERE id=:id"),
        {"h": password_hash, "id": user_id}
    )
    await db.commit()
    
    return {"message": "Пароль сброшен", "success": True}


# ============================================================================
# РАЗБЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.post("/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Разблокировка после неудачных попыток (только admin)"""
    await db.execute(
        text("UPDATE users SET login_attempts=0, locked_until=NULL WHERE id=:id"),
        {"id": user_id}
    )
    await db.commit()
    return {"message": "Пользователь разблокирован", "success": True}


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get("/stats/summary")
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Статистика по пользователям (только admin)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")
    
    try:
        r = await db.execute(text("SELECT COUNT(*) FROM users"))
        total = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM users WHERE is_active=true"))
        active = r.scalar() or 0
        
        r = await db.execute(text("SELECT role, COUNT(*) FROM users WHERE is_active=true GROUP BY role"))
        by_role = {row.role: row.count for row in r.fetchall()}
        
        r = await db.execute(text("SELECT COUNT(*) FROM users WHERE locked_until > NOW()"))
        locked = r.scalar() or 0
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "locked": locked,
            "by_role": by_role
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total": 0, "active": 0, "inactive": 0, "locked": 0, "by_role": {}}
