#!/usr/bin/env python3
"""Settings schemas - ПОЛНАЯ ВЕРСИЯ ВСЕХ СХЕМ НАСТРОЕК"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class TransportType(str, Enum):
    """Тип транспорта для SIP"""
    UDP = "udp"
    TCP = "tcp"
    TLS = "tls"
    WS = "ws"
    WSS = "wss"


class LogLevel(str, Enum):
    """Уровень логирования"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Timezone(str, Enum):
    """Часовые пояса"""
    MOSCOW = "Europe/Moscow"
    LONDON = "Europe/London"
    BERLIN = "Europe/Berlin"
    NEW_YORK = "America/New_York"
    LOS_ANGELES = "America/Los_Angeles"
    TOKYO = "Asia/Tokyo"
    DUBAI = "Asia/Dubai"
    UTC = "UTC"


class CodecType(str, Enum):
    """Типы кодеков"""
    ULAW = "ulaw"
    ALAW = "alaw"
    G729 = "g729"
    G722 = "g722"
    OPUS = "opus"
    GSM = "gsm"
    SPEEX = "speex"


class RegistrationStatus(str, Enum):
    """Статус регистрации"""
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    FAILED = "failed"
    UNKNOWN = "unknown"


# ============================================================================
# PBX SETTINGS
# ============================================================================

class PBXSettings(BaseModel):
    """Настройки FreePBX"""
    host: str = Field("192.168.1.10", description="IP адрес FreePBX")
    port: int = Field(5060, ge=1, le=65535, description="Порт SIP")
    extension: str = Field("gochs", min_length=1, max_length=20, description="Внутренний номер")
    username: str = Field("gochs", min_length=1, max_length=50, description="Логин")
    password: str = Field("", description="Пароль")
    transport: str = Field("udp", description="Транспорт")
    max_channels: int = Field(20, ge=1, le=100, description="Максимум каналов")
    codecs: List[str] = Field(["ulaw", "alaw"], description="Кодеки")
    register_enabled: bool = Field(True, description="Включить регистрацию")


class PBXSettingsUpdate(BaseModel):
    """Обновление настроек FreePBX"""
    host: Optional[str] = Field(None, description="IP адрес FreePBX")
    port: Optional[int] = Field(None, ge=1, le=65535)
    extension: Optional[str] = Field(None, min_length=1, max_length=20)
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    password: Optional[str] = Field(None)
    transport: Optional[str] = Field(None)
    max_channels: Optional[int] = Field(None, ge=1, le=100)
    codecs: Optional[List[str]] = Field(None)
    register_enabled: Optional[bool] = Field(None)


class PBXSettingsResponse(BaseModel):
    """Ответ с настройками FreePBX"""
    host: str
    port: int
    extension: str
    username: str
    password: str = Field("", description="Пароль (скрыт)")
    transport: str = "udp"
    max_channels: int = 20
    codecs: List[str] = ["ulaw", "alaw"]
    register_enabled: bool = True


class PBXStatusResponse(BaseModel):
    """Статус регистрации в FreePBX"""
    registered: bool = Field(False, description="Зарегистрирован ли")
    message: str = Field("", description="Сообщение")
    host: Optional[str] = Field(None, description="Хост")
    port: Optional[int] = Field(None, description="Порт")
    extension: Optional[str] = Field(None, description="Extension")


class PBXTestResponse(BaseModel):
    """Результат тестирования подключения"""
    success: bool = Field(False, description="Успешно ли")
    message: str = Field("", description="Сообщение")
    error: Optional[str] = Field(None, description="Ошибка")


class PBXReloadResponse(BaseModel):
    """Ответ при перезагрузке PJSIP"""
    message: str = Field("", description="Сообщение")
    success: bool = Field(True, description="Успешно ли")


class PBXApplyResponse(BaseModel):
    """Ответ при применении настроек"""
    message: str = Field("", description="Сообщение")
    config_updated: bool = Field(False, description="Конфиг обновлен")
    registration_status: Optional[PBXStatusResponse] = Field(None, description="Статус регистрации")


# ============================================================================
# SYSTEM SETTINGS
# ============================================================================

class SystemSettings(BaseModel):
    """Системные настройки"""
    app_name: str = Field("ГО-ЧС Информирование", min_length=1, max_length=100, description="Название системы")
    timezone: str = Field("Europe/Moscow", description="Часовой пояс")
    log_level: str = Field("INFO", description="Уровень логирования")
    max_concurrent_calls: int = Field(20, ge=1, le=100, description="Максимум звонков")
    recording_retention_days: int = Field(90, ge=1, le=365, description="Хранить записи (дней)")
    backup_enabled: bool = Field(True, description="Авто-бэкап")
    backup_time: str = Field("02:00", description="Время бэкапа")


class SystemSettingsUpdate(BaseModel):
    """Обновление системных настроек"""
    app_name: Optional[str] = Field(None, min_length=1, max_length=100)
    timezone: Optional[str] = Field(None)
    log_level: Optional[str] = Field(None)
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=100)
    recording_retention_days: Optional[int] = Field(None, ge=1, le=365)
    backup_enabled: Optional[bool] = Field(None)
    backup_time: Optional[str] = Field(None)


class SystemSettingsResponse(BaseModel):
    """Ответ с системными настройками"""
    app_name: str
    timezone: str
    log_level: str
    max_concurrent_calls: int
    recording_retention_days: int
    backup_enabled: bool
    backup_time: str


# ============================================================================
# SECURITY SETTINGS
# ============================================================================

class SecuritySettings(BaseModel):
    """Настройки безопасности"""
    jwt_expire_minutes: int = Field(60, ge=5, le=1440, description="Срок JWT (минут)")
    refresh_token_expire_days: int = Field(7, ge=1, le=30, description="Срок Refresh (дней)")
    max_login_attempts: int = Field(5, ge=3, le=10, description="Макс. попыток входа")
    lockout_minutes: int = Field(15, ge=5, le=60, description="Блокировка (минут)")
    password_min_length: int = Field(8, ge=6, le=32, description="Мин. длина пароля")
    require_special_chars: bool = Field(True, description="Требовать спецсимволы")
    session_timeout_minutes: int = Field(30, ge=5, le=480, description="Таймаут сессии")


class SecuritySettingsUpdate(BaseModel):
    """Обновление настроек безопасности"""
    jwt_expire_minutes: Optional[int] = Field(None, ge=5, le=1440)
    refresh_token_expire_days: Optional[int] = Field(None, ge=1, le=30)
    max_login_attempts: Optional[int] = Field(None, ge=3, le=10)
    lockout_minutes: Optional[int] = Field(None, ge=5, le=60)
    password_min_length: Optional[int] = Field(None, ge=6, le=32)
    require_special_chars: Optional[bool] = Field(None)
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=480)


class SecuritySettingsResponse(BaseModel):
    """Ответ с настройками безопасности"""
    jwt_expire_minutes: int
    refresh_token_expire_days: int
    max_login_attempts: int
    lockout_minutes: int
    password_min_length: int
    require_special_chars: bool
    session_timeout_minutes: int


# ============================================================================
# NOTIFICATION SETTINGS
# ============================================================================

class NotificationSettings(BaseModel):
    """Настройки уведомлений"""
    email_enabled: bool = Field(False, description="Включить Email")
    smtp_server: str = Field("", description="SMTP сервер")
    smtp_port: int = Field(587, ge=1, le=65535, description="SMTP порт")
    smtp_username: str = Field("", description="SMTP пользователь")
    smtp_password: str = Field("", description="SMTP пароль")
    from_email: str = Field("", description="От кого")
    admin_email: str = Field("", description="Email администратора")
    notify_on_campaign_complete: bool = Field(True, description="При завершении кампании")
    notify_on_system_error: bool = Field(True, description="При ошибке системы")


class NotificationSettingsUpdate(BaseModel):
    """Обновление настроек уведомлений"""
    email_enabled: Optional[bool] = Field(None)
    smtp_server: Optional[str] = Field(None)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_username: Optional[str] = Field(None)
    smtp_password: Optional[str] = Field(None)
    from_email: Optional[str] = Field(None)
    admin_email: Optional[str] = Field(None)
    notify_on_campaign_complete: Optional[bool] = Field(None)
    notify_on_system_error: Optional[bool] = Field(None)


class NotificationSettingsResponse(BaseModel):
    """Ответ с настройками уведомлений"""
    email_enabled: bool
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str = Field("", description="Пароль (скрыт)")
    from_email: str
    admin_email: str
    notify_on_campaign_complete: bool
    notify_on_system_error: bool


# ============================================================================
# ALL SETTINGS
# ============================================================================

class AllSettingsResponse(BaseModel):
    """Все настройки системы"""
    pbx: PBXSettingsResponse
    system: SystemSettingsResponse
    security: SecuritySettingsResponse
    notifications: NotificationSettingsResponse


# ============================================================================
# CREDENTIALS
# ============================================================================

class FreepbxCredentialInfo(BaseModel):
    """Информация об учетных данных FreePBX"""
    host: str = ""
    port: int = 5060
    extension: str = ""
    has_password: bool = False


class PostgresqlCredentialInfo(BaseModel):
    """Информация об учетных данных PostgreSQL"""
    database: str = ""
    user: str = ""
    has_password: bool = False


class RedisCredentialInfo(BaseModel):
    """Информация об учетных данных Redis"""
    has_password: bool = False


class AsteriskCredentialInfo(BaseModel):
    """Информация об учетных данных Asterisk"""
    ami_user: str = ""
    has_ami_password: bool = False
    has_ari_password: bool = False


class CredentialsInfoResponse(BaseModel):
    """Информация об учетных данных (без паролей)"""
    freepbx: FreepbxCredentialInfo = Field(default_factory=FreepbxCredentialInfo)
    postgresql: PostgresqlCredentialInfo = Field(default_factory=PostgresqlCredentialInfo)
    redis: RedisCredentialInfo = Field(default_factory=RedisCredentialInfo)
    asterisk: AsteriskCredentialInfo = Field(default_factory=AsteriskCredentialInfo)


# ============================================================================
# BACKUP
# ============================================================================

class BackupResponse(BaseModel):
    """Ответ при создании бэкапа"""
    message: str = Field("", description="Сообщение")
    backup_file: str = Field("", description="Файл бэкапа")
    timestamp: str = Field("", description="Временная метка")


class BackupListItem(BaseModel):
    """Элемент списка бэкапов"""
    name: str = Field(..., description="Имя файла")
    size: int = Field(..., description="Размер в байтах")
    created: str = Field(..., description="Дата создания")
    path: str = Field(..., description="Полный путь")


class BackupsListResponse(BaseModel):
    """Список бэкапов"""
    backups: List[BackupListItem] = Field([], description="Список бэкапов")


# ============================================================================
# RESET
# ============================================================================

class ResetSettingsResponse(BaseModel):
    """Ответ при сбросе настроек"""
    message: str = Field("", description="Сообщение")
    success: bool = Field(False, description="Успешно ли")


# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Enums
    "TransportType",
    "LogLevel",
    "Timezone",
    "CodecType",
    "RegistrationStatus",
    
    # PBX
    "PBXSettings",
    "PBXSettingsUpdate",
    "PBXSettingsResponse",
    "PBXStatusResponse",
    "PBXTestResponse",
    "PBXReloadResponse",
    "PBXApplyResponse",
    
    # System
    "SystemSettings",
    "SystemSettingsUpdate",
    "SystemSettingsResponse",
    
    # Security
    "SecuritySettings",
    "SecuritySettingsUpdate",
    "SecuritySettingsResponse",
    
    # Notifications
    "NotificationSettings",
    "NotificationSettingsUpdate",
    "NotificationSettingsResponse",
    
    # All
    "AllSettingsResponse",
    
    # Credentials
    "FreepbxCredentialInfo",
    "PostgresqlCredentialInfo",
    "RedisCredentialInfo",
    "AsteriskCredentialInfo",
    "CredentialsInfoResponse",
    
    # Backup
    "BackupResponse",
    "BackupListItem",
    "BackupsListResponse",
    
    # Reset
    "ResetSettingsResponse",
]
