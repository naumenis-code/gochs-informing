#!/usr/bin/env python3
"""
API эндпоинты для управления группами контактов ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база — группы

Функционал:
- CRUD операции с группами
- Управление участниками (добавление/удаление/обновление)
- Массовые операции
- Объединение групп
- Получение списка для обзвона
- Статистика
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, Request
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.services.group_service import GroupService
from app.schemas.group import (
    GroupCreate, GroupUpdate, GroupResponse, GroupDetailResponse,
    GroupListResponse, GroupMemberInfo,
    AddMembersRequest, RemoveMembersRequest, UpdateMemberRequest,
    GroupFilterParams, GroupBulkAction, GroupMergeRequest, GroupStats,
    GroupDialerInfo
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
# ПОЛУЧЕНИЕ СПИСКА ГРУПП
# ============================================================================

@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="Получить список групп",
    description="Возвращает список групп контактов с пагинацией и фильтрацией."
)
async def list_groups(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, min_length=1, max_length=255, description="Поиск по названию"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    is_system: Optional[bool] = Query(None, description="Только системные/пользовательские"),
    has_members: Optional[bool] = Query(None, description="Только с участниками"),
    min_members: Optional[int] = Query(None, ge=0, description="Мин. количество участников"),
    max_members: Optional[int] = Query(None, ge=0, description="Макс. количество участников"),
    sort_field: str = Query("name", description="Поле сортировки"),
    sort_direction: str = Query("asc", description="Направление (asc/desc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка групп с фильтрацией
    
    Доступно: admin, operator, viewer
    """
    try:
        service = GroupService(db)
        result = await service.list_groups(
            pagination=pagination,
            search=search,
            is_active=is_active,
            is_system=is_system,
            has_members=has_members,
            min_members=min_members,
            max_members=max_members,
            sort_field=sort_field,
            sort_direction=sort_direction
        )
        return result
        
    except Exception as e:
        logger.error(f"Ошибка получения списка групп: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения списка: {str(e)}"
        )


# ============================================================================
# ПОЛУЧЕНИЕ ГРУППЫ ПО ID
# ============================================================================

@router.get(
    "/{group_id}",
    response_model=GroupDetailResponse,
    summary="Получить группу по ID",
    description="Возвращает детальную информацию о группе с участниками."
)
async def get_group(
    group_id: UUID,
    include_members: bool = Query(True, description="Включить список участников"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение группы по ID с участниками"""
    service = GroupService(db)
    group = await service.get_group(group_id, include_members=include_members)
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена"
        )
    
    # Формирование ответа
    members = []
    if include_members:
        for m in group.memberships:
            if m.contact:
                members.append(GroupMemberInfo(
                    contact_id=m.contact_id,
                    contact_name=m.contact.full_name,
                    department=m.contact.department,
                    position=m.contact.position,
                    mobile_number=m.contact.mobile_number,
                    internal_number=m.contact.internal_number,
                    email=m.contact.email,
                    is_active=m.contact.is_active,
                    role=m.role,
                    priority=m.priority,
                    note=m.note,
                    added_at=m.added_at,
                    added_by=m.added_by,
                ))
    
    # Статистика по подразделениям
    dept_count = {}
    for m in group.memberships:
        if m.contact and m.contact.department:
            dept = m.contact.department
            dept_count[dept] = dept_count.get(dept, 0) + 1
    
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        color=group.color,
        is_active=group.is_active,
        is_archived=group.is_archived,
        is_system=group.is_system,
        member_count=group.member_count,
        total_member_count=group.total_member_count,
        mobile_members_count=group.mobile_members_count,
        internal_members_count=group.internal_members_count,
        default_priority=group.default_priority,
        max_retries=group.max_retries,
        created_by=group.created_by,
        updated_by=group.updated_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=members,
        members_by_department=[
            {"department": k, "count": v}
            for k, v in sorted(dept_count.items(), key=lambda x: x[1], reverse=True)
        ],
        active_members=len([m for m in members if m.is_active]),
        inactive_members=len([m for m in members if not m.is_active]),
    )


# ============================================================================
# СОЗДАНИЕ ГРУППЫ
# ============================================================================

@router.post(
    "/",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую группу",
    description="Создает новую группу контактов. Только для администраторов."
)
async def create_group(
    group_data: GroupCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Создание новой группы
    
    Требует роль: admin
    
    Можно сразу добавить контакты, указав их ID в contact_ids.
    """
    try:
        service = GroupService(db)
        group = await service.create_group(
            group_data=group_data,
            created_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="group_created",
            entity_type="group",
            entity_id=group.id,
            entity_name=group.name,
            details={
                "description": group.description,
                "color": group.color,
                "is_system": group.is_system,
                "member_count": group.member_count,
                "contact_ids": [str(cid) for cid in (group_data.contact_ids or [])],
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            color=group.color,
            is_active=group.is_active,
            is_archived=False,
            is_system=group.is_system,
            member_count=group.member_count,
            total_member_count=group.total_member_count,
            mobile_members_count=0,
            internal_members_count=0,
            default_priority=group.default_priority,
            max_retries=group.max_retries,
            created_by=group.created_by,
            updated_by=None,
            created_at=group.created_at,
            updated_at=None,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка создания группы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания: {str(e)}"
        )


# ============================================================================
# ОБНОВЛЕНИЕ ГРУППЫ
# ============================================================================

@router.patch(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Обновить группу",
    description="Обновляет данные группы. Только для администраторов."
)
async def update_group(
    group_id: UUID,
    update_data: GroupUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Обновление группы
    
    Требует роль: admin
    """
    try:
        service = GroupService(db)
        group = await service.update_group(
            group_id=group_id,
            update_data=update_data,
            updated_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="group_updated",
            entity_type="group",
            entity_id=group.id,
            entity_name=group.name,
            details={
                "updated_fields": update_data.model_dump(exclude_unset=True, exclude_none=True),
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            color=group.color,
            is_active=group.is_active,
            is_archived=group.is_archived,
            is_system=group.is_system,
            member_count=group.member_count,
            total_member_count=group.total_member_count,
            mobile_members_count=group.mobile_members_count,
            internal_members_count=group.internal_members_count,
            default_priority=group.default_priority,
            max_retries=group.max_retries,
            created_by=group.created_by,
            updated_by=group.updated_by,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# УДАЛЕНИЕ ГРУППЫ
# ============================================================================

@router.delete(
    "/{group_id}",
    response_model=MessageResponse,
    summary="Удалить/архивировать группу",
    description="Удаляет или архивирует группу. Только для администраторов."
)
async def delete_group(
    group_id: UUID,
    hard_delete: bool = Query(False, description="Полное удаление"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Удаление/архивирование группы
    
    Требует роль: admin
    
    Системные группы (Все сотрудники, Руководство, Дежурная смена) нельзя удалить.
    """
    try:
        service = GroupService(db)
        await service.delete_group(
            group_id=group_id,
            deleted_by=current_user.id,
            hard_delete=hard_delete
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="group_deleted" if hard_delete else "group_archived",
            entity_type="group",
            entity_id=group_id,
            details={"hard_delete": hard_delete},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        action_text = "удалена" if hard_delete else "архивирована"
        return MessageResponse(
            message=f"Группа успешно {action_text}",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# ДОБАВЛЕНИЕ УЧАСТНИКОВ В ГРУППУ
# ============================================================================

@router.post(
    "/{group_id}/members",
    response_model=BulkOperationResult,
    summary="Добавить участников в группу",
    description="Добавляет контакты в группу. Доступно: admin, operator."
)
async def add_members(
    group_id: UUID,
    members_data: AddMembersRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавление контактов в группу
    
    Доступно: admin, operator
    
    Можно указать:
    - role: роль контакта в группе (например, "руководитель")
    - priority: приоритет обзвона (1-10)
    - reason: причина добавления (для аудита)
    - note: заметка
    """
    # Проверка прав
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для добавления участников"
        )
    
    try:
        service = GroupService(db)
        result = await service.add_members(
            group_id=group_id,
            request=members_data,
            added_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="group_members_added",
            entity_type="group",
            entity_id=group_id,
            details={
                "count": len(members_data.contact_ids),
                "added": result.success_count,
                "skipped": result.skipped_count,
                "errors": result.error_count,
            },
            ip_address=request.client.host if request else None,
            status="success" if result.error_count == 0 else "warning"
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# УДАЛЕНИЕ УЧАСТНИКОВ ИЗ ГРУППЫ
# ============================================================================

@router.delete(
    "/{group_id}/members",
    response_model=BulkOperationResult,
    summary="Удалить участников из группы",
    description="Удаляет контакты из группы. Доступно: admin, operator."
)
async def remove_members(
    group_id: UUID,
    members_data: RemoveMembersRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удаление контактов из группы
    
    Доступно: admin, operator
    
    - hard_delete=False: мягкое удаление (можно восстановить)
    - hard_delete=True: полное удаление связи
    """
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления участников"
        )
    
    try:
        service = GroupService(db)
        result = await service.remove_members(
            group_id=group_id,
            request=members_data,
            removed_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="group_members_removed",
            entity_type="group",
            entity_id=group_id,
            details={
                "count": len(members_data.contact_ids),
                "removed": result.success_count,
                "not_found": result.error_count,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# ОБНОВЛЕНИЕ ПАРАМЕТРОВ УЧАСТНИКА
# ============================================================================

@router.patch(
    "/{group_id}/members/{contact_id}",
    response_model=MessageResponse,
    summary="Обновить параметры участника",
    description="Обновляет роль, приоритет или статус участника в группе."
)
async def update_member(
    group_id: UUID,
    contact_id: UUID,
    update_data: UpdateMemberRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновление параметров участника группы
    
    Доступно: admin, operator
    
    Можно изменить:
    - role: роль в группе
    - priority: приоритет обзвона (1-10)
    - is_active: активен/неактивен
    - note: заметка
    """
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    try:
        service = GroupService(db)
        
        # ID контакта из пути имеет приоритет
        update_data.contact_id = contact_id
        
        await service.update_member(
            group_id=group_id,
            request=update_data,
            updated_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="group_member_updated",
            entity_type="group",
            entity_id=group_id,
            details={
                "contact_id": str(contact_id),
                "updates": update_data.model_dump(exclude_unset=True, exclude_none=True),
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message="Параметры участника обновлены",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА УЧАСТНИКОВ
# ============================================================================

@router.get(
    "/{group_id}/members",
    response_model=PaginatedResponse,
    summary="Получить список участников группы",
    description="Возвращает список участников группы с пагинацией."
)
async def get_members(
    group_id: UUID,
    pagination: PaginationParams = Depends(),
    active_only: bool = Query(True, description="Только активные"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка участников группы"""
    service = GroupService(db)
    
    # Проверка существования группы
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена"
        )
    
    result = await service.get_members(
        group_id=group_id,
        active_only=active_only,
        pagination=pagination
    )
    
    return result


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА ДЛЯ ОБЗВОНА
# ============================================================================

@router.get(
    "/{group_id}/dialer-list",
    summary="Получить список для обзвона",
    description="Возвращает список контактов с номерами для запуска обзвона."
)
async def get_dialer_list(
    group_id: UUID,
    prefer_mobile: bool = Query(True, description="Предпочитать мобильные номера"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка для обзвона
    
    Возвращает отсортированный по приоритету список контактов
    с номерами телефонов, готовый для запуска кампании обзвона.
    """
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    service = GroupService(db)
    
    # Проверка существования группы
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с ID {group_id} не найдена"
        )
    
    if not group.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Группа неактивна"
        )
    
    dial_list = await service.get_dialer_list(
        group_id=group_id,
        prefer_mobile=prefer_mobile
    )
    
    return {
        "group_id": str(group_id),
        "group_name": group.name,
        "total_contacts": len(dial_list),
        "contacts": dial_list,
    }


# ============================================================================
# МАССОВЫЕ ОПЕРАЦИИ С ГРУППАМИ
# ============================================================================

@router.post(
    "/bulk-action",
    response_model=BulkOperationResult,
    summary="Массовое действие с группами",
    description="Выполняет массовое действие. Только для администраторов."
)
async def bulk_group_action(
    bulk_data: GroupBulkAction,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Массовое действие с группами
    
    Действия: activate, deactivate, archive, delete
    """
    try:
        service = GroupService(db)
        result = await service.bulk_action(
            group_ids=bulk_data.group_ids,
            action=bulk_data.action,
            performed_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action=f"groups_{bulk_data.action}",
            entity_type="group",
            details={
                "action": bulk_data.action,
                "count": len(bulk_data.group_ids),
                "success": result.success_count,
                "errors": result.error_count,
            },
            ip_address=request.client.host if request else None,
            status="success" if result.error_count == 0 else "warning"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка массового действия: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {str(e)}"
        )


# ============================================================================
# ОБЪЕДИНЕНИЕ ГРУПП
# ============================================================================

@router.post(
    "/merge",
    response_model=GroupResponse,
    summary="Объединить группы",
    description="Объединяет несколько групп в одну. Только для администраторов."
)
async def merge_groups(
    merge_data: GroupMergeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Объединение групп
    
    Требует роль: admin
    
    Все участники исходных групп переносятся в целевую.
    Исходные группы можно удалить после объединения.
    """
    try:
        service = GroupService(db)
        result_group = await service.merge_groups(
            source_group_ids=merge_data.source_group_ids,
            target_group_id=merge_data.target_group_id,
            new_group_name=merge_data.new_group_name,
            delete_sources=merge_data.delete_source_groups,
            performed_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="groups_merged",
            entity_type="group",
            entity_id=result_group.id,
            entity_name=result_group.name,
            details={
                "source_group_ids": [str(gid) for gid in merge_data.source_group_ids],
                "target_group_id": str(result_group.id),
                "delete_sources": merge_data.delete_source_groups,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return GroupResponse(
            id=result_group.id,
            name=result_group.name,
            description=result_group.description,
            color=result_group.color,
            is_active=result_group.is_active,
            is_archived=result_group.is_archived,
            is_system=result_group.is_system,
            member_count=result_group.member_count,
            total_member_count=result_group.total_member_count,
            mobile_members_count=result_group.mobile_members_count,
            internal_members_count=result_group.internal_members_count,
            default_priority=result_group.default_priority,
            max_retries=result_group.max_retries,
            created_by=result_group.created_by,
            updated_by=result_group.updated_by,
            created_at=result_group.created_at,
            updated_at=result_group.updated_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# ВОССТАНОВЛЕНИЕ ГРУППЫ
# ============================================================================

@router.post(
    "/{group_id}/restore",
    response_model=MessageResponse,
    summary="Восстановить группу из архива",
    description="Восстанавливает архивированную группу. Только для администраторов."
)
async def restore_group(
    group_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Восстановление архивированной группы"""
    try:
        service = GroupService(db)
        group = await service.restore_group(
            group_id=group_id,
            restored_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="group_restored",
            entity_type="group",
            entity_id=group_id,
            entity_name=group.name,
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message=f"Группа '{group.name}' восстановлена",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# СТАТИСТИКА ПО ГРУППАМ
# ============================================================================

@router.get(
    "/stats/summary",
    summary="Получить статистику по группам",
    description="Возвращает сводную статистику."
)
async def get_group_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение статистики по группам"""
    service = GroupService(db)
    stats = await service.get_stats()
    return stats


# ============================================================================
# БЫСТРОЕ ДОБАВЛЕНИЕ КОНТАКТА В ГРУППУ
# ============================================================================

@router.post(
    "/{group_id}/members/{contact_id}",
    response_model=MessageResponse,
    summary="Быстро добавить контакт в группу",
    description="Добавляет один контакт в группу."
)
async def add_single_member(
    group_id: UUID,
    contact_id: UUID,
    priority: int = Query(5, ge=1, le=10, description="Приоритет обзвона"),
    role: Optional[str] = Query(None, description="Роль в группе"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Быстрое добавление одного контакта в группу"""
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    try:
        service = GroupService(db)
        add_request = AddMembersRequest(
            contact_ids=[contact_id],
            priority=priority,
            role=role,
        )
        
        result = await service.add_members(
            group_id=group_id,
            request=add_request,
            added_by=current_user.id
        )
        
        if result.success_count > 0:
            return MessageResponse(
                message="Контакт добавлен в группу",
                success=True
            )
        elif result.skipped_count > 0:
            return MessageResponse(
                message="Контакт уже состоит в группе",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.errors[0]['error'] if result.errors else "Неизвестная ошибка"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка добавления контакта в группу: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {str(e)}"
        )
