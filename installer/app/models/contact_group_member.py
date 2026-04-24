#!/usr/bin/env python3
"""
Модель связи контакт-группа (M2M) для ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база — группы
Обеспечивает связь many-to-many между контактами и группами
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Column, String, DateTime, Index, UniqueConstraint, ForeignKey, Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.contact_group import ContactGroup
    from app.models.user import User


class ContactGroupMember(Base):
    """
    Связка many-to-many: Контакт <-> Группа контактов
    
    Один контакт может состоять во многих группах.
    Одна группа может содержать много контактов.
    
    Особенности:
    - Композитный первичный ключ (contact_id + group_id)
    - Защита от дубликатов (уникальный constraint)
    - Каскадное удаление при удалении контакта или группы
    - Аудит: кто и когда добавил контакт в группу
    - Возможность указания роли контакта в группе
    - Отслеживание статуса участия (активен/неактивен)
    """
    
    __tablename__ = "contact_group_members"
    __table_args__ = (
        UniqueConstraint(
            "contact_id", "group_id",
            name="uq_contact_group_member"
        ),
        Index("idx_cgm_contact_id", "contact_id"),
        Index("idx_cgm_group_id", "group_id"),
        Index("idx_cgm_added_at", "added_at"),
        Index("idx_cgm_is_active", "is_active"),
        {"comment": "Связь many-to-many: контакты <-> группы"}
    )
    
    # =========================================================================
    # Внешние ключи (составной первичный ключ)
    # =========================================================================
    
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
        comment="ID контакта"
    )
    
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contact_groups.id", ondelete="CASCADE"),
        primary_key=True,
        comment="ID группы"
    )
    
    # =========================================================================
    # Статусные поля
    # =========================================================================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активно ли участие (можно временно отключить без удаления)"
    )
    
    # Роль контакта в группе (опционально)
    role: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Роль контакта в группе (например: руководитель, участник, наблюдатель)"
    )
    
    # Приоритет контакта в группе для обзвона (1-10, где 1 = высший)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="Приоритет обзвона для этого контакта в группе (1-10)"
    )
    
    # =========================================================================
    # Метаданные связи
    # =========================================================================
    
    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто добавил контакт в группу"
    )
    
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Когда контакт был добавлен в группу"
    )
    
    removed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Когда контакт был удален из группы (если is_active=False)"
    )
    
    removed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто удалил контакт из группы"
    )
    
    # Причина добавления/изменения (для аудита)
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Причина добавления/изменения (для аудита)"
    )
    
    # Заметка о контакте в контексте группы
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Заметка о контакте в контексте группы"
    )
    
    # =========================================================================
    # Связи (relationships)
    # =========================================================================
    
    contact: Mapped["Contact"] = relationship(
        "Contact",
        back_populates="group_memberships",
        lazy="selectin"
    )
    
    group: Mapped["ContactGroup"] = relationship(
        "ContactGroup",
        back_populates="memberships",
        lazy="selectin"
    )
    
    # Кто добавил
    adder: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[added_by],
        backref="group_memberships_added",
        lazy="selectin"
    )
    
    # Кто удалил
    remover: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[removed_by],
        backref="group_memberships_removed",
        lazy="selectin"
    )
    
    # =========================================================================
    # Свойства
    # =========================================================================
    
    @property
    def contact_name(self) -> str:
        """Имя контакта (для быстрого доступа)"""
        return self.contact.full_name if self.contact else "Неизвестный контакт"
    
    @property
    def group_name(self) -> str:
        """Имя группы (для быстрого доступа)"""
        return self.group.name if self.group else "Неизвестная группа"
    
    @property
    def contact_department(self) -> Optional[str]:
        """Подразделение контакта"""
        return self.contact.department if self.contact else None
    
    @property
    def contact_mobile(self) -> Optional[str]:
        """Мобильный номер контакта"""
        return self.contact.mobile_number if self.contact else None
    
    @property
    def contact_internal(self) -> Optional[str]:
        """Внутренний номер контакта"""
        return self.contact.internal_number if self.contact else None
    
    @property
    def contact_email(self) -> Optional[str]:
        """Email контакта"""
        return self.contact.email if self.contact else None
    
    @property
    def age(self) -> str:
        """Сколько времени в группе (человекочитаемый формат)"""
        if not self.added_at:
            return "неизвестно"
        
        from datetime import timezone
        now = datetime.now(timezone.utc)
        diff = now - self.added_at.replace(tzinfo=timezone.utc)
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} г."
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} мес."
        elif diff.days > 0:
            return f"{diff.days} дн."
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч."
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин."
        else:
            return "только что"
    
    @property
    def status_display(self) -> str:
        """Статус для отображения"""
        if self.is_active:
            return "Активен"
        elif self.removed_at:
            return f"Удален ({self.removed_at.strftime('%d.%m.%Y')})"
        else:
            return "Неактивен"
    
    @property
    def priority_label(self) -> str:
        """Метка приоритета"""
        labels = {
            1: "🔴 Экстренный",
            2: "🟠 Высокий",
            3: "🟡 Повышенный",
            4: "🟢 Средний",
            5: "🔵 Обычный",
            6: "⚪ Низкий",
            7: "⚪ Очень низкий",
            8: "⚪ Минимальный",
            9: "⚪ Неважный",
            10: "⚪ Последний",
        }
        return labels.get(self.priority, f"Приоритет {self.priority}")
    
    # =========================================================================
    # Методы
    # =========================================================================
    
    def deactivate(self, removed_by_user: Optional[uuid.UUID] = None, reason: Optional[str] = None):
        """Деактивировать участие (мягкое удаление из группы)"""
        self.is_active = False
        self.removed_at = func.now()
        self.removed_by = removed_by_user
        if reason:
            self.reason = reason
    
    def reactivate(self, reactivated_by: Optional[uuid.UUID] = None):
        """Восстановить участие в группе"""
        self.is_active = True
        self.removed_at = None
        self.removed_by = None
        self.added_at = func.now()
        if reactivated_by:
            self.added_by = reactivated_by
    
    def change_priority(self, new_priority: int, changed_by: Optional[uuid.UUID] = None):
        """Изменить приоритет контакта в группе"""
        if not 1 <= new_priority <= 10:
            raise ValueError("Приоритет должен быть от 1 до 10")
        self.priority = new_priority
        if changed_by:
            self.added_by = changed_by
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Сериализация в словарь"""
        result = {
            "contact_id": str(self.contact_id),
            "contact_name": self.contact_name,
            "group_id": str(self.group_id),
            "group_name": self.group_name,
            "is_active": self.is_active,
            "role": self.role,
            "priority": self.priority,
            "priority_label": self.priority_label,
            "added_by": str(self.added_by) if self.added_by else None,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "removed_at": self.removed_at.isoformat() if self.removed_at else None,
            "removed_by": str(self.removed_by) if self.removed_by else None,
            "reason": self.reason,
            "note": self.note,
            "age": self.age,
            "status_display": self.status_display,
        }
        
        if include_details:
            result.update({
                "contact_department": self.contact_department,
                "contact_mobile": self.contact_mobile,
                "contact_internal": self.contact_internal,
                "contact_email": self.contact_email,
                "contact_is_active": self.contact.is_active if self.contact else None,
            })
        
        return result
    
    @classmethod
    async def add_contact_to_group(
        cls,
        db_session,
        contact_id: uuid.UUID,
        group_id: uuid.UUID,
        added_by: Optional[uuid.UUID] = None,
        role: Optional[str] = None,
        priority: int = 5,
        reason: Optional[str] = None,
        note: Optional[str] = None
    ) -> "ContactGroupMember":
        """
        Добавить контакт в группу с проверками и обновлением счетчика
        
        Args:
            db_session: асинхронная сессия БД
            contact_id: ID контакта
            group_id: ID группы
            added_by: кто добавил
            role: роль контакта в группе
            priority: приоритет обзвона (1-10)
            reason: причина добавления
            note: заметка
            
        Returns:
            Созданная связь ContactGroupMember
            
        Raises:
            ValueError: если связь уже существует
        """
        from sqlalchemy import select, update
        from app.models.contact_group import ContactGroup
        from app.models.contact import Contact
        
        # Проверяем существование контакта
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await db_session.execute(stmt)
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError(f"Контакт с ID {contact_id} не найден")
        if contact.is_archived:
            raise ValueError(f"Контакт '{contact.full_name}' в архиве")
        
        # Проверяем существование группы
        stmt = select(ContactGroup).where(ContactGroup.id == group_id)
        result = await db_session.execute(stmt)
        group = result.scalar_one_or_none()
        if not group:
            raise ValueError(f"Г�������па с ID {group_id} не найдена")
        if group.is_archived:
            raise ValueError(f"Группа '{group.name}' в архиве")
        
        # Проверяем, нет ли уже такой связи
        stmt = select(cls).where(
            cls.contact_id == contact_id,
            cls.group_id == group_id
        )
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            if existing.is_active:
                raise ValueError(
                    f"Контакт '{contact.full_name}' уже состоит в группе '{group.name}'"
                )
            else:
                # Реактивируем существующую связь
                existing.reactivate(added_by)
                if role:
                    existing.role = role
                if priority != 5:
                    existing.priority = priority
                if reason:
                    existing.reason = reason
                if note:
                    existing.note = note
                await db_session.flush()
                return existing
        
        # Создаем новую связь
        membership = cls(
            contact_id=contact_id,
            group_id=group_id,
            added_by=added_by,
            role=role,
            priority=priority,
            reason=reason,
            note=note
        )
        db_session.add(membership)
        
        # Обновляем счетчики группы
        group.update_member_counts()
        
        await db_session.flush()
        return membership
    
    @classmethod
    async def remove_contact_from_group(
        cls,
        db_session,
        contact_id: uuid.UUID,
        group_id: uuid.UUID,
        removed_by: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Удалить контакт из группы
        
        Args:
            db_session: асинхронная сессия БД
            contact_id: ID контакта
            group_id: ID группы
            removed_by: кто удалил
            reason: причина удаления
            hard_delete: True - полное удаление, False - мягкая деактивация
            
        Returns:
            True если удалено, False если связь не найдена
        """
        from sqlalchemy import select, update
        from app.models.contact_group import ContactGroup
        
        # Ищем связь
        stmt = select(cls).where(
            cls.contact_id == contact_id,
            cls.group_id == group_id
        )
        result = await db_session.execute(stmt)
        membership = result.scalar_one_or_none()
        
        if not membership:
            return False
        
        if hard_delete:
            # Полное удаление
            await db_session.delete(membership)
        else:
            # Мягкая деактивация
            membership.deactivate(removed_by, reason)
        
        # Обновляем счетчики группы
        if membership.group:
            membership.group.update_member_counts()
        
        await db_session.flush()
        return True
    
    @classmethod
    async def get_group_members(
        cls,
        db_session,
        group_id: uuid.UUID,
        active_only: bool = True,
        include_contact_details: bool = False
    ) -> List["ContactGroupMember"]:
        """Получить всех участников группы"""
        from sqlalchemy import select
        from app.models.contact import Contact
        
        stmt = (
            select(cls)
            .join(Contact, cls.contact_id == Contact.id)
            .where(cls.group_id == group_id)
        )
        
        if active_only:
            stmt = stmt.where(cls.is_active == True)
            stmt = stmt.where(Contact.is_active == True)
            stmt = stmt.where(Contact.is_archived == False)
        
        stmt = stmt.order_by(cls.priority.asc(), cls.added_at.desc())
        
        result = await db_session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_contact_groups(
        cls,
        db_session,
        contact_id: uuid.UUID,
        active_only: bool = True
    ) -> List["ContactGroupMember"]:
        """Получить все группы, в которых состоит контакт"""
        from sqlalchemy import select
        from app.models.contact_group import ContactGroup
        
        stmt = (
            select(cls)
            .join(ContactGroup, cls.group_id == ContactGroup.id)
            .where(cls.contact_id == contact_id)
        )
        
        if active_only:
            stmt = stmt.where(cls.is_active == True)
            stmt = stmt.where(ContactGroup.is_active == True)
            stmt = stmt.where(ContactGroup.is_archived == False)
        
        stmt = stmt.order_by(cls.added_at.desc())
        
        result = await db_session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def bulk_add_contacts(
        cls,
        db_session,
        contact_ids: List[uuid.UUID],
        group_id: uuid.UUID,
        added_by: Optional[uuid.UUID] = None,
        reason: Optional[str] = None
    ) -> dict:
        """
        Массовое добавление контактов в группу
        
        Returns:
            {"added": count, "skipped": count, "errors": [...]}
        """
        result = {"added": 0, "skipped": 0, "errors": []}
        
        for contact_id in contact_ids:
            try:
                await cls.add_contact_to_group(
                    db_session, contact_id, group_id, added_by, reason=reason
                )
                result["added"] += 1
            except ValueError as e:
                if "уже состоит" in str(e):
                    result["skipped"] += 1
                else:
                    result["errors"].append({
                        "contact_id": str(contact_id),
                        "error": str(e)
                    })
            except Exception as e:
                result["errors"].append({
                    "contact_id": str(contact_id),
                    "error": str(e)
                })
        
        return result
    
    @classmethod
    async def bulk_remove_contacts(
        cls,
        db_session,
        contact_ids: List[uuid.UUID],
        group_id: uuid.UUID,
        removed_by: Optional[uuid.UUID] = None,
        reason: Optional[str] = None
    ) -> dict:
        """
        Массовое удаление контактов из группы
        
        Returns:
            {"removed": count, "not_found": count}
        """
        result = {"removed": 0, "not_found": 0}
        
        for contact_id in contact_ids:
            removed = await cls.remove_contact_from_group(
                db_session, contact_id, group_id, removed_by, reason
            )
            if removed:
                result["removed"] += 1
            else:
                result["not_found"] += 1
        
        return result
    
    def __repr__(self) -> str:
        status = "активен" if self.is_active else "неактивен"
        return f"<ContactGroupMember(contact='{self.contact_name}', group='{self.group_name}', status='{status}')>"


# Необходимые импорты (добавить в начало файла)
from sqlalchemy import Integer
