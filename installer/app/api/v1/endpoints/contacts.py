#!/usr/bin/env python3
"""
API эндпоинты для управления контактами ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база

Функционал:
- CRUD операции с контактами
- Импорт из CSV/XLSX файлов
- Экспорт в CSV/XLSX/JSON
- Массовые операции (добавление в группы, назначение тегов)
- Поиск и фильтрация
- Статистика
"""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query,
    Request, UploadFile, File, BackgroundTasks
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.services.contact_service import ContactService
from app.schemas.contact import (
    ContactCreate, ContactUpdate, ContactResponse, ContactListResponse,
    ContactImportRequest, ContactExportRequest, ContactFilterParams,
    ContactBulkAction, ContactBulkDelete, ContactStats
)
from app.schemas.common import (
    PaginatedResponse, MessageResponse, IDResponse,
    BulkOperationResult, PaginationParams, FileUploadResponse
)
from app.models.user import User
from app.utils.audit_helper import log_action

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА КОНТАКТОВ
# ============================================================================

@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="Получить список контактов",
    description="Возвращает список контактов с пагинацией и фильтрацией."
)
async def list_contacts(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, min_length=1, max_length=255, description="Поиск"),
    department: Optional[str] = Query(None, description="Фильтр по подразделению"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    group_id: Optional[UUID] = Query(None, description="Фильтр по ID группы"),
    tag_id: Optional[UUID] = Query(None, description="Фильтр по ID тега"),
    has_mobile: Optional[bool] = Query(None, description="Только с мобильным"),
    has_internal: Optional[bool] = Query(None, description="Только с внутренним"),
    has_email: Optional[bool] = Query(None, description="Только с email"),
    sort_field: str = Query("full_name", description="Поле сортировки"),
    sort_direction: str = Query("asc", description="Направление (asc/desc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка контактов с фильтрацией
    
    Доступно: admin, operator, viewer
    """
    try:
        service = ContactService(db)
        
        filters = ContactFilterParams(
            search=search,
            department=department,
            is_active=is_active,
            group_id=group_id,
            tag_id=tag_id,
            has_mobile=has_mobile,
            has_internal=has_internal,
            has_email=has_email,
        )
        
        result = await service.list_contacts(
            pagination=pagination,
            filters=filters,
            sort_field=sort_field,
            sort_direction=sort_direction
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка получения списка контактов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения списка: {str(e)}"
        )


# ============================================================================
# ПОЛУЧЕНИЕ КОНТАКТА ПО ID
# ============================================================================

@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Получить контакт по ID",
    description="Возвращает детальную информацию о контакте."
)
async def get_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение контакта по ID"""
    service = ContactService(db)
    contact = await service.get_contact(contact_id, include_relations=True)
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Контакт с ID {contact_id} не найден"
        )
    
    return ContactResponse(
        id=contact.id,
        full_name=contact.full_name,
        department=contact.department,
        position=contact.position,
        internal_number=contact.internal_number,
        mobile_number=contact.mobile_number,
        email=contact.email,
        is_active=contact.is_active,
        is_archived=contact.is_archived,
        comment=contact.comment,
        groups=[
            {
                "id": str(gm.group.id),
                "name": gm.group.name,
                "color": gm.group.color,
                "added_at": gm.added_at,
                "role": gm.role,
                "priority": gm.priority,
            }
            for gm in contact.group_memberships
            if gm.group and gm.is_active
        ],
        tags=[
            {
                "id": str(ct.tag.id),
                "name": ct.tag.name,
                "color": ct.tag.color,
                "added_at": None,
            }
            for ct in contact.tag_assignments
            if ct.tag
        ],
        primary_phone=contact.primary_phone,
        has_mobile=contact.has_mobile,
        has_internal=contact.has_internal,
        created_by=contact.created_by,
        updated_by=contact.updated_by,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


# ============================================================================
# ПОИСК КОНТАКТА ПО НОМЕРУ
# ============================================================================

@router.get(
    "/by-phone/{phone}",
    response_model=ContactResponse,
    summary="Найти контакт по номеру телефона",
    description="Поиск контакта по мобильному или внутреннему номеру."
)
async def get_contact_by_phone(
    phone: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск контакта по номеру телефона"""
    service = ContactService(db)
    contact = await service.get_contact_by_phone(phone)
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Контакт с номером '{phone}' не найден"
        )
    
    return ContactResponse(
        id=contact.id,
        full_name=contact.full_name,
        department=contact.department,
        position=contact.position,
        internal_number=contact.internal_number,
        mobile_number=contact.mobile_number,
        email=contact.email,
        is_active=contact.is_active,
        is_archived=contact.is_archived,
        comment=contact.comment,
        groups=[],
        tags=[],
        primary_phone=contact.primary_phone,
        has_mobile=contact.has_mobile,
        has_internal=contact.has_internal,
        created_by=contact.created_by,
        updated_by=contact.updated_by,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


# ============================================================================
# СОЗДАНИЕ КОНТАКТА
# ============================================================================

@router.post(
    "/",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый контакт",
    description="Создает новый контакт. Доступно: admin, operator."
)
async def create_contact(
    contact_data: ContactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание нового контакта
    
    Требуется хотя бы один номер телефона (мобильный или внутренний).
    
    Доступно: admin, operator
    """
    try:
        service = ContactService(db)
        contact = await service.create_contact(
            contact_data=contact_data,
            created_by=current_user.id
        )
        
        # Аудит
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="contact_created",
            entity_type="contact",
            entity_id=contact.id,
            entity_name=contact.full_name,
            details={
                "mobile_number": contact.mobile_number,
                "internal_number": contact.internal_number,
                "department": contact.department,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return ContactResponse(
            id=contact.id,
            full_name=contact.full_name,
            department=contact.department,
            position=contact.position,
            internal_number=contact.internal_number,
            mobile_number=contact.mobile_number,
            email=contact.email,
            is_active=contact.is_active,
            is_archived=False,
            comment=contact.comment,
            groups=[],
            tags=[],
            primary_phone=contact.primary_phone,
            has_mobile=contact.has_mobile,
            has_internal=contact.has_internal,
            created_by=contact.created_by,
            updated_by=None,
            created_at=contact.created_at,
            updated_at=None,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка создания контакта: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания: {str(e)}"
        )


# ============================================================================
# ОБНОВЛЕНИЕ КОНТАКТА
# ============================================================================

@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Обновить контакт",
    description="Обновляет данные контакта. Доступно: admin, operator."
)
async def update_contact(
    contact_id: UUID,
    update_data: ContactUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновление контакта
    
    Доступно: admin, operator
    """
    try:
        service = ContactService(db)
        contact = await service.update_contact(
            contact_id=contact_id,
            update_data=update_data,
            updated_by=current_user.id
        )
        
        # Аудит
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="contact_updated",
            entity_type="contact",
            entity_id=contact.id,
            entity_name=contact.full_name,
            details={
                "updated_fields": update_data.model_dump(exclude_unset=True, exclude_none=True),
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return ContactResponse(
            id=contact.id,
            full_name=contact.full_name,
            department=contact.department,
            position=contact.position,
            internal_number=contact.internal_number,
            mobile_number=contact.mobile_number,
            email=contact.email,
            is_active=contact.is_active,
            is_archived=contact.is_archived,
            comment=contact.comment,
            groups=[],
            tags=[],
            primary_phone=contact.primary_phone,
            has_mobile=contact.has_mobile,
            has_internal=contact.has_internal,
            created_by=contact.created_by,
            updated_by=contact.updated_by,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка обновления контакта: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления: {str(e)}"
        )


# ============================================================================
# УДАЛЕНИЕ КОНТАКТА
# ============================================================================

@router.delete(
    "/{contact_id}",
    response_model=MessageResponse,
    summary="Удалить/архивировать контакт",
    description="Удаляет или архивирует контакт. Только для администраторов."
)
async def delete_contact(
    contact_id: UUID,
    hard_delete: bool = Query(False, description="Полное удаление (False = архивирование)"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Удаление/архивирование контакта
    
    Требует роль: admin
    - hard_delete=False: архивирование (мягкое удаление)
    - hard_delete=True: полное удаление из БД
    """
    try:
        service = ContactService(db)
        await service.delete_contact(
            contact_id=contact_id,
            deleted_by=current_user.id,
            hard_delete=hard_delete
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="contact_deleted" if hard_delete else "contact_archived",
            entity_type="contact",
            entity_id=contact_id,
            details={"hard_delete": hard_delete},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        action_text = "удален" if hard_delete else "архивирован"
        return MessageResponse(
            message=f"Контакт успешно {action_text}",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# ВОССТАНОВЛЕНИЕ КОНТАКТА
# ============================================================================

@router.post(
    "/{contact_id}/restore",
    response_model=MessageResponse,
    summary="Восстановить контакт из архива",
    description="Восстанавливает архивированный контакт. Только для администраторов."
)
async def restore_contact(
    contact_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Восстановление архивированного контакта"""
    try:
        service = ContactService(db)
        await service.restore_contact(
            contact_id=contact_id,
            restored_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="contact_restored",
            entity_type="contact",
            entity_id=contact_id,
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return MessageResponse(
            message="Контакт успешно восстановлен",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# ИМПОРТ КОНТАКТОВ
# ============================================================================

@router.post(
    "/import",
    response_model=BulkOperationResult,
    summary="Импорт контактов из файла",
    description="Импортирует контакты из CSV или XLSX файла. Только для администраторов."
)
async def import_contacts(
    file: UploadFile = File(..., description="CSV или XLSX файл с контактами"),
    update_existing: bool = Query(False, description="Обновлять существующие контакты по мобильному номеру"),
    skip_duplicates: bool = Query(True, description="Пропускать дубликаты"),
    default_group_id: Optional[UUID] = Query(None, description="ID группы для добавления всех импортированных"),
    encoding: str = Query("utf-8", description="Кодировка файла (для CSV)"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Импорт контактов из CSV/XLSX файла
    
    Требует роль: admin
    
    Поддерживаемые форматы:
    - CSV (разделитель: запятая, кодировка: utf-8)
    - XLSX (первый лист)
    
    Колонки (русские или английские названия):
    - full_name / ФИО (обязательно)
    - department / Подразделение
    - position / Должность
    - mobile_number / Мобильный
    - internal_number / Внутренний
    - email / Email
    - comment / Комментарий
    - group_names / Группы (через запятую)
    
    Максимальный размер файла: 10 МБ
    Максимальное количество строк: 10 000
    """
    try:
        # Проверка формата
        filename = file.filename or "import.csv"
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in ['csv', 'xlsx', 'xls']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неподдерживаемый формат: .{ext}. Допустимые: csv, xlsx, xls"
            )
        
        # Чтение содержимого
        content = await file.read()
        
        # Проверка размера
        max_size = 10 * 1024 * 1024  # 10 МБ
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер файла ({len(content) // 1024} КБ) превышает максимальный ({max_size // (1024*1024)} МБ)"
            )
        
        service = ContactService(db)
        
        import_options = ContactImportRequest(
            file_format=ext,
            update_existing=update_existing,
            skip_duplicates=skip_duplicates,
            default_group_ids=[default_group_id] if default_group_id else None,
            encoding=encoding,
        )
        
        result = await service.import_contacts(
            file_content=content,
            filename=filename,
            import_options=import_options,
            imported_by=current_user.id
        )
        
        # Аудит
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="contacts_imported",
            entity_type="contact",
            details={
                "filename": filename,
                "total": result.total_processed,
                "success": result.success_count,
                "skipped": result.skipped_count,
                "errors": result.error_count,
            },
            ip_address=request.client.host if request else None,
            status="success" if result.error_count == 0 else "warning"
        )
        
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка импорта контактов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка импорта: {str(e)}"
        )


# ============================================================================
# ЭКСПОРТ КОНТАКТОВ
# ============================================================================

@router.get(
    "/export",
    summary="Экспорт контактов",
    description="Экспортирует контакты в CSV, XLSX или JSON файл."
)
async def export_contacts(
    format: str = Query("csv", description="Формат: csv, xlsx, json"),
    fields: Optional[str] = Query(None, description="Поля через запятую (если None — все)"),
    group_id: Optional[UUID] = Query(None, description="Экспортировать только из группы"),
    include_archived: bool = Query(False, description="Включая архивные"),
    encoding: str = Query("utf-8", description="Кодировка"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Экспорт контактов
    
    Доступно: admin, operator
    """
    try:
        field_list = fields.split(',') if fields else None
        
        export_options = ContactExportRequest(
            format=format,
            fields=field_list,
            group_ids=[group_id] if group_id else None,
            include_archived=include_archived,
            encoding=encoding,
        )
        
        service = ContactService(db)
        content, filename, mime_type = await service.export_contacts(
            export_options=export_options
        )
        
        # Аудит
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="contacts_exported",
            entity_type="contact",
            details={
                "format": format,
                "fields": field_list,
                "group_id": str(group_id) if group_id else None,
            },
            status="success"
        )
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка экспорта: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка экспорта: {str(e)}"
        )


# ============================================================================
# МАССОВЫЕ ОПЕРАЦИИ
# ============================================================================

@router.post(
    "/bulk-action",
    response_model=BulkOperationResult,
    summary="Массовое действие с контактами",
    description="Выполняет массовое действие. Доступно: admin, operator (ограниченно)."
)
async def bulk_contact_action(
    bulk_data: ContactBulkAction,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Массовое действие с контактами
    
    Действия:
    - activate: активировать
    - deactivate: деактивировать
    - archive: архивировать
    - delete: удалить
    - add_to_group: добавить в группу (требуется group_id)
    - remove_from_group: удалить из группы (требуется group_id)
    - add_tag: назначить тег (требуется tag_id)
    - remove_tag: снять тег (требуется tag_id)
    
    Ограничения:
    - archive и delete только для admin
    """
    # Проверка прав на опасные действия
    dangerous_actions = ['archive', 'delete']
    if bulk_data.action in dangerous_actions and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Действие '{bulk_data.action}' требует роли администратора"
        )
    
    try:
        service = ContactService(db)
        
        params = {}
        if bulk_data.group_id:
            params['group_id'] = bulk_data.group_id
        if bulk_data.tag_id:
            params['tag_id'] = bulk_data.tag_id
        if bulk_data.reason:
            params['reason'] = bulk_data.reason
        
        result = await service.bulk_action(
            contact_ids=bulk_data.contact_ids,
            action=bulk_data.action,
            params=params,
            performed_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action=f"contacts_{bulk_data.action}",
            entity_type="contact",
            details={
                "action": bulk_data.action,
                "count": len(bulk_data.contact_ids),
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
# МАССОВОЕ УДАЛЕНИЕ
# ============================================================================

@router.post(
    "/bulk-delete",
    response_model=BulkOperationResult,
    summary="Массовое удаление контактов",
    description="Удаляет несколько контактов. Только для администраторов."
)
async def bulk_delete_contacts(
    delete_data: ContactBulkDelete,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Массовое удаление контактов
    
    Требует роль: admin
    - hard_delete=False: архивирование
    - hard_delete=True: полное удаление
    """
    try:
        service = ContactService(db)
        
        result = await service.bulk_action(
            contact_ids=delete_data.contact_ids,
            action="delete" if delete_data.hard_delete else "archive",
            params={
                "hard_delete": delete_data.hard_delete,
                "reason": delete_data.reason,
            },
            performed_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="contacts_bulk_deleted",
            entity_type="contact",
            details={
                "count": len(delete_data.contact_ids),
                "hard_delete": delete_data.hard_delete,
                "success": result.success_count,
                "errors": result.error_count,
            },
            ip_address=request.client.host if request else None,
            status="success" if result.error_count == 0 else "warning"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка массового удаления: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {str(e)}"
        )


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get(
    "/stats/summary",
    summary="Получить статистику по контактам",
    description="Возвращает сводную статистику."
)
async def get_contact_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение статистики по контактам"""
    service = ContactService(db)
    stats = await service.get_stats()
    return stats


# ============================================================================
# ШАБЛОН ДЛЯ ИМПОРТА
# ============================================================================

@router.get(
    "/import-template",
    summary="Скачать шаблон для импорта контактов",
    description="Возвращает пустой CSV файл с правильными заголовками."
)
async def download_import_template(
    format: str = Query("csv", description="Формат: csv, xlsx"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Скачать шаблон для импорта контактов
    
    Шаблон содержит все необходимые колонки и пример заполнения.
    """
    import csv
    import io as io_module
    
    headers = [
        'full_name', 'department', 'position',
        'mobile_number', 'internal_number', 'email',
        'comment', 'is_active', 'group_names'
    ]
    
    example_row = [
        'Иванов Иван Иванович', 'ИТ-отдел', 'Инженер',
        '+79161234567', '123', 'ivanov@example.com',
        'Пример комментария', 'true', 'Все сотрудники, ИТ-отдел'
    ]
    
    if format == 'csv':
        output = io_module.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerow(example_row)
        content = output.getvalue().encode('utf-8')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type='text/csv',
            headers={
                "Content-Disposition": 'attachment; filename="contacts_import_template.csv"'
            }
        )
    else:
        # XLSX шаблон
        import pandas as pd
        df = pd.DataFrame([example_row], columns=headers)
        output = io_module.BytesIO()
        df.to_excel(output, index=False)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                "Content-Disposition": 'attachment; filename="contacts_import_template.xlsx"'
            }
        )
