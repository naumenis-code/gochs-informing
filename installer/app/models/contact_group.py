#!/usr/bin/env python3
"""
Модель группы контактов для ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база — группы
Группы используются для организации контактов и массового обзвона
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer,
    Index, UniqueConstraint, CheckConstraint, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contact_group_member import ContactGroupMember
    from app.models.user import User


class ContactGroup(Base):
    """
    Модель группы контактов
    
    Группы используются для:
    - Организации контактов по отделам/подразделениям
    - Массового обзвона (выбор группы в кампании)
    - Фильтрации и поиска
    
    Примеры групп:
    - Все сотрудники
    - Руководство
    - ИТ-отдел
    - Бухгалтерия
    - Корпус А
    - Корпус Б
    - Дежурная смена
    - Склад
    
    Особенности:
    - Уникальное имя группы
    - Цвет для визуального отображения
    - Счетчик участников (кэш)
    - Мягкое удаление (архивирование)
    - Аудит создания/обновления
    """
    
    __tablename__ = "contact_groups"
    __table_args__ = (
        UniqueConstraint("name", name="uq_contact_groups_name"),
        Index("idx_contact_groups_name", "name"),
        Index("idx_contact_groups_is_active", "is_active"),
        Index("idx_contact_groups_name_trgm", func.lower(func.cast("name", String))),
        Index("idx_contact_groups_created_at", "created_at"),
        CheckConstraint(
            "color ~ '^#[0-9a-fA-F]{6}$'",
            name="ck_contact_groups_color_hex"
        ),
        {"comment": "Группы контактов для организации и обзвона"}
    )
    
    # =========================================================================
    # Основные поля
    # =========================================================================
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Уникальный идентификатор группы"
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Название группы (уникальное)"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Описание группы (назначение, состав)"
    )
    
    color: Mapped[str] = mapped_column(
        String(7),
        default="#3498db",
        nullable=False,
        comment="Цвет группы в HEX формате (#RRGGBB)"
    )
    
    # =========================================================================
    # Статусные поля
    # =========================================================================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активна ли группа (можно использовать в обзвоне)"
    )
    
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="В архиве (мягкое удаление)"
    )
    
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Системная группа (нельзя удалить, например 'Все сотрудники')"
    )
    
    # =========================================================================
    # Счетчик участников (кэш для оптимизации)
    # =========================================================================
    
    member_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Количество активных участников группы (кэш)"
    )
    
    total_member_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Общее количество участников (включая неактивных)"
    )
    
    # =========================================================================
    # Настройки обзвона для группы (по умолчанию)
    # =========================================================================
    
    default_priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="Приоритет обзвона по умолчанию (1-10, где 1 = высший)"
    )
    
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="Максимальное количество повторных попыток для этой группы"
    )
    
    # =========================================================================
    # Аудит и метаданные
    # =========================================================================
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто создал группу"
    )
    
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто последним обновил группу"
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
        backref="created_groups",
        lazy="selectin"
    )
    
    # Редактор
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
        backref="updated_groups",
        lazy="selectin"
    )
    
    # Связь с контактами (many-to-many через contact_group_members)
    memberships: Mapped[List["ContactGroupMember"]] = relationship(
        "ContactGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # =========================================================================
    # Свойства (properties)
    # =========================================================================
    
    @property
    def members(self) -> List["Contact"]:
        """Получить всех активных участников группы"""
        return [
            m.contact
            for m in self.memberships
            if m.contact and m.contact.is_active and not m.contact.is_archived
        ]
    
    @property
    def all_members(self) -> List["Contact"]:
        """Получить всех участников группы (включая неактивных)"""
        return [
            m.contact
            for m in self.memberships
            if m.contact and not m.contact.is_archived
        ]
    
    @property
    def active_member_count(self) -> int:
        """Количество активных участников (вычисляемое)"""
        return len(self.members)
    
    @property
    def display_color(self) -> str:
        """Цвет для отображения (с фолбэком)"""
        return self.color if self.color else "#3498db"
    
    @property
    def is_deletable(self) -> bool:
        """Можно ли удалить группу (системные нельзя)"""
        return not self.is_system
    
    @property
    def is_editable(self) -> bool:
        """Можно ли редактировать группу (системные — только частично)"""
        return True  # Системные можно редактировать, но не удалять
    
    @property
    def mobile_members_count(self) -> int:
        """Количество участников с мобильными номерами"""
        return len([m for m in self.members if m.has_mobile])
    
    @property
    def internal_members_count(self) -> int:
        """Количество участников с внутренними номерами"""
        return len([m for m in self.members if m.has_internal])
    
    # =========================================================================
    # Предопределенные цвета для UI
    # =========================================================================
    
    PRESET_COLORS = {
        "blue": "#3498db",
        "green": "#2ecc71",
        "red": "#e74c3c",
        "orange": "#e67e22",
        "purple": "#9b59b6",
        "teal": "#1abc9c",
        "yellow": "#f1c40f",
        "pink": "#e91e63",
        "indigo": "#3f51b5",
        "grey": "#95a5a6",
        "dark": "#34495e",
    }
    
    # =========================================================================
    # Методы
    # =========================================================================
    
    def update_member_counts(self):
        """Обновить счетчики участников"""
        self.member_count = self.active_member_count
        self.total_member_count = len(self.all_members)
    
    def soft_delete(self, deleted_by: Optional[uuid.UUID] = None):
        """Мягкое удаление (архивирование)"""
        if self.is_system:
            raise ValueError(f"Нельзя удалить системную группу: {self.name}")
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
    
    def to_dict(self, include_members: bool = False) -> dict:
        """Сериализация в словарь"""
        result = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "is_system": self.is_system,
            "member_count": self.member_count,
            "total_member_count": self.total_member_count,
            "mobile_members_count": self.mobile_members_count,
            "internal_members_count": self.internal_members_count,
            "default_priority": self.default_priority,
            "max_retries": self.max_retries,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_members:
            result["members"] = [
                {
                    "id": str(m.contact.id),
                    "full_name": m.contact.full_name,
                    "department": m.contact.department,
                    "mobile_number": m.contact.mobile_number,
                    "internal_number": m.contact.internal_number,
                    "is_active": m.contact.is_active,
                    "added_at": m.added_at.isoformat() if m.added_at else None,
                }
                for m in self.memberships
                if m.contact and not m.contact.is_archived
            ]
        
        return result
    
    @classmethod
    def get_preset_color(cls, color_name: str) -> str:
        """Получить HEX-код по названию цвета"""
        return cls.PRESET_COLORS.get(color_name, "#3498db")
    
    def get_phone_numbers(self, prefer_mobile: bool = True) -> List[str]:
        """
        Получить список телефонных номеров участников группы
        
        Args:
            prefer_mobile: True - сначала мобильные, False - сначала внутренние
            
        Returns:
            Список номеров телефонов
        """
        numbers = []
        for member in self.members:
            if prefer_mobile:
                if member.has_mobile:
                    numbers.append(member.mobile_number)
                elif member.has_internal:
                    numbers.append(member.internal_number)
            else:
                if member.has_internal:
                    numbers.append(member.internal_number)
                elif member.has_mobile:
                    numbers.append(member.mobile_number)
        return numbers
    
    def get_contacts_for_dialer(self) -> List[dict]:
        """
        Получить список контактов для обзвона (только активные с номерами)
        
        Returns:
            Список словарей с id, name, phone
        """
        dial_list = []
        for member in self.members:
            phone = member.primary_phone
            if phone:
                dial_list.append({
                    "contact_id": str(member.id),
                    "name": member.full_name,
                    "phone": phone,
                    "department": member.department,
                })
        return dial_list
    
    def __repr__(self) -> str:
        return f"<ContactGroup(id={self.id}, name='{self.name}', members={self.member_count})>"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.member_count} чел.)"


# =============================================================================
# Предзагруженные системные группы (для миграции)
# =============================================================================

SYSTEM_GROUPS = [
    {
        "name": "Все сотрудники",
        "description": "Все активные сотрудники предприятия",
        "color": "#3498db",
        "is_system": True,
        "default_priority": 5,
    },
    {
        "name": "Руководство",
        "description": "Руководители и топ-менеджмент",
        "color": "#e74c3c",
        "is_system": True,
        "default_priority": 1,
    },
    {
        "name": "Дежурная смена",
        "description": "Текущая дежурная смена",
        "color": "#e67e22",
        "is_system": True,
        "default_priority": 2,
    },
    {
        "name": "ИТ-отдел",
        "description": "Сотрудники ИТ-подразделения",
        "color": "#2ecc71",
        "is_system": False,
        "default_priority": 3,
    },
]
