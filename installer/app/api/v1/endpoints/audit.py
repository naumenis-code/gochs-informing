#!/usr/bin/env python3
"""Audit endpoints - полная исправленная версия"""

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
from app.schemas.audit import (
    AuditLogResponse, AuditStatsResponse, AuditLogCreate,
    AuditLogListResponse, ClearOldLogsResponse, UserActivityResponse
)

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
        entity_name: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> AuditLog:
        """Запись события в аудит"""
        log = AuditLog(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            status=status,
            error_message=error_message,
            execution_time_ms=execution_time_ms
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log


def get_client_info(request: Request) -> dict:
    """Получение информации о клиенте из запроса"""
    ip_address = None
    if request.client:
        ip_address = request.client.host
    elif request.headers.get("x-forwarded-for"):
        ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()
    elif request.headers.get("x-real-ip"):
        ip_address = request.headers.get("x-real-ip")
    
    return {
        "ip_address": ip_address,
        "user_agent": request.headers.get("user-agent", ""),
        "request_method": request.method,
        "request_path": request.url.path
    }


@router.get("/logs")
async def get_audit_logs(
    request: Request,
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(100, ge=1, le=1000, description="Количество записей"),
    action: Optional[str] = Query(None, description="Фильтр по действию"),
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    user_name: Optional[str] = Query(None, description="Фильтр по имени пользователя"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка событий аудита с фильтрацией и пагинацией
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    # Применяем фильтры
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.where(AuditLog.entity_type.ilike(f"%{entity_type}%"))
    if user_name:
        query = query.where(AuditLog.user_name.ilike(f"%{user_name}%"))
    if status:
        query = query.where(AuditLog.status == status)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    # Общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Пагинация
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Логируем просмотр аудита
    client_info = get_client_info(request)
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        action="view",
        entity_type="audit",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"]
    )
    
    items = [AuditLogResponse.model_validate(log) for log in logs]
    
    return AuditLogListResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение расширенной статистики аудита
    """
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Общее количество
    total_query = select(func.count()).select_from(AuditLog)
    total_events = (await db.execute(total_query)).scalar() or 0
    
    # За сегодня
    today_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= today)
    today_events = (await db.execute(today_query)).scalar() or 0
    
    # За неделю
    week_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= week_ago)
    week_events = (await db.execute(week_query)).scalar() or 0
    
    # За месяц
    month_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= month_ago)
    month_events = (await db.execute(month_query)).scalar() or 0
    
    # Уникальные пользователи
    users_query = select(func.count(func.distinct(AuditLog.user_id))).select_from(AuditLog)
    unique_users = (await db.execute(users_query)).scalar() or 0
    
    # Ошибки
    error_query = select(func.count()).select_from(AuditLog).where(AuditLog.status == 'error')
    error_events = (await db.execute(error_query)).scalar() or 0
    
    # Предупреждения
    warning_query = select(func.count()).select_from(AuditLog).where(AuditLog.status == 'warning')
    warning_events = (await db.execute(warning_query)).scalar() or 0
    
    # Топ действий
    top_actions_query = (
        select(AuditLog.action, func.count().label('count'))
        .group_by(AuditLog.action)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_actions_result = await db.execute(top_actions_query)
    top_actions = [{"action": row[0], "count": row[1]} for row in top_actions_result.all()]
    
    # Топ сущностей
    top_entities_query = (
        select(AuditLog.entity_type, func.count().label('count'))
        .where(AuditLog.entity_type.isnot(None))
        .group_by(AuditLog.entity_type)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_entities_result = await db.execute(top_entities_query)
    top_entities = [{"entity_type": row[0], "count": row[1]} for row in top_entities_result.all()]
    
    # Топ пользователей
    top_users_query = (
        select(AuditLog.user_name, func.count().label('count'))
        .where(AuditLog.user_name.isnot(None))
        .group_by(AuditLog.user_name)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_users_result = await db.execute(top_users_query)
    top_users = [{"user_name": row[0], "count": row[1]} for row in top_users_result.all()]
    
    # Последняя активность
    recent_query = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    recent_result = await db.execute(recent_query)
    recent_activity = []
    for log in recent_result.scalars().all():
        recent_activity.append({
            "id": str(log.id),
            "time": log.created_at.isoformat(),
            "user": log.user_name or "Система",
            "action": log.action,
            "entity_type": log.entity_type,
            "status": log.status,
            "description": f"{log.user_name or 'Система'}: {log.action} {log.entity_type or ''}"
        })
    
    # Почасовая статистика за сегодня
    hourly_stats = []
    for hour in range(24):
        hour_start = today.replace(hour=hour)
        hour_end = hour_start + timedelta(hours=1)
        hour_query = select(func.count()).select_from(AuditLog).where(
            and_(AuditLog.created_at >= hour_start, AuditLog.created_at < hour_end)
        )
        count = (await db.execute(hour_query)).scalar() or 0
        hourly_stats.append({"hour": hour, "count": count})
    
    return AuditStatsResponse(
        total_events=total_events,
        today_events=today_events,
        week_events=week_events,
        month_events=month_events,
        unique_users=unique_users,
        error_events=error_events,
        warning_events=warning_events,
        top_actions=top_actions,
        top_entities=top_entities,
        top_users=top_users,
        recent_activity=recent_activity,
        hourly_stats=hourly_stats
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    request: Request,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение детальной информации о событии аудита
    """
    query = select(AuditLog).where(AuditLog.id == log_id)
    result = await db.execute(query)
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # Логируем просмотр деталей
    client_info = get_client_info(request)
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        action="view_details",
        entity_type="audit",
        entity_id=log_id,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"]
    )
    
    return AuditLogResponse.model_validate(log)


@router.post("/logs", response_model=AuditLogResponse)
async def create_audit_log(
    log_data: AuditLogCreate,
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание записи аудита (для внутреннего использования)
    """
    client_info = get_client_info(request)
    audit_service = AuditService(db)
    
    log = await audit_service.log_action(
        user_id=log_data.user_id or current_user.id,
        user_name=log_data.user_name or current_user.full_name,
        user_role=log_data.user_role or current_user.role,
        action=log_data.action,
        entity_type=log_data.entity_type,
        entity_id=log_data.entity_id,
        entity_name=log_data.entity_name,
        details=log_data.details,
        ip_address=log_data.ip_address or client_info["ip_address"],
        user_agent=log_data.user_agent or client_info["user_agent"],
        request_method=log_data.request_method or client_info["request_method"],
        request_path=log_data.request_path or client_info["request_path"],
        status=log_data.status.value if hasattr(log_data.status, 'value') else str(log_data.status),
        error_message=log_data.error_message,
        execution_time_ms=log_data.execution_time_ms
    )
    
    return AuditLogResponse.model_validate(log)


@router.get("/export")
async def export_audit_logs(
    action: Optional[str] = Query(None, description="Фильтр по действию"),
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    user_name: Optional[str] = Query(None, description="Фильтр по имени пользователя"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Экспорт журнала аудита в CSV (UTF-8 BOM для Excel)
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.where(AuditLog.entity_type.ilike(f"%{entity_type}%"))
    if user_name:
        query = query.where(AuditLog.user_name.ilike(f"%{user_name}%"))
    if status:
        query = query.where(AuditLog.status == status)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Создаем CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Заголовки
    writer.writerow([
        'ID', 'Дата и время', 'Пользователь', 'Роль', 'Действие',
        'Тип объекта', 'ID объекта', 'Имя объекта', 'Статус',
        'IP адрес', 'Метод', 'Путь', 'Время выполнения (мс)', 'Ошибка'
    ])
    
    # Данные
    for log in logs:
        writer.writerow([
            str(log.id),
            log.created_at.isoformat() if log.created_at else '',
            log.user_name or 'Система',
            log.user_role or '',
            log.action,
            log.entity_type or '',
            str(log.entity_id) if log.entity_id else '',
            log.entity_name or '',
            log.status,
            log.ip_address or '',
            log.request_method or '',
            log.request_path or '',
            str(log.execution_time_ms) if log.execution_time_ms else '',
            log.error_message or ''
        ])
    
    output.seek(0)
    
    # Логируем экспорт
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        action="export",
        entity_type="audit",
        details={"filters": {"action": action, "entity_type": entity_type, "user_name": user_name}},
        ip_address=current_user.last_login_ip if hasattr(current_user, 'last_login_ip') else None
    )
    
    filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # UTF-8 BOM для корректного открытия в Excel
    return StreamingResponse(
        iter([output.getvalue().encode('utf-8-sig')]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/logs", response_model=ClearOldLogsResponse)
async def clear_old_logs(
    older_than_days: int = Query(90, ge=7, le=365, description="Удалить записи старше (дней)"),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление старых записей аудита
    """
    cutoff_date = datetime.now() - timedelta(days=older_than_days)
    
    # Считаем сколько будет удалено
    count_query = select(func.count()).select_from(AuditLog).where(AuditLog.created_at < cutoff_date)
    deleted_count = (await db.execute(count_query)).scalar() or 0
    
    if deleted_count == 0:
        return ClearOldLogsResponse(
            message="No old logs to delete",
            deleted_count=0,
            older_than_days=older_than_days,
            cutoff_date=cutoff_date.isoformat()
        )
    
    # Удаляем
    delete_stmt = AuditLog.__table__.delete().where(AuditLog.created_at < cutoff_date)
    await db.execute(delete_stmt)
    await db.commit()
    
    # Логируем очистку
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        action="delete",
        entity_type="audit",
        details={"deleted_count": deleted_count, "older_than_days": older_than_days},
        status="success"
    )
    
    logger.info(f"Deleted {deleted_count} audit logs older than {older_than_days} days by {current_user.full_name}")
    
    return ClearOldLogsResponse(
        message=f"Deleted {deleted_count} audit logs older than {older_than_days} days",
        deleted_count=deleted_count,
        older_than_days=older_than_days,
        cutoff_date=cutoff_date.isoformat()
    )


@router.get("/users/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Количество записей"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение активности конкретного пользователя
    """
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
    
    if not logs:
        return UserActivityResponse(
            user_id=str(user_id),
            user_name=None,
            total_actions=0
        )
    
    # Статистика по пользователю
    actions_by_type = {}
    actions_by_entity = {}
    
    for log in logs:
        actions_by_type[log.action] = actions_by_type.get(log.action, 0) + 1
        if log.entity_type:
            actions_by_entity[log.entity_type] = actions_by_entity.get(log.entity_type, 0) + 1
    
    return UserActivityResponse(
        user_id=str(user_id),
        user_name=logs[0].user_name,
        user_role=logs[0].user_role,
        total_actions=len(logs),
        first_action=logs[-1].created_at.isoformat() if logs else None,
        last_action=logs[0].created_at.isoformat() if logs else None,
        actions_by_type=actions_by_type,
        actions_by_entity=actions_by_entity,
        recent_logs=[AuditLogResponse.model_validate(log) for log in logs[:10]]
    )


@router.get("/summary/daily")
async def get_daily_summary(
    days: int = Query(7, ge=1, le=30, description="Количество дней"),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение сводки по дням
    """
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
            "date": row.date.isoformat() if row.date else None,
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
