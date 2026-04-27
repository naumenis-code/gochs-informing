#!/usr/bin/env python3
"""
API эндпоинты для управления сценариями оповещения
Соответствует ТЗ, разделы 11, 12

Функционал:
- CRUD операции со сценариями
- Создание из текста (TTS) или загрузка аудиофайла (WAV/MP3)
- Категории: пожар, эвакуация, сбор руководства, тест и др.
- Статистика использования
"""
import logging
import os
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Категории сценариев согласно ТЗ
CATEGORIES = {
    "fire": {"name": "Пожар", "icon": "🔥", "color": "#e74c3c"},
    "evacuation": {"name": "Эвакуация", "icon": "🚶", "color": "#e67e22"},
    "emergency": {"name": "Экстренный сбор", "icon": "🚨", "color": "#f39c12"},
    "accident": {"name": "Технологическая авария", "icon": "⚠️", "color": "#9b59b6"},
    "gas": {"name": "Утечка газа", "icon": "💨", "color": "#3498db"},
    "test": {"name": "Проверка связи", "icon": "📞", "color": "#2ecc71"},
    "training": {"name": "Учебная тревога", "icon": "📚", "color": "#1abc9c"},
    "info": {"name": "Информационное", "icon": "ℹ️", "color": "#95a5a6"},
}


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА СЦЕНАРИЕВ
# ============================================================================

@router.get("/")
async def list_scenarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    is_active: Optional[bool] = Query(None, description="Только активные"),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка сценариев оповещения
    
    Доступ: admin, operator, viewer
    """
    conditions = ["1=1"]
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if category:
        conditions.append("category = :cat")
        params["cat"] = category
    if is_active is not None:
        conditions.append("is_active = :active")
        params["active"] = is_active
    if search:
        conditions.append("(name ILIKE :s OR text_content ILIKE :s)")
        params["s"] = f"%{search}%"
    
    where = " AND ".join(conditions)
    
    try:
        r = await db.execute(text(f"SELECT COUNT(*) FROM notification_scenarios WHERE {where}"), params)
        total = r.scalar() or 0
        
        r = await db.execute(
            text(f"""
                SELECT * FROM notification_scenarios 
                WHERE {where}
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset
            """),
            params
        )
        
        items = []
        for row in r.fetchall():
            cat_info = CATEGORIES.get(row.category, {"name": row.category, "color": "#95a5a6"})
            items.append({
                "id": str(row.id),
                "name": row.name,
                "category": row.category,
                "category_name": cat_info["name"],
                "category_color": cat_info["color"],
                "description": row.description,
                "text_content": row.text_content[:200] if row.text_content else None,
                "audio_file_path": row.audio_file_path,
                "duration": row.duration,
                "is_active": row.is_active if row.is_active is not None else True,
                "is_archived": row.is_archived or False,
                "created_by": str(row.created_by) if row.created_by else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if hasattr(row, 'updated_at') and row.updated_at else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Error listing scenarios: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================================
# ПОЛУЧЕНИЕ КАТЕГОРИЙ
# ============================================================================

@router.get("/categories")
async def get_categories():
    """Получение списка категорий сценариев"""
    return {"categories": [
        {"value": k, "name": v["name"], "icon": v["icon"], "color": v["color"]}
        for k, v in CATEGORIES.items()
    ]}


# ============================================================================
# ПОЛУЧЕНИЕ СЦЕНАРИЯ ПО ID
# ============================================================================

@router.get("/{scenario_id}")
async def get_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение сценария по ID"""
    r = await db.execute(
        text("SELECT * FROM notification_scenarios WHERE id=:id"),
        {"id": scenario_id}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    
    return {
        "id": str(row.id),
        "name": row.name,
        "category": row.category,
        "description": row.description,
        "text_content": row.text_content,
        "audio_file_path": row.audio_file_path,
        "duration": row.duration,
        "is_active": row.is_active if row.is_active is not None else True,
        "is_archived": row.is_archived or False,
        "usage_count": row.usage_count or 0,
        "last_used_at": row.last_used_at.isoformat() if hasattr(row, 'last_used_at') and row.last_used_at else None,
        "created_by": str(row.created_by) if row.created_by else None,
        "created_at": row.created_at.isoformat() if row.created_at else None
    }


# ============================================================================
# СОЗДАНИЕ СЦЕНАРИЯ
# ============================================================================

@router.post("/", status_code=201)
async def create_scenario(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового сценария оповещения
    
    Доступ: admin, operator
    
    Поля:
    - name: название (обязательно)
    - category: категория (fire/evacuation/emergency/accident/gas/test/training/info)
    - description: описание
    - text_content: текст для TTS
    - is_active: активен (по умолчанию true)
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="Название сценария обязательно")
    
    category = data.get("category", "info")
    if category not in CATEGORIES:
        category = "info"
    
    try:
        r = await db.execute(
            text("""
                INSERT INTO notification_scenarios (name, category, description, text_content, is_active, created_by)
                VALUES (:n, :c, :d, :t, :a, :cb)
                RETURNING id, created_at
            """),
            {
                "n": data["name"],
                "c": category,
                "d": data.get("description"),
                "t": data.get("text_content"),
                "a": data.get("is_active", True),
                "cb": current_user.get("id")
            }
        )
        row = r.fetchone()
        await db.commit()
        
        logger.info(f"Создан сценарий: {data['name']}")
        
        return {
            "id": str(row.id),
            "name": data["name"],
            "category": category,
            "description": data.get("description"),
            "text_content": data.get("text_content"),
            "is_active": data.get("is_active", True),
            "created_at": row.created_at.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания: {str(e)}")


# ============================================================================
# ЗАГРУЗКА АУДИО ДЛЯ СЦЕНАРИЯ
# ============================================================================

@router.post("/{scenario_id}/audio")
async def upload_scenario_audio(
    scenario_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Загрузка аудиофайла для сценария (WAV/MP3)
    
    Доступ: admin, operator
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Проверка формата
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")
    
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ['wav', 'mp3']:
        raise HTTPException(status_code=400, detail="Поддерживаются только WAV и MP3 файлы")
    
    # Проверка существования сценария
    r = await db.execute(text("SELECT id FROM notification_scenarios WHERE id=:id"), {"id": scenario_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    
    try:
        # Сохраняем файл
        audio_dir = "/opt/gochs-informing/generated_voice"
        os.makedirs(audio_dir, exist_ok=True)
        
        filename = f"scenario_{scenario_id}_{file.filename}"
        filepath = os.path.join(audio_dir, filename)
        
        content = await file.read()
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # Обновляем сценарий
        await db.execute(
            text("UPDATE notification_scenarios SET audio_file_path=:p WHERE id=:id"),
            {"p": filepath, "id": scenario_id}
        )
        await db.commit()
        
        return {
            "message": "Аудиофайл загружен",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": len(content)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")


# ============================================================================
# ОБНОВЛЕНИЕ СЦЕНАРИЯ
# ============================================================================

@router.patch("/{scenario_id}")
async def update_scenario(
    scenario_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновление сценария"""
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    r = await db.execute(text("SELECT id FROM notification_scenarios WHERE id=:id"), {"id": scenario_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    
    updates = []
    params = {"id": scenario_id}
    
    for field in ["name", "category", "description", "text_content", "is_active"]:
        if field in data and data[field] is not None:
            updates.append(f"{field}=:{field}")
            params[field] = data[field]
    
    if updates:
        await db.execute(
            text(f"UPDATE notification_scenarios SET {', '.join(updates)} WHERE id=:id"),
            params
        )
        await db.commit()
    
    return await get_scenario(scenario_id, db, current_user)


# ============================================================================
# УДАЛЕНИЕ СЦЕНАРИЯ
# ============================================================================

@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление/архивирование сценария
    
    Доступ: admin - полное удаление, operator - архивирование
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if current_user["role"] == "admin":
        await db.execute(text("DELETE FROM notification_scenarios WHERE id=:id"), {"id": scenario_id})
        msg = "Сценарий удален"
    else:
        await db.execute(
            text("UPDATE notification_scenarios SET is_archived=true, is_active=false WHERE id=:id"),
            {"id": scenario_id}
        )
        msg = "Сценарий архивирован"
    
    await db.commit()
    return {"message": msg, "success": True}


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get("/stats/summary")
async def get_scenario_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Статистика по сценариям"""
    try:
        r = await db.execute(text("SELECT COUNT(*) FROM notification_scenarios WHERE is_archived=false"))
        total = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM notification_scenarios WHERE is_active=true AND is_archived=false"))
        active = r.scalar() or 0
        
        r = await db.execute(
            text("SELECT category, COUNT(*) FROM notification_scenarios WHERE is_archived=false GROUP BY category ORDER BY COUNT(*) DESC")
        )
        by_category = {row.category: row.count for row in r.fetchall()}
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "by_category": by_category
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total": 0, "active": 0, "inactive": 0, "by_category": {}}
