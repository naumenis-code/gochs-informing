#!/usr/bin/env python3
"""
API эндпоинты для управления пользователями ГО-ЧС Информирование
Соответствует ТЗ, раздел 22: Роли пользователей

Доступ:
- Администратор: полный доступ (CRUD, блокировка, сброс пароля)
- Оператор: только просмотр своего профиля
"""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.services.user_service import UserService
from app.schemas.user import (
    UserCreate, UserUpdate, UserPasswordChange, UserPasswordReset,
    UserResponse, UserDetailResponse, UserListResponse,
    UserRole, UserFilterParams
)
from app.schemas.common import (
    PaginatedResponse, MessageResponse, IDResponse,
    BulkOperationResult, PaginationParams
)
from app.models.user import User
from app.utils.audit_helper import log_action

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="Получить список пользователей",
    description="Возвращает список пользователей с пагинацией и фильтрацией. Только для администраторов."
)
async def list_users(
    pagination: PaginationParams = Depends(),
    role: Optional[UserRole] = Query(None, description="Фильтр по роли"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    search: Optional[str] = Query(None, min_length=2, description="Поиск по имени/email/логину"),
    sort_field: str = Query("created_at", description="Поле сортировки"),
    sort_direction: str = Query("desc", description="Направление (asc/desc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    """
    Получение списка пользователей с фильтрацией
    
    Требует роль: admin
    """
    try:
        service = UserService(db)
        result = await service.list_users(
            page=pagination.page,
            page_size=pagination.page_size,
            role=role,
            is_active=is_active,
            search=search,
            sort_field=sort_field,
            sort_direction=sort_direction
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения списка: {str(e)}"
        )


# ============================================================================
# ПОЛУЧЕНИЕ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.get(
    "/me",
    response_model=UserDetailResponse,
    summary="Получить свой профиль",
    description="Возвращает данные текущего авторизованного пользователя."
)
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение профиля текущего пользователя"""
    service = UserService(db)
    user = await service.get_user(current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login,
        login_attempts=user.login_attempts or 0,
        force_password_change=user.force_password_change or False,
        created_at=user.created_at,
        updated_at=user.updated_at,
        created_by=user.created_by,
        updated_by=user.updated_by,
        total_campaigns=0,  # TODO: добавить реальный подсчет
        total_logins=user.login_count or 0,
        account_locked_until=user.locked_until,
    )


# ============================================================================
# ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО ID
# ============================================================================

@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    summary="Получить пользователя по ID",
    description="Возвращает детальную информацию о пользователе. Только для администраторов."
)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получение пользователя по ID (только admin)"""
    service = UserService(db)
    user = await service.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден"
        )
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login,
        login_attempts=user.login_attempts or 0,
        force_password_change=user.force_password_change or False,
        created_at=user.created_at,
        updated_at=user.updated_at,
        created_by=user.created_by,
        updated_by=user.updated_by,
        total_campaigns=0,
        total_logins=user.login_count or 0,
        account_locked_until=user.locked_until,
    )


# ============================================================================
# СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.post(
    "/",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового пользователя",
    description="Создает нового пользователя системы. Только для администраторов."
)
async def create_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Создание нового пользователя
    
    Требует роль: admin
    Пароль должен содержать:
    - Минимум 8 символов
    - Хотя бы одну цифру
    - Хотя бы одну букву
    - Хотя бы одну заглавную букву
    - Хотя бы один спецсимвол
    """
    try:
        service = UserService(db)
        user = await service.create_user(
            user_data=user_data,
            created_by=current_user.id
        )
        
        # Аудит
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="user_created",
            entity_type="user",
            entity_id=user.id,
            entity_name=user.username,
            details={
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return UserDetailResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            last_login=None,
            login_attempts=0,
            force_password_change=True,
            created_at=user.created_at,
            updated_at=None,
            created_by=user.created_by,
            updated_by=None,
            total_campaigns=0,
            total_logins=0,
            account_locked_until=None,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка создания пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания пользователя: {str(e)}"
        )


# ============================================================================
# ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.patch(
    "/{user_id}",
    response_model=UserDetailResponse,
    summary="Обновить пользователя",
    description="Обновляет данные пользователя. Только для администраторов."
)
async def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Обновление данных пользователя
    
    Требует роль: admin
    Можно обновить: email, username, full_name, role, is_active
    """
    try:
        service = UserService(db)
        user = await service.update_user(
            user_id=user_id,
            update_data=update_data,
            updated_by=current_user.id
        )
        
        # Аудит
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="user_updated",
            entity_type="user",
            entity_id=user.id,
            entity_name=user.username,
            details={
                "updated_fields": update_data.model_dump(exclude_unset=True, exclude_none=True),
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return UserDetailResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            login_attempts=user.login_attempts or 0,
            force_password_change=user.force_password_change or False,
            created_at=user.created_at,
            updated_at=user.updated_at,
            created_by=user.created_by,
            updated_by=user.updated_by,
            total_campaigns=0,
            total_logins=user.login_count or 0,
            account_locked_until=user.locked_until,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления: {str(e)}"
        )


# ============================================================================
# УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Удалить/деактивировать пользователя",
    description="Удаляет или деактивирует пользователя. Только для администраторов."
)
async def delete_user(
    user_id: UUID,
    hard_delete: bool = Query(False, description="Полное удаление (False = деактивация)"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Удаление/деактивация пользователя
    
    Требует роль: admin
    - hard_delete=False: деактивация (пользователь не сможет войти)
    - hard_delete=True: полное удаление из БД
    
    Нельзя удалить самого себя.
    """
    # Защита от удаления самого себя
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя"
        )
    
    try:
        service = UserService(db)
        await service.delete_user(
            user_id=user_id,
            deleted_by=current_user.id,
            hard_delete=hard_delete
        )
        
        # Аудит
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="user_deleted" if hard_delete else "user_deactivated",
            entity_type="user",
            entity_id=user_id,
            details={"hard_delete": hard_delete},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        action_text = "удален" if hard_delete else "деактивирован"
        return MessageResponse(
            message=f"Пользователь успешно {action_text}",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления: {str(e)}"
        )


# ============================================================================
# СМЕНА ПАРОЛЯ (ТЕКУЩИМ ПОЛЬЗОВАТЕЛЕМ)
# ============================================================================

@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    summary="Сменить свой пароль",
    description="Позволяет текущему пользователю сменить свой пароль."
)
async def change_my_password(
    password_data: UserPasswordChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Смена собственного пароля
    
    Требуется:
    - Текущий пароль
    - Новый пароль (соответствующий требованиям сложности)
    - Подтверждение нового пароля
    """
    try:
        service = UserService(db)
        await service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="password_changed",
            entity_type="user",
            entity_id=current_user.id,
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message="Пароль успешно изменен",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# СБРОС ПАРОЛЯ (АДМИНИСТРАТОРОМ)
# ============================================================================

@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    summary="Сбросить пароль пользователя",
    description="Сбрасывает пароль пользователя. Только для администраторов."
)
async def reset_user_password(
    user_id: UUID,
    password_data: UserPasswordReset,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Сброс пароля пользователя администратором
    
    Требует роль: admin
    Пользователь должен будет сменить пароль при следующем входе.
    """
    try:
        service = UserService(db)
        new_password = await service.reset_password(
            user_id=user_id,
            new_password=password_data.new_password,
            force_change=password_data.force_change,
            reset_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="password_reset",
            entity_type="user",
            entity_id=user_id,
            details={"force_change": password_data.force_change},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message="Пароль успешно сброшен. Пользователь должен сменить его при следующем входе.",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# ИЗМЕНЕНИЕ РОЛИ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.post(
    "/{user_id}/change-role",
    response_model=MessageResponse,
    summary="Изменить роль пользователя",
    description="Изменяет роль пользователя. Только для администраторов."
)
async def change_user_role(
    user_id: UUID,
    new_role: UserRole = Query(..., description="Новая роль"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Изменение роли пользователя
    
    Требует роль: admin
    Нельзя изменить роль самому себе.
    Нельзя снять роль с последнего администратора.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя изменить свою собственную роль"
        )
    
    try:
        service = UserService(db)
        user = await service.change_role(
            user_id=user_id,
            new_role=new_role,
            changed_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="role_changed",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.username,
            details={"new_role": new_role.value if hasattr(new_role, 'value') else new_role},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message=f"Роль пользователя '{user.username}' изменена на '{new_role.value if hasattr(new_role, 'value') else new_role}'",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# РАЗБЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.post(
    "/{user_id}/unlock",
    response_model=MessageResponse,
    summary="Разблокировать пользователя",
    description="Снимает блокировку после неудачных попыток входа. Только для администраторов."
)
async def unlock_user(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Разблокировка пользователя
    
    Требует роль: admin
    Сбрасывает счетчик неудачных попыток и время блокировки.
    """
    try:
        service = UserService(db)
        user = await service.unlock_user(
            user_id=user_id,
            unlocked_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="user_unlocked",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.username,
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message=f"Пользователь '{user.username}' разблокирован",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# ВОССТАНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@router.post(
    "/{user_id}/restore",
    response_model=MessageResponse,
    summary="Восстановить пользователя",
    description="Восстанавливает деактивированного пользователя. Только для администраторов."
)
async def restore_user(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Восстановление деактивированного пользователя
    
    Требует роль: admin
    """
    try:
        service = UserService(db)
        user = await service.restore_user(
            user_id=user_id,
            restored_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="user_restored",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.username,
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message=f"Пользователь '{user.username}' восстановлен",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ
# ============================================================================

@router.get(
    "/stats/summary",
    summary="Получить статистику по пользователям",
    description="Возвращает сводную статистику. Только для администраторов."
)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получение статистики по пользователям (только admin)"""
    service = UserService(db)
    stats = await service.get_user_stats()
    return stats


# ============================================================================
# МАССОВОЕ ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

@router.post(
    "/bulk-update",
    response_model=BulkOperationResult,
    summary="Массовое обновление пользователей",
    description="Обновляет нескольких пользователей. Только для администраторов."
)
async def bulk_update_users(
    user_ids: List[UUID],
    update_data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Массовое обновление пользователей
    
    Требует роль: admin
    """
    if current_user.id in user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя массово обновить самого себя"
        )
    
    try:
        service = UserService(db)
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        result = await service.bulk_update_users(
            user_ids=user_ids,
            update_data=update_dict,
            updated_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="users_bulk_updated",
            entity_type="user",
            details={
                "count": len(user_ids),
                "updated_fields": list(update_dict.keys()),
                "success_count": result.success_count,
                "error_count": result.error_count,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка массового обновления: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {str(e)}"
        )
