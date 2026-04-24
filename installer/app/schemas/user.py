#!/usr/bin/env python3
"""
Pydantic схемы для пользователей ГО-ЧС Информирование
Соответствует ТЗ, раздел 22: Роли пользователей

Роли:
- Администратор: полный доступ ко всем разделам
- Оператор: запуск/остановка обзвона, просмотр статусов, входящие, сценарии, контакты (ограниченно)
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime
from enum import Enum


# ============================================================================
# ЕНАМЫ (перечисления)
# ============================================================================

class UserRole(str, Enum):
    """Роли пользователей системы"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"  # Наблюдатель (только просмотр, без запуска)


class UserStatus(str, Enum):
    """Статусы пользователя"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"        # Заблокирован (после неудачных попыток)
    PENDING = "pending"      # Ожидает активации


class UserAction(str, Enum):
    """Действия над пользователем (для аудита)"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    ROLE_CHANGED = "role_changed"


# ============================================================================
# БАЗОВЫЕ СХЕМЫ
# ============================================================================

class UserBase(BaseModel):
    """Базовая схема пользователя"""
    email: EmailStr = Field(
        ...,
        description="Email пользователя (уникальный, используется для входа)"
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r'^[a-zA-Z0-9_\-\.]+$',
        description="Имя пользователя (логин, 3-100 символов, латиница)"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Полное имя (ФИО)"
    )
    role: UserRole = Field(
        default=UserRole.OPERATOR,
        description="Роль пользователя"
    )
    is_active: bool = Field(
        default=True,
        description="Активен ли пользователь"
    )


class UserCreate(UserBase):
    """Схема для создания пользователя"""
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль (8-128 символов)"
    )
    password_confirm: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Подтверждение пароля"
    )
    
    @field_validator('password')
    def validate_password_strength(cls, v: str) -> str:
        """Проверка сложности пароля"""
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        
        # Проверка наличия цифр
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        
        # Проверка наличия букв
        if not any(c.isalpha() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        
        # Проверка наличия заглавных букв
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        
        # Проверка наличия спецсимволов
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        if not any(c in special_chars for c in v):
            raise ValueError(f'Пароль должен содержать хотя бы один спецсимвол: {special_chars}')
        
        return v
    
    @field_validator('password_confirm')
    def passwords_match(cls, v: str, info) -> str:
        """Проверка совпадения паролей"""
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Пароли не совпадают')
        return v


class UserUpdate(BaseModel):
    """Схема для обновления пользователя (все поля опциональны)"""
    email: Optional[EmailStr] = Field(
        default=None,
        description="Новый email"
    )
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100,
        pattern=r'^[a-zA-Z0-9_\-\.]+$',
        description="Новое имя пользователя"
    )
    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Новое полное имя"
    )
    role: Optional[UserRole] = Field(
        default=None,
        description="Новая роль"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Активен/неактивен"
    )


class UserPasswordChange(BaseModel):
    """Схема для смены пароля"""
    current_password: str = Field(
        ...,
        description="Текущий пароль"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Новый пароль"
    )
    new_password_confirm: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Подтверждение нового пароля"
    )
    
    @field_validator('new_password')
    def validate_password_strength(cls, v: str) -> str:
        """Проверка сложности нового пароля"""
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(c.isalpha() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        if not any(c in special_chars for c in v):
            raise ValueError(f'Пароль должен содержать хотя бы один спецсимвол: {special_chars}')
        return v
    
    @field_validator('new_password_confirm')
    def passwords_match(cls, v: str, info) -> str:
        """Проверка совпадения нового пароля"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Новые пароли не совпадают')
        return v


class UserPasswordReset(BaseModel):
    """Схема для сброса пароля (администратором)"""
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Новый пароль"
    )
    force_change: bool = Field(
        default=True,
        description="Требовать смену пароля при следующем входе"
    )


# ============================================================================
# СХЕМЫ ОТВЕТОВ
# ============================================================================

class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    id: UUID = Field(..., description="ID пользователя")
    email: str = Field(..., description="Email")
    username: str = Field(..., description="Имя пользователя")
    full_name: str = Field(..., description="Полное имя")
    role: str = Field(..., description="Роль")
    is_active: bool = Field(..., description="Активен")
    is_superuser: bool = Field(default=False, description="Суперпользователь")
    last_login: Optional[datetime] = Field(None, description="Последний вход")
    login_attempts: int = Field(default=0, description="Неудачных попыток входа")
    force_password_change: bool = Field(default=False, description="Требуется смена пароля")
    created_at: Optional[datetime] = Field(None, description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    
    model_config = ConfigDict(from_attributes=True)
    
    @property
    def role_display(self) -> str:
        """Отображаемое название роли"""
        roles = {
            "admin": "👑 Администратор",
            "operator": "🔧 Оператор",
            "viewer": "👁 Наблюдатель",
        }
        return roles.get(self.role, self.role)
    
    @property
    def status_display(self) -> str:
        """Отображаемый статус"""
        if self.is_active:
            return "✅ Активен"
        elif self.login_attempts >= 5:
            return "🔒 Заблокирован"
        else:
            return "❌ Неактивен"


class UserListResponse(BaseModel):
    """Схема ответа со списком пользователей (без чувствительных данных)"""
    id: UUID = Field(..., description="ID")
    email: str = Field(..., description="Email")
    username: str = Field(..., description="Логин")
    full_name: str = Field(..., description="ФИО")
    role: str = Field(..., description="Роль")
    is_active: bool = Field(..., description="Активен")
    last_login: Optional[datetime] = Field(None, description="Последний вход")
    created_at: Optional[datetime] = Field(None, description="Создан")
    
    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    """Расширенный ответ с дополнительной информацией (для админа)"""
    created_by: Optional[UUID] = Field(None, description="Кто создал")
    updated_by: Optional[UUID] = Field(None, description="Кто обновил")
    total_campaigns: int = Field(default=0, description="Всего кампаний")
    total_logins: int = Field(default=0, description="Всего входов")
    account_locked_until: Optional[datetime] = Field(None, description="Заблокирован до")


class UserLoginResponse(BaseModel):
    """Ответ после успешного входа"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Тип токена")
    user: UserResponse = Field(..., description="Данные пользователя")
    expires_in: int = Field(..., description="Срок действия токена (секунд)")


# ============================================================================
# СХЕМЫ ДЛЯ ФИЛЬТРАЦИИ И ПОИСКА
# ============================================================================

class UserFilterParams(BaseModel):
    """Параметры фильтрации пользователей"""
    role: Optional[UserRole] = Field(
        default=None,
        description="Фильтр по роли"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Фильтр по активности"
    )
    search: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Поиск по имени/email/логину"
    )
    created_after: Optional[datetime] = Field(
        default=None,
        description="Создан после даты"
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Создан до даты"
    )


# ============================================================================
# СХЕМЫ ДЛЯ АУДИТА
# ============================================================================

class UserAuditEntry(BaseModel):
    """Запись аудита действий с пользователем"""
    action: UserAction = Field(..., description="Действие")
    user_id: UUID = Field(..., description="ID пользователя")
    performed_by: Optional[UUID] = Field(None, description="Кто выполнил действие")
    details: Optional[Dict[str, Any]] = Field(None, description="Детали изменений")
    ip_address: Optional[str] = Field(None, description="IP адрес")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время действия")


# ============================================================================
# ВАЛИДАТОРЫ И КОНСТАНТЫ
# ============================================================================

# Минимальная длина пароля
MIN_PASSWORD_LENGTH = 8

# Максимальное количество неудачных попыток входа
MAX_LOGIN_ATTEMPTS = 5

# Время блокировки после превышения попыток (минут)
LOCKOUT_MINUTES = 15

# Разрешенные роли
ALLOWED_ROLES = [role.value for role in UserRole]

# Словарь с описанием прав для каждой роли
ROLE_PERMISSIONS = {
    "admin": {
        "name": "Администратор",
        "description": "Полный доступ ко всем разделам системы",
        "permissions": [
            "users:read", "users:create", "users:update", "users:delete",
            "contacts:read", "contacts:create", "contacts:update", "contacts:delete", "contacts:import",
            "groups:read", "groups:create", "groups:update", "groups:delete",
            "scenarios:read", "scenarios:create", "scenarios:update", "scenarios:delete",
            "playbooks:read", "playbooks:create", "playbooks:update", "playbooks:delete",
            "campaigns:read", "campaigns:create", "campaigns:start", "campaigns:stop",
            "inbound:read", "inbound:delete",
            "settings:read", "settings:update",
            "audit:read", "audit:export",
            "system:backup", "system:restore",
        ]
    },
    "operator": {
        "name": "Оператор",
        "description": "Управление обзвоном, просмотр статусов и входящих",
        "permissions": [
            "contacts:read",
            "groups:read",
            "scenarios:read",
            "campaigns:read", "campaigns:start", "campaigns:stop",
            "inbound:read",
            "playbooks:read",
        ]
    },
    "viewer": {
        "name": "Наблюдатель",
        "description": "Только просмотр (без запуска обзвона)",
        "permissions": [
            "contacts:read",
            "groups:read",
            "scenarios:read",
            "campaigns:read",
            "inbound:read",
            "playbooks:read",
        ]
    },
}


def get_role_permissions(role: str) -> List[str]:
    """Получить список прав для роли"""
    role_data = ROLE_PERMISSIONS.get(role, {})
    return role_data.get("permissions", [])


def has_permission(role: str, permission: str) -> bool:
    """Проверить, имеет ли роль указанное право"""
    permissions = get_role_permissions(role)
    return permission in permissions
