#!/usr/bin/env python3
"""
Модель контакта для ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ForeignKey,
    Index, event, inspect
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contact_group_member import ContactGroupMember
    from app.models.contact_tag import ContactTag
    from app.models.user import User


class Contact(Base):
    """
    Модель контакта — сотрудника/абонента для оповещения
    
    Поля согласно ТЗ:
    - ФИО
    - подразделение
    - должность
    - внутренний номер (3-4 знака)
    - мобильный номер (+7XXXXXXXXXX / 8XXXXXXXXXX)
    - email (опционально)
    - активен/неактивен
    - комментарий
    """
    
    __tablename__ = "contacts"
    __table_args__ = (
        Index("idx_contacts_full_name", "full_name"),
        Index("idx_contacts_department", "department"),
        Index("idx_contacts_mobile_number", "mobile_number"),
        Index("idx_contacts_internal_number", "internal_number"),
        Index("idx_contacts_is_active", "is_active"),
        Index("idx_contacts_created_at", "created_at"),
        Index("idx_contacts_full_name_trgm", text("full_name gin_trgm_ops"), postgresql_using="gin"),
        {"comment": "Контакты (сотрудники/абоненты) для системы оповещения"}
    )
    
    # =========================================================================
    # Основные поля
    # =========================================================================
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Уникальный идентификатор контакта"
    )
    
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ФИО сотрудника полностью"
    )
    
    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Подразделение / отдел"
    )
    
    position: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Должность"
    )
    
    internal_number: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Внутренний номер (3-4 знака)"
    )
    
    mobile_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Мобильный номер (+7XXXXXXXXXX или 8XXXXXXXXXX)"
    )
    
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email (опционально)"
    )
    
    # =========================================================================
    # Статусные поля
    # =========================================================================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли контакт (для включения в обзвон)"
    )
    
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="В архиве (мягкое удаление)"
    )
    
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Произвольный комментарий"
    )
    
    # =========================================================================
    # Аудит и метаданные
    # =========================================================================
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто создал запись"
    )
    
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто последним обновил запись"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата/время создания"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Дата/время последнего обновления"
    )
    
    # =========================================================================
    # Связи (relationships)
    # =========================================================================
    
    # Создатель
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        backref="created_contacts",
        lazy="selectin"
    )
    
    # Редактор
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
        backref="updated_contacts",
        lazy="selectin"
    )
    
    # Связь с группами (many-to-many через contact_group_members)
    group_memberships: Mapped[List["ContactGroupMember"]] = relationship(
        "ContactGroupMember",
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Связь с тегами (many-to-many через contact_tags)
    tag_assignments: Mapped[List["ContactTag"]] = relationship(
        "ContactTag",
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # =========================================================================
    # Свойства (properties)
    # =========================================================================
    
    @property
    def groups(self) -> List["ContactGroup"]:
        """Получить все группы, в которых состоит контакт"""
        return [gm.group for gm in self.group_memberships if gm.group and not gm.group.is_archived]
    
    @property
    def tags(self) -> List["Tag"]:
        """Получить все теги контакта"""
        return [ta.tag for ta in self.tag_assignments if ta.tag]
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя (ФИО или заглушка)"""
        return self.full_name or "Без имени"
    
    @property
    def primary_phone(self) -> Optional[str]:
        """
        Основной телефон для обзвона.
        Приоритет: мобильный > внутренний
        """
        if self.mobile_number:
            return self.mobile_number
        if self.internal_number:
            return self.internal_number
        return None
    
    @property
    def has_mobile(self) -> bool:
        """Есть ли мобильный номер"""
        return bool(self.mobile_number and self.mobile_number.strip())
    
    @property
    def has_internal(self) -> bool:
        """Есть ли внутренний номер"""
        return bool(self.internal_number and self.internal_number.strip())
    
    @property
    def has_any_phone(self) -> bool:
        """Есть ли хотя бы один номер"""
        return self.has_mobile or self.has_internal
    
    # =========================================================================
    # Методы
    # =========================================================================
    
    def to_dict(self, include_relations: bool = False) -> dict:
        """Сериализация в словарь"""
        result = {
            "id": str(self.id),
            "full_name": self.full_name,
            "department": self.department,
            "position": self.position,
            "internal_number": self.internal_number,
            "mobile_number": self.mobile_number,
            "email": self.email,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "comment": self.comment,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_relations:
            result["groups"] = [
                {
                    "id": str(gm.group.id),
                    "name": gm.group.name
                }
                for gm in self.group_memberships
                if gm.group and not gm.group.is_archived
            ]
            result["tags"] = [
                {
                    "id": str(ta.tag.id),
                    "name": ta.tag.name,
                    "color": ta.tag.color
                }
                for ta in self.tag_assignments
                if ta.tag
            ]
        
        return result
    
    def soft_delete(self, deleted_by: Optional[uuid.UUID] = None):
        """Мягкое удаление (архивирование)"""
        self.is_archived = True
        self.is_active = False
        self.updated_by = deleted_by
        self.updated_at = func.now()
    
    def restore(self, restored_by: Optional[uuid.UUID] = None):
        """Восстановление из архива"""
        self.is_archived = False
        self.is_active = True
        self.updated_by = restored_by
        self.updated_at = func.now()
    
    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name='{self.full_name}', active={self.is_active})>"
    
    def __str__(self) -> str:
        return self.display_name


# =============================================================================
# События SQLAlchemy (для аудита)
# =============================================================================

@event.listens_for(Contact, "before_insert")
def contact_before_insert(mapper, connection, target):
    """Перед вставкой: нормализация номеров"""
    if target.mobile_number:
        # Удаляем всё, кроме цифр и +
        import re
        cleaned = re.sub(r'[^\d+]', '', target.mobile_number)
        # Если номер начинается с 8, заменяем на +7
        if cleaned.startswith('8') and len(cleaned) == 11:
            cleaned = '+7' + cleaned[1:]
        elif cleaned.startswith('7') and len(cleaned) == 11:
            cleaned = '+' + cleaned
        target.mobile_number = cleaned


@event.listens_for(Contact, "before_update")
def contact_before_update(mapper, connection, target):
    """Перед обновлением: нормализация номеров"""
    if target.mobile_number:
        import re
        cleaned = re.sub(r'[^\d+]', '', target.mobile_number)
        if cleaned.startswith('8') and len(cleaned) == 11:
            cleaned = '+7' + cleaned[1:]
        elif cleaned.startswith('7') and len(cleaned) == 11:
            cleaned = '+' + cleaned
        target.mobile_number = cleaned
