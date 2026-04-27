#!/usr/bin/env python3
"""Audit endpoints - ПОЛНАЯ ВЕРСИЯ С ЛОГИРОВАНИЕМ ВСЕХ ДЕЙСТВИЙ СОГЛАСНО ТЗ"""

import logging
import json
import csv
import io
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# PYDANTIC МОДЕЛИ
# ============================================================================

class AuditLogCreate(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str
    created_at: str


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_client_info(request: Request) -> Dict[str, Any]:
    """Получение информации о клиенте"""
    ip = None
    if request.client:
        ip = request.client.host
    elif request.headers.get("x-forwarded-for"):
        ip = request.headers.get("x-forwarded-for").split(",")[0].strip()
    elif request.headers.get("x-real-ip"):
        ip = request.headers.get("x-real-ip")
    
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent", ""),
        "request_method": request.method,
        "request_path": request.url.path
    }


async def ensure_audit_table(db: AsyncSession) -> bool:
    """Проверка и создание таблицы аудита если её нет"""
    try:
        # Проверяем существование таблицы
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'audit_logs'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            # Создаем таблицу
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID,
                    user_name VARCHAR(255),
                    user_role VARCHAR(50),
                    action VARCHAR(100) NOT NULL,
                    entity_type VARCHAR(50),
                    entity_id UUID,
                    entity_name VARCHAR(255),
                    details JSONB,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    request_method VARCHAR(10),
                    request_path VARCHAR(500),
                    status VARCHAR(20) DEFAULT 'success',
                    error_message TEXT,
                    execution_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Создаем индексы
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at DESC)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_user_name ON audit_logs(user_name)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_entity_type ON audit_logs(entity_type)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_logs(status)"))
            
            await db.commit()
            logger.info("Audit table created")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring audit table: {e}")
        return False


async def log_event(
    db: AsyncSession,
    user_id: Optional[str] = None,
    user_name: Optional[str] = "system",
    user_role: Optional[str] = None,
    action: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> bool:
    """Универсальная функция логирования"""
    try:
        await ensure_audit_table(db)
        
        details_json = json.dumps(details) if details else None
        
        await db.execute(text("""
            INSERT INTO audit_logs 
            (user_id, user_name, user_role, action, entity_type, entity_id, entity_name,
             details, ip_address, user_agent, request_method, request_path,
             status, error_message, execution_time_ms, created_at)
            VALUES (:user_id, :user_name, :user_role, :action, :entity_type, :entity_id, :entity_name,
                    :details::jsonb, :ip_address, :user_agent, :request_method, :request_path,
                    :status, :error_message, :execution_time_ms, NOW())
        """), {
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "details": details_json,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_method": request_method,
            "request_path": request_path,
            "status": status,
            "error_message": error_message,
            "execution_time_ms": execution_time_ms
        })
        
        await db.commit()
        logger.debug(f"Audit log: {user_name} - {action}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        return False


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/logs")
async def get_audit_logs(
    request: Request,
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(100, ge=1, le=1000, description="Количество записей"),
    action: Optional[str] = Query(None, description="Фильтр по действию"),
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    user_name: Optional[str] = Query(None, description="Фильтр по имени пользователя"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка событий аудита с фильтрацией"""
    await ensure_audit_table(db)
    
    try:
        # Строим условия WHERE
        conditions = []
        params = {"limit": limit, "skip": skip}
        
        if action:
            conditions.append("action ILIKE :action")
            params["action"] = f"%{action}%"
        if entity_type:
            conditions.append("entity_type ILIKE :entity_type")
            params["entity_type"] = f"%{entity_type}%"
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
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Общее количество
        count_params = {k: v for k, v in params.items() if k not in ["limit", "skip"]}
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}"),
            count_params
        )
        total = count_result.scalar() or 0
        
        # Получаем записи
        result = await db.execute(
            text(f"""
                SELECT id, user_id, user_name, user_role, action, entity_type, 
                       entity_id, entity_name, details, ip_address, user_agent,
                       request_method, request_path, status, error_message, 
                       execution_time_ms, created_at
                FROM audit_logs 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """),
            params
        )
        
        items = []
        for row in result.fetchall():
            items.append({
                "id": str(row.id) if row.id else None,
                "user_id": str(row.user_id) if row.user_id else None,
                "user_name": row.user_name,
                "user_role": row.user_role,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id) if row.entity_id else None,
                "entity_name": row.entity_name,
                "details": row.details,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "request_method": row.request_method,
                "request_path": row.request_path,
                "status": row.status or "success",
                "error_message": row.error_message,
                "execution_time_ms": row.execution_time_ms,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        # Логируем просмотр аудита
        client_info = get_client_info(request)
        await log_event(
            db=db,
            user_name="system",
            action="view_audit",
            entity_type="audit",
            details={"filters": {"action": action, "entity_type": entity_type}},
            **client_info
        )
        
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": limit,
            "has_next": (skip + limit) < total,
            "has_prev": skip > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return {"items": [], "total": 0, "page": 1, "page_size": limit}


@router.get("/stats")
async def get_audit_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Количество дней для статистики"),
    db: AsyncSession = Depends(get_db)
):
    """Получение расширенной статистики аудита"""
    await ensure_audit_table(db)
    
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        start_date = today - timedelta(days=days)
        
        # Общее количество
        total_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs"))
        total_events = total_result.scalar() or 0
        
        # За сегодня
        today_result = await db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at >= :today"),
            {"today": today}
        )
        today_events = today_result.scalar() or 0
        
        # За неделю
        week_result = await db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at >= :week_ago"),
            {"week_ago": week_ago}
        )
        week_events = week_result.scalar() or 0
        
        # За месяц
        month_result = await db.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE created_at >= :month_ago"),
            {"month_ago": month_ago}
        )
        month_events = month_result.scalar() or 0
        
        # Уникальные пользователи
        users_result = await db.execute(
            text("SELECT COUNT(DISTINCT user_name) FROM audit_logs WHERE user_name IS NOT NULL")
        )
        unique_users = users_result.scalar() or 0
        
        # По статусам
        error_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs WHERE status = 'error'"))
        error_events = error_result.scalar() or 0
        
        warning_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs WHERE status = 'warning'"))
        warning_events = warning_result.scalar() or 0
        
        # Топ действий
        top_actions_result = await db.execute(text("""
            SELECT action, COUNT(*) as count 
            FROM audit_logs 
            WHERE created_at >= :start_date
            GROUP BY action 
            ORDER BY count DESC 
            LIMIT 10
        """), {"start_date": start_date})
        top_actions = [{"action": row[0], "count": row[1]} for row in top_actions_result.fetchall()]
        
        # Топ сущностей
        top_entities_result = await db.execute(text("""
            SELECT entity_type, COUNT(*) as count 
            FROM audit_logs 
            WHERE entity_type IS NOT NULL AND created_at >= :start_date
            GROUP BY entity_type 
            ORDER BY count DESC 
            LIMIT 10
        """), {"start_date": start_date})
        top_entities = [{"entity_type": row[0], "count": row[1]} for row in top_entities_result.fetchall()]
        
        # Последняя активность
        recent_result = await db.execute(text("""
            SELECT user_name, action, entity_type, entity_name, status, created_at, ip_address
            FROM audit_logs 
            ORDER BY created_at DESC 
            LIMIT 20
        """))
        recent_activity = []
        for row in recent_result.fetchall():
            recent_activity.append({
                "time": row.created_at.isoformat() if row.created_at else None,
                "user": row.user_name or "Система",
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_name": row.entity_name,
                "status": row.status,
                "ip_address": row.ip_address,
                "description": f"{row.user_name or 'Система'}: {row.action} {row.entity_type or ''}"
            })
        
        return {
            "total_events": total_events,
            "today_events": today_events,
            "week_events": week_events,
            "month_events": month_events,
            "unique_users": unique_users,
            "error_events": error_events,
            "warning_events": warning_events,
            "success_events": total_events - error_events - warning_events,
            "top_actions": top_actions,
            "top_entities": top_entities,
            "recent_activity": recent_activity
        }
        
    except Exception as e:
        logger.error(f"Error getting audit stats: {e}")
        return {
            "total_events": 0, "today_events": 0, "week_events": 0, "month_events": 0,
            "unique_users": 0, "error_events": 0, "warning_events": 0, "success_events": 0,
            "top_actions": [], "top_entities": [], "recent_activity": []
        }


@router.post("/log")
async def create_audit_log(
    request: Request,
    log_data: AuditLogCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание записи аудита (внутренний API)"""
    client_info = get_client_info(request)
    
    success = await log_event(
        db=db,
        user_id=log_data.user_id,
        user_name=log_data.user_name,
        user_role=log_data.user_role,
        action=log_data.action,
        entity_type=log_data.entity_type,
        entity_id=log_data.entity_id,
        entity_name=log_data.entity_name,
        details=log_data.details,
        ip_address=log_data.ip_address or client_info["ip_address"],
        user_agent=log_data.user_agent or client_info["user_agent"],
        status=log_data.status
    )
    
    return {"success": success, "message": "Event logged" if success else "Failed to log event"}


@router.get("/export")
async def export_audit_logs(
    action: Optional[str] = Query(None, description="Фильтр по действию"),
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    user_name: Optional[str] = Query(None, description="Фильтр по имени пользователя"),
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """Экспорт журнала аудита в CSV"""
    await ensure_audit_table(db)
    
    try:
        conditions = []
        params = {}
        
        if action:
            conditions.append("action ILIKE :action")
            params["action"] = f"%{action}%"
        if entity_type:
            conditions.append("entity_type ILIKE :entity_type")
            params["entity_type"] = f"%{entity_type}%"
        if user_name:
            conditions.append("user_name ILIKE :user_name")
            params["user_name"] = f"%{user_name}%"
        if start_date:
            conditions.append("created_at >= :start_date")
            params["start_date"] = f"{start_date} 00:00:00"
        if end_date:
            conditions.append("created_at <= :end_date")
            params["end_date"] = f"{end_date} 23:59:59"
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        result = await db.execute(text(f"""
            SELECT id, created_at, user_name, user_role, action, entity_type, 
                   entity_name, status, ip_address, user_agent
            FROM audit_logs 
            WHERE {where_clause}
            ORDER BY created_at DESC 
            LIMIT 10000
        """), params)
        rows = result.fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Заголовки
        writer.writerow([
            'ID', 'Дата и время', 'Пользователь', 'Роль', 'Действие',
            'Тип объекта', 'Имя объекта', 'Статус', 'IP адрес', 'User Agent'
        ])
        
        # Данные
        for row in rows:
            writer.writerow([
                str(row.id) if row.id else '',
                row.created_at.isoformat() if row.created_at else '',
                row.user_name or 'Система',
                row.user_role or '',
                row.action,
                row.entity_type or '',
                row.entity_name or '',
                row.status or 'success',
                row.ip_address or '',
                (row.user_agent or '')[:200]
            ])
        
        output.seek(0)
        
        # Логируем экспорт
        await log_event(
            db=db,
            user_name="system",
            action="export_audit",
            entity_type="audit",
            details={"count": len(rows)}
        )
        
        filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue().encode('utf-8-sig')]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting audit: {e}")
        return StreamingResponse(
            io.BytesIO(f"Error: {str(e)}".encode()),
            media_type="text/plain"
        )


@router.delete("/logs")
async def clear_old_logs(
    older_than_days: int = Query(90, ge=7, le=365, description="Удалить записи старше (дней)"),
    entity_type: Optional[str] = Query(None, description="Только для указанного типа сущности"),
    db: AsyncSession = Depends(get_db)
):
    """Удаление старых записей аудита"""
    await ensure_audit_table(db)
    
    try:
        cutoff = datetime.now() - timedelta(days=older_than_days)
        
        conditions = ["created_at < :cutoff"]
        params = {"cutoff": cutoff}
        
        if entity_type:
            conditions.append("entity_type = :entity_type")
            params["entity_type"] = entity_type
        
        where_clause = " AND ".join(conditions)
        
        # Считаем количество
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}"),
            params
        )
        count = count_result.scalar() or 0
        
        if count > 0:
            await db.execute(text(f"DELETE FROM audit_logs WHERE {where_clause}"), params)
            await db.commit()
            
            await log_event(
                db=db,
                user_name="system",
                action="cleanup_audit",
                entity_type="audit",
                details={"deleted_count": count, "older_than_days": older_than_days}
            )
        
        return {
            "message": f"Deleted {count} audit logs",
            "deleted_count": count,
            "older_than_days": older_than_days,
            "cutoff_date": cutoff.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return {"message": str(e), "deleted_count": 0}


@router.get("/users/{user_name}/activity")
async def get_user_activity(
    user_name: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Получение активности конкретного пользователя"""
    await ensure_audit_table(db)
    
    try:
        result = await db.execute(text("""
            SELECT id, action, entity_type, entity_name, status, created_at, ip_address
            FROM audit_logs 
            WHERE user_name = :user_name
            ORDER BY created_at DESC 
            LIMIT :limit
        """), {"user_name": user_name, "limit": limit})
        
        rows = result.fetchall()
        
        if not rows:
            return {"user_name": user_name, "total_actions": 0, "logs": []}
        
        logs = []
        for row in rows:
            logs.append({
                "id": str(row.id) if row.id else None,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_name": row.entity_name,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "ip_address": row.ip_address
            })
        
        return {
            "user_name": user_name,
            "total_actions": len(rows),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return {"user_name": user_name, "total_actions": 0, "logs": []}
