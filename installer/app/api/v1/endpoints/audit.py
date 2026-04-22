#!/usr/bin/env python3
"""Audit endpoints - ПОЛНАЯ версия со всеми функциями"""

import logging
import csv
import io
import json
from fastapi import APIRouter, Depends, Query, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from typing import Optional, List, Any, Dict
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
    error_message: Optional[str] = None


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
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: str


class AuditStatsResponse(BaseModel):
    total_events: int = 0
    today_events: int = 0
    week_events: int = 0
    month_events: int = 0
    unique_users: int = 0
    error_events: int = 0
    warning_events: int = 0
    success_events: int = 0
    top_actions: List[Dict[str, Any]] = []
    top_entities: List[Dict[str, Any]] = []
    top_users: List[Dict[str, Any]] = []
    recent_activity: List[Dict[str, Any]] = []
    hourly_stats: List[Dict[str, Any]] = []
    daily_stats: List[Dict[str, Any]] = []


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 100
    has_next: bool = False
    has_prev: bool = False


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_client_ip(request: Request) -> str:
    """Получение IP клиента"""
    if request.client:
        return request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return ""


async def log_audit_event(
    db: AsyncSession,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    action: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> bool:
    """Запись события в аудит"""
    try:
        details_json = json.dumps(details) if details else None
        
        query = text("""
            INSERT INTO audit_logs 
            (user_id, user_name, user_role, action, entity_type, entity_id, entity_name, 
             details, ip_address, user_agent, request_method, request_path, 
             status, error_message, execution_time_ms, created_at)
            VALUES (:user_id, :user_name, :user_role, :action, :entity_type, :entity_id, :entity_name,
                    :details::jsonb, :ip_address, :user_agent, :request_method, :request_path,
                    :status, :error_message, :execution_time_ms, NOW())
            RETURNING id
        """)
        
        result = await db.execute(query, {
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
        
        log_id = result.scalar()
        logger.debug(f"Audit log created: {log_id} - {user_name} - {action}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        await db.rollback()
        return False


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
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_entity_type ON audit_logs(entity_type)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_logs(status)"))
            
            await db.commit()
            logger.info("Audit table created")
            return True
    except Exception as e:
        logger.error(f"Error ensuring audit table: {e}")
    return False


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/log", response_model=Dict[str, Any])
async def create_audit_log(
    request: Request,
    log_data: AuditLogCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание записи аудита"""
    await ensure_audit_table(db)
    
    success = await log_audit_event(
        db=db,
        user_id=log_data.user_id,
        user_name=log_data.user_name,
        user_role=log_data.user_role,
        action=log_data.action,
        entity_type=log_data.entity_type,
        entity_id=log_data.entity_id,
        entity_name=log_data.entity_name,
        details=log_data.details,
        ip_address=log_data.ip_address or get_client_ip(request),
        user_agent=log_data.user_agent or request.headers.get("user-agent"),
        status=log_data.status,
        error_message=log_data.error_message
    )
    
    return {"success": success, "message": "Event logged" if success else "Failed to log event"}


@router.get("/logs", response_model=AuditLogListResponse)
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
        count_query = text(f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}")
        count_params = {k: v for k, v in params.items() if k not in ["limit", "skip"]}
        total_result = await db.execute(count_query, count_params)
        total = total_result.scalar() or 0
        
        # Получаем записи
        query = text(f"""
            SELECT id, user_id, user_name, user_role, action, entity_type, entity_id, 
                   entity_name, details, ip_address, user_agent, request_method, request_path,
                   status, error_message, execution_time_ms, created_at
            FROM audit_logs 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """)
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        items = []
        for row in rows:
            items.append(AuditLogResponse(
                id=str(row.id) if row.id else "",
                user_id=str(row.user_id) if row.user_id else None,
                user_name=row.user_name,
                user_role=row.user_role,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=str(row.entity_id) if row.entity_id else None,
                entity_name=row.entity_name,
                details=row.details,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                request_method=row.request_method,
                request_path=row.request_path,
                status=row.status or "success",
                error_message=row.error_message,
                execution_time_ms=row.execution_time_ms,
                created_at=row.created_at.isoformat() if row.created_at else ""
            ))
        
        # Логируем просмотр
        await log_audit_event(
            db=db,
            user_name="system",
            action="view_audit_logs",
            entity_type="audit",
            ip_address=get_client_ip(request),
            details={"filters": {"action": action, "entity_type": entity_type, "user_name": user_name}}
        )
        
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return AuditLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=limit,
            has_next=(skip + limit) < total,
            has_prev=skip > 0
        )
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return AuditLogListResponse(items=[], total=0)


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Количество дней для статистики"),
    db: AsyncSession = Depends(get_db)
):
    """Получение расширенной статистики аудита"""
    await ensure_audit_table(db)
    
    try:
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
        users_result = await db.execute(text("SELECT COUNT(DISTINCT user_name) FROM audit_logs WHERE user_name IS NOT NULL"))
        unique_users = users_result.scalar() or 0
        
        # Статусы
        error_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs WHERE status = 'error'"))
        error_events = error_result.scalar() or 0
        
        warning_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs WHERE status = 'warning'"))
        warning_events = warning_result.scalar() or 0
        
        success_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs WHERE status = 'success'"))
        success_events = success_result.scalar() or 0
        
        # Топ действий
        top_actions_result = await db.execute(text("""
            SELECT action, COUNT(*) as count 
            FROM audit_logs 
            WHERE created_at >= :start_date
            GROUP BY action 
            ORDER BY count DESC 
            LIMIT 15
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
        
        # Топ пользователей
        top_users_result = await db.execute(text("""
            SELECT user_name, user_role, COUNT(*) as count 
            FROM audit_logs 
            WHERE user_name IS NOT NULL AND created_at >= :start_date
            GROUP BY user_name, user_role 
            ORDER BY count DESC 
            LIMIT 10
        """), {"start_date": start_date})
        top_users = [{"user_name": row[0], "user_role": row[1], "count": row[2]} for row in top_users_result.fetchall()]
        
        # Последняя активность
        recent_result = await db.execute(text("""
            SELECT id, user_name, action, entity_type, entity_name, status, created_at, ip_address
            FROM audit_logs 
            ORDER BY created_at DESC 
            LIMIT 20
        """))
        recent_activity = []
        for row in recent_result.fetchall():
            recent_activity.append({
                "id": str(row.id) if row.id else None,
                "time": row.created_at.isoformat() if row.created_at else None,
                "user": row.user_name or "Система",
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_name": row.entity_name,
                "status": row.status,
                "ip_address": row.ip_address,
                "description": f"{row.user_name or 'Система'}: {row.action} {row.entity_type or ''} {row.entity_name or ''}"
            })
        
        # Почасовая статистика
        hourly_stats = []
        for hour in range(24):
            hour_start = today.replace(hour=hour)
            hour_end = hour_start + timedelta(hours=1)
            hour_result = await db.execute(text("""
                SELECT COUNT(*) FROM audit_logs 
                WHERE created_at >= :hour_start AND created_at < :hour_end
            """), {"hour_start": hour_start, "hour_end": hour_end})
            count = hour_result.scalar() or 0
            hourly_stats.append({"hour": hour, "count": count})
        
        # Дневная статистика
        daily_stats = []
        for i in range(days):
            day_start = today - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            day_result = await db.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'success') as success,
                    COUNT(*) FILTER (WHERE status = 'warning') as warnings,
                    COUNT(*) FILTER (WHERE status = 'error') as errors
                FROM audit_logs 
                WHERE created_at >= :day_start AND created_at < :day_end
            """), {"day_start": day_start, "day_end": day_end})
            row = day_result.fetchone()
            daily_stats.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "total": row.total or 0,
                "success": row.success or 0,
                "warnings": row.warnings or 0,
                "errors": row.errors or 0
            })
        
        return AuditStatsResponse(
            total_events=total_events,
            today_events=today_events,
            week_events=week_events,
            month_events=month_events,
            unique_users=unique_users,
            error_events=error_events,
            warning_events=warning_events,
            success_events=success_events,
            top_actions=top_actions,
            top_entities=top_entities,
            top_users=top_users,
            recent_activity=recent_activity,
            hourly_stats=hourly_stats,
            daily_stats=daily_stats
        )
        
    except Exception as e:
        logger.error(f"Error getting audit stats: {e}")
        return AuditStatsResponse()


@router.get("/logs/{log_id}")
async def get_audit_log_by_id(
    log_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получение детальной информации о событии аудита"""
    await ensure_audit_table(db)
    
    try:
        result = await db.execute(text("""
            SELECT id, user_id, user_name, user_role, action, entity_type, entity_id, 
                   entity_name, details, ip_address, user_agent, request_method, request_path,
                   status, error_message, execution_time_ms, created_at
            FROM audit_logs 
            WHERE id::text = :log_id
        """), {"log_id": log_id})
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Audit log not found")
        
        return {
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
            "status": row.status,
            "error_message": row.error_message,
            "execution_time_ms": row.execution_time_ms,
            "created_at": row.created_at.isoformat() if row.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_audit_logs(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    user_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
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
                   entity_name, status, ip_address, user_agent, error_message
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
            'Тип объекта', 'Имя объекта', 'Статус', 'IP адрес', 'User Agent', 'Ошибка'
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
                (row.user_agent or '')[:200],
                row.error_message or ''
            ])
        
        output.seek(0)
        
        filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Логируем экспорт
        await log_audit_event(
            db=db,
            user_name="system",
            action="export_audit",
            entity_type="audit",
            details={"count": len(rows), "filters": {"action": action, "entity_type": entity_type}}
        )
        
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
    older_than_days: int = Query(90, ge=7, le=365),
    entity_type: Optional[str] = Query(None),
    background_tasks: BackgroundTasks,
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
        count_result = await db.execute(text(f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}"), params)
        count = count_result.scalar() or 0
        
        if count == 0:
            return {"message": "No logs to delete", "deleted_count": 0}
        
        # Удаляем
        await db.execute(text(f"DELETE FROM audit_logs WHERE {where_clause}"), params)
        await db.commit()
        
        # Логируем очистку в фоне
        def log_cleanup():
            import asyncio
            async def _log():
                async for session in get_db():
                    await log_audit_event(
                        db=session,
                        user_name="system",
                        action="cleanup_audit",
                        entity_type="audit",
                        details={"deleted_count": count, "older_than_days": older_than_days, "entity_type": entity_type}
                    )
                    break
            asyncio.create_task(_log())
        
        background_tasks.add_task(log_cleanup)
        
        logger.info(f"Deleted {count} audit logs older than {older_than_days} days")
        
        return {
            "message": f"Deleted {count} audit logs",
            "deleted_count": count,
            "older_than_days": older_than_days,
            "cutoff_date": cutoff.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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
        
        # Статистика
        stats_result = await db.execute(text("""
            SELECT 
                COUNT(*) as total,
                MIN(created_at) as first_action,
                MAX(created_at) as last_action,
                COUNT(DISTINCT action) as unique_actions,
                COUNT(*) FILTER (WHERE status = 'error') as errors
            FROM audit_logs 
            WHERE user_name = :user_name
        """), {"user_name": user_name})
        stats = stats_result.fetchone()
        
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
            "total_actions": stats.total if stats else 0,
            "first_action": stats.first_action.isoformat() if stats and stats.first_action else None,
            "last_action": stats.last_action.isoformat() if stats and stats.last_action else None,
            "unique_actions": stats.unique_actions if stats else 0,
            "errors": stats.errors if stats else 0,
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return {"user_name": user_name, "total_actions": 0, "logs": []}


@router.post("/ensure-table")
async def ensure_audit_table_endpoint(db: AsyncSession = Depends(get_db)):
    """Проверка и создание таблицы аудита"""
    success = await ensure_audit_table(db)
    return {"success": success, "message": "Table ensured" if success else "Failed to ensure table"}
