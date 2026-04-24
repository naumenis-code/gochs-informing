#!/usr/bin/env python3
"""
Сервис управления группами контактов ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база — группы

Функционал:
- CRUD операции с группами
- Управление участниками (добавление/удаление/обновление)
- Массовые операции
- Получение списков для обзвона
- Статистика по группам
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update, delete, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact import Contact
from app.models.contact_group import ContactGroup
from app.models.contact_group_member import ContactGroupMember
from app.schemas.group import (
    GroupCreate, GroupUpdate,
    AddMembersRequest, RemoveMembersRequest, UpdateMemberRequest
)
from app.schemas.common import (
    PaginatedResponse, BulkOperationResult, PaginationParams
)

logger = logging.getLogger(__name__)

# Системные группы (нельзя удалить)
SYSTEM_GROUP_NAMES = ["Все сотрудники", "Руководство", "Дежурная смена"]


class GroupService:
    """Сервис управления группами контактов"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # CRUD ОПЕРАЦИИ
    # =========================================================================
    
    async def create_group(
        self,
        group_data: GroupCreate,
        created_by: Optional[UUID] = None
    ) -> ContactGroup:
        """
        Создание новой группы
        
        Args:
            group_data: данные группы
            created_by: ID создателя
            
        Returns:
            Созданная группа
            
        Raises:
            ValueError: если группа с таким именем уже существует
        """
        # Проверка уникальности имени
        existing = await self.db.execute(
            select(ContactGroup).where(
                and_(
                    ContactGroup.name == group_data.name,
                    ContactGroup.is_archived == False
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Группа с названием '{group_data.name}' уже существует")
        
        # Создание группы
        group = ContactGroup(
            name=group_data.name,
            description=group_data.description,
            color=group_data.color,
            is_active=group_data.is_active,
            is_system=group_data.is_system,
            default_priority=group_data.default_priority,
            max_retries=group_data.max_retries,
            created_by=created_by,
        )
        
        self.db.add(group)
        await self.db.flush()
        
        # Добавление контактов (если указаны)
        if group_data.contact_ids:
            for contact_id in group_data.contact_ids:
                membership = ContactGroupMember(
                    contact_id=contact_id,
                    group_id=group.id,
                    added_by=created_by,
                )
                self.db.add(membership)
            
            await self.db.flush()
            group.member_count = len(group_data.contact_ids)
            group.total_member_count = len(group_data.contact_ids)
        
        await self.db.flush()
        await self.db.refresh(group)
        
        logger.info(f"Создана группа: {group.name} (ID: {group.id})")
        return group
    
    async def get_group(self, group_id: UUID, include_members: bool = False) -> Optional[ContactGroup]:
        """
        Получить группу по ID
        
        Args:
            group_id: ID группы
            include_members: загружать участников
            
        Returns:
            Группа или None
        """
        query = select(ContactGroup).where(
            and_(ContactGroup.id == group_id, ContactGroup.is_archived == False)
        )
        
        if include_members:
            query = query.options(
                selectinload(ContactGroup.memberships)
                .selectinload(ContactGroupMember.contact)
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_group_by_name(self, name: str) -> Optional[ContactGroup]:
        """Найти группу по имени"""
        result = await self.db.execute(
            select(ContactGroup).where(
                and_(ContactGroup.name == name, ContactGroup.is_archived == False)
            )
        )
        return result.scalar_one_or_none()
    
    async def list_groups(
        self,
        pagination: PaginationParams = PaginationParams(),
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_system: Optional[bool] = None,
        has_members: Optional[bool] = None,
        min_members: Optional[int] = None,
        max_members: Optional[int] = None,
        sort_field: str = "name",
        sort_direction: str = "asc"
    ) -> PaginatedResponse:
        """
        Получить список групп с фильтрацией и пагинацией
        
        Args:
            pagination: параметры пагинации
            search: поиск по названию/описанию
            is_active: фильтр по активности
            is_system: фильтр по системности
            has_members: только с участниками
            min_members: минимальное количество участников
            max_members: максимальное количество участников
            sort_field: поле сортировки
            sort_direction: направление
            
        Returns:
            PaginatedResponse со списком групп
        """
        query = select(ContactGroup).where(ContactGroup.is_archived == False)
        count_query = select(func.count(ContactGroup.id)).where(ContactGroup.is_archived == False)
        
        # Фильтры
        filters = []
        
        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    ContactGroup.name.ilike(search_term),
                    ContactGroup.description.ilike(search_term),
                )
            )
        
        if is_active is not None:
            filters.append(ContactGroup.is_active == is_active)
        
        if is_system is not None:
            filters.append(ContactGroup.is_system == is_system)
        
        if has_members is not None:
            if has_members:
                filters.append(ContactGroup.member_count > 0)
            else:
                filters.append(ContactGroup.member_count == 0)
        
        if min_members is not None:
            filters.append(ContactGroup.member_count >= min_members)
        
        if max_members is not None:
            filters.append(ContactGroup.member_count <= max_members)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Сортировка
        allowed_sort_fields = [
            "name", "member_count", "default_priority",
            "created_at", "updated_at"
        ]
        if sort_field not in allowed_sort_fields:
            sort_field = "name"
        
        sort_column = getattr(ContactGroup, sort_field)
        if sort_direction == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Пагинация
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await self.db.execute(query)
        groups = result.scalars().all()
        
        # Формирование ответа
        items = [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color,
                "is_active": group.is_active,
                "is_system": group.is_system,
                "is_archived": group.is_archived,
                "member_count": group.member_count,
                "total_member_count": group.total_member_count,
                "default_priority": group.default_priority,
                "max_retries": group.max_retries,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None,
            }
            for group in groups
        ]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    
    async def update_group(
        self,
        group_id: UUID,
        update_data: GroupUpdate,
        updated_by: Optional[UUID] = None
    ) -> ContactGroup:
        """
        Обновление группы
        
        Args:
            group_id: ID группы
            update_data: данные для обновления
            updated_by: кто обновляет
            
        Returns:
            Обновленная группа
        """
        group = await self.get_group(group_id)
        if not group:
            raise ValueError(f"Группа с ID {group_id} не найдена")
        
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Проверка уникальности имени при изменении
        if 'name' in update_dict and update_dict['name'] != group.name:
            existing = await self.db.execute(
                select(ContactGroup).where(
                    and_(
                        ContactGroup.name == update_dict['name'],
                        ContactGroup.id != group_id,
                        ContactGroup.is_archived == False
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Группа с названием '{update_dict['name']}' уже существует")
        
        for key, value in update_dict.items():
            if hasattr(group, key):
                setattr(group, key, value)
        
        group.updated_by = updated_by
        group.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(group)
        
        logger.info(f"Обновлена группа: {group.name}")
        return group
    
    async def delete_group(
        self,
        group_id: UUID,
        deleted_by: Optional[UUID] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Удаление группы
        
        Args:
            group_id: ID группы
            deleted_by: кто удаляет
            hard_delete: полное удаление (False = архивирование)
            
        Returns:
            True если удалена
        """
        group = await self.get_group(group_id)
        if not group:
            raise ValueError(f"Группа с ID {group_id} не найдена")
        
        # Системные группы нельзя удалить
        if group.is_system:
            raise ValueError(f"Нельзя удалить системную группу '{group.name}'")
        
        if hard_delete:
            await self.db.delete(group)
            logger.info(f"Группа полностью удалена: {group.name}")
        else:
            group.is_archived = True
            group.is_active = False
            group.updated_by = deleted_by
            group.updated_at = datetime.now(timezone.utc)
            logger.info(f"Группа архивирована: {group.name}")
        
        await self.db.flush()
        return True
    
    async def restore_group(
        self,
        group_id: UUID,
        restored_by: Optional[UUID] = None
    ) -> ContactGroup:
        """Восстановление архивированной группы"""
        group = await self.db.execute(
            select(ContactGroup).where(ContactGroup.id == group_id)
        )
        group = group.scalar_one_or_none()
        
        if not group:
            raise ValueError(f"Группа с ID {group_id} не найдена")
        
        group.is_archived = False
        group.is_active = True
        group.updated_by = restored_by
        group.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(group)
        
        logger.info(f"Группа восстановлена: {group.name}")
        return group
    
    # =========================================================================
    # УПРАВЛЕНИЕ УЧАСТНИКАМИ
    # =========================================================================
    
    async def add_members(
        self,
        group_id: UUID,
        request: AddMembersRequest,
        added_by: UUID
    ) -> BulkOperationResult:
        """
        Добавление контактов в группу
        
        Args:
            group_id: ID группы
            request: запрос с ID контактов
            added_by: кто добавляет
            
        Returns:
            Результат операции
        """
        group = await self.get_group(group_id)
        if not group:
            raise ValueError(f"Группа с ID {group_id} не найдена")
        
        success_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        
        for contact_id in request.contact_ids:
            try:
                # Проверка существования контакта
                contact = await self.db.execute(
                    select(Contact).where(
                        and_(Contact.id == contact_id, Contact.is_archived == False)
                    )
                )
                if not contact.scalar_one_or_none():
                    errors.append({
                        "contact_id": str(contact_id),
                        "error": "Контакт не найден или архивирован"
                    })
                    error_count += 1
                    continue
                
                # Проверка на дубликат
                existing = await self.db.execute(
                    select(ContactGroupMember).where(
                        and_(
                            ContactGroupMember.contact_id == contact_id,
                            ContactGroupMember.group_id == group_id
                        )
                    )
                )
                existing_membership = existing.scalar_one_or_none()
                
                if existing_membership:
                    if existing_membership.is_active:
                        skipped_count += 1
                        continue
                    else:
                        # Реактивируем
                        existing_membership.is_active = True
                        existing_membership.removed_at = None
                        existing_membership.removed_by = None
                        existing_membership.added_by = added_by
                        existing_membership.role = request.role or existing_membership.role
                        existing_membership.priority = request.priority
                        existing_membership.note = request.note
                        success_count += 1
                else:
                    # Создаем новую связь
                    membership = ContactGroupMember(
                        contact_id=contact_id,
                        group_id=group_id,
                        added_by=added_by,
                        role=request.role,
                        priority=request.priority,
                        reason=request.reason,
                        note=request.note,
                    )
                    self.db.add(membership)
                    success_count += 1
                    
            except Exception as e:
                errors.append({
                    "contact_id": str(contact_id),
                    "error": str(e)
                })
                error_count += 1
        
        await self.db.flush()
        
        # Обновление счетчиков группы
        await self._update_group_counts(group_id)
        
        return BulkOperationResult(
            total_processed=len(request.contact_ids),
            success_count=success_count,
            skipped_count=skipped_count,
            error_count=error_count,
            errors=errors,
            message=f"Добавлено: {success_count}, пропущено: {skipped_count}, ошибок: {error_count}"
        )
    
    async def remove_members(
        self,
        group_id: UUID,
        request: RemoveMembersRequest,
        removed_by: UUID
    ) -> BulkOperationResult:
        """
        Удаление контактов из группы
        
        Args:
            group_id: ID группы
            request: запрос с ID контактов
            removed_by: кто удаляет
            
        Returns:
            Результат операции
        """
        group = await self.get_group(group_id)
        if not group:
            raise ValueError(f"Группа с ID {group_id} не найдена")
        
        removed_count = 0
        not_found_count = 0
        errors = []
        
        for contact_id in request.contact_ids:
            try:
                existing = await self.db.execute(
                    select(ContactGroupMember).where(
                        and_(
                            ContactGroupMember.contact_id == contact_id,
                            ContactGroupMember.group_id == group_id
                        )
                    )
                )
                membership = existing.scalar_one_or_none()
                
                if not membership:
                    not_found_count += 1
                    continue
                
                if request.hard_delete:
                    await self.db.delete(membership)
                else:
                    membership.is_active = False
                    membership.removed_at = datetime.now(timezone.utc)
                    membership.removed_by = removed_by
                    membership.reason = request.reason
                
                removed_count += 1
                
            except Exception as e:
                errors.append({
                    "contact_id": str(contact_id),
                    "error": str(e)
                })
        
        await self.db.flush()
        
        # Обновление счетчиков группы
        await self._update_group_counts(group_id)
        
        return BulkOperationResult(
            total_processed=len(request.contact_ids),
            success_count=removed_count,
            error_count=len(errors),
            errors=errors,
            message=f"Удалено: {removed_count}, не найдено: {not_found_count}"
        )
    
    async def update_member(
        self,
        group_id: UUID,
        request: UpdateMemberRequest,
        updated_by: UUID
    ) -> ContactGroupMember:
        """
        Обновление параметров участника группы
        
        Args:
            group_id: ID группы
            request: данные для обновления
            updated_by: кто обновляет
            
        Returns:
            Обновленная связь
        """
        existing = await self.db.execute(
            select(ContactGroupMember).where(
                and_(
                    ContactGroupMember.contact_id == request.contact_id,
                    ContactGroupMember.group_id == group_id
                )
            )
        )
        membership = existing.scalar_one_or_none()
        
        if not membership:
            raise ValueError(f"Контакт {request.contact_id} не состоит в группе {group_id}")
        
        if request.role is not None:
            membership.role = request.role
        if request.priority is not None:
            membership.priority = request.priority
        if request.is_active is not None:
            if request.is_active and not membership.is_active:
                membership.is_active = True
                membership.removed_at = None
                membership.removed_by = None
            elif not request.is_active and membership.is_active:
                membership.is_active = False
                membership.removed_at = datetime.now(timezone.utc)
                membership.removed_by = updated_by
        if request.note is not None:
            membership.note = request.note
        
        membership.added_by = updated_by
        
        await self.db.flush()
        await self.db.refresh(membership)
        
        # Обновление счетчиков группы
        await self._update_group_counts(group_id)
        
        return membership
    
    async def get_members(
        self,
        group_id: UUID,
        active_only: bool = True,
        pagination: PaginationParams = PaginationParams()
    ) -> PaginatedResponse:
        """
        Получить список участников группы
        
        Args:
            group_id: ID группы
            active_only: только активные
            pagination: параметры пагинации
            
        Returns:
            PaginatedResponse с участниками
        """
        query = select(ContactGroupMember).where(
            ContactGroupMember.group_id == group_id
        )
        
        if active_only:
            query = query.where(ContactGroupMember.is_active == True)
        
        # Общее количество
        count_query = select(func.count(ContactGroupMember.contact_id)).where(
            ContactGroupMember.group_id == group_id
        )
        if active_only:
            count_query = count_query.where(ContactGroupMember.is_active == True)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Сортировка по приоритету и дате добавления
        query = query.order_by(
            ContactGroupMember.priority.asc(),
            ContactGroupMember.added_at.desc()
        )
        query = query.options(
            selectinload(ContactGroupMember.contact)
        )
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await self.db.execute(query)
        memberships = result.scalars().all()
        
        items = []
        for m in memberships:
            items.append({
                "contact_id": str(m.contact_id),
                "contact_name": m.contact.full_name if m.contact else "Неизвестный",
                "department": m.contact.department if m.contact else None,
                "position": m.contact.position if m.contact else None,
                "mobile_number": m.contact.mobile_number if m.contact else None,
                "internal_number": m.contact.internal_number if m.contact else None,
                "email": m.contact.email if m.contact else None,
                "is_active": m.is_active,
                "role": m.role,
                "priority": m.priority,
                "note": m.note,
                "added_at": m.added_at.isoformat() if m.added_at else None,
                "added_by": str(m.added_by) if m.added_by else None,
            })
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    
    # =========================================================================
    # ОБЗВОН
    # =========================================================================
    
    async def get_dialer_list(
        self,
        group_id: UUID,
        prefer_mobile: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить список контактов для обзвона
        
        Args:
            group_id: ID группы
            prefer_mobile: предпочитать мобильные номера
            
        Returns:
            Список {contact_id, name, phone, department}
        """
        memberships = await self.db.execute(
            select(ContactGroupMember)
            .where(
                and_(
                    ContactGroupMember.group_id == group_id,
                    ContactGroupMember.is_active == True
                )
            )
            .options(selectinload(ContactGroupMember.contact))
            .order_by(ContactGroupMember.priority.asc())
        )
        memberships = memberships.scalars().all()
        
        dial_list = []
        for m in memberships:
            if not m.contact or not m.contact.is_active or m.contact.is_archived:
                continue
            
            phone = None
            if prefer_mobile:
                phone = m.contact.mobile_number or m.contact.internal_number
            else:
                phone = m.contact.internal_number or m.contact.mobile_number
            
            if phone:
                dial_list.append({
                    "contact_id": str(m.contact.id),
                    "name": m.contact.full_name,
                    "phone": phone,
                    "department": m.contact.department,
                    "priority": m.priority,
                })
        
        return dial_list
    
    # =========================================================================
    # МАССОВЫЕ ОПЕРАЦИИ
    # =========================================================================
    
    async def bulk_action(
        self,
        group_ids: List[UUID],
        action: str,
        performed_by: UUID
    ) -> BulkOperationResult:
        """
        Массовое действие над группами
        
        Args:
            group_ids: список ID групп
            action: действие (activate, deactivate, archive, delete)
            performed_by: кто выполняет
            
        Returns:
            Результат операции
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for group_id in group_ids:
            try:
                if action == "activate":
                    await self.update_group(group_id, GroupUpdate(is_active=True), performed_by)
                elif action == "deactivate":
                    await self.update_group(group_id, GroupUpdate(is_active=False), performed_by)
                elif action == "archive":
                    await self.delete_group(group_id, performed_by, hard_delete=False)
                elif action == "delete":
                    await self.delete_group(group_id, performed_by, hard_delete=True)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"group_id": str(group_id), "error": str(e)})
        
        return BulkOperationResult(
            total_processed=len(group_ids),
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            message=f"Обработано: {success_count}, ошибок: {error_count}"
        )
    
    async def merge_groups(
        self,
        source_group_ids: List[UUID],
        target_group_id: Optional[UUID],
        new_group_name: Optional[str],
        delete_sources: bool,
        performed_by: UUID
    ) -> ContactGroup:
        """
        Объединение групп
        
        Args:
            source_group_ids: ID исходных групп
            target_group_id: ID целевой группы (если None — создать новую)
            new_group_name: имя новой группы (если создается)
            delete_sources: удалить исходные группы
            performed_by: кто выполняет
            
        Returns:
            Целевая группа
        """
        # Определение целевой группы
        if target_group_id:
            target_group = await self.get_group(target_group_id)
            if not target_group:
                raise ValueError(f"Целевая группа с ID {target_group_id} не найдена")
        else:
            if not new_group_name:
                raise ValueError("Укажите имя новой группы")
            target_group = await self.create_group(
                GroupCreate(name=new_group_name),
                performed_by
            )
        
        # Перенос участников
        all_contact_ids = set()
        for source_id in source_group_ids:
            members = await self.db.execute(
                select(ContactGroupMember.contact_id).where(
                    and_(
                        ContactGroupMember.group_id == source_id,
                        ContactGroupMember.is_active == True
                    )
                )
            )
            for row in members:
                all_contact_ids.add(row[0])
        
        # Добавление в целевую группу
        if all_contact_ids:
            await self.add_members(
                target_group.id,
                AddMembersRequest(contact_ids=list(all_contact_ids)),
                performed_by
            )
        
        # Удаление исходных групп (опционально)
        if delete_sources:
            for source_id in source_group_ids:
                if source_id != target_group.id:
                    try:
                        await self.delete_group(source_id, performed_by, hard_delete=False)
                    except Exception as e:
                        logger.warning(f"Не удалось удалить группу {source_id}: {e}")
        
        await self.db.refresh(target_group)
        return target_group
    
    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику по группам"""
        # Всего групп
        total = await self.db.execute(
            select(func.count(ContactGroup.id)).where(ContactGroup.is_archived == False)
        )
        total_count = total.scalar() or 0
        
        # Активных
        active = await self.db.execute(
            select(func.count(ContactGroup.id)).where(
                and_(ContactGroup.is_active == True, ContactGroup.is_archived == False)
            )
        )
        active_count = active.scalar() or 0
        
        # Системных
        system = await self.db.execute(
            select(func.count(ContactGroup.id)).where(
                and_(ContactGroup.is_system == True, ContactGroup.is_archived == False)
            )
        )
        system_count = system.scalar() or 0
        
        # Всего участий
        memberships = await self.db.execute(
            select(func.count(ContactGroupMember.contact_id)).where(
                ContactGroupMember.is_active == True
            )
        )
        total_memberships = memberships.scalar() or 0
        
        # Среднее участников на группу
        avg = total_memberships / total_count if total_count > 0 else 0
        
        # Пустые группы
        empty = await self.db.execute(
            select(func.count(ContactGroup.id)).where(
                and_(
                    ContactGroup.member_count == 0,
                    ContactGroup.is_archived == False
                )
            )
        )
        empty_count = empty.scalar() or 0
        
        # Самая большая группа
        largest = await self.db.execute(
            select(ContactGroup)
            .where(ContactGroup.is_archived == False)
            .order_by(ContactGroup.member_count.desc())
            .limit(1)
        )
        largest_group = largest.scalar_one_or_none()
        
        # По приоритетам
        priorities = await self.db.execute(
            select(ContactGroup.default_priority, func.count(ContactGroup.id))
            .where(ContactGroup.is_archived == False)
            .group_by(ContactGroup.default_priority)
            .order_by(ContactGroup.default_priority)
        )
        by_priority = [
            {"priority": row[0], "count": row[1]}
            for row in priorities
        ]
        
        return {
            "total_groups": total_count,
            "active_groups": active_count,
            "system_groups": system_count,
            "user_groups": total_count - system_count,
            "archived_groups": await self._count_archived(),
            "total_memberships": total_memberships,
            "avg_members_per_group": round(avg, 1),
            "groups_without_members": empty_count,
            "largest_group": {
                "name": largest_group.name,
                "count": largest_group.member_count,
            } if largest_group else None,
            "by_priority": by_priority,
        }
    
    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    async def _update_group_counts(self, group_id: UUID):
        """Обновить счетчики участников группы"""
        # Активные участники
        active = await self.db.execute(
            select(func.count(ContactGroupMember.contact_id)).where(
                and_(
                    ContactGroupMember.group_id == group_id,
                    ContactGroupMember.is_active == True
                )
            )
        )
        active_count = active.scalar() or 0
        
        # Все участники
        total = await self.db.execute(
            select(func.count(ContactGroupMember.contact_id)).where(
                ContactGroupMember.group_id == group_id
            )
        )
        total_count = total.scalar() or 0
        
        await self.db.execute(
            update(ContactGroup)
            .where(ContactGroup.id == group_id)
            .values(
                member_count=active_count,
                total_member_count=total_count
            )
        )
    
    async def _count_archived(self) -> int:
        """Количество архивированных групп"""
        result = await self.db.execute(
            select(func.count(ContactGroup.id)).where(ContactGroup.is_archived == True)
        )
        return result.scalar() or 0
