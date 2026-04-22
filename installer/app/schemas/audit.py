#!/usr/bin/env python3
"""Audit schemas - исправленная рабочая версия"""

from pydantic import BaseModel, ConfigDict
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
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str = ""
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    entity_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    status: AuditStatus = AuditStatus.SUCCESS
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class AuditLogCreate(AuditLogBase):
    """Схема для создания записи аудита"""
    pass


class AuditLogUpdate(BaseModel):
    """Схема для обновления записи аудита"""
    status: Optional[AuditStatus] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class AuditLogResponse(AuditLogBase):
    """Схема для ответа с записью аудита"""
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# СХЕМЫ ДЛЯ СТАТИСТИКИ
# ============================================================================

class AuditStatsResponse(BaseModel):
    """Схема статистики аудита"""
    total_events: int = 0
    today_events: int = 0
    week_events: int = 0
    month_events: int = 0
    unique_users: int = 0
    error_events: int = 0
    warning_events: int = 0
    top_actions: List[Dict[str, Any]] = []
    top_entities: List[Dict[str, Any]] = []
    top_users: List[Dict[str, Any]] = []
    recent_activity: List[Dict[str, Any]] = []
    hourly_stats: List[Dict[str, Any]] = []


class DailyStatsResponse(BaseModel):
    """Схема дневной статистики"""
    date: str
    total: int = 0
    success: int = 0
    warnings: int = 0
    errors: int = 0


class UserActivityResponse(BaseModel):
    """Схема активности пользователя"""
    user_id: str
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    total_actions: int = 0
    first_action: Optional[str] = None
    last_action: Optional[str] = None
    actions_by_type: Dict[str, int] = {}
    actions_by_entity: Dict[str, int] = {}
    recent_logs: List[AuditLogResponse] = []


# ============================================================================
# СХЕМЫ ДЛЯ ЗАПРОСОВ
# ============================================================================

class AuditLogFilterParams(BaseModel):
    """Параметры фильтрации аудита"""
    action: Optional[str] = None
    entity_type: Optional[str] = None
    user_name: Optional[str] = None
    user_id: Optional[UUID] = None
    status: Optional[AuditStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None


class AuditLogListResponse(BaseModel):
    """Схема списка записей аудита"""
    items: List[AuditLogResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 100
    has_next: bool = False
    has_prev: bool = False


class ClearOldLogsResponse(BaseModel):
    """Схема ответа при очистке старых логов"""
    message: str = ""
    deleted_count: int = 0
    older_than_days: int = 0
    cutoff_date: Optional[str] = None
