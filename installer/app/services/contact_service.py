#!/usr/bin/env python3
"""
Сервис управления контактами ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база

Функционал:
- CRUD операции с контактами
- Импорт из CSV/XLSX
- Экспорт в CSV/XLSX/JSON
- Массовые операции (добавление в группы, назначение тегов)
- Поиск и фильтрация
- Статистика
"""

import logging
import csv
import io
import json
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact import Contact
from app.models.contact_group import ContactGroup
from app.models.contact_group_member import ContactGroupMember
from app.models.tag import Tag
from app.models.contact_tag import ContactTag
from app.schemas.contact import (
    ContactCreate, ContactUpdate, ContactFilterParams,
    ContactImportRequest, ContactExportRequest
)
from app.schemas.common import (
    PaginatedResponse, BulkOperationResult, PaginationParams
)

logger = logging.getLogger(__name__)

# Максимальный размер файла импорта (10 МБ)
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024
# Максимальное количество строк в одном импорте
MAX_IMPORT_ROWS = 10000


class ContactService:
    """Сервис управления контактами"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # CRUD ОПЕРАЦИИ
    # =========================================================================
    
    async def create_contact(
        self,
        contact_data: ContactCreate,
        created_by: Optional[UUID] = None
    ) -> Contact:
        """
        Создание нового контакта
        
        Args:
            contact_data: данные контакта
            created_by: ID создателя
            
        Returns:
            Созданный контакт
            
        Raises:
            ValueError: если контакт с таким номером уже существует
        """
        # Проверка дубликата по мобильному номеру
        if contact_data.mobile_number:
            existing = await self.db.execute(
                select(Contact).where(
                    and_(
                        Contact.mobile_number == contact_data.mobile_number,
                        Contact.is_archived == False
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(
                    f"Контакт с номером '{contact_data.mobile_number}' уже существует"
                )
        
        # Создание контакта
        contact = Contact(
            full_name=contact_data.full_name,
            department=contact_data.department,
            position=contact_data.position,
            internal_number=contact_data.internal_number,
            mobile_number=contact_data.mobile_number,
            email=contact_data.email,
            is_active=contact_data.is_active,
            comment=contact_data.comment,
            created_by=created_by,
        )
        
        self.db.add(contact)
        await self.db.flush()
        
        # Добавление в группы (если указаны)
        if contact_data.group_ids:
            for group_id in contact_data.group_ids:
                membership = ContactGroupMember(
                    contact_id=contact.id,
                    group_id=group_id,
                    added_by=created_by,
                )
                self.db.add(membership)
            
            # Обновление счетчиков групп
            await self._update_group_counts(contact_data.group_ids)
        
        # Назначение тегов (если указаны)
        if contact_data.tag_ids:
            for tag_id in contact_data.tag_ids:
                contact_tag = ContactTag(
                    contact_id=contact.id,
                    tag_id=tag_id,
                    added_by=created_by,
                )
                self.db.add(contact_tag)
            
            # Обновление счетчиков тегов
            await self._update_tag_counts(contact_data.tag_ids)
        
        await self.db.flush()
        await self.db.refresh(contact)
        
        logger.info(f"Создан контакт: {contact.full_name} (ID: {contact.id})")
        return contact
    
    async def get_contact(self, contact_id: UUID, include_relations: bool = True) -> Optional[Contact]:
        """
        Получить контакт по ID
        
        Args:
            contact_id: ID контакта
            include_relations: загружать связанные данные (группы, теги)
            
        Returns:
            Контакт или None
        """
        query = select(Contact).where(
            and_(Contact.id == contact_id, Contact.is_archived == False)
        )
        
        if include_relations:
            query = query.options(
                selectinload(Contact.group_memberships).selectinload(ContactGroupMember.group),
                selectinload(Contact.tag_assignments).selectinload(ContactTag.tag),
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """Найти контакт по номеру телефона"""
        result = await self.db.execute(
            select(Contact).where(
                and_(
                    or_(
                        Contact.mobile_number == phone,
                        Contact.internal_number == phone
                    ),
                    Contact.is_archived == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def list_contacts(
        self,
        pagination: PaginationParams = PaginationParams(),
        filters: Optional[ContactFilterParams] = None,
        sort_field: str = "full_name",
        sort_direction: str = "asc"
    ) -> PaginatedResponse:
        """
        Получить список контактов с фильтрацией и пагинацией
        
        Args:
            pagination: параметры пагинации
            filters: параметры фильтрации
            sort_field: поле сортировки
            sort_direction: направление сортировки
            
        Returns:
            PaginatedResponse со списком контактов
        """
        # Базовый запрос (только неархивные)
        query = select(Contact).where(Contact.is_archived == False)
        count_query = select(func.count(Contact.id)).where(Contact.is_archived == False)
        
        # Применение фильтров
        if filters:
            filter_conditions = []
            
            if filters.search:
                search = f"%{filters.search}%"
                filter_conditions.append(
                    or_(
                        Contact.full_name.ilike(search),
                        Contact.department.ilike(search),
                        Contact.position.ilike(search),
                        Contact.mobile_number.ilike(search),
                        Contact.internal_number.ilike(search),
                        Contact.email.ilike(search),
                    )
                )
            
            if filters.department:
                filter_conditions.append(Contact.department == filters.department)
            
            if filters.is_active is not None:
                filter_conditions.append(Contact.is_active == filters.is_active)
            
            if filters.has_mobile is not None:
                if filters.has_mobile:
                    filter_conditions.append(Contact.mobile_number.isnot(None))
                else:
                    filter_conditions.append(Contact.mobile_number.is_(None))
            
            if filters.has_internal is not None:
                if filters.has_internal:
                    filter_conditions.append(Contact.internal_number.isnot(None))
                else:
                    filter_conditions.append(Contact.internal_number.is_(None))
            
            if filters.has_email is not None:
                if filters.has_email:
                    filter_conditions.append(Contact.email.isnot(None))
                else:
                    filter_conditions.append(Contact.email.is_(None))
            
            if filters.created_after:
                filter_conditions.append(Contact.created_at >= filters.created_after)
            
            if filters.created_before:
                filter_conditions.append(Contact.created_at <= filters.created_before)
            
            # Фильтр по группе
            if filters.group_id:
                query = query.join(
                    ContactGroupMember,
                    and_(
                        ContactGroupMember.contact_id == Contact.id,
                        ContactGroupMember.is_active == True
                    )
                ).where(ContactGroupMember.group_id == filters.group_id)
                
                count_query = count_query.join(
                    ContactGroupMember,
                    and_(
                        ContactGroupMember.contact_id == Contact.id,
                        ContactGroupMember.is_active == True
                    )
                ).where(ContactGroupMember.group_id == filters.group_id)
            
            # Фильтр по тегу
            if filters.tag_id:
                query = query.join(
                    ContactTag,
                    ContactTag.contact_id == Contact.id
                ).where(ContactTag.tag_id == filters.tag_id)
                
                count_query = count_query.join(
                    ContactTag,
                    ContactTag.contact_id == Contact.id
                ).where(ContactTag.tag_id == filters.tag_id)
            
            if filter_conditions:
                query = query.where(and_(*filter_conditions))
                count_query = count_query.where(and_(*filter_conditions))
        
        # Сортировка
        allowed_sort_fields = [
            "full_name", "department", "position", "mobile_number",
            "internal_number", "email", "is_active", "created_at", "updated_at"
        ]
        if sort_field not in allowed_sort_fields:
            sort_field = "full_name"
        
        sort_column = getattr(Contact, sort_field)
        if sort_direction == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Пагинация
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.options(
            selectinload(Contact.group_memberships).selectinload(ContactGroupMember.group),
            selectinload(Contact.tag_assignments).selectinload(ContactTag.tag),
        )
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await self.db.execute(query)
        contacts = result.scalars().all()
        
        # Формирование ответа
        items = []
        for contact in contacts:
            items.append({
                "id": str(contact.id),
                "full_name": contact.full_name,
                "department": contact.department,
                "position": contact.position,
                "mobile_number": contact.mobile_number,
                "internal_number": contact.internal_number,
                "email": contact.email,
                "is_active": contact.is_active,
                "is_archived": contact.is_archived,
                "comment": contact.comment,
                "groups": [
                    {
                        "id": str(gm.group.id),
                        "name": gm.group.name,
                        "color": gm.group.color,
                    }
                    for gm in contact.group_memberships
                    if gm.group and gm.is_active
                ],
                "tags": [
                    {
                        "id": str(ct.tag.id),
                        "name": ct.tag.name,
                        "color": ct.tag.color,
                    }
                    for ct in contact.tag_assignments
                    if ct.tag
                ],
                "primary_phone": contact.primary_phone,
                "has_mobile": contact.has_mobile,
                "has_internal": contact.has_internal,
                "created_at": contact.created_at.isoformat() if contact.created_at else None,
                "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
            })
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    
    async def update_contact(
        self,
        contact_id: UUID,
        update_data: ContactUpdate,
        updated_by: Optional[UUID] = None
    ) -> Contact:
        """
        Обновление контакта
        
        Args:
            contact_id: ID контакта
            update_data: данные для обновления
            updated_by: кто обновляет
            
        Returns:
            Обновленный контакт
        """
        contact = await self.get_contact(contact_id, include_relations=False)
        if not contact:
            raise ValueError(f"Контакт с ID {contact_id} не найден")
        
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Проверка дубликата номера при изменении
        if 'mobile_number' in update_dict and update_dict['mobile_number'] != contact.mobile_number:
            existing = await self.db.execute(
                select(Contact).where(
                    and_(
                        Contact.mobile_number == update_dict['mobile_number'],
                        Contact.id != contact_id,
                        Contact.is_archived == False
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Контакт с номером '{update_dict['mobile_number']}' уже существует")
        
        for key, value in update_dict.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
        
        contact.updated_by = updated_by
        contact.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(contact)
        
        logger.info(f"Обновлен контакт: {contact.full_name}")
        return contact
    
    async def delete_contact(
        self,
        contact_id: UUID,
        deleted_by: Optional[UUID] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Удаление контакта
        
        Args:
            contact_id: ID контакта
            deleted_by: кто удаляет
            hard_delete: полное удаление (False = архивирование)
            
        Returns:
            True если удален
        """
        contact = await self.get_contact(contact_id, include_relations=False)
        if not contact:
            raise ValueError(f"Контакт с ID {contact_id} не найден")
        
        if hard_delete:
            await self.db.delete(contact)
            logger.info(f"Контакт полностью удален: {contact.full_name}")
        else:
            contact.is_archived = True
            contact.is_active = False
            contact.updated_by = deleted_by
            contact.updated_at = datetime.now(timezone.utc)
            logger.info(f"Контакт архивирован: {contact.full_name}")
        
        await self.db.flush()
        return True
    
    async def restore_contact(
        self,
        contact_id: UUID,
        restored_by: Optional[UUID] = None
    ) -> Contact:
        """Восстановление архивированного контакта"""
        contact = await self.db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = contact.scalar_one_or_none()
        
        if not contact:
            raise ValueError(f"Контакт с ID {contact_id} не найден")
        
        contact.is_archived = False
        contact.is_active = True
        contact.updated_by = restored_by
        contact.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(contact)
        
        logger.info(f"Контакт восстановлен: {contact.full_name}")
        return contact
    
    # =========================================================================
    # ИМПОРТ КОНТАКТОВ
    # =========================================================================
    
    async def import_contacts(
        self,
        file_content: bytes,
        filename: str,
        import_options: ContactImportRequest,
        imported_by: UUID
    ) -> BulkOperationResult:
        """
        Импорт контактов из CSV/XLSX файла
        
        Args:
            file_content: содержимое файла
            filename: имя файла
            import_options: настройки импорта
            imported_by: кто импортирует
            
        Returns:
            Результат импорта
        """
        # Определение формата
        file_format = import_options.file_format or self._detect_format(filename)
        
        # Парсинг файла
        try:
            if file_format == "csv":
                df = self._parse_csv(file_content, import_options.encoding)
            elif file_format in ["xlsx", "xls"]:
                df = self._parse_xlsx(file_content)
            else:
                raise ValueError(f"Неподдерживаемый формат: {file_format}")
        except Exception as e:
            raise ValueError(f"Ошибка парсинга файла: {str(e)}")
        
        if df.empty:
            raise ValueError("Файл не содержит данных")
        
        if len(df) > MAX_IMPORT_ROWS:
            raise ValueError(f"Слишком много строк: {len(df)}. Максимум: {MAX_IMPORT_ROWS}")
        
        # Нормализация колонок
        df = self._normalize_columns(df)
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Поиск существующего контакта по мобильному номеру
                mobile = self._clean_phone(str(row.get('mobile_number', ''))) if pd.notna(row.get('mobile_number')) else None
                
                existing = None
                if mobile and import_options.update_existing:
                    existing = await self.get_contact_by_phone(mobile)
                
                if existing and import_options.update_existing:
                    # Обновление существующего
                    update_dict = {
                        'full_name': str(row.get('full_name', existing.full_name)),
                        'department': str(row.get('department', '')) if pd.notna(row.get('department')) else existing.department,
                        'position': str(row.get('position', '')) if pd.notna(row.get('position')) else existing.position,
                        'mobile_number': mobile or existing.mobile_number,
                        'internal_number': self._clean_internal(str(row.get('internal_number', ''))) if pd.notna(row.get('internal_number')) else existing.internal_number,
                        'email': str(row.get('email', '')) if pd.notna(row.get('email')) else existing.email,
                    }
                    await self.update_contact(existing.id, ContactUpdate(**update_dict), imported_by)
                    success_count += 1
                    
                elif existing and import_options.skip_duplicates:
                    skipped_count += 1
                    
                elif not existing:
                    # Создание нового
                    contact_data = ContactCreate(
                        full_name=str(row.get('full_name', 'Без имени')),
                        department=str(row.get('department', '')) if pd.notna(row.get('department')) else None,
                        position=str(row.get('position', '')) if pd.notna(row.get('position')) else None,
                        mobile_number=mobile,
                        internal_number=self._clean_internal(str(row.get('internal_number', ''))) if pd.notna(row.get('internal_number')) else None,
                        email=str(row.get('email', '')) if pd.notna(row.get('email')) else None,
                        is_active=True,
                        group_ids=import_options.default_group_ids,
                    )
                    await self.create_contact(contact_data, imported_by)
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                errors.append({
                    "row": idx + 2,  # +2 для учета заголовка и 0-based индекса
                    "name": str(row.get('full_name', 'Неизвестно')),
                    "error": str(e)
                })
        
        return BulkOperationResult(
            total_processed=len(df),
            success_count=success_count,
            error_count=error_count,
            skipped_count=skipped_count,
            errors=errors,
            message=f"Импортировано: {success_count}, пропущено: {skipped_count}, ошибок: {error_count}"
        )
    
    async def export_contacts(
        self,
        export_options: ContactExportRequest,
        filters: Optional[ContactFilterParams] = None
    ) -> Tuple[bytes, str, str]:
        """
        Экспорт контактов в файл
        
        Args:
            export_options: настройки экспорта
            filters: фильтры для выбора контактов
            
        Returns:
            (содержимое файла, имя файла, MIME тип)
        """
        # Получение контактов
        contacts = await self._get_contacts_for_export(filters, export_options)
        
        # Определение полей
        fields = export_options.fields or [
            "full_name", "department", "position",
            "mobile_number", "internal_number", "email",
            "is_active", "comment"
        ]
        
        # Генерация файла
        export_format = export_options.format or "csv"
        
        if export_format == "csv":
            content, mime_type = self._generate_csv(contacts, fields, export_options.encoding)
            filename = f"contacts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_format == "xlsx":
            content, mime_type = self._generate_xlsx(contacts, fields)
            filename = f"contacts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        elif export_format == "json":
            content, mime_type = self._generate_json(contacts, fields)
            filename = f"contacts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            raise ValueError(f"Неподдерживаемый формат экспорта: {export_format}")
        
        return content, filename, mime_type
    
    # =========================================================================
    # МАССОВЫЕ ОПЕРАЦИИ
    # =========================================================================
    
    async def bulk_action(
        self,
        contact_ids: List[UUID],
        action: str,
        params: Dict[str, Any],
        performed_by: UUID
    ) -> BulkOperationResult:
        """
        Массовое действие над контактами
        
        Args:
            contact_ids: список ID контактов
            action: действие (activate, deactivate, archive, delete)
            params: дополнительные параметры
            performed_by: кто выполняет
            
        Returns:
            Результат операции
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for contact_id in contact_ids:
            try:
                if action == "activate":
                    await self.update_contact(contact_id, ContactUpdate(is_active=True), performed_by)
                elif action == "deactivate":
                    await self.update_contact(contact_id, ContactUpdate(is_active=False), performed_by)
                elif action == "archive":
                    await self.delete_contact(contact_id, performed_by, hard_delete=False)
                elif action == "delete":
                    await self.delete_contact(contact_id, performed_by, hard_delete=params.get("hard_delete", False))
                elif action == "add_to_group" and params.get("group_id"):
                    await self._add_to_group(contact_id, params["group_id"], performed_by)
                elif action == "remove_from_group" and params.get("group_id"):
                    await self._remove_from_group(contact_id, params["group_id"], performed_by)
                elif action == "add_tag" and params.get("tag_id"):
                    await self._add_tag(contact_id, params["tag_id"], performed_by)
                elif action == "remove_tag" and params.get("tag_id"):
                    await self._remove_tag(contact_id, params["tag_id"])
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"contact_id": str(contact_id), "error": str(e)})
        
        await self.db.flush()
        
        return BulkOperationResult(
            total_processed=len(contact_ids),
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            message=f"Обработано: {success_count}, ошибок: {error_count}"
        )
    
    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику по контактам"""
        # Всего
        total = await self.db.execute(
            select(func.count(Contact.id)).where(Contact.is_archived == False)
        )
        total_count = total.scalar() or 0
        
        # Активных
        active = await self.db.execute(
            select(func.count(Contact.id)).where(
                and_(Contact.is_active == True, Contact.is_archived == False)
            )
        )
        active_count = active.scalar() or 0
        
        # С мобильными
        with_mobile = await self.db.execute(
            select(func.count(Contact.id)).where(
                and_(Contact.mobile_number.isnot(None), Contact.is_archived == False)
            )
        )
        with_mobile_count = with_mobile.scalar() or 0
        
        # С внутренними
        with_internal = await self.db.execute(
            select(func.count(Contact.id)).where(
                and_(Contact.internal_number.isnot(None), Contact.is_archived == False)
            )
        )
        with_internal_count = with_internal.scalar() or 0
        
        # По подразделениям
        departments = await self.db.execute(
            select(Contact.department, func.count(Contact.id))
            .where(Contact.is_archived == False)
            .group_by(Contact.department)
            .order_by(func.count(Contact.id).desc())
            .limit(10)
        )
        by_department = [
            {"department": row[0] or "Без подразделения", "count": row[1]}
            for row in departments
        ]
        
        return {
            "total": total_count,
            "active": active_count,
            "inactive": total_count - active_count,
            "archived": await self._count_archived(),
            "with_mobile": with_mobile_count,
            "with_internal": with_internal_count,
            "with_both": await self._count_with_both(),
            "with_email": await self._count_with_email(),
            "by_department": by_department,
        }
    
    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    async def _add_to_group(self, contact_id: UUID, group_id: UUID, added_by: UUID):
        """Добавить контакт в группу"""
        existing = await self.db.execute(
            select(ContactGroupMember).where(
                and_(
                    ContactGroupMember.contact_id == contact_id,
                    ContactGroupMember.group_id == group_id
                )
            )
        )
        if existing.scalar_one_or_none():
            return  # Уже в группе
        
        membership = ContactGroupMember(
            contact_id=contact_id,
            group_id=group_id,
            added_by=added_by,
        )
        self.db.add(membership)
    
    async def _remove_from_group(self, contact_id: UUID, group_id: UUID, removed_by: UUID):
        """Удалить контакт из группы"""
        await self.db.execute(
            delete(ContactGroupMember).where(
                and_(
                    ContactGroupMember.contact_id == contact_id,
                    ContactGroupMember.group_id == group_id
                )
            )
        )
    
    async def _add_tag(self, contact_id: UUID, tag_id: UUID, added_by: UUID):
        """Назначить тег контакту"""
        existing = await self.db.execute(
            select(ContactTag).where(
                and_(
                    ContactTag.contact_id == contact_id,
                    ContactTag.tag_id == tag_id
                )
            )
        )
        if existing.scalar_one_or_none():
            return
        
        contact_tag = ContactTag(
            contact_id=contact_id,
            tag_id=tag_id,
            added_by=added_by,
        )
        self.db.add(contact_tag)
    
    async def _remove_tag(self, contact_id: UUID, tag_id: UUID):
        """Удалить тег у контакта"""
        await self.db.execute(
            delete(ContactTag).where(
                and_(
                    ContactTag.contact_id == contact_id,
                    ContactTag.tag_id == tag_id
                )
            )
        )
    
    async def _update_group_counts(self, group_ids: List[UUID]):
        """Обновить счетчики участников групп"""
        for group_id in group_ids:
            count = await self.db.execute(
                select(func.count(ContactGroupMember.contact_id)).where(
                    and_(
                        ContactGroupMember.group_id == group_id,
                        ContactGroupMember.is_active == True
                    )
                )
            )
            member_count = count.scalar() or 0
            
            await self.db.execute(
                update(ContactGroup)
                .where(ContactGroup.id == group_id)
                .values(member_count=member_count)
            )
    
    async def _update_tag_counts(self, tag_ids: List[UUID]):
        """Обновить счетчики использования тегов"""
        for tag_id in tag_ids:
            count = await self.db.execute(
                select(func.count(ContactTag.contact_id)).where(
                    ContactTag.tag_id == tag_id
                )
            )
            usage_count = count.scalar() or 0
            
            await self.db.execute(
                update(Tag)
                .where(Tag.id == tag_id)
                .values(usage_count=usage_count)
            )
    
    def _detect_format(self, filename: str) -> str:
        """Определить формат файла по расширению"""
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        format_map = {
            'csv': 'csv',
            'xlsx': 'xlsx',
            'xls': 'xlsx',
        }
        return format_map.get(ext, 'csv')
    
    def _parse_csv(self, content: bytes, encoding: str) -> pd.DataFrame:
        """Парсинг CSV"""
        text = content.decode(encoding or 'utf-8')
        return pd.read_csv(io.StringIO(text))
    
    def _parse_xlsx(self, content: bytes) -> pd.DataFrame:
        """Парсинг XLSX"""
        return pd.read_excel(io.BytesIO(content))
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализация названий колонок"""
        column_map = {
            'фио': 'full_name',
            'ф.и.о.': 'full_name',
            'fio': 'full_name',
            'full_name': 'full_name',
            'имя': 'full_name',
            'name': 'full_name',
            'подразделение': 'department',
            'отдел': 'department',
            'department': 'department',
            'должность': 'position',
            'position': 'position',
            'мобильный': 'mobile_number',
            'мобильный номер': 'mobile_number',
            'mobile': 'mobile_number',
            'mobile_number': 'mobile_number',
            'телефон': 'mobile_number',
            'phone': 'mobile_number',
            'внутренний': 'internal_number',
            'внутренний номер': 'internal_number',
            'internal': 'internal_number',
            'internal_number': 'internal_number',
            'email': 'email',
            'почта': 'email',
            'комментарий': 'comment',
            'comment': 'comment',
            'примечание': 'comment',
        }
        df.columns = [column_map.get(col.lower().strip(), col) for col in df.columns]
        return df
    
    def _clean_phone(self, phone: str) -> Optional[str]:
        """Очистка и нормализация номера телефона"""
        import re
        if not phone or phone.strip() in ['', 'nan', 'None']:
            return None
        cleaned = re.sub(r'[^\d+]', '', phone)
        if cleaned.startswith('8') and len(cleaned) == 11:
            return '+7' + cleaned[1:]
        if cleaned.startswith('7') and len(cleaned) == 11:
            return '+' + cleaned
        return cleaned if cleaned else None
    
    def _clean_internal(self, number: str) -> Optional[str]:
        """Очистка внутреннего номера"""
        import re
        if not number or number.strip() in ['', 'nan', 'None']:
            return None
        return re.sub(r'[^\d]', '', number)[:10]
    
    async def _get_contacts_for_export(
        self,
        filters: Optional[ContactFilterParams],
        export_options: ContactExportRequest
    ) -> List[Contact]:
        """Получить контакты для экспорта"""
        query = select(Contact)
        
        if not export_options.include_archived:
            query = query.where(Contact.is_archived == False)
        
        if export_options.group_ids:
            query = query.join(
                ContactGroupMember,
                ContactGroupMember.contact_id == Contact.id
            ).where(ContactGroupMember.group_id.in_(export_options.group_ids))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def _generate_csv(self, contacts: List[Contact], fields: List[str], encoding: str) -> Tuple[bytes, str]:
        """Генерация CSV"""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        
        for contact in contacts:
            row = {}
            for field in fields:
                value = getattr(contact, field, None)
                row[field] = str(value) if value is not None else ''
            writer.writerow(row)
        
        return output.getvalue().encode(encoding or 'utf-8'), 'text/csv'
    
    def _generate_xlsx(self, contacts: List[Contact], fields: List[str]) -> Tuple[bytes, str]:
        """Генерация XLSX"""
        data = []
        for contact in contacts:
            row = {}
            for field in fields:
                value = getattr(contact, field, None)
                row[field] = str(value) if value is not None else ''
            data.append(row)
        
        df = pd.DataFrame(data, columns=fields)
        output = io.BytesIO()
        df.to_excel(output, index=False)
        return output.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    def _generate_json(self, contacts: List[Contact], fields: List[str]) -> Tuple[bytes, str]:
        """Генерация JSON"""
        data = []
        for contact in contacts:
            row = {}
            for field in fields:
                value = getattr(contact, field, None)
                if isinstance(value, datetime):
                    row[field] = value.isoformat()
                elif isinstance(value, UUID):
                    row[field] = str(value)
                else:
                    row[field] = value
            data.append(row)
        
        return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'), 'application/json'
    
    async def _count_archived(self) -> int:
        """Количество архивированных контактов"""
        result = await self.db.execute(
            select(func.count(Contact.id)).where(Contact.is_archived == True)
        )
        return result.scalar() or 0
    
    async def _count_with_both(self) -> int:
        """Контакты с обоими номерами"""
        result = await self.db.execute(
            select(func.count(Contact.id)).where(
                and_(
                    Contact.mobile_number.isnot(None),
                    Contact.internal_number.isnot(None),
                    Contact.is_archived == False
                )
            )
        )
        return result.scalar() or 0
    
    async def _count_with_email(self) -> int:
        """Контакты с email"""
        result = await self.db.execute(
            select(func.count(Contact.id)).where(
                and_(Contact.email.isnot(None), Contact.is_archived == False)
            )
        )
        return result.scalar() or 0
