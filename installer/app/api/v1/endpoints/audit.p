#!/usr/bin/env python3
"""Audit endpoints"""

import logging
import csv
import io
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_admin_user
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogResponse, AuditStatsResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/logs")
async def get_audit_logs(
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
    
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if user_name:
        query = query.where(AuditLog.user_name.ilike(f"%{user_name}%"))
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginated items
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    
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
    
    # Total events
    total_query = select(func.count()).select_from(AuditLog)
    total_events = (await db.execute(total_query)).scalar() or 0
    
    # Today events
    today_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= today)
    today_events = (await db.execute(today_query)).scalar() or 0
    
    # Unique users
    users_query = select(func.count(func.distinct(AuditLog.user_id))).select_from(AuditLog)
    unique_users = (await db.execute(users_query)).scalar() or 0
    
    # Error events
    error_query = select(func.count()).select_from(AuditLog).where(AuditLog.status == 'error')
    error_events = (await db.execute(error_query)).scalar() or 0
    
    # Top actions
    top_actions_query = (
        select(AuditLog.action, func.count().label('count'))
        .group_by(AuditLog.action)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_actions_result = await db.execute(top_actions_query)
    top_actions = [{"action": row[0], "count": row[1]} for row in top_actions_result.all()]
    
    # Recent activity
    recent_query = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    )
    recent_result = await db.execute(recent_query)
    recent_activity = []
    for log in recent_result.scalars().all():
        recent_activity.append({
            "time": log.created_at.isoformat(),
            "description": f"{log.user_name or 'Система'}: {log.action} {log.entity_type or ''}"
        })
    
    return AuditStatsResponse(
        total_events=total_events,
        today_events=today_events,
        unique_users=unique_users,
        error_events=error_events,
        top_actions=top_actions,
        recent_activity=recent_activity
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение детальной информации о событии аудита"""
    
    query = select(AuditLog).where(AuditLog.id == log_id)
    result = await db.execute(query)
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
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
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
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
        'Тип объекта', 'ID объекта', 'Статус', 'IP адрес', 'User Agent'
    ])
    
    # Data
    for log in logs:
        writer.writerow([
            str(log.id),
            log.created_at.isoformat(),
            log.user_name or 'Система',
            log.user_role or '',
            log.action,
            log.entity_type or '',
            str(log.entity_id) if log.entity_id else '',
            log.status,
            log.ip_address or '',
            log.user_agent or ''
        ])
    
    output.seek(0)
    
    # Log export action
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        action="export",
        entity_type="audit",
        details={"filters": {
            "action": action, "entity_type": entity_type,
            "user_name": user_name, "start_date": str(start_date), "end_date": str(end_date)
        }},
        ip_address=current_user.last_login_ip
    )
    
    filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/logs")
async def clear_old_logs(
    older_than_days: int = Query(90, ge=30, le=365),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Удаление старых записей аудита"""
    
    cutoff_date = datetime.now() - timedelta(days=older_than_days)
    
    delete_query = select(AuditLog).where(AuditLog.created_at < cutoff_date)
    result = await db.execute(delete_query)
    old_logs = result.scalars().all()
    
    deleted_count = len(old_logs)
    for log in old_logs:
        await db.delete(log)
    
    await db.commit()
    
    # Log cleanup action
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        action="delete",
        entity_type="audit",
        details={"deleted_count": deleted_count, "older_than_days": older_than_days},
        ip_address=current_user.last_login_ip
    )
    
    return {"message": f"Deleted {deleted_count} audit logs older than {older_than_days} days"}


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение активности конкретного пользователя"""
    
    query = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [AuditLogResponse.model_validate(log) for log in logs]
