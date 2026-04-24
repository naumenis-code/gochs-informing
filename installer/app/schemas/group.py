#!/usr/bin/env python3
"""
Pydantic схемы для групп контактов ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база — группы

Группы используются для:
- Организации контактов по отделам/подразделениям
- Массового обзвона (выбор группы в кампании)
- Фильтрации и поиска
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime
import re


# ============================================================================
# БАЗОВЫЕ СХЕМЫ
# ============================================================================

class GroupBase(BaseModel):
    """Базовая схема группы контактов"""
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Название группы (уникальное)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Описание группы (назначение, состав)"
    )
    color: str = Field(
        default="#3498db",
        pattern=r'^#[0-9a-fA-F]{6}$',
        description="Цвет группы в HEX формате (#RRGGBB)"
    )
    is_active: bool = Field(
        default=True,
        description="Активна ли группа (можно использовать в обзвоне)"
    )
    default_priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Приоритет обзвона по умолчанию (1-10, где 1 = высший)"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Максимальное количество повторных попыток для этой группы"
    )
    
    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Валидация названия группы"""
        v = v.strip()
        if len(v) < 2:
            raise ValueError('Название группы должно содержать минимум 2 символа')
        
        # Проверка на недопустимые символы
        if re.search(r'[<>@#$%^&*(){}\[\]\\|]', v):
            raise ValueError('Название группы содержит недопустимые символы')
        
        return v


class GroupCreate(GroupBase):
    """Схема для создания группы"""
    contact_ids: Optional[List[UUID]] = Field(
        default=None,
        description="ID контактов для добавления в группу при создании"
    )
    is_system: bool = Field(
        default=False,
        description="Системная группа (нельзя удалить)"
    )


class GroupUpdate(BaseModel):
    """Схема для обновления группы (все поля опциональны)"""
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Новое название"
    )
    description: Optional[str] = Field(
        default=None,
        description="Новое описание"
    )
    color: Optional[str] = Field(
        default=None,
        pattern=r'^#[0-9a-fA-F]{6}$',
        description="Новый цвет"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Активна/неактивна"
    )
    default_priority: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Приоритет обзвона"
    )
    max_retries: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Максимальное число повторов"
    )


# ============================================================================
# СХЕМЫ ДЛЯ УПРАВЛЕНИЯ УЧАСТНИКАМИ
# ============================================================================

class AddMembersRequest(BaseModel):
    """Запрос на добавление контактов в группу"""
    contact_ids: List[UUID] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="ID контактов для добавления (1-500)"
    )
    role: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Роль добавляемых контактов в группе"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Приоритет обзвона для добавляемых контактов"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Причина добавления (для аудита)"
    )
    note: Optional[str] = Field(
        default=None,
        description="Общая заметка для добавляемых контактов"
    )


class RemoveMembersRequest(BaseModel):
    """Запрос на удаление контактов из группы"""
    contact_ids: List[UUID] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="ID контактов для удаления (1-500)"
    )
    hard_delete: bool = Field(
        default=False,
        description="Полное удаление (False = мягкая деактивация)"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Причина удаления (для аудита)"
    )


class UpdateMemberRequest(BaseModel):
    """Запрос на обновление параметров участника группы"""
    contact_id: UUID = Field(..., description="ID контакта")
    role: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Новая роль"
    )
    priority: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Новый приоритет"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Активен/неактивен"
    )
    note: Optional[str] = Field(
        default=None,
        description="Новая заметка"
    )


# ============================================================================
# СХЕМЫ ОТВЕТОВ
# ============================================================================

class GroupMemberInfo(BaseModel):
    """Информация об участнике группы"""
    contact_id: UUID = Field(..., description="ID контакта")
    contact_name: str = Field(..., description="ФИО контакта")
    department: Optional[str] = Field(None, description="Подразделение")
    position: Optional[str] = Field(None, description="Должность")
    mobile_number: Optional[str] = Field(None, description="Мобильный")
    internal_number: Optional[str] = Field(None, description="Внутренний")
    email: Optional[str] = Field(None, description="Email")
    is_active: bool = Field(..., description="Активен ли контакт")
    
    # Параметры участия в группе
    role: Optional[str] = Field(None, description="Роль в группе")
    priority: int = Field(default=5, description="Приоритет обзвона")
    note: Optional[str] = Field(None, description="Заметка")
    
    # Аудит
    added_at: Optional[datetime] = Field(None, description="Когда добавлен")
    added_by: Optional[UUID] = Field(None, description="Кем добавлен")
    
    model_config = ConfigDict(from_attributes=True)


class GroupResponse(BaseModel):
    """Схема ответа с данными группы"""
    id: UUID = Field(..., description="ID группы")
    name: str = Field(..., description="Название")
    description: Optional[str] = Field(None, description="Описание")
    color: str = Field(..., description="Цвет (HEX)")
    
    # Статусы
    is_active: bool = Field(..., description="Активна")
    is_archived: bool = Field(default=False, description="В архиве")
    is_system: bool = Field(default=False, description="Системная")
    
    # Счетчики
    member_count: int = Field(default=0, description="Активных участников")
    total_member_count: int = Field(default=0, description="Всего участников")
    mobile_members_count: int = Field(default=0, description="С мобильными")
    internal_members_count: int = Field(default=0, description="С внутренними")
    
    # Настройки обзвона
    default_priority: int = Field(default=5, description="Приоритет по умолчанию")
    max_retries: int = Field(default=3, description="Максимум повторов")
    
    # Аудит
    created_by: Optional[UUID] = Field(None, description="Кто создал")
    updated_by: Optional[UUID] = Field(None, description="Кто обновил")
    created_at: Optional[datetime] = Field(None, description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    
    model_config = ConfigDict(from_attributes=True)
    
    @property
    def status_display(self) -> str:
        """Статус для отображения"""
        if self.is_archived:
            return "📦 Архив"
        elif self.is_system:
            return "🔒 Системная"
        elif self.is_active:
            return "✅ Активна"
        else:
            return "❌ Неактивна"
    
    @property
    def is_deletable(self) -> bool:
        """Можно ли удалить группу"""
        return not self.is_system and not self.is_archived


class GroupListResponse(BaseModel):
    """Краткая схема группы для списков"""
    id: UUID = Field(..., description="ID")
    name: str = Field(..., description="Название")
    description: Optional[str] = Field(None, description="Описание")
    color: str = Field(..., description="Цвет")
    is_active: bool = Field(..., description="Активна")
    is_system: bool = Field(default=False, description="Системная")
    member_count: int = Field(default=0, description="Участников")
    default_priority: int = Field(default=5, description="Приоритет")
    created_at: Optional[datetime] = Field(None, description="Создана")
    
    model_config = ConfigDict(from_attributes=True)


class GroupDetailResponse(GroupResponse):
    """Расширенный ответ с участниками группы"""
    members: List[GroupMemberInfo] = Field(
        default_factory=list,
        description="Список участников"
    )
    
    # Дополнительная статистика
    members_by_department: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Участники по подразделениям [{department, count}]"
    )
    active_members: int = Field(default=0, description="Активных участников")
    inactive_members: int = Field(default=0, description="Неактивных участников")


# ============================================================================
# СХЕМЫ ДЛЯ ФИЛЬТРАЦИИ И ПОИСКА
# ============================================================================

class GroupFilterParams(BaseModel):
    """Параметры фильтрации групп"""
    search: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Поиск по названию/описанию"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Фильтр по активности"
    )
    is_system: Optional[bool] = Field(
        default=None,
        description="Только системные/пользовательские"
    )
    has_members: Optional[bool] = Field(
        default=None,
        description="Только с участниками"
    )
    min_members: Optional[int] = Field(
        default=None,
        ge=0,
        description="Минимальное количество участников"
    )
    max_members: Optional[int] = Field(
        default=None,
        ge=0,
        description="Максимальное количество участников"
    )
    created_after: Optional[datetime] = Field(
        default=None,
        description="Создана после"
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Создана до"
    )


# ============================================================================
# СХЕМЫ ДЛЯ МАССОВЫХ ОПЕРАЦИЙ
# ============================================================================

class GroupBulkAction(BaseModel):
    """Запрос на массовое действие с группами"""
    group_ids: List[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID групп (1-100)"
    )
    action: str = Field(
        ...,
        description="Действие: activate, deactivate, archive, delete"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Причина (для аудита)"
    )
    
    @field_validator('action')
    def validate_action(cls, v: str) -> str:
        """Валидация действия"""
        valid_actions = ['activate', 'deactivate', 'archive', 'delete']
        if v not in valid_actions:
            raise ValueError(f'Недопустимое действие. Допустимые: {valid_actions}')
        return v


class GroupMergeRequest(BaseModel):
    """Запрос на объединение групп"""
    source_group_ids: List[UUID] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="ID исходных групп для объединения"
    )
    target_group_id: Optional[UUID] = Field(
        default=None,
        description="ID целевой группы (если None — создать новую)"
    )
    new_group_name: Optional[str] = Field(
        default=None,
        description="Название новой группы (если создается новая)"
    )
    delete_source_groups: bool = Field(
        default=False,
        description="Удалить исходные группы после объединения"
    )


# ============================================================================
# СХЕМЫ СТАТИСТИКИ
# ============================================================================

class GroupStats(BaseModel):
    """Статистика по группам"""
    total_groups: int = Field(..., description="Всего групп")
    active_groups: int = Field(..., description="Активных")
    system_groups: int = Field(..., description="Системных")
    user_groups: int = Field(..., description="Пользовательских")
    archived_groups: int = Field(..., description="В архиве")
    total_memberships: int = Field(..., description="Всего участий (связей)")
    avg_members_per_group: float = Field(..., description="Среднее участников на группу")
    groups_without_members: int = Field(..., description="Пустых групп")
    largest_group: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Самая большая группа {name, count}"
    )
    by_priority: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="По приоритетам [{priority, count}]"
    )


# ============================================================================
# СХЕМЫ ДЛЯ ОБЗВОНА
# ============================================================================

class GroupDialerInfo(BaseModel):
    """Информация о группе для обзвона"""
    group_id: UUID = Field(..., description="ID группы")
    group_name: str = Field(..., description="Название группы")
    total_contacts: int = Field(..., description="Всего контактов")
    active_contacts: int = Field(..., description="Активных контактов")
    contacts_with_phone: int = Field(..., description="С номерами телефонов")
    
    # Настройки обзвона
    default_priority: int = Field(default=5, description="Приоритет")
    max_retries: int = Field(default=3, description="Максимум повторов")
    
    # Список номеров для обзвона
    phone_numbers: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Список {contact_id, name, phone} для обзвона"
    )


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# Предопределенные цвета для групп
GROUP_PRESET_COLORS = {
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

# Системные группы (нельзя удалить)
SYSTEM_GROUP_NAMES = [
    "Все сотрудники",
    "Руководство",
    "Дежурная смена",
]

# Максимальное количество контактов в группе
MAX_MEMBERS_PER_GROUP = 10000

# Максимальное количество групп для одного контакта
MAX_GROUPS_PER_CONTACT = 50
