#!/usr/bin/env python3
"""Audit endpoints - полная версия с логированием"""

import logging
import csv
import io
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_admin_user, get_current_user
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse, AuditStatsResponse, AuditLogCreate

logger = logging.getLogger(__name__)
router = APIRouter()


class AuditService:
    """Сервис для работы с аудитом"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_action(
        self,
        user_id: Optional[UUID] = None,
        user_name: Optional[str] = None,
        user_role: Optional[str] = None,
        action: str = "",
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success"
    ) -> AuditLog:
        """Запись события в аудит"""
        log = AuditLog(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log


@router.get("/logs")
async def get_audit_logs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка событий аудита с фильтрацией"""
    
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    # Применяем фильтры
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.where(AuditLog.entity_type.ilike(f"%{entity_type}%"))
    if user_name:
        query = query.where(AuditLog.user_name.ilike(f"%{user_name}%"))
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginated items
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Логируем просмотр аудита
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        action="view",
        entity_type="audit",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "items": [AuditLogResponse.model_validate(log) for log in logs],
        "total": total
    }


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение статистики аудита"""
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    # Total events
    total_query = select(func.count()).select_from(AuditLog)
    total_events = (await db.execute(total_query)).scalar() or 0
    
    # Today events
    today_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= today)
    today_events = (await db.execute(today_query)).scalar() or 0
    
    # This week events
    week_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= week_ago)
    week_events = (await db.execute(week_query)).scalar() or 0
    
    # Unique users
    users_query = select(func.count(func.distinct(AuditLog.user_id))).select_from(AuditLog)
    unique_users = (await db.execute(users_query)).scalar() or 0
    
    # Error events
    error_query = select(func.count()).select_from(AuditLog).where(AuditLog.status == 'error')
    error_events = (await db.execute(error_query)).scalar() or 0
    
    # Warning events
    warning_query = select(func.count()).select_from(AuditLog).where(AuditLog.status == 'warning')
    warning_events = (await db.execute(warning_query)).scalar() or 0
    
    # Top actions
    top_actions_query = (
        select(AuditLog.action, func.count().label('count'))
        .group_by(AuditLog.action)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_actions_result = await db.execute(top_actions_query)
    top_actions = [{"action": row[0], "count": row[1]} for row in top_actions_result.all()]
    
    # Top entity types
    top_entities_query = (
        select(AuditLog.entity_type, func.count().label('count'))
        .where(AuditLog.entity_type.isnot(None))
        .group_by(AuditLog.entity_type)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_entities_result = await db.execute(top_entities_query)
    top_entities = [{"entity_type": row[0], "count": row[1]} for row in top_entities_result.all()]
    
    # Recent activity
    recent_query = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    recent_result = await db.execute(recent_query)
    recent_activity = []
    for log in recent_result.scalars().all():
        recent_activity.append({
            "time": log.created_at.isoformat(),
            "user": log.user_name or "Система",
            "action": log.action,
            "entity_type": log.entity_type,
            "status": log.status,
            "description": f"{log.user_name or 'Система'}: {log.action} {log.entity_type or ''}"
        })
    
    return AuditStatsResponse(
        total_events=total_events,
        today_events=today_events,
        week_events=week_events,
        unique_users=unique_users,
        error_events=error_events,
        warning_events=warning_events,
        top_actions=top_actions,
        top_entities=top_entities,
        recent_activity=recent_activity
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    request: Request,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение детальной информации о событии аудита"""
    
    query = select(AuditLog).where(AuditLog.id == log_id)
    result = await db.execute(query)
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # Логируем просмотр деталей
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        action="view_details",
        entity_type="audit",
        entity_id=log_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return AuditLogResponse.model_validate(log)


@router.post("/logs", response_model=AuditLogResponse)
async def create_audit_log(
    log_data: AuditLogCreate,
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создание записи аудита (для внутреннего использования)"""
    
    audit_service = AuditService(db)
    log = await audit_service.log_action(
        user_id=log_data.user_id or current_user.id,
        user_name=log_data.user_name or current_user.full_name,
        user_role=log_data.user_role or current_user.role,
        action=log_data.action,
        entity_type=log_data.entity_type,
        entity_id=log_data.entity_id,
        details=log_data.details,
        ip_address=log_data.ip_address or (request.client.host if request.client else None),
        user_agent=log_data.user_agent or request.headers.get("user-agent"),
        status=log_data.status.value if hasattr(log_data.status, 'value') else str(log_data.status)
    )
    
    return AuditLogResponse.model_validate(log)


@router.get("/export")
async def export_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Экспорт журнала аудита в CSV"""
    
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.where(AuditLog.entity_type.ilike(f"%{entity_type}%"))
    if user_name:
        query = query.where(AuditLog.user_name.ilike(f"%{user_name}%"))
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Headers
    writer.writerow([
        'ID', 'Время', 'Пользователь', 'Роль', 'Действие',
        'Тип объекта', 'ID объекта', 'Статус', 'IP адрес', 'Детали'
    ])
    
    # Data
    for log in logs:
        details_str = str(log.details) if log.details else ''
        writer.writerow([
            str(log.id),
            log.created_at.isoformat() if log.created_at else '',
            log.user_name or 'Система',
            log.user_role or '',
            log.action,
            log.entity_type or '',
            str(log.entity_id) if log.entity_id else '',
            log.status,
            log.ip_address or '',
            details_str[:500]  # Ограничиваем длину
        ])
    
    output.seek(0)
    
    filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue().encode('utf-8-sig')]),  # UTF-8 BOM для Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/logs")
async def clear_old_logs(
    older_than_days: int = Query(90, ge=7, le=365),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Удаление старых записей аудита"""
    
    cutoff_date = datetime.now() - timedelta(days=older_than_days)
    
    # Считаем сколько будет удалено
    count_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at < cutoff_date)
    deleted_count = (await db.execute(count_query)).scalar() or 0
    
    if deleted_count == 0:
        return {"message": "No old logs to delete", "deleted_count": 0}
    
    # Удаляем
    delete_query = AuditLog.__table__.delete().where(AuditLog.created_at < cutoff_date)
    await db.execute(delete_query)
    await db.commit()
    
    logger.info(f"Deleted {deleted_count} audit logs older than {older_than_days} days by user {current_user.full_name}")
    
    return {
        "message": f"Deleted {deleted_count} audit logs older than {older_than_days} days",
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat()
    }


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение активности конкретного пользователя"""
    
    query = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
    )
    
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Статистика по пользователю
    stats = {
        "total_actions": len(logs),
        "actions_by_type": {},
        "first_action": logs[-1].created_at.isoformat() if logs else None,
        "last_action": logs[0].created_at.isoformat() if logs else None,
    }
    
    for log in logs:
        stats["actions_by_type"][log.action] = stats["actions_by_type"].get(log.action, 0) + 1
    
    return {
        "user_id": str(user_id),
        "user_name": logs[0].user_name if logs else None,
        "stats": stats,
        "logs": [AuditLogResponse.model_validate(log) for log in logs]
    }


@router.get("/summary/daily")
async def get_daily_summary(
    days: int = Query(7, ge=1, le=30),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение сводки по дням"""
    
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days-1)
    
    query = (
        select(
            func.date(AuditLog.created_at).label('date'),
            func.count().label('total'),
            func.count().filter(AuditLog.status == 'error').label('errors'),
            func.count().filter(AuditLog.status == 'warning').label('warnings')
        )
        .where(AuditLog.created_at >= start_date)
        .group_by(func.date(AuditLog.created_at))
        .order_by(func.date(AuditLog.created_at).desc())
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    daily_stats = []
    for row in rows:
        daily_stats.append({
            "date": row.date.isoformat(),
            "total": row.total,
            "errors": row.errors,
            "warnings": row.warnings,
            "success": row.total - row.errors - row.warnings
        })
    
    return {
        "days": days,
        "start_date": start_date.isoformat(),
        "daily_stats": daily_stats
    }
