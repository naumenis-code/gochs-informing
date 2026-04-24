#!/usr/bin/env python3
"""
Pydantic схемы для контактов ГО-ЧС Информирование
Соответствует ТЗ, раздел 10: Контактная база

Поля контакта:
- ФИО
- подразделение
- должность
- внутренний номер (3-4 знака)
- мобильный номер (+7XXXXXXXXXX / 8XXXXXXXXXX)
- email (опционально)
- активен/неактивен
- комментарий
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator, model_validator
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime
import re


# ============================================================================
# БАЗОВЫЕ СХЕМЫ
# ============================================================================

class ContactBase(BaseModel):
    """Базовая схема контакта"""
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="ФИО сотрудника полностью"
    )
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Подразделение / отдел"
    )
    position: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Должность"
    )
    internal_number: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Внутренний номер (3-4 знака)"
    )
    mobile_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Мобильный номер (+7XXXXXXXXXX или 8XXXXXXXXXX)"
    )
    email: Optional[EmailStr] = Field(
        default=None,
        max_length=255,
        description="Email (опционально)"
    )
    is_active: bool = Field(
        default=True,
        description="Активен ли контакт (для включения в обзвон)"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Произвольный комментарий"
    )
    
    # =========================================================================
    # Валидаторы
    # =========================================================================
    
    @field_validator('mobile_number')
    def validate_mobile_phone(cls, v: Optional[str]) -> Optional[str]:
        """Валидация и нормализация мобильного номера"""
        if v is None or v.strip() == '':
            return None
        
        # Удаляем все пробелы, дефисы, скобки
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        
        # Проверяем форматы
        if re.match(r'^\+7\d{10}$', cleaned):
            return cleaned
        elif re.match(r'^8\d{10}$', cleaned):
            return '+7' + cleaned[1:]
        elif re.match(r'^7\d{10}$', cleaned):
            return '+' + cleaned
        elif re.match(r'^\d{10}$', cleaned):
            return '+7' + cleaned
        else:
            raise ValueError(
                'Неверный формат мобильного номера. '
                'Допустимые форматы: +7XXXXXXXXXX, 8XXXXXXXXXX, 7XXXXXXXXXX, XXXXXXXXXX'
            )
    
    @field_validator('internal_number')
    def validate_internal_number(cls, v: Optional[str]) -> Optional[str]:
        """Валидация внутреннего номера"""
        if v is None or v.strip() == '':
            return None
        
        # Удаляем пробелы и дефисы
        cleaned = re.sub(r'[\s\-]', '', v)
        
        # Проверяем, что номер содержит 3-4 цифры
        if re.match(r'^\d{3,4}$', cleaned):
            return cleaned
        else:
            raise ValueError('Внутренний номер должен содержать 3-4 цифры')
    
    @field_validator('full_name')
    def validate_full_name(cls, v: str) -> str:
        """Валидация ФИО"""
        v = v.strip()
        if len(v) < 2:
            raise ValueError('ФИО должно содержать минимум 2 символа')
        
        # Проверка на недопустимые символы
        if re.search(r'[<>@#$%^&*(){}\[\]\\|]', v):
            raise ValueError('ФИО содержит недопустимые символы')
        
        return v


class ContactCreate(ContactBase):
    """Схема для создания контакта"""
    group_ids: Optional[List[UUID]] = Field(
        default=None,
        description="ID групп, в которые добавить контакт"
    )
    tag_ids: Optional[List[UUID]] = Field(
        default=None,
        description="ID тегов для назначения контакту"
    )
    
    @model_validator(mode='after')
    def check_at_least_one_phone(self):
        """Проверка наличия хотя бы одного номера"""
        if not self.mobile_number and not self.internal_number:
            raise ValueError('Должен быть указан хотя бы один номер: мобильный или внутренний')
        return self


class ContactUpdate(BaseModel):
    """Схема для обновления контакта (все поля опциональны)"""
    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="ФИО"
    )
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Подразделение"
    )
    position: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Должность"
    )
    internal_number: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Внутренний номер"
    )
    mobile_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Мобильный номер"
    )
    email: Optional[EmailStr] = Field(
        default=None,
        max_length=255,
        description="Email"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Активен"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Комментарий"
    )
    
    @field_validator('mobile_number')
    def validate_mobile_phone(cls, v: Optional[str]) -> Optional[str]:
        """Валидация мобильного номера (если передан)"""
        if v is None or v.strip() == '':
            return None
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if re.match(r'^\+7\d{10}$', cleaned):
            return cleaned
        elif re.match(r'^8\d{10}$', cleaned):
            return '+7' + cleaned[1:]
        elif re.match(r'^7\d{10}$', cleaned):
            return '+' + cleaned
        elif re.match(r'^\d{10}$', cleaned):
            return '+7' + cleaned
        else:
            raise ValueError('Неверный формат мобильного номера')
    
    @field_validator('internal_number')
    def validate_internal_number(cls, v: Optional[str]) -> Optional[str]:
        """Валидация внутреннего номера (если передан)"""
        if v is None or v.strip() == '':
            return None
        cleaned = re.sub(r'[\s\-]', '', v)
        if re.match(r'^\d{3,4}$', cleaned):
            return cleaned
        else:
            raise ValueError('Внутренний номер должен содержать 3-4 цифры')


# ============================================================================
# СХЕМЫ ОТВЕТОВ
# ============================================================================

class ContactTagInfo(BaseModel):
    """Информация о теге контакта"""
    id: UUID = Field(..., description="ID тега")
    name: str = Field(..., description="Название тега")
    color: str = Field(default="#95a5a6", description="Цвет тега")
    added_at: Optional[datetime] = Field(None, description="Когда добавлен")
    
    model_config = ConfigDict(from_attributes=True)


class ContactGroupInfo(BaseModel):
    """Информация о группе контакта"""
    id: UUID = Field(..., description="ID группы")
    name: str = Field(..., description="Название группы")
    color: str = Field(default="#3498db", description="Цвет группы")
    added_at: Optional[datetime] = Field(None, description="Когда добавлен")
    role: Optional[str] = Field(None, description="Роль в группе")
    priority: int = Field(default=5, description="Приоритет в группе")
    
    model_config = ConfigDict(from_attributes=True)


class ContactResponse(BaseModel):
    """Схема ответа с данными контакта"""
    id: UUID = Field(..., description="ID контакта")
    full_name: str = Field(..., description="ФИО")
    department: Optional[str] = Field(None, description="Подразделение")
    position: Optional[str] = Field(None, description="Должность")
    internal_number: Optional[str] = Field(None, description="Внутренний номер")
    mobile_number: Optional[str] = Field(None, description="Мобильный номер")
    email: Optional[str] = Field(None, description="Email")
    is_active: bool = Field(..., description="Активен")
    is_archived: bool = Field(default=False, description="В архиве")
    comment: Optional[str] = Field(None, description="Комментарий")
    
    # Связанные данные
    groups: List[ContactGroupInfo] = Field(
        default_factory=list,
        description="Группы, в которых состоит контакт"
    )
    tags: List[ContactTagInfo] = Field(
        default_factory=list,
        description="Теги контакта"
    )
    
    # Вычисляемые поля
    primary_phone: Optional[str] = Field(
        None,
        description="Основной телефон (мобильный или внутренний)"
    )
    has_mobile: bool = Field(default=False, description="Есть мобильный")
    has_internal: bool = Field(default=False, description="Есть внутренний")
    
    # Аудит
    created_by: Optional[UUID] = Field(None, description="Кто создал")
    updated_by: Optional[UUID] = Field(None, description="Кто обновил")
    created_at: Optional[datetime] = Field(None, description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    
    model_config = ConfigDict(from_attributes=True)
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя"""
        parts = [self.full_name]
        if self.department:
            parts.append(f"({self.department})")
        return " ".join(parts)
    
    @property
    def status_badge(self) -> str:
        """Статус для отображения"""
        if self.is_archived:
            return "📦 Архив"
        elif self.is_active:
            return "✅ Активен"
        else:
            return "❌ Неактивен"


class ContactListResponse(BaseModel):
    """Краткая схема контакта для списков"""
    id: UUID = Field(..., description="ID")
    full_name: str = Field(..., description="ФИО")
    department: Optional[str] = Field(None, description="Отдел")
    position: Optional[str] = Field(None, description="Должность")
    mobile_number: Optional[str] = Field(None, description="Мобильный")
    internal_number: Optional[str] = Field(None, description="Внутренний")
    email: Optional[str] = Field(None, description="Email")
    is_active: bool = Field(..., description="Активен")
    
    # Сокращенная информация о группах и тегах
    group_names: List[str] = Field(
        default_factory=list,
        description="Названия групп"
    )
    tag_names: List[str] = Field(
        default_factory=list,
        description="Названия тегов"
    )
    tag_colors: Dict[str, str] = Field(
        default_factory=dict,
        description="Цвета тегов {имя: цвет}"
    )
    
    created_at: Optional[datetime] = Field(None, description="Создан")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# СХЕМЫ ДЛЯ ИМПОРТА/ЭКСПОРТА
# ============================================================================

class ContactImportRow(BaseModel):
    """Схема одной строки импорта"""
    full_name: str = Field(..., description="ФИО")
    department: Optional[str] = Field(None, description="Подразделение")
    position: Optional[str] = Field(None, description="Должность")
    internal_number: Optional[str] = Field(None, description="Внутренний номер")
    mobile_number: Optional[str] = Field(None, description="Мобильный номер")
    email: Optional[str] = Field(None, description="Email")
    comment: Optional[str] = Field(None, description="Комментарий")
    group_names: Optional[str] = Field(
        None,
        description="Группы через запятую (для авто-добавления)"
    )
    is_active: bool = Field(default=True, description="Активен")


class ContactImportRequest(BaseModel):
    """Запрос на импорт контактов"""
    file_format: str = Field(
        default="csv",
        description="Формат файла (csv, xlsx)"
    )
    update_existing: bool = Field(
        default=False,
        description="Обновлять существующие контакты (по мобильному номеру)"
    )
    skip_duplicates: bool = Field(
        default=True,
        description="Пропускать дубликаты"
    )
    default_group_ids: Optional[List[UUID]] = Field(
        default=None,
        description="ID групп для добавления всех импортированных контактов"
    )
    encoding: str = Field(
        default="utf-8",
        description="Кодировка файла"
    )


class ContactExportRequest(BaseModel):
    """Запрос на экспорт контактов"""
    format: str = Field(default="csv", description="Формат (csv, xlsx, json)")
    fields: Optional[List[str]] = Field(
        default=None,
        description="Поля для экспорта (если None — все)"
    )
    group_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Экспортировать только контакты из указанных групп"
    )
    include_archived: bool = Field(default=False, description="Включая архивные")
    encoding: str = Field(default="utf-8", description="Кодировка")


# ============================================================================
# СХЕМЫ ДЛЯ ФИЛЬТРАЦИИ И ПОИСКА
# ============================================================================

class ContactFilterParams(BaseModel):
    """Параметры фильтрации контактов"""
    search: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Поиск по ФИО, отделу, должности, номеру"
    )
    department: Optional[str] = Field(
        default=None,
        description="Фильтр по подразделению"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Фильтр по активности"
    )
    group_id: Optional[UUID] = Field(
        default=None,
        description="Фильтр по ID группы"
    )
    tag_id: Optional[UUID] = Field(
        default=None,
        description="Фильтр по ID тега"
    )
    has_mobile: Optional[bool] = Field(
        default=None,
        description="Только с мобильным номером"
    )
    has_internal: Optional[bool] = Field(
        default=None,
        description="Только с внутренним номером"
    )
    has_email: Optional[bool] = Field(
        default=None,
        description="Только с email"
    )
    created_after: Optional[datetime] = Field(
        default=None,
        description="Создан после"
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Создан до"
    )


# ============================================================================
# СХЕМЫ ДЛЯ МАССОВЫХ ОПЕРАЦИЙ
# ============================================================================

class ContactBulkAction(BaseModel):
    """Запрос на массовое действие с контактами"""
    contact_ids: List[UUID] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="ID контактов (1-1000)"
    )
    action: str = Field(
        ...,
        description="Действие: activate, deactivate, archive, delete, add_to_group, remove_from_group, add_tag, remove_tag"
    )
    group_id: Optional[UUID] = Field(
        default=None,
        description="ID группы (для действий с группой)"
    )
    tag_id: Optional[UUID] = Field(
        default=None,
        description="ID тега (для действий с тегом)"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Причина (для аудита)"
    )
    
    @field_validator('action')
    def validate_action(cls, v: str) -> str:
        """Валидация действия"""
        valid_actions = [
            'activate', 'deactivate', 'archive', 'delete',
            'add_to_group', 'remove_from_group',
            'add_tag', 'remove_tag'
        ]
        if v not in valid_actions:
            raise ValueError(f'Недопустимое действие. Допустимые: {valid_actions}')
        return v


class ContactBulkDelete(BaseModel):
    """Запрос на массовое удаление контактов"""
    contact_ids: List[UUID] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="ID контактов для удаления"
    )
    hard_delete: bool = Field(
        default=False,
        description="Полное удаление (False = архивирование)"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Причина удаления (для аудита)"
    )


# ============================================================================
# СХЕМЫ СТАТИСТИКИ
# ============================================================================

class ContactStats(BaseModel):
    """Статистика по контактам"""
    total: int = Field(..., description="Всего контактов")
    active: int = Field(..., description="Активных")
    inactive: int = Field(..., description="Неактивных")
    archived: int = Field(..., description="В архиве")
    with_mobile: int = Field(..., description="С мобильным")
    with_internal: int = Field(..., description="С внутренним")
    with_both: int = Field(..., description="С обоими номерами")
    with_email: int = Field(..., description="С email")
    without_phone: int = Field(..., description="Без номеров")
    by_department: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="По подразделениям [{department, count}]"
    )
    by_group: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="По группам [{group_name, count}]"
    )


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# Поля контакта для импорта/экспорта
CONTACT_FIELDS = [
    "full_name",
    "department",
    "position",
    "internal_number",
    "mobile_number",
    "email",
    "comment",
    "is_active",
]

# Обязательные поля при импорте
REQUIRED_IMPORT_FIELDS = ["full_name"]

# Поля для поиска (текстовые)
SEARCHABLE_FIELDS = [
    "full_name",
    "department",
    "position",
    "mobile_number",
    "internal_number",
    "email",
]
