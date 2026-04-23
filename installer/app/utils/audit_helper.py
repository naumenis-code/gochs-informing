#!/usr/bin/env python3
"""Audit helper - ХЕЛПЕР ДЛЯ ЛОГИРОВАНИЯ АУДИТА ИЗ ЛЮБЫХ МОДУЛЕЙ"""

import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ ЛОГИРОВАНИЯ
# ============================================================================

async def log_action(
    db: AsyncSession,
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = "system",
    user_role: Optional[str] = None,
    action: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> bool:
    """
    Универсальная функция логирования действий в аудит
    
    Args:
        db: Сессия базы данных
        request: Объект Request для получения IP и User-Agent
        user_id: ID пользователя
        user_name: Имя пользователя
        user_role: Роль пользователя
        action: Тип действия (login, create, update, delete, etc.)
        entity_type: Тип объекта (user, campaign, contact, etc.)
        entity_id: ID объекта
        entity_name: Имя объекта
        details: Дополнительные детали
        status: Статус (success, warning, error)
        error_message: Сообщение об ошибке
        execution_time_ms: Время выполнения в мс
    
    Returns:
        bool: True если запись создана, False в случае ошибки
    """
    try:
        from app.api.v1.endpoints.audit import log_event
        
        ip_address = None
        user_agent = None
        request_method = None
        request_path = None
        
        if request:
            if request.client:
                ip_address = request.client.host
            elif request.headers.get("x-forwarded-for"):
                ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()
            
            user_agent = request.headers.get("user-agent", "")
            request_method = request.method
            request_path = request.url.path
        
        return await log_event(
            db=db,
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
    except ImportError:
        # Если аудит не доступен - просто логируем в консоль
        logger.warning(f"Audit not available, action not logged: {action} by {user_name}")
        return False
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
        return False


# ============================================================================
# ДЕКОРАТОР ДЛЯ АВТОМАТИЧЕСКОГО ЛОГИРОВАНИЯ
# ============================================================================

def audit(
    action: str,
    entity_type: Optional[str] = None,
    get_entity_id: Optional[Callable] = None,
    get_entity_name: Optional[Callable] = None,
    log_request: bool = True,
    log_response: bool = False,
    log_errors: bool = True
):
    """
    Декоратор для автоматического логирования действий в эндпоинтах
    
    Args:
        action: Тип действия (create, update, delete, view, etc.)
        entity_type: Тип сущности
        get_entity_id: Функция для извлечения ID из результата
        get_entity_name: Функция для извлечения имени из результата
        log_request: Логировать ли запрос
        log_response: Логировать ли ответ
        log_errors: Логировать ли ошибки
    
    Example:
        @router.post("/contacts")
        @audit(action="create", entity_type="contact", get_entity_id=lambda r: r.get("id"))
        async def create_contact(...):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            # Извлекаем request и db из аргументов
            request = None
            db = None
            current_user = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, AsyncSession):
                    db = arg
                elif hasattr(arg, '__class__') and arg.__class__.__name__ == 'AsyncSession':
                    db = arg
                elif hasattr(arg, 'id') and hasattr(arg, 'username'):
                    current_user = arg
            
            if 'request' in kwargs:
                request = kwargs['request']
            if 'db' in kwargs:
                db = kwargs['db']
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            
            # Логируем запрос
            if log_request and db:
                await log_action(
                    db=db,
                    request=request,
                    user_id=str(current_user.id) if current_user else None,
                    user_name=current_user.username if current_user else "system",
                    user_role=current_user.role if current_user else None,
                    action=f"{action}_request",
                    entity_type=entity_type
                )
            
            try:
                # Выполняем функцию
                result = await func(*args, **kwargs)
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                # Логируем успешный ответ
                if db:
                    entity_id = None
                    entity_name = None
                    
                    if get_entity_id and result:
                        entity_id = get_entity_id(result)
                    elif isinstance(result, dict) and 'id' in result:
                        entity_id = result.get('id')
                    
                    if get_entity_name and result:
                        entity_name = get_entity_name(result)
                    elif isinstance(result, dict) and 'name' in result:
                        entity_name = result.get('name')
                    
                    await log_action(
                        db=db,
                        request=request,
                        user_id=str(current_user.id) if current_user else None,
                        user_name=current_user.username if current_user else "system",
                        user_role=current_user.role if current_user else None,
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        execution_time_ms=execution_time_ms,
                        status="success"
                    )
                
                return result
                
            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                # Логируем ошибку
                if log_errors and db:
                    await log_action(
                        db=db,
                        request=request,
                        user_id=str(current_user.id) if current_user else None,
                        user_name=current_user.username if current_user else "system",
                        user_role=current_user.role if current_user else None,
                        action=action,
                        entity_type=entity_type,
                        execution_time_ms=execution_time_ms,
                        status="error",
                        error_message=str(e)
                    )
                
                raise
        
        return wrapper
    return decorator


# ============================================================================
# ХЕЛПЕРЫ ДЛЯ ЧАСТЫХ ДЕЙСТВИЙ
# ============================================================================

async def log_login(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str,
    success: bool = True,
    error_message: Optional[str] = None
) -> bool:
    """Логирование входа в систему"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="login" if success else "login_failed",
        entity_type="user",
        entity_id=user_id,
        entity_name=username,
        status="success" if success else "error",
        error_message=error_message
    )


async def log_logout(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str
) -> bool:
    """Логирование выхода из системы"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="logout",
        entity_type="user",
        entity_id=user_id,
        entity_name=username,
        status="success"
    )


async def log_create(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str,
    entity_type: str,
    entity_id: str,
    entity_name: Optional[str] = None
) -> bool:
    """Логирование создания объекта"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="create",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        status="success"
    )


async def log_update(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str,
    entity_type: str,
    entity_id: str,
    entity_name: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None
) -> bool:
    """Логирование обновления объекта"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="update",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        details=changes,
        status="success"
    )


async def log_delete(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str,
    entity_type: str,
    entity_id: str,
    entity_name: Optional[str] = None
) -> bool:
    """Логирование удаления объекта"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="delete",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        status="success"
    )


async def log_view(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None
) -> bool:
    """Логирование просмотра объекта или списка"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="view",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        status="success"
    )


async def log_export(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str,
    entity_type: str,
    record_count: Optional[int] = None
) -> bool:
    """Логирование экспорта данных"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="export",
        entity_type=entity_type,
        details={"record_count": record_count} if record_count else None,
        status="success"
    )


async def log_settings_change(
    db: AsyncSession,
    request: Request,
    user_id: str,
    username: str,
    role: str,
    section: str,
    changes: Dict[str, Any]
) -> bool:
    """Логирование изменения настроек"""
    return await log_action(
        db=db,
        request=request,
        user_id=user_id,
        user_name=username,
        user_role=role,
        action="update_settings",
        entity_type="settings",
        entity_name=section,
        details=changes,
        status="success"
    )


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О КЛИЕНТЕ
# ============================================================================

def get_client_info(request: Request) -> Dict[str, Any]:
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


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
    # Основная функция
    "log_action",
    
    # Декоратор
    "audit",
    
    # Хелперы для частых действий
    "log_login",
    "log_logout",
    "log_create",
    "log_update",
    "log_delete",
    "log_view",
    "log_export",
    "log_settings_change",
    
    # Информация о клиенте
    "get_client_info",
]
