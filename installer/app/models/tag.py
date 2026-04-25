#!/usr/bin/env python3
"""
Модель тега для ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база — теги
Теги используются для категоризации и быстрой фильтрации контактов
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Boolean, Integer, ForeignKey,
    Column, String, DateTime, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contact_tag import ContactTag


class Tag(Base):
    """
    Модель тега — метка для категоризации контактов
    
    Примеры тегов:
    - Руководитель
    - ИТ-отдел
    - Бухгалтерия
    - Склад
    - Удаленный сотрудник
    - VIP
    - Дежурный
    
    Особенности:
    - Каждый тег имеет уникальное имя
    - Цвет для визуального отображения в интерфейсе (HEX)
    - Мягкое удаление через флаг is_archived
    - Аудит создания/обновления
    """
    
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("name", name="uq_tags_name"),
        Index("idx_tags_name", "name"),
        Index("idx_tags_is_active", "is_active"),
        Index("idx_tags_name_trgm", func.lower(func.cast("name", String))),
        CheckConstraint(
            "color ~ '^#[0-9a-fA-F]{6}$'",
            name="ck_tags_color_hex"
        ),
        {"comment": "Теги для категоризации контактов"}
    )
    
    # =========================================================================
    # Основные поля
    # =========================================================================
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Уникальный идентификатор тега"
    )
    
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Название тега (уникальное)"
    )
    
    color: Mapped[str] = mapped_column(
        String(7),
        default="#95a5a6",
        nullable=False,
        comment="Цвет тега в HEX формате (#RRGGBB)"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Описание тега (для чего используется)"
    )
    
    # =========================================================================
    # Статусные поля
    # =========================================================================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли тег (можно назначать контактам)"
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
        comment="Системный тег (нельзя удалить/редактировать)"
    )
    
    # =========================================================================
    # Счетчик использования (для оптимизации запросов)
    # =========================================================================
    
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Количество контактов с этим тегом (кэш)"
    )
    
    # =========================================================================
    # Аудит и метаданные
    # =========================================================================
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто создал тег"
    )
    
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто последним обновил тег"
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
        backref="created_tags",
        lazy="selectin"
    )
    
    # Редактор
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
        backref="updated_tags",
        lazy="selectin"
    )
    
    # Связь с контактами (many-to-many через contact_tags)
    contact_assignments: Mapped[List["ContactTag"]] = relationship(
        "ContactTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # =========================================================================
    # Свойства (properties)
    # =========================================================================
    
    @property
    def contacts(self) -> List["Contact"]:
        """Получить все контакты с этим тегом"""
        return [
            ca.contact 
            for ca in self.contact_assignments 
            if ca.contact and not ca.contact.is_archived
        ]
    
    @property
    def active_contacts_count(self) -> int:
        """Количество активных контактов с этим тегом"""
        return len([
            ca for ca in self.contact_assignments 
            if ca.contact and ca.contact.is_active and not ca.contact.is_archived
        ])
    
    @property
    def display_color(self) -> str:
        """Цвет для отображения (с фолбэком)"""
        return self.color if self.color else "#95a5a6"
    
    @property
    def is_deletable(self) -> bool:
        """Можно ли удалить тег (системные нельзя)"""
        return not self.is_system
    
    @property
    def is_editable(self) -> bool:
        """Можно ли редактировать тег (системные нельзя)"""
        return not self.is_system
    
    # =========================================================================
    # Предопределенные цвета для UI
    # =========================================================================
    
    PRESET_COLORS = {
        "red": "#e74c3c",
        "orange": "#e67e22",
        "yellow": "#f1c40f",
        "green": "#2ecc71",
        "blue": "#3498db",
        "purple": "#9b59b6",
        "pink": "#e91e63",
        "teal": "#1abc9c",
        "grey": "#95a5a6",
        "dark": "#34495e",
        "indigo": "#3f51b5",
        "lime": "#cddc39",
    }
    
    # =========================================================================
    # Методы
    # =========================================================================
    
    def update_usage_count(self, session=None):
        """Обновить счетчик использования (вызывается после изменения связей)"""
        self.usage_count = self.active_contacts_count
    
    def soft_delete(self, deleted_by: Optional[uuid.UUID] = None):
        """Мягкое удаление (архивирование)"""
        if self.is_system:
            raise ValueError(f"Нельзя удалить системный тег: {self.name}")
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
    
    def to_dict(self, include_contacts: bool = False) -> dict:
        """Сериализация в словарь"""
        result = {
            "id": str(self.id),
            "name": self.name,
            "color": self.color,
            "description": self.description,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "is_system": self.is_system,
            "usage_count": self.usage_count,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_contacts:
            result["contacts"] = [
                {
                    "id": str(ca.contact.id),
                    "full_name": ca.contact.full_name
                }
                for ca in self.contact_assignments
                if ca.contact and not ca.contact.is_archived
            ]
        
        return result
    
    @classmethod
    def get_preset_color(cls, color_name: str) -> str:
        """Получить HEX-код по названию цвета"""
        return cls.PRESET_COLORS.get(color_name, "#95a5a6")
    
    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', color='{self.color}')>"
    
    def __str__(self) -> str:
        return self.name


# =============================================================================
# Предзагруженные системные теги (для миграции)
# =============================================================================

SYSTEM_TAGS = [
    {
        "name": "VIP",
        "color": "#e74c3c",
        "description": "Руководители и ключевые сотрудники",
        "is_system": True,
    },
    {
        "name": "Дежурный",
        "color": "#e67e22",
        "description": "Дежурная смена",
        "is_system": True,
    },
    {
        "name": "Оповещение",
        "color": "#f1c40f",
        "description": "Обязательные для оповещения",
        "is_system": True,
    },
    {
        "name": "Удаленный",
        "color": "#3498db",
        "description": "Работает удаленно",
        "is_system": True,
    },
]
