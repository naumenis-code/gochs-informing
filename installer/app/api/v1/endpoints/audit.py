#!/usr/bin/env python3
"""
API эндпоинты для журнала аудита
Соответствует ТЗ, разделы 23, 29, 31

Функционал:
- Просмотр журнала действий пользователей
- Фильтрация по действию, пользователю, дате
- Статистика аудита
- Экспорт в CSV
- Очистка старых записей
"""
import logging
import csv
import io
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ ЗАПИСЕЙ АУДИТА
# ============================================================================

@router.get("/logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(20, ge=1, le=100, description="Количество записей"),
    action: Optional[str] = Query(None, description="Фильтр по действию"),
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    user_name: Optional[str] = Query(None, description="Фильтр по пользователю"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение записей журнала аудита с фильтрацией
    
    Доступ: admin - все записи, operator/viewer - только свои
    """
    if current_user["role"] != "admin":
        return {"items": [], "total": 0, "message": "Только для администраторов"}
    
    conditions = ["1=1"]
    params = {"limit": limit, "skip": skip}
    
    if action:
        conditions.append("action ILIKE :action")
        params["action"] = f"%{action}%"
    if entity_type:
        conditions.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    if user_name:
        conditions.append("user_name ILIKE :user_name")
        params["user_name"] = f"%{user_name}%"
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if start_date:
        conditions.append("created_at >= :start_date")
        params["start_date"] = f"{start_date} 00:00:00"
    if end_date:
        conditions.append("created_at <= :end_date")
        params["end_date"] = f"{end_date} 23:59:59"
    
    where = " AND ".join(conditions)
    
    try:
        r = await db.execute(
            text(f"SELECT COUNT(*) FROM audit_logs WHERE {where}"),
            {k: v for k, v in params.items() if k not in ["limit", "skip"]}
        )
        total = r.scalar() or 0
        
        r = await db.execute(
            text(f"""
                SELECT * FROM audit_logs 
                WHERE {where}
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :skip
            """),
            params
        )
        
        items = []
        for row in r.fetchall():
            items.append({
                "id": str(row.id),
                "user_id": str(row.user_id) if row.user_id else None,
                "user_name": row.user_name or "Система",
                "user_role": row.user_role,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id) if row.entity_id else None,
                "entity_name": row.entity_name,
                "details": row.details,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent[:200] if row.user_agent else None,
                "request_method": row.request_method,
                "request_path": row.request_path,
                "status": row.status or "success",
                "error_message": row.error_message,
                "execution_time_ms": row.execution_time_ms,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": (skip // limit) + 1,
            "page_size": limit,
            "has_next": (skip + limit) < total,
            "has_prev": skip > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return {"items": [], "total": 0, "page": 1, "page_size": limit}


# ============================================================================
# СТАТИСТИКА АУДИТА
# ============================================================================

@router.get("/stats")
async def get_audit_stats(
    days: int = Query(30, ge=1, le=365, description="Количество дней"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Статистика аудита за период
    
    Доступ: admin
    """
    if current_user["role"] != "admin":
        return {"error": "Только для администраторов"}
    
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Всего
        r = await db.execute(text("SELECT COUNT(*) FROM audit_logs"))
        total = r.scalar() or 0
        
        # За сегодня
        r = await db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at >= :today"),
            {"today": today}
        )
        today_count = r.scalar() or 0
        
        # За неделю
        r = await db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at >= :week"),
            {"week": week_ago}
        )
        week_count = r.scalar() or 0
        
        # За месяц
        r = await db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at >= :month"),
            {"month": month_ago}
        )
        month_count = r.scalar() or 0
        
        # Уникальные пользователи
        r = await db.execute(
            text("SELECT COUNT(DISTINCT user_name) FROM audit_logs WHERE user_name IS NOT NULL")
        )
        unique_users = r.scalar() or 0
        
        # Топ действий
        r = await db.execute(
            text("""
                SELECT action, COUNT(*) as cnt 
                FROM audit_logs 
                WHERE created_at >= :month
                GROUP BY action 
                ORDER BY cnt DESC 
                LIMIT 10
            """),
            {"month": month_ago}
        )
        top_actions = [{"action": row.action, "count": row.cnt} for row in r.fetchall()]
        
        # Топ сущностей
        r = await db.execute(
            text("""
                SELECT entity_type, COUNT(*) as cnt 
                FROM audit_logs 
                WHERE entity_type IS NOT NULL AND created_at >= :month
                GROUP BY entity_type 
                ORDER BY cnt DESC 
                LIMIT 10
            """),
            {"month": month_ago}
        )
        top_entities = [{"entity_type": row.entity_type, "count": row.cnt} for row in r.fetchall()]
        
        # Последняя активность
        r = await db.execute(
            text("""
                SELECT user_name, action, entity_type, entity_name, status, created_at, ip_address
                FROM audit_logs 
                ORDER BY created_at DESC 
                LIMIT 20
            """)
        )
        recent = []
        for row in r.fetchall():
            recent.append({
                "time": row.created_at.isoformat() if row.created_at else None,
                "user": row.user_name or "Система",
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_name": row.entity_name,
                "status": row.status,
                "ip_address": row.ip_address,
                "description": f"{row.user_name or 'Система'}: {row.action} {row.entity_type or ''} {row.entity_name or ''}"
            })
        
        # Статусы
        r = await db.execute(text("SELECT COUNT(*) FROM audit_logs WHERE status='error'"))
        errors = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM audit_logs WHERE status='warning'"))
        warnings = r.scalar() or 0
        
        return {
            "total_events": total,
            "today_events": today_count,
            "week_events": week_count,
            "month_events": month_count,
            "unique_users": unique_users,
            "error_events": errors,
            "warning_events": warnings,
            "success_events": total - errors - warnings,
            "top_actions": top_actions,
            "top_entities": top_entities,
            "top_users": [],
            "recent_activity": recent
        }
        
    except Exception as e:
        logger.error(f"Error audit stats: {e}")
        return {
            "total_events": 0, "today_events": 0, "week_events": 0, "month_events": 0,
            "unique_users": 0, "error_events": 0, "warning_events": 0, "success_events": 0,
            "top_actions": [], "top_entities": [], "recent_activity": []
        }


# ============================================================================
# СОЗДАНИЕ ЗАПИСИ АУДИТА (ВНУТРЕННИЙ API)
# ============================================================================

@router.post("/log")
async def create_audit_log(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание записи аудита (внутренний API)
    
    Вызывается другими модулями для логирования действий.
    """
    try:
        ip = request.client.host if request and request.client else None
        ua = request.headers.get("user-agent", "") if request else ""
        
        await db.execute(
            text("""
                INSERT INTO audit_logs 
                (user_id, user_name, user_role, action, entity_type, entity_id, entity_name,
                 details, ip_address, user_agent, request_method, request_path, status)
                VALUES (:uid, :un, :ur, :a, :et, :eid, :en, :d, :ip, :ua, :rm, :rp, :s)
            """),
            {
                "uid": data.get("user_id"),
                "un": data.get("user_name", "system"),
                "ur": data.get("user_role"),
                "a": data.get("action", "unknown"),
                "et": data.get("entity_type"),
                "eid": data.get("entity_id"),
                "en": data.get("entity_name"),
                "d": data.get("details"),
                "ip": data.get("ip_address", ip),
                "ua": data.get("user_agent", ua[:200]) if data.get("user_agent") else ua[:200],
                "rm": data.get("request_method"),
                "rp": data.get("request_path"),
                "s": data.get("status", "success")
            }
        )
        await db.commit()
        return {"success": True, "message": "Событие записано"}
        
    except Exception as e:
        logger.error(f"Error creating audit log: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# ЭКСПОРТ АУДИТА
# ============================================================================

@router.get("/export")
async def export_audit(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    user_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Экспорт журнала аудита в CSV
    
    Доступ: admin
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")
    
    conditions = ["1=1"]
    params = {}
    
    if action:
        conditions.append("action ILIKE :action")
        params["action"] = f"%{action}%"
    if entity_type:
        conditions.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    if user_name:
        conditions.append("user_name ILIKE :user_name")
        params["user_name"] = f"%{user_name}%"
    if start_date:
        conditions.append("created_at >= :start_date")
        params["start_date"] = f"{start_date} 00:00:00"
    if end_date:
        conditions.append("created_at <= :end_date")
        params["end_date"] = f"{end_date} 23:59:59"
    
    where = " AND ".join(conditions)
    
    try:
        r = await db.execute(
            text(f"""
                SELECT created_at, user_name, user_role, action, entity_type, 
                       entity_name, status, ip_address, request_method, request_path
                FROM audit_logs 
                WHERE {where}
                ORDER BY created_at DESC 
                LIMIT 10000
            """),
            params
        )
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            'Дата', 'Пользователь', 'Роль', 'Действие', 'Тип объекта',
            'Объект', 'Статус', 'IP', 'Метод', 'Путь'
        ])
        
        for row in r.fetchall():
            writer.writerow([
                row.created_at.isoformat() if row.created_at else '',
                row.user_name or 'Система',
                row.user_role or '',
                row.action,
                row.entity_type or '',
                row.entity_name or '',
                row.status or 'success',
                row.ip_address or '',
                row.request_method or '',
                row.request_path or ''
            ])
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ОЧИСТКА СТАРЫХ ЗАПИСЕЙ
# ============================================================================

@router.delete("/logs")
async def clear_old_logs(
    older_than_days: int = Query(90, ge=7, le=365, description="Старше дней"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удаление старых записей аудита
    
    Доступ: admin
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")
    
    try:
        cutoff = datetime.now() - timedelta(days=older_than_days)
        
        r = await db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff}
        )
        count = r.scalar() or 0
        
        if count > 0:
            await db.execute(
                text("DELETE FROM audit_logs WHERE created_at < :cutoff"),
                {"cutoff": cutoff}
            )
            await db.commit()
        
        return {
            "message": f"Удалено записей: {count}",
            "deleted_count": count,
            "older_than_days": older_than_days,
            "cutoff_date": cutoff.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.get("/users/{user_name}/activity")
async def get_user_activity(
    user_name: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Активность конкретного пользователя
    
    Доступ: admin
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")
    
    try:
        r = await db.execute(
            text("""
                SELECT * FROM audit_logs 
                WHERE user_name = :un
                ORDER BY created_at DESC 
                LIMIT :limit
            """),
            {"un": user_name, "limit": limit}
        )
        
        logs = []
        for row in r.fetchall():
            logs.append({
                "id": str(row.id),
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_name": row.entity_name,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "ip_address": row.ip_address
            })
        
        return {
            "user_name": user_name,
            "total_actions": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error user activity: {e}")
        return {"user_name": user_name, "total_actions": 0, "logs": []}
