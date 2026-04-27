#!/usr/bin/env python3
"""
API эндпоинты для управления входящими звонками
Соответствует ТЗ, разделы 18, 19, 20

Функционал:
- Просмотр списка входящих звонков
- Получение записи звонка (WAV)
- Получение транскрипции
- Статистика входящих звонков

Маршрут звонка:
Сотрудник → FreePBX → ГО-ЧС Asterisk → Автоответ → Playbook → Запись → Сохранение WAV
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА ВХОДЯЩИХ ЗВОНКОВ
# ============================================================================

@router.get("/calls")
async def list_inbound_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    search: Optional[str] = Query(None, description="Поиск по номеру"),
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка входящих звонков с фильтрацией
    
    Доступ: admin, operator, viewer
    
    Статусы:
    - recorded: записан
    - missed: пропущен
    - transcribed: расшифрован
    - failed: ошибка
    """
    conditions = ["1=1"]
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if search:
        conditions.append("caller_number ILIKE :search")
        params["search"] = f"%{search}%"
    if start_date:
        conditions.append("started_at >= :start_date")
        params["start_date"] = f"{start_date} 00:00:00"
    if end_date:
        conditions.append("started_at <= :end_date")
        params["end_date"] = f"{end_date} 23:59:59"
    
    where = " AND ".join(conditions)
    
    try:
        r = await db.execute(text(f"SELECT COUNT(*) FROM inbound_calls WHERE {where}"), params)
        total = r.scalar() or 0
        
        r = await db.execute(
            text(f"""
                SELECT * FROM inbound_calls 
                WHERE {where}
                ORDER BY started_at DESC 
                LIMIT :limit OFFSET :offset
            """),
            params
        )
        
        items = []
        for row in r.fetchall():
            items.append({
                "id": str(row.id),
                "caller_number": row.caller_number,
                "caller_name": row.caller_name,
                "recording_path": row.recording_path,
                "transcription": row.transcription[:500] if row.transcription else None,
                "duration": row.duration,
                "status": row.status or "unknown",
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None
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
        logger.error(f"Error listing inbound calls: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================================
# ПОЛУЧЕНИЕ ЗВОНКА ПО ID
# ============================================================================

@router.get("/calls/{call_id}")
async def get_inbound_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение детальной информации о входящем звонке"""
    r = await db.execute(
        text("SELECT * FROM inbound_calls WHERE id=:id"),
        {"id": call_id}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Звонок не найден")
    
    return {
        "id": str(row.id),
        "caller_number": row.caller_number,
        "caller_name": row.caller_name,
        "recording_path": row.recording_path,
        "transcription": row.transcription,
        "duration": row.duration,
        "status": row.status or "unknown",
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "ended_at": row.ended_at.isoformat() if row.ended_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None
    }


# ============================================================================
# ПОЛУЧЕНИЕ АУДИОЗАПИСИ
# ============================================================================

@router.get("/calls/{call_id}/recording")
async def get_call_recording(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение аудиозаписи входящего звонка (WAV)
    
    Доступ: admin, operator, viewer
    """
    r = await db.execute(
        text("SELECT recording_path, caller_number FROM inbound_calls WHERE id=:id"),
        {"id": call_id}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Звонок не найден")
    
    if not row.recording_path or not os.path.exists(row.recording_path):
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    return FileResponse(
        row.recording_path,
        media_type="audio/wav",
        filename=f"inbound_{row.caller_number}_{call_id}.wav"
    )


# ============================================================================
# ПОЛУЧЕНИЕ ТРАНСКРИПЦИИ
# ============================================================================

@router.get("/calls/{call_id}/transcription")
async def get_call_transcription(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение расшифровки речи (текст)"""
    r = await db.execute(
        text("SELECT transcription, caller_number FROM inbound_calls WHERE id=:id"),
        {"id": call_id}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Звонок не найден")
    
    return {
        "call_id": call_id,
        "caller_number": row.caller_number,
        "transcription": row.transcription or "Расшифровка недоступна"
    }


# ============================================================================
# ПОСЛЕДНИЕ ВХОДЯЩИЕ (ДЛЯ DASHBOARD)
# ============================================================================

@router.get("/recent")
async def get_recent_inbound(
    limit: int = Query(10, ge=1, le=50, description="Количество записей"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение последних входящих звонков (для Dashboard)
    
    Доступ: все авторизованные
    """
    try:
        r = await db.execute(
            text("""
                SELECT * FROM inbound_calls 
                ORDER BY started_at DESC 
                LIMIT :limit
            """),
            {"limit": limit}
        )
        
        calls = []
        for row in r.fetchall():
            calls.append({
                "id": str(row.id),
                "time": row.started_at.isoformat() if row.started_at else None,
                "caller_number": row.caller_number,
                "caller_name": row.caller_name,
                "duration": row.duration,
                "status": row.status or "unknown",
                "has_recording": bool(row.recording_path),
                "has_transcription": bool(row.transcription)
            })
        
        return {"calls": calls, "total": len(calls)}
        
    except Exception as e:
        logger.error(f"Error recent inbound: {e}")
        return {"calls": [], "total": 0}


# ============================================================================
# СОЗДАНИЕ ЗАПИСИ О ВХОДЯЩЕМ ЗВОНКЕ (WEBHOOK ОТ ASTERISK)
# ============================================================================

@router.post("/calls", status_code=201)
async def create_inbound_call(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание записи о входящем звонке
    
    Вызывается автоматически Asterisk через webhook после записи сообщения.
    Не требует авторизации (внутренний API).
    
    Поля:
    - caller_number: номер звонящего (обязательно)
    - caller_name: имя звонящего
    - recording_path: путь к аудиозаписи
    - transcription: расшифровка речи
    - duration: длительность в секундах
    - status: статус звонка
    """
    if not data.get("caller_number"):
        raise HTTPException(status_code=400, detail="Номер звонящего обязателен")
    
    try:
        r = await db.execute(
            text("""
                INSERT INTO inbound_calls (caller_number, caller_name, recording_path, transcription, duration, status, started_at)
                VALUES (:num, :name, :path, :trans, :dur, :status, NOW())
                RETURNING id, created_at
            """),
            {
                "num": data["caller_number"],
                "name": data.get("caller_name"),
                "path": data.get("recording_path"),
                "trans": data.get("transcription"),
                "dur": data.get("duration", 0),
                "status": data.get("status", "recorded")
            }
        )
        row = r.fetchone()
        await db.commit()
        
        logger.info(f"Входящий звонок: {data['caller_number']}")
        
        return {
            "id": str(row.id),
            "caller_number": data["caller_number"],
            "status": "recorded",
            "created_at": row.created_at.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating inbound call: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения: {str(e)}")


# ============================================================================
# СТАТИСТИКА ВХОДЯЩИХ ЗВОНКОВ
# ============================================================================

@router.get("/stats")
async def get_inbound_stats(
    days: int = Query(7, ge=1, le=365, description="Количество дней"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Статистика входящих звонков за период
    
    Доступ: admin, operator, viewer
    """
    try:
        # Всего звонков
        r = await db.execute(
            text("SELECT COUNT(*) FROM inbound_calls WHERE started_at >= NOW() - INTERVAL :days DAY"),
            {"days": str(days)}
        )
        total = r.scalar() or 0
        
        # Записанных
        r = await db.execute(
            text("SELECT COUNT(*) FROM inbound_calls WHERE status='recorded' AND started_at >= NOW() - INTERVAL :days DAY"),
            {"days": str(days)}
        )
        recorded = r.scalar() or 0
        
        # Пропущенных
        r = await db.execute(
            text("SELECT COUNT(*) FROM inbound_calls WHERE status='missed' AND started_at >= NOW() - INTERVAL :days DAY"),
            {"days": str(days)}
        )
        missed = r.scalar() or 0
        
        # Средняя длительность
        r = await db.execute(
            text("SELECT AVG(duration) FROM inbound_calls WHERE duration > 0 AND started_at >= NOW() - INTERVAL :days DAY"),
            {"days": str(days)}
        )
        avg_duration = round(r.scalar() or 0, 1)
        
        # По дням
        r = await db.execute(
            text("""
                SELECT DATE(started_at) as d, COUNT(*) as cnt 
                FROM inbound_calls 
                WHERE started_at >= NOW() - INTERVAL :days DAY
                GROUP BY DATE(started_at) 
                ORDER BY d DESC
            """),
            {"days": str(days)}
        )
        daily = [{"date": row.d.isoformat(), "count": row.cnt} for row in r.fetchall()]
        
        return {
            "total_calls": total,
            "recorded_calls": recorded,
            "missed_calls": missed,
            "avg_duration": avg_duration,
            "daily_stats": daily
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total_calls": 0, "recorded_calls": 0, "missed_calls": 0, "avg_duration": 0, "daily_stats": []}
