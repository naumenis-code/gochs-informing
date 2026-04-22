#!/usr/bin/env python3
"""Audit schemas - ПОЛНАЯ версия со всеми исправлениями"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Any, Dict, Union
from uuid import UUID
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class AuditStatus(str, Enum):
    """Статус события аудита"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"


class AuditAction(str, Enum):
    """Предопределенные типы действий"""
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    TOKEN_REFRESH = "token_refresh"
    
    # CRUD
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    VIEW_DETAILS = "view_details"
    
    # Export/Import
    EXPORT = "export"
    IMPORT = "import"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    
    # Campaign
    START_CAMPAIGN = "start_campaign"
    STOP_CAMPAIGN = "stop_campaign"
    PAUSE_CAMPAIGN = "pause_campaign"
    RESUME_CAMPAIGN = "resume_campaign"
    
    # System
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_RESTART = "system_restart"
    CONFIG_CHANGE = "config_change"
    RELOAD_CONFIG = "reload_config"
    
    # Settings
    GET_SETTINGS = "get_settings"
    UPDATE_SETTINGS = "update_settings"
    RESET_SETTINGS = "reset_settings"
    BACKUP_SETTINGS = "backup_settings"
    RESTORE_SETTINGS = "restore_settings"
    
    # PBX
    PBX_REGISTER = "pbx_register"
    PBX_UNREGISTER = "pbx_unregister"
    PBX_RELOAD = "pbx_reload"
    PBX_TEST = "pbx_test"
    
    # Call
    MAKE_CALL = "make_call"
    RECEIVE_CALL = "receive_call"
    END_CALL = "end_call"
    RECORD_CALL = "record_call"
    
    # Audit
    VIEW_AUDIT = "view_audit"
    EXPORT_AUDIT = "export_audit"
    CLEANUP_AUDIT = "cleanup_audit"
    
    # Other
    EXECUTE = "execute"
    CANCEL = "cancel"
    RETRY = "retry"
    VALIDATE = "validate"
    TEST = "test"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Типы сущностей"""
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    CAMPAIGN = "campaign"
    CONTACT = "contact"
    GROUP = "group"
    SCENARIO = "scenario"
    PLAYBOOK = "playbook"
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    CALL = "call"
    RECORDING = "recording"
    SETTINGS = "settings"
    PBX = "pbx"
    AUDIT = "audit"
    REPORT = "report"
    BACKUP = "backup"
    SYSTEM = "system"
    TTS = "tts"
    STT = "stt"
    NOTIFICATION = "notification"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    """Уровень важности события"""
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class AuditLogBase(BaseModel):
    """Базовая схема аудита"""
    
    # Пользователь
    user_id: Optional[UUID] = Field(None, description="ID пользователя")
    user_name: Optional[str] = Field(None, max_length=255, description="Имя пользователя")
    user_role: Optional[str] = Field(None, max_length=50, description="Роль пользователя")
    
    # Действие
    action: str = Field("unknown", max_length=100, description="Тип действия")
    action_category: Optional[str] = Field(None, max_length=50, description="Категория действия")
    
    # Объект
    entity_type: Optional[str] = Field(None, max_length=50, description="Тип объекта")
    entity_id: Optional[UUID] = Field(None, description="ID объекта")
    entity_name: Optional[str] = Field(None, max_length=255, description="Имя объекта")
    
    # Детали
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")
    changes: Optional[Dict[str, Any]] = Field(None, description="Изменения (до/после)")
    
    # Сетевые данные
    ip_address: Optional[str] = Field(None, max_length=45, description="IP адрес")
    user_agent: Optional[str] = Field(None, description="User-Agent")
    request_method: Optional[str] = Field(None, max_length=10, description="HTTP метод")
    request_path: Optional[str] = Field(None, max_length=500, description="Путь запроса")
    request_id: Optional[str] = Field(None, description="ID запроса (для трассировки)")
    session_id: Optional[str] = Field(None, description="ID сессии")
    
    # Статус
    status: AuditStatus = Field(AuditStatus.SUCCESS, description="Статус")
    severity: SeverityLevel = Field(SeverityLevel.INFO, description="Уровень важности")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    error_code: Optional[str] = Field(None, max_length=50, description="Код ошибки")
    
    # Производительность
    execution_time_ms: Optional[int] = Field(None, ge=0, description="Время выполнения (мс)")
    
    # Дополнительно
    tags: Optional[List[str]] = Field(None, description="Теги для фильтрации")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные")
    
    model_config = ConfigDict(
        use_enum_values=True,
        extra="ignore"
    )


class AuditLogCreate(AuditLogBase):
    """Схема для создания записи аудита"""
    pass


class AuditLogUpdate(BaseModel):
    """Схема для обновления записи аудита"""
    status: Optional[AuditStatus] = None
    severity: Optional[SeverityLevel] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(use_enum_values=True)


class AuditLogResponse(AuditLogBase):
    """Схема для ответа с записью аудита"""
    id: UUID = Field(..., description="ID записи")
    created_at: datetime = Field(..., description="Дата создания")
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    @field_validator('created_at', mode='before')
    @classmethod
    def validate_created_at(cls, v: Any) -> Any:
        """Преобразование datetime в ISO формат если нужно"""
        if isinstance(v, datetime):
            return v.isoformat()
        return v


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class AuditStatsResponse(BaseModel):
    """Схема расширенной статистики аудита"""
    
    # Общие метрики
    total_events: int = Field(0, description="Всего событий")
    today_events: int = Field(0, description="Событий за сегодня")
    week_events: int = Field(0, description="Событий за неделю")
    month_events: int = Field(0, description="Событий за месяц")
    year_events: int = Field(0, description="Событий за год")
    
    # Уникальные значения
    unique_users: int = Field(0, description="Уникальных пользователей")
    unique_ips: int = Field(0, description="Уникальных IP адресов")
    unique_actions: int = Field(0, description="Уникальных действий")
    unique_entities: int = Field(0, description="Уникальных типов сущностей")
    
    # Статусы
    success_events: int = Field(0, description="Успешных событий")
    warning_events: int = Field(0, description="Предупреждений")
    error_events: int = Field(0, description="Ошибок")
    pending_events: int = Field(0, description="В ожидании")
    in_progress_events: int = Field(0, description="В процессе")
    cancelled_events: int = Field(0, description="Отменено")
    
    # Топы
    top_actions: List[Dict[str, Any]] = Field([], description="Топ действий")
    top_entities: List[Dict[str, Any]] = Field([], description="Топ сущностей")
    top_users: List[Dict[str, Any]] = Field([], description="Топ пользователей")
    top_ips: List[Dict[str, Any]] = Field([], description="Топ IP адресов")
    top_errors: List[Dict[str, Any]] = Field([], description="Топ ошибок")
    
    # Временные ряды
    hourly_stats: List[Dict[str, Any]] = Field([], description="Почасовая статистика")
    daily_stats: List[Dict[str, Any]] = Field([], description="Дневная статистика")
    weekly_stats: List[Dict[str, Any]] = Field([], description="Недельная статистика")
    monthly_stats: List[Dict[str, Any]] = Field([], description="Месячная статистика")
    
    # Последняя активность
    recent_activity: List[Dict[str, Any]] = Field([], description="Последняя активность")
    recent_errors: List[Dict[str, Any]] = Field([], description="Последние ошибки")
    
    # Производительность
    avg_execution_time_ms: float = Field(0.0, description="Среднее время выполнения (мс)")
    max_execution_time_ms: int = Field(0, description="Макс. время выполнения (мс)")
    min_execution_time_ms: int = Field(0, description="Мин. время выполнения (мс)")
    
    model_config = ConfigDict(extra="ignore")


class DailyStatsResponse(BaseModel):
    """Схема дневной статистики"""
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")
    total: int = Field(0, description="Всего событий")
    success: int = Field(0, description="Успешных")
    warnings: int = Field(0, description="Предупреждений")
    errors: int = Field(0, description="Ошибок")
    unique_users: int = Field(0, description="Уникальных пользователей")
    avg_execution_time_ms: float = Field(0.0, description="Среднее время выполнения")
    
    model_config = ConfigDict(extra="ignore")


class HourlyStatsResponse(BaseModel):
    """Схема почасовой статистики"""
    hour: int = Field(..., ge=0, le=23, description="Час (0-23)")
    count: int = Field(0, description="Количество событий")
    
    model_config = ConfigDict(extra="ignore")


class UserActivityResponse(BaseModel):
    """Схема активности пользователя"""
    user_id: Optional[str] = Field(None, description="ID пользователя")
    user_name: str = Field(..., description="Имя пользователя")
    user_role: Optional[str] = Field(None, description="Роль пользователя")
    
    # Статистика
    total_actions: int = Field(0, description="Всего действий")
    success_actions: int = Field(0, description="Успешных действий")
    error_actions: int = Field(0, description="Действий с ошибками")
    
    # Временные метки
    first_action: Optional[str] = Field(None, description="Первое действие")
    last_action: Optional[str] = Field(None, description="Последнее действие")
    
    # Детализация
    actions_by_type: Dict[str, int] = Field({}, description="Действия по типам")
    actions_by_entity: Dict[str, int] = Field({}, description="Действия по сущностям")
    actions_by_status: Dict[str, int] = Field({}, description="Действия по статусам")
    
    # IP адреса
    ip_addresses: List[str] = Field([], description="Используемые IP адреса")
    
    # Последние записи
    recent_logs: List[AuditLogResponse] = Field([], description="Последние записи")
    
    model_config = ConfigDict(extra="ignore")


class EntityStatsResponse(BaseModel):
    """Схема статистики по сущности"""
    entity_type: str = Field(..., description="Тип сущности")
    entity_id: Optional[str] = Field(None, description="ID сущности")
    entity_name: Optional[str] = Field(None, description="Имя сущности")
    total_events: int = Field(0, description="Всего событий")
    last_event: Optional[str] = Field(None, description="Последнее событие")
    actions: Dict[str, int] = Field({}, description="Действия")
    users: List[str] = Field([], description="Пользователи")
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# FILTER SCHEMAS
# ============================================================================

class AuditLogFilterParams(BaseModel):
    """Параметры фильтрации аудита"""
    
    # Основные фильтры
    action: Optional[str] = Field(None, description="Фильтр по действию")
    action_category: Optional[str] = Field(None, description="Фильтр по категории действия")
    entity_type: Optional[str] = Field(None, description="Фильтр по типу сущности")
    entity_id: Optional[UUID] = Field(None, description="Фильтр по ID сущности")
    
    # Пользователь
    user_id: Optional[UUID] = Field(None, description="Фильтр по ID пользователя")
    user_name: Optional[str] = Field(None, description="Фильтр по имени пользователя")
    user_role: Optional[str] = Field(None, description="Фильтр по роли пользователя")
    
    # Статус и важность
    status: Optional[AuditStatus] = Field(None, description="Фильтр по статусу")
    severity: Optional[SeverityLevel] = Field(None, description="Фильтр по уровню важности")
    
    # Даты
    start_date: Optional[datetime] = Field(None, description="Начальная дата")
    end_date: Optional[datetime] = Field(None, description="Конечная дата")
    
    # Сеть
    ip_address: Optional[str] = Field(None, description="Фильтр по IP адресу")
    
    # Ошибки
    has_error: Optional[bool] = Field(None, description="Только с ошибками")
    error_code: Optional[str] = Field(None, description="Фильтр по коду ошибки")
    
    # Теги
    tags: Optional[List[str]] = Field(None, description="Фильтр по тегам")
    
    # Поиск
    search: Optional[str] = Field(None, description="Поиск по всем текстовым полям")
    
    model_config = ConfigDict(use_enum_values=True, extra="ignore")


class AuditLogListResponse(BaseModel):
    """Схема списка записей аудита с пагинацией"""
    items: List[AuditLogResponse] = Field([], description="Список записей")
    total: int = Field(0, description="Общее количество")
    page: int = Field(1, ge=1, description="Текущая страница")
    page_size: int = Field(100, ge=1, le=1000, description="Размер страницы")
    total_pages: int = Field(0, description="Всего страниц")
    has_next: bool = Field(False, description="Есть ли следующая страница")
    has_prev: bool = Field(False, description="Есть ли предыдущая страница")
    
    # Дополнительная информация
    filters_applied: Optional[AuditLogFilterParams] = Field(None, description="Примененные фильтры")
    
    model_config = ConfigDict(extra="ignore")
    
    @field_validator('total_pages', mode='before')
    @classmethod
    def calculate_total_pages(cls, v: Any, info: Any) -> int:
        """Автоматический расчет количества страниц"""
        if v:
            return v
        data = info.data
        if data.get('page_size') and data.get('total'):
            return (data['total'] + data['page_size'] - 1) // data['page_size']
        return 0


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ClearOldLogsResponse(BaseModel):
    """Схема ответа при очистке старых логов"""
    message: str = Field("", description="Сообщение")
    deleted_count: int = Field(0, description="Количество удаленных записей")
    older_than_days: int = Field(0, description="Старше (дней)")
    cutoff_date: Optional[str] = Field(None, description="Дата отсечки")
    entity_type: Optional[str] = Field(None, description="Тип сущности (если указан)")
    execution_time_ms: Optional[int] = Field(None, description="Время выполнения (мс)")
    
    model_config = ConfigDict(extra="ignore")


class ExportAuditResponse(BaseModel):
    """Схема ответа при экспорте аудита"""
    filename: str = Field(..., description="Имя файла")
    total_records: int = Field(0, description="Количество записей")
    file_size_bytes: Optional[int] = Field(None, description="Размер файла в байтах")
    filters_applied: Optional[AuditLogFilterParams] = Field(None, description="Примененные фильтры")
    
    model_config = ConfigDict(extra="ignore")


class AuditSummaryResponse(BaseModel):
    """Схема сводки аудита"""
    period: str = Field(..., description="Период (today/week/month/year)")
    start_date: str = Field(..., description="Начало периода")
    end_date: str = Field(..., description="Конец периода")
    stats: AuditStatsResponse = Field(..., description="Статистика")
    
    model_config = ConfigDict(extra="ignore")


class AuditHealthResponse(BaseModel):
    """Схема проверки здоровья аудита"""
    table_exists: bool = Field(..., description="Существует ли таблица")
    record_count: int = Field(0, description="Количество записей")
    last_record_at: Optional[str] = Field(None, description="Последняя запись")
    indexes_exist: bool = Field(True, description="Существуют ли индексы")
    status: str = Field("healthy", description="Статус")
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# BATCH SCHEMAS
# ============================================================================

class AuditLogBatchCreate(BaseModel):
    """Схема для пакетного создания записей аудита"""
    logs: List[AuditLogCreate] = Field(..., min_length=1, max_length=1000, description="Список записей")
    
    model_config = ConfigDict(extra="ignore")


class AuditLogBatchResponse(BaseModel):
    """Схема ответа при пакетном создании"""
    success: bool = Field(..., description="Успешно ли")
    created_count: int = Field(0, description="Создано записей")
    failed_count: int = Field(0, description="Не создано записей")
    errors: List[str] = Field([], description="Ошибки")
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Enums
    "AuditStatus",
    "AuditAction",
    "EntityType",
    "SeverityLevel",
    
    # Base
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogUpdate",
    "AuditLogResponse",
    
    # Stats
    "AuditStatsResponse",
    "DailyStatsResponse",
    "HourlyStatsResponse",
    "UserActivityResponse",
    "EntityStatsResponse",
    
    # Filter
    "AuditLogFilterParams",
    "AuditLogListResponse",
    
    # Response
    "ClearOldLogsResponse",
    "ExportAuditResponse",
    "AuditSummaryResponse",
    "AuditHealthResponse",
    
    # Batch
    "AuditLogBatchCreate",
    "AuditLogBatchResponse"
]
