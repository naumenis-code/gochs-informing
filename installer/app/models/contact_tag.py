#!/usr/bin/env python3
"""
Модель связи контакт-тег (M2M) для ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база — теги
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Column, DateTime, Index, UniqueConstraint, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.tag import Tag


class ContactTag(Base):
    """
    Связка many-to-many: Контакт <-> Тег
    
    Один контакт может иметь много тегов.
    Один тег может быть назначен многим контактам.
    
    Особенности:
    - Композитный первичный ключ (contact_id + tag_id)
    - Защита от дубликатов (уникальный constraint)
    - Каскадное удаление при удалении контакта или тега
    - Аудит: кто и когда добавил тег
    """
    
    __tablename__ = "contact_tags"
    __table_args__ = (
        UniqueConstraint(
            "contact_id", "tag_id",
            name="uq_contact_tag"
        ),
        Index("idx_contact_tags_contact_id", "contact_id"),
        Index("idx_contact_tags_tag_id", "tag_id"),
        Index("idx_contact_tags_added_at", "added_at"),
        {"comment": "Связь many-to-many: контакты <-> теги"}
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
    
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        comment="ID тега"
    )
    
    # =========================================================================
    # Метаданные связи
    # =========================================================================
    
    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто добавил тег контакту"
    )
    
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Когда тег был добавлен"
    )
    
    # Причина добавления (опционально, для аудита)
    reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Причина добавления тега (для аудита)"
    )
    
    # =========================================================================
    # Связи (relationships)
    # =========================================================================
    
    contact: Mapped["Contact"] = relationship(
        "Contact",
        back_populates="tag_assignments",
        lazy="selectin"
    )
    
    tag: Mapped["Tag"] = relationship(
        "Tag",
        back_populates="contact_assignments",
        lazy="selectin"
    )
    
    # Кто добавил
    added_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[added_by],
        backref="tag_assignments_made",
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
    def tag_name(self) -> str:
        """Имя тега (для быстрого доступа)"""
        return self.tag.name if self.tag else "Неизвестный тег"
    
    @property
    def tag_color(self) -> str:
        """Цвет тега"""
        return self.tag.color if self.tag else "#95a5a6"
    
    @property
    def age(self) -> str:
        """Сколько времени назад добавлен тег (человекочитаемый формат)"""
        if not self.added_at:
            return "неизвестно"
        
        from datetime import timezone
        now = datetime.now(timezone.utc)
        diff = now - self.added_at.replace(tzinfo=timezone.utc)
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} г. назад"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} мес. назад"
        elif diff.days > 0:
            return f"{diff.days} дн. назад"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"
    
    # =========================================================================
    # Методы
    # =========================================================================
    
    def to_dict(self) -> dict:
        """Сериализация в словарь"""
        return {
            "contact_id": str(self.contact_id),
            "contact_name": self.contact_name,
            "tag_id": str(self.tag_id),
            "tag_name": self.tag_name,
            "tag_color": self.tag_color,
            "added_by": str(self.added_by) if self.added_by else None,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "reason": self.reason,
            "age": self.age,
        }
    
    @classmethod
    async def add_tag_to_contact(
        cls,
        db_session,
        contact_id: uuid.UUID,
        tag_id: uuid.UUID,
        added_by: Optional[uuid.UUID] = None,
        reason: Optional[str] = None
    ) -> "ContactTag":
        """
        Добавить тег контакту с проверками и обновлением счетчика
        
        Args:
            db_session: асинхронная сессия БД
            contact_id: ID контакта
            tag_id: ID тега
            added_by: кто добавил
            reason: причина добавления
            
        Returns:
            Созданная связь ContactTag
            
        Raises:
            ValueError: если связь уже существует
        """
        from sqlalchemy import select, update
        from app.models.tag import Tag
        
        # Проверяем, нет ли уже такой связи
        stmt = select(cls).where(
            cls.contact_id == contact_id,
            cls.tag_id == tag_id
        )
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError(f"Тег уже назначен этому контакту")
        
        # Создаем связь
        contact_tag = cls(
            contact_id=contact_id,
            tag_id=tag_id,
            added_by=added_by,
            reason=reason
        )
        db_session.add(contact_tag)
        
        # Обновляем счетчик использования тега
        stmt = (
            update(Tag)
            .where(Tag.id == tag_id)
            .values(usage_count=Tag.usage_count + 1)
        )
        await db_session.execute(stmt)
        
        await db_session.flush()
        return contact_tag
    
    @classmethod
    async def remove_tag_from_contact(
        cls,
        db_session,
        contact_id: uuid.UUID,
        tag_id: uuid.UUID
    ) -> bool:
        """
        Удалить тег у контакта с обновлением счетчика
        
        Args:
            db_session: асинхронная сессия БД
            contact_id: ID контакта
            tag_id: ID тега
            
        Returns:
            True если удалено, False если связь не найдена
        """
        from sqlalchemy import select, delete, update
        from app.models.tag import Tag
        
        # Ищем связь
        stmt = select(cls).where(
            cls.contact_id == contact_id,
            cls.tag_id == tag_id
        )
        result = await db_session.execute(stmt)
        contact_tag = result.scalar_one_or_none()
        
        if not contact_tag:
            return False
        
        # Удаляем связь
        await db_session.delete(contact_tag)
        
        # Обновляем счетчик использования тега
        stmt = (
            update(Tag)
            .where(Tag.id == tag_id)
            .values(usage_count=func.greatest(Tag.usage_count - 1, 0))
        )
        await db_session.execute(stmt)
        
        await db_session.flush()
        return True
    
    @classmethod
    async def get_contact_tags(
        cls,
        db_session,
        contact_id: uuid.UUID
    ) -> list["ContactTag"]:
        """Получить все связи тегов для контакта"""
        from sqlalchemy import select
        
        stmt = (
            select(cls)
            .where(cls.contact_id == contact_id)
            .order_by(cls.added_at.desc())
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_tag_contacts(
        cls,
        db_session,
        tag_id: uuid.UUID,
        include_archived: bool = False
    ) -> list["ContactTag"]:
        """Получить все связи контактов для тега"""
        from sqlalchemy import select
        from app.models.contact import Contact
        
        stmt = (
            select(cls)
            .join(Contact, cls.contact_id == Contact.id)
            .where(cls.tag_id == tag_id)
        )
        
        if not include_archived:
            stmt = stmt.where(Contact.is_archived == False)
        
        stmt = stmt.order_by(cls.added_at.desc())
        result = await db_session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def bulk_add_tags(
        cls,
        db_session,
        contact_id: uuid.UUID,
        tag_ids: list[uuid.UUID],
        added_by: Optional[uuid.UUID] = None
    ) -> dict:
        """
        Массовое добавление тегов контакту
        
        Returns:
            {"added": count, "skipped": count, "errors": []}
        """
        result = {"added": 0, "skipped": 0, "errors": []}
        
        for tag_id in tag_ids:
            try:
                await cls.add_tag_to_contact(
                    db_session, contact_id, tag_id, added_by
                )
                result["added"] += 1
            except ValueError:
                result["skipped"] += 1
            except Exception as e:
                result["errors"].append({
                    "tag_id": str(tag_id),
                    "error": str(e)
                })
        
        return result
    
    @classmethod
    async def bulk_remove_tags(
        cls,
        db_session,
        contact_id: uuid.UUID,
        tag_ids: list[uuid.UUID]
    ) -> dict:
        """
        Массовое удаление тегов у контакта
        
        Returns:
            {"removed": count, "not_found": count}
        """
        result = {"removed": 0, "not_found": 0}
        
        for tag_id in tag_ids:
            removed = await cls.remove_tag_from_contact(
                db_session, contact_id, tag_id
            )
            if removed:
                result["removed"] += 1
            else:
                result["not_found"] += 1
        
        return result
    
    def __repr__(self) -> str:
        return f"<ContactTag(contact='{self.contact_name}', tag='{self.tag_name}')>"


# Необходимые импорты (в начало файла)
from sqlalchemy import String
