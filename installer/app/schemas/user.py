#!/usr/bin/env python3
"""
Модель пользователя
Соответствует ТЗ, раздел 22: Роли пользователей

Роли:
- admin: полный доступ
- operator: запуск/остановка обзвона, просмотр
- viewer: только просмотр
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer,
    Index, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """Модель пользователя системы"""
    
    __tablename__ = "users"
    
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
        Index("idx_users_role", "role"),
        Index("idx_users_is_active", "is_active"),
        {"comment": "Пользователи системы ГО-ЧС Информирование"}
    )
    
    # ========================================================================
    # ОСНОВНЫЕ ПОЛЯ
    # ========================================================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Уникальный идентификатор"
    )
    
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        comment="Email (используется для входа)"
    )
    
    username = Column(
        String(100),
        unique=True,
        nullable=False,
        comment="Логин (3-100 символов)"
    )
    
    full_name = Column(
        String(255),
        nullable=False,
        comment="Полное имя (ФИО)"
    )
    
    hashed_password = Column(
        String(255),
        nullable=False,
        comment="Хеш пароля (SHA256 или bcrypt)"
    )
    
    # ========================================================================
    # РОЛЬ И СТАТУС
    # ========================================================================
    
    role = Column(
        String(50),
        nullable=False,
        default="operator",
        comment="Роль: admin, operator, viewer"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли пользователь"
    )
    
    is_superuser = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Суперпользователь (устаревшее, использовать role=admin)"
    )
    
    # ========================================================================
    # БЕЗОПАСНОСТЬ
    # ========================================================================
    
    login_attempts = Column(
        Integer,
        default=0,
        comment="Количество неудачных попыток входа"
    )
    
    locked_until = Column(
        DateTime,
        comment="Заблокирован до (после превышения лимита попыток)"
    )
    
    force_password_change = Column(
        Boolean,
        default=False,
        comment="Требовать смену пароля при следующем входе"
    )
    
    password_changed_at = Column(
        DateTime,
        comment="Дата последней смены пароля"
    )
    
    password_history = Column(
        JSONB,
        default=list,
        comment="История паролей (последние 5)"
    )
    
    # ========================================================================
    # МЕТАДАННЫЕ
    # ========================================================================
    
    last_login = Column(
        DateTime,
        comment="Дата последнего входа"
    )
    
    last_ip = Column(
        String(45),
        comment="IP адрес последнего входа"
    )
    
    login_count = Column(
        Integer,
        default=0,
        comment="Общее количество входов"
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="Кто создал пользователя"
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="Кто обновил пользователя"
    )
    
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="Дата создания"
    )
    
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Дата обновления"
    )
    
    # ========================================================================
    # СВОЙСТВА
    # ========================================================================
    
    @property
    def is_admin(self) -> bool:
        """Является ли администратором"""
        return self.role == "admin"
    
    @property
    def is_operator(self) -> bool:
        """Является ли оператором"""
        return self.role == "operator"
    
    @property
    def is_viewer(self) -> bool:
        """Является ли наблюдателем"""
        return self.role == "viewer"
    
    @property
    def is_locked(self) -> bool:
        """Заблокирован ли"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    @property
    def status(self) -> str:
        """Статус пользователя"""
        if self.is_locked:
            return "locked"
        if not self.is_active:
            return "inactive"
        return "active"
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя"""
        return self.full_name or self.username
    
    @property
    def role_display(self) -> str:
        """Отображаемое название роли"""
        roles = {
            "admin": "Администратор",
            "operator": "Оператор",
            "viewer": "Наблюдатель"
        }
        return roles.get(self.role, self.role)
    
    # ========================================================================
    # МЕТОДЫ
    # ========================================================================
    
    def to_dict(self) -> dict:
        """Сериализация в словарь"""
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_attempts": self.login_attempts or 0,
            "is_locked": self.is_locked,
            "force_password_change": self.force_password_change or False,
            "login_count": self.login_count or 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "role_display": self.role_display
        }
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
