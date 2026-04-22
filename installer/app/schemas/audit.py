#!/usr/bin/env python3
"""Audit schemas - полная версия"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime
from enum import Enum


class AuditStatus(str, Enum):
    """Статус события аудита"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class AuditAction(str, Enum):
    """Предопределенные типы действий"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"
    LOGIN = "login"
    LOGOUT = "logout"
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    EXECUTE = "execute"
    CANCEL = "cancel"
    RELOAD = "reload"
    TEST = "test"
    BACKUP = "backup"
    RESTORE = "restore"


class EntityType(str, Enum):
    """Типы сущностей"""
    USER = "user"
    CAMPAIGN = "campaign"
    CONTACT = "contact"
    GROUP = "group"
    SCENARIO = "scenario"
    PLAYBOOK = "playbook"
    INBOUND = "inbound"
    SETTINGS = "settings"
    AUDIT = "audit"
    REPORT = "report"
    BACKUP = "backup"
    SYSTEM = "system"


# ============================================================================
# БАЗОВЫЕ СХЕМЫ
# ============================================================================

class AuditLogBase(BaseModel):
    """Базовая схема аудита"""
    user_id: Optional[UUID] = Field(None, description="ID пользователя")
    user_name: Optional[str] = Field(None, max_length=255, description="Имя пользователя")
    user_role: Optional[str] = Field(None, max_length=50, description="Роль пользователя")
    action: str = Field(..., max_length=100, description="Тип действия")
    entity_type: Optional[str] = Field(None, max_length=50, description="Тип объекта")
    entity_id: Optional[UUID] = Field(None, description="ID объекта")
    entity_name: Optional[str] = Field(None, max_length=255, description="Имя объекта")
    details: Optional[Dict[str, Any]] = Field(None, description="Детали")
    ip_address: Optional[str] = Field(None, max_length=45, description="IP адрес")
    user_agent: Optional[str] = Field(None, description="User-Agent")
    request_method: Optional[str] = Field(None, max_length=10, description="HTTP метод")
    request_path: Optional[str] = Field(None, max_length=500, description="Путь запроса")
    status: AuditStatus = Field(AuditStatus.SUCCESS, description="Статус")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    execution_time_ms: Optional[int] = Field(None, ge=0, description="Время выполнения (мс)")


class AuditLogCreate(AuditLogBase):
    """Схема для создания записи аудита"""
    pass


class AuditLogUpdate(BaseModel):
    """Схема для обновления записи аудита"""
    status: Optional[AuditStatus] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = Field(None, ge=0)


class AuditLogResponse(AuditLogBase):
    """Схема для ответа с записью аудита"""
    id: UUID = Field(..., description="ID записи")
    created_at: datetime = Field(..., description="Дата создания")
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('created_at', mode='before')
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v


# ============================================================================
# СХЕМЫ ДЛЯ СТАТИСТИКИ
# ============================================================================

class AuditStatsResponse(BaseModel):
    """Схема статистики аудита"""
    total_events: int = Field(..., description="Всего событий")
    today_events: int = Field(..., description="Событий за сегодня")
    week_events: int = Field(..., description="Событий за неделю")
    month_events: int = Field(..., description="Событий за месяц", default=0)
    unique_users: int = Field(..., description="Уникальных пользователей")
    error_events: int = Field(..., description="Событий с ошибками")
    warning_events: int = Field(..., description="Событий с предупреждениями")
    top_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Топ действий")
    top_entities: List[Dict[str, Any]] = Field(default_factory=list, description="Топ сущностей")
    top_users: List[Dict[str, Any]] = Field(default_factory=list, description="Топ пользователей")
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Последняя активность")
    hourly_stats: List[Dict[str, Any]] = Field(default_factory=list, description="Почасовая статистика")


class DailyStatsResponse(BaseModel):
    """Схема дневной статистики"""
    date: str = Field(..., description="Дата")
    total: int = Field(..., description="Всего событий")
    success: int = Field(..., description="Успешных")
    warnings: int = Field(..., description="Предупреждений")
    errors: int = Field(..., description="Ошибок")


class UserActivityResponse(BaseModel):
    """Схема активности пользователя"""
    user_id: str = Field(..., description="ID пользователя")
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    user_role: Optional[str] = Field(None, description="Роль")
    total_actions: int = Field(..., description="Всего действий")
    first_action: Optional[str] = Field(None, description="Первое действие")
    last_action: Optional[str] = Field(None, description="Последнее действие")
    actions_by_type: Dict[str, int] = Field(default_factory=dict, description="Действия по типам")
    actions_by_entity: Dict[str, int] = Field(default_factory=dict, description="Действия по сущностям")
    recent_logs: List[AuditLogResponse] = Field(default_factory=list, description="Последние записи")


# ============================================================================
# СХЕМЫ ДЛЯ ЗАПРОСОВ
# ============================================================================

class AuditLogFilterParams(BaseModel):
    """Параметры фильтрации аудита"""
    action: Optional[str] = Field(None, description="Фильтр по действию")
    entity_type: Optional[str] = Field(None, description="Фильтр по типу сущности")
    user_name: Optional[str] = Field(None, description="Фильтр по имени пользователя")
    user_id: Optional[UUID] = Field(None, description="Фильтр по ID пользователя")
    status: Optional[AuditStatus] = Field(None, description="Фильтр по статусу")
    start_date: Optional[datetime] = Field(None, description="Начальная дата")
    end_date: Optional[datetime] = Field(None, description="Конечная дата")
    ip_address: Optional[str] = Field(None, description="Фильтр по IP")


class AuditLogListResponse(BaseModel):
    """Схема списка записей аудита"""
    items: List[AuditLogResponse] = Field(..., description="Список записей")
    total: int = Field(..., description="Общее количество")
    page: int = Field(1, description="Текущая страница")
    page_size: int = Field(100, description="Размер страницы")
    has_next: bool = Field(False, description="Есть ли следующая страница")
    has_prev: bool = Field(False, description="Есть ли предыдущая страница")


class ClearOldLogsResponse(BaseModel):
    """Схема ответа при очистке старых логов"""
    message: str = Field(..., description="Сообщение")
    deleted_count: int = Field(..., description="Количество удаленных записей")
    older_than_days: int = Field(..., description="Старше (дней)")
    cutoff_date: str = Field(..., description="Дата отсечки")
