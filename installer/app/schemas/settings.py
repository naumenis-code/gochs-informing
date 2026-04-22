#!/usr/bin/env python3
"""Settings schemas - ПОЛНАЯ версия со всеми исправлениями и дополнениями"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Any, Dict, Union
from enum import Enum
from datetime import datetime


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
    SHANGHAI = "Asia/Shanghai"
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
    H264 = "h264"
    VP8 = "vp8"


class AuthMethod(str, Enum):
    """Методы аутентификации"""
    PASSWORD = "password"
    MD5 = "md5"
    SHA256 = "sha256"
    SHA512 = "sha512"


class BackupType(str, Enum):
    """Типы резервного копирования"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SETTINGS_ONLY = "settings_only"
    DATABASE_ONLY = "database_only"
    RECORDINGS_ONLY = "recordings_only"


class BackupStatus(str, Enum):
    """Статус резервного копирования"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationType(str, Enum):
    """Типы уведомлений"""
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"


class NotificationPriority(str, Enum):
    """Приоритет уведомлений"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RegistrationStatus(str, Enum):
    """Статус регистрации"""
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ConnectionTestResult(str, Enum):
    """Результат теста подключения"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REFUSED = "refused"
    UNKNOWN = "unknown"


# ============================================================================
# PBX SETTINGS
# ============================================================================

class PBXSettings(BaseModel):
    """Настройки FreePBX / Asterisk"""
    
    # Основные настройки
    host: str = Field("192.168.1.10", description="IP адрес или домен FreePBX")
    port: int = Field(5060, ge=1, le=65535, description="Порт SIP")
    extension: str = Field("gochs", min_length=1, max_length=20, description="Внутренний номер")
    username: str = Field("gochs", min_length=1, max_length=50, description="Логин")
    password: str = Field("", description="Пароль")
    
    # Транспорт и кодеки
    transport: TransportType = Field(TransportType.UDP, description="Транспорт")
    codecs: List[CodecType] = Field([CodecType.ULAW, CodecType.ALAW], description="Кодеки в порядке приоритета")
    
    # Лимиты
    max_channels: int = Field(20, ge=1, le=500, description="Максимум одновременных каналов")
    max_retries: int = Field(3, ge=1, le=10, description="Максимум повторных попыток")
    retry_interval: int = Field(300, ge=30, le=3600, description="Интервал повторов (сек)")
    
    # Таймауты
    call_timeout: int = Field(40, ge=10, le=300, description="Таймаут звонка (сек)")
    register_timeout: int = Field(30, ge=10, le=120, description="Таймаут регистрации (сек)")
    keepalive_interval: int = Field(30, ge=10, le=300, description="Интервал keepalive (сек)")
    
    # Безопасность
    use_srtp: bool = Field(False, description="Использовать SRTP")
    use_tls_verify: bool = Field(False, description="Проверять TLS сертификат")
    allow_guest: bool = Field(False, description="Разрешить гостевые звонки")
    
    # Регистрация
    register_enabled: bool = Field(True, description="Включить регистрацию")
    register_on_startup: bool = Field(True, description="Регистрироваться при запуске")
    
    # Дополнительно
    context: str = Field("gochs-inbound", description="Контекст для входящих")
    caller_id: str = Field("ГО-ЧС", max_length=50, description="Caller ID")
    nat_mode: str = Field("auto", description="Режим NAT (auto/force/disable)")
    
    model_config = ConfigDict(use_enum_values=True)


class PBXSettingsUpdate(BaseModel):
    """Обновление настроек FreePBX"""
    host: Optional[str] = Field(None, description="IP адрес или домен")
    port: Optional[int] = Field(None, ge=1, le=65535)
    extension: Optional[str] = Field(None, min_length=1, max_length=20)
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    password: Optional[str] = Field(None)
    transport: Optional[TransportType] = None
    codecs: Optional[List[CodecType]] = None
    max_channels: Optional[int] = Field(None, ge=1, le=500)
    max_retries: Optional[int] = Field(None, ge=1, le=10)
    retry_interval: Optional[int] = Field(None, ge=30, le=3600)
    call_timeout: Optional[int] = Field(None, ge=10, le=300)
    register_timeout: Optional[int] = Field(None, ge=10, le=120)
    keepalive_interval: Optional[int] = Field(None, ge=10, le=300)
    use_srtp: Optional[bool] = None
    use_tls_verify: Optional[bool] = None
    allow_guest: Optional[bool] = None
    register_enabled: Optional[bool] = None
    register_on_startup: Optional[bool] = None
    context: Optional[str] = None
    caller_id: Optional[str] = Field(None, max_length=50)
    nat_mode: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True)


class PBXSettingsResponse(BaseModel):
    """Ответ с настройками FreePBX"""
    host: str
    port: int
    extension: str
    username: str
    password: str = Field("", description="Пароль (скрыт)")
    transport: str = "udp"
    codecs: List[str] = ["ulaw", "alaw"]
    max_channels: int = 20
    max_retries: int = 3
    retry_interval: int = 300
    call_timeout: int = 40
    register_timeout: int = 30
    keepalive_interval: int = 30
    use_srtp: bool = False
    use_tls_verify: bool = False
    allow_guest: bool = False
    register_enabled: bool = True
    register_on_startup: bool = True
    context: str = "gochs-inbound"
    caller_id: str = "ГО-ЧС"
    nat_mode: str = "auto"
    
    model_config = ConfigDict(extra="ignore")


class PBXStatusResponse(BaseModel):
    """Статус регистрации в FreePBX"""
    registered: bool = Field(False, description="Зарегистрирован ли")
    status: RegistrationStatus = Field(RegistrationStatus.UNKNOWN, description="Статус")
    message: str = Field("", description="Сообщение")
    host: Optional[str] = Field(None, description="Хост")
    port: Optional[int] = Field(None, description="Порт")
    extension: Optional[str] = Field(None, description="Extension")
    register_time: Optional[datetime] = Field(None, description="Время регистрации")
    last_check: Optional[datetime] = Field(None, description="Последняя проверка")
    details: Optional[str] = Field(None, description="Детали")
    
    model_config = ConfigDict(use_enum_values=True)


class PBXTestResponse(BaseModel):
    """Результат тестирования подключения"""
    success: bool = Field(False, description="Успешно ли")
    result: ConnectionTestResult = Field(ConnectionTestResult.UNKNOWN, description="Результат")
    message: str = Field("", description="Сообщение")
    error: Optional[str] = Field(None, description="Ошибка")
    host: Optional[str] = Field(None, description="Проверенный хост")
    port: Optional[int] = Field(None, description="Проверенный порт")
    response_time_ms: Optional[int] = Field(None, description="Время ответа (мс)")
    tested_at: Optional[datetime] = Field(None, description="Время теста")
    
    model_config = ConfigDict(use_enum_values=True)


class PBXReloadResponse(BaseModel):
    """Ответ при перезагрузке PJSIP"""
    message: str = Field("", description="Сообщение")
    success: bool = Field(True, description="Успешно ли")
    details: Optional[str] = Field(None, description="Детали")
    reloaded_at: Optional[datetime] = Field(None, description="Время перезагрузки")


class PBXRestartResponse(BaseModel):
    """Ответ при перезапуске Asterisk"""
    message: str = Field("", description="Сообщение")
    success: bool = Field(True, description="Успешно ли")
    details: Optional[str] = Field(None, description="Детали")
    restarted_at: Optional[datetime] = Field(None, description="Время перезапуска")


class PBXApplyResponse(BaseModel):
    """Ответ при применении настроек"""
    message: str = Field("", description="Сообщение")
    config_updated: bool = Field(False, description="Конфиг обновлен")
    pjsip_reloaded: bool = Field(False, description="PJSIP перезагружен")
    asterisk_restarted: bool = Field(False, description="Asterisk перезапущен")
    registration_status: Optional[PBXStatusResponse] = Field(None, description="Статус регистрации")
    applied_at: Optional[datetime] = Field(None, description="Время применения")


# ============================================================================
# SYSTEM SETTINGS
# ============================================================================

class SystemSettings(BaseModel):
    """Системные настройки"""
    
    # Основные
    app_name: str = Field("ГО-ЧС Информирование", min_length=1, max_length=100, description="Название системы")
    app_version: str = Field("1.0.0", description="Версия системы")
    environment: str = Field("production", description="Окружение (development/staging/production)")
    
    # Время и локаль
    timezone: Timezone = Field(Timezone.MOSCOW, description="Часовой пояс")
    language: str = Field("ru", min_length=2, max_length=5, description="Язык")
    date_format: str = Field("DD.MM.YYYY", description="Формат даты")
    time_format: str = Field("HH:mm:ss", description="Формат времени")
    
    # Логирование
    log_level: LogLevel = Field(LogLevel.INFO, description="Уровень логирования")
    log_retention_days: int = Field(30, ge=1, le=365, description="Хранить логи (дней)")
    log_to_file: bool = Field(True, description="Писать в файл")
    log_to_console: bool = Field(True, description="Писать в консоль")
    
    # Лимиты
    max_concurrent_calls: int = Field(20, ge=1, le=500, description="Максимум звонков")
    max_recording_size_mb: int = Field(100, ge=10, le=1000, description="Макс. размер записи (МБ)")
    max_upload_size_mb: int = Field(50, ge=1, le=500, description="Макс. размер загрузки (МБ)")
    
    # Записи
    recording_retention_days: int = Field(90, ge=1, le=365, description="Хранить записи (дней)")
    recording_format: str = Field("wav", description="Формат записи (wav/mp3)")
    recording_compression: bool = Field(False, description="Сжимать записи")
    
    # Очистка
    auto_cleanup_enabled: bool = Field(True, description="Авто-очистка")
    cleanup_hour: int = Field(2, ge=0, le=23, description="Час очистки")
    
    model_config = ConfigDict(use_enum_values=True)


class SystemSettingsUpdate(BaseModel):
    """Обновление системных настроек"""
    app_name: Optional[str] = Field(None, min_length=1, max_length=100)
    environment: Optional[str] = None
    timezone: Optional[Timezone] = None
    language: Optional[str] = Field(None, min_length=2, max_length=5)
    date_format: Optional[str] = None
    time_format: Optional[str] = None
    log_level: Optional[LogLevel] = None
    log_retention_days: Optional[int] = Field(None, ge=1, le=365)
    log_to_file: Optional[bool] = None
    log_to_console: Optional[bool] = None
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=500)
    max_recording_size_mb: Optional[int] = Field(None, ge=10, le=1000)
    max_upload_size_mb: Optional[int] = Field(None, ge=1, le=500)
    recording_retention_days: Optional[int] = Field(None, ge=1, le=365)
    recording_format: Optional[str] = None
    recording_compression: Optional[bool] = None
    auto_cleanup_enabled: Optional[bool] = None
    cleanup_hour: Optional[int] = Field(None, ge=0, le=23)
    
    model_config = ConfigDict(use_enum_values=True)


class SystemSettingsResponse(BaseModel):
    """Ответ с системными настройками"""
    app_name: str
    app_version: str
    environment: str
    timezone: str
    language: str
    date_format: str
    time_format: str
    log_level: str
    log_retention_days: int
    log_to_file: bool
    log_to_console: bool
    max_concurrent_calls: int
    max_recording_size_mb: int
    max_upload_size_mb: int
    recording_retention_days: int
    recording_format: str
    recording_compression: bool
    auto_cleanup_enabled: bool
    cleanup_hour: int
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# SECURITY SETTINGS
# ============================================================================

class SecuritySettings(BaseModel):
    """Настройки безопасности"""
    
    # JWT
    jwt_expire_minutes: int = Field(60, ge=5, le=1440, description="Срок JWT (минут)")
    jwt_refresh_expire_days: int = Field(7, ge=1, le=30, description="Срок Refresh (дней)")
    jwt_algorithm: str = Field("HS256", description="Алгоритм JWT")
    
    # Пароли
    password_min_length: int = Field(8, ge=6, le=32, description="Мин. длина пароля")
    password_require_uppercase: bool = Field(True, description="Требовать заглавные")
    password_require_lowercase: bool = Field(True, description="Требовать строчные")
    password_require_digits: bool = Field(True, description="Требовать цифры")
    password_require_special: bool = Field(True, description="Требовать спецсимволы")
    password_expire_days: int = Field(90, ge=0, le=365, description="Срок действия пароля (0=нет)")
    
    # Вход
    max_login_attempts: int = Field(5, ge=3, le=10, description="Макс. попыток входа")
    lockout_minutes: int = Field(15, ge=5, le=60, description="Блокировка (минут)")
    session_timeout_minutes: int = Field(30, ge=5, le=480, description="Таймаут сессии")
    
    # 2FA
    two_factor_enabled: bool = Field(False, description="Включить 2FA")
    two_factor_method: str = Field("email", description="Метод 2FA (email/sms/totp)")
    
    # IP
    ip_whitelist: List[str] = Field([], description="Белый список IP")
    ip_blacklist: List[str] = Field([], description="Черный список IP")
    allow_api_without_auth: bool = Field(False, description="API без авторизации")
    
    # CORS
    cors_origins: List[str] = Field(["*"], description="Разрешенные origins")
    
    model_config = ConfigDict(extra="ignore")


class SecuritySettingsUpdate(BaseModel):
    """Обновление настроек безопасности"""
    jwt_expire_minutes: Optional[int] = Field(None, ge=5, le=1440)
    jwt_refresh_expire_days: Optional[int] = Field(None, ge=1, le=30)
    jwt_algorithm: Optional[str] = None
    password_min_length: Optional[int] = Field(None, ge=6, le=32)
    password_require_uppercase: Optional[bool] = None
    password_require_lowercase: Optional[bool] = None
    password_require_digits: Optional[bool] = None
    password_require_special: Optional[bool] = None
    password_expire_days: Optional[int] = Field(None, ge=0, le=365)
    max_login_attempts: Optional[int] = Field(None, ge=3, le=10)
    lockout_minutes: Optional[int] = Field(None, ge=5, le=60)
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=480)
    two_factor_enabled: Optional[bool] = None
    two_factor_method: Optional[str] = None
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None
    allow_api_without_auth: Optional[bool] = None
    cors_origins: Optional[List[str]] = None


class SecuritySettingsResponse(BaseModel):
    """Ответ с настройками безопасности"""
    jwt_expire_minutes: int
    jwt_refresh_expire_days: int
    jwt_algorithm: str
    password_min_length: int
    password_require_uppercase: bool
    password_require_lowercase: bool
    password_require_digits: bool
    password_require_special: bool
    password_expire_days: int
    max_login_attempts: int
    lockout_minutes: int
    session_timeout_minutes: int
    two_factor_enabled: bool
    two_factor_method: str
    ip_whitelist: List[str]
    ip_blacklist: List[str]
    allow_api_without_auth: bool
    cors_origins: List[str]
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# NOTIFICATION SETTINGS
# ============================================================================

class NotificationSettings(BaseModel):
    """Настройки уведомлений"""
    
    # Email
    email_enabled: bool = Field(False, description="Включить Email")
    email_smtp_server: str = Field("", description="SMTP сервер")
    email_smtp_port: int = Field(587, ge=1, le=65535, description="SMTP порт")
    email_smtp_username: str = Field("", description="SMTP пользователь")
    email_smtp_password: str = Field("", description="SMTP пароль")
    email_smtp_use_tls: bool = Field(True, description="Использовать TLS")
    email_from: str = Field("", description="От кого")
    email_from_name: str = Field("ГО-ЧС Информирование", description="Имя отправителя")
    
    # Telegram
    telegram_enabled: bool = Field(False, description="Включить Telegram")
    telegram_bot_token: str = Field("", description="Токен бота")
    telegram_chat_ids: List[str] = Field([], description="ID чатов")
    
    # Webhook
    webhook_enabled: bool = Field(False, description="Включить Webhook")
    webhook_url: str = Field("", description="URL вебхука")
    webhook_secret: str = Field("", description="Секретный ключ")
    
    # Триггеры
    notify_on_campaign_start: bool = Field(True, description="При запуске кампании")
    notify_on_campaign_complete: bool = Field(True, description="При завершении кампании")
    notify_on_campaign_error: bool = Field(True, description="При ошибке кампании")
    notify_on_system_error: bool = Field(True, description="При ошибке системы")
    notify_on_system_startup: bool = Field(False, description="При запуске системы")
    notify_on_backup_complete: bool = Field(False, description="При завершении бэкапа")
    
    # Приоритеты
    min_priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Мин. приоритет")
    
    model_config = ConfigDict(use_enum_values=True, extra="ignore")


class NotificationSettingsUpdate(BaseModel):
    """Обновление настроек уведомлений"""
    email_enabled: Optional[bool] = None
    email_smtp_server: Optional[str] = None
    email_smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    email_smtp_username: Optional[str] = None
    email_smtp_password: Optional[str] = None
    email_smtp_use_tls: Optional[bool] = None
    email_from: Optional[str] = None
    email_from_name: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_ids: Optional[List[str]] = None
    webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    notify_on_campaign_start: Optional[bool] = None
    notify_on_campaign_complete: Optional[bool] = None
    notify_on_campaign_error: Optional[bool] = None
    notify_on_system_error: Optional[bool] = None
    notify_on_system_startup: Optional[bool] = None
    notify_on_backup_complete: Optional[bool] = None
    min_priority: Optional[NotificationPriority] = None
    
    model_config = ConfigDict(use_enum_values=True)


class NotificationSettingsResponse(BaseModel):
    """Ответ с настройками уведомлений"""
    email_enabled: bool
    email_smtp_server: str
    email_smtp_port: int
    email_smtp_username: str
    email_smtp_password: str = Field("", description="Пароль (скрыт)")
    email_smtp_use_tls: bool
    email_from: str
    email_from_name: str
    telegram_enabled: bool
    telegram_bot_token: str = Field("", description="Токен (скрыт)")
    telegram_chat_ids: List[str]
    webhook_enabled: bool
    webhook_url: str
    webhook_secret: str = Field("", description="Секрет (скрыт)")
    notify_on_campaign_start: bool
    notify_on_campaign_complete: bool
    notify_on_campaign_error: bool
    notify_on_system_error: bool
    notify_on_system_startup: bool
    notify_on_backup_complete: bool
    min_priority: str
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# BACKUP SETTINGS
# ============================================================================

class BackupSettings(BaseModel):
    """Настройки резервного копирования"""
    
    enabled: bool = Field(True, description="Включить авто-бэкап")
    type: BackupType = Field(BackupType.FULL, description="Тип бэкапа")
    schedule: str = Field("0 2 * * *", description="Расписание (cron)")
    retention_days: int = Field(30, ge=1, le=365, description="Хранить (дней)")
    max_backups: int = Field(10, ge=1, le=100, description="Макс. количество бэкапов")
    
    # Пути
    backup_dir: str = Field("/opt/gochs-informing/backups", description="Директория бэкапов")
    
    # Что бэкапить
    include_database: bool = Field(True, description="База данных")
    include_settings: bool = Field(True, description="Настройки")
    include_recordings: bool = Field(False, description="Записи звонков")
    include_logs: bool = Field(False, description="Логи")
    
    # Сжатие
    compress: bool = Field(True, description="Сжимать")
    compression_level: int = Field(6, ge=1, le=9, description="Уровень сжатия")
    
    # Удаленное хранилище
    remote_enabled: bool = Field(False, description="Удаленное хранилище")
    remote_type: str = Field("sftp", description="Тип (sftp/ftp/s3)")
    remote_host: str = Field("", description="Хост")
    remote_port: int = Field(22, ge=1, le=65535)
    remote_path: str = Field("", description="Путь")
    remote_username: str = Field("", description="Пользователь")
    remote_password: str = Field("", description="Пароль")
    
    model_config = ConfigDict(use_enum_values=True)


class BackupSettingsUpdate(BaseModel):
    """Обновление настроек бэкапа"""
    enabled: Optional[bool] = None
    type: Optional[BackupType] = None
    schedule: Optional[str] = None
    retention_days: Optional[int] = Field(None, ge=1, le=365)
    max_backups: Optional[int] = Field(None, ge=1, le=100)
    backup_dir: Optional[str] = None
    include_database: Optional[bool] = None
    include_settings: Optional[bool] = None
    include_recordings: Optional[bool] = None
    include_logs: Optional[bool] = None
    compress: Optional[bool] = None
    compression_level: Optional[int] = Field(None, ge=1, le=9)
    remote_enabled: Optional[bool] = None
    remote_type: Optional[str] = None
    remote_host: Optional[str] = None
    remote_port: Optional[int] = Field(None, ge=1, le=65535)
    remote_path: Optional[str] = None
    remote_username: Optional[str] = None
    remote_password: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True)


class BackupResponse(BaseModel):
    """Ответ при создании бэкапа"""
    message: str = Field("", description="Сообщение")
    backup_id: str = Field("", description="ID бэкапа")
    backup_file: str = Field("", description="Файл бэкапа")
    backup_type: BackupType = Field(BackupType.FULL, description="Тип бэкапа")
    size_bytes: int = Field(0, description="Размер в байтах")
    timestamp: str = Field("", description="Временная метка")
    status: BackupStatus = Field(BackupStatus.PENDING, description="Статус")
    
    model_config = ConfigDict(use_enum_values=True)


class BackupListItem(BaseModel):
    """Элемент списка бэкапов"""
    id: str = Field(..., description="ID бэкапа")
    name: str = Field(..., description="Имя файла")
    size: int = Field(..., description="Размер в байтах")
    type: BackupType = Field(..., description="Тип бэкапа")
    status: BackupStatus = Field(..., description="Статус")
    created: str = Field(..., description="Дата создания")
    path: str = Field(..., description="Полный путь")
    
    model_config = ConfigDict(use_enum_values=True)


class BackupsListResponse(BaseModel):
    """Список бэкапов"""
    backups: List[BackupListItem] = Field([], description="Список бэкапов")
    total: int = Field(0, description="Всего бэкапов")
    total_size_bytes: int = Field(0, description="Общий размер")
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# ALL SETTINGS
# ============================================================================

class AllSettingsResponse(BaseModel):
    """Все настройки системы"""
    pbx: PBXSettingsResponse
    system: SystemSettingsResponse
    security: SecuritySettingsResponse
    notifications: NotificationSettingsResponse
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# CREDENTIALS
# ============================================================================

class CredentialsInfoResponse(BaseModel):
    """Информация об учетных данных (без паролей)"""
    freepbx: Dict[str, Any] = Field({}, description="FreePBX")
    postgresql: Dict[str, Any] = Field({}, description="PostgreSQL")
    redis: Dict[str, Any] = Field({}, description="Redis")
    asterisk: Dict[str, Any] = Field({}, description="Asterisk")
    
    model_config = ConfigDict(extra="ignore")


# ============================================================================
# RESET
# ============================================================================

class ResetSettingsResponse(BaseModel):
    """Ответ при сбросе настроек"""
    message: str = Field("", description="Сообщение")
    success: bool = Field(False, description="Успешно ли")
    reset_sections: List[str] = Field([], description="Сброшенные секции")
    reset_at: Optional[datetime] = Field(None, description="Время сброса")


# ============================================================================
# IMPORT/EXPORT
# ============================================================================

class ExportSettingsResponse(BaseModel):
    """Ответ при экспорте настроек"""
    filename: str = Field(..., description="Имя файла")
    content: str = Field("", description="Содержимое (base64)")
    timestamp: str = Field(..., description="Временная метка")
    sections: List[str] = Field([], description="Экспортированные секции")


class ImportSettingsResponse(BaseModel):
    """Ответ при импорте настроек"""
    message: str = Field("", description="Сообщение")
    success: bool = Field(False, description="Успешно ли")
    imported_sections: List[str] = Field([], description="Импортированные секции")
    errors: List[str] = Field([], description="Ошибки")


class ValidateSettingsResponse(BaseModel):
    """Ответ при валидации настроек"""
    valid: bool = Field(False, description="Валидны ли")
    errors: List[Dict[str, Any]] = Field([], description="Ошибки валидации")
    warnings: List[Dict[str, Any]] = Field([], description="Предупреждения")


# ============================================================================
# HEALTH
# ============================================================================

class SettingsHealthResponse(BaseModel):
    """Проверка здоровья настроек"""
    env_file_exists: bool = Field(False, description="Существует ли .env")
    cred_file_exists: bool = Field(False, description="Существует ли credentials")
    config_file_exists: bool = Field(False, description="Существует ли config.yaml")
    settings_loaded: bool = Field(False, description="Настройки загружены")
    status: str = Field("unknown", description="Статус")


# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Enums
    "TransportType", "LogLevel", "Timezone", "CodecType", "AuthMethod",
    "BackupType", "BackupStatus", "NotificationType", "NotificationPriority",
    "RegistrationStatus", "ConnectionTestResult",
    
    # PBX
    "PBXSettings", "PBXSettingsUpdate", "PBXSettingsResponse",
    "PBXStatusResponse", "PBXTestResponse", "PBXReloadResponse",
    "PBXRestartResponse", "PBXApplyResponse",
    
    # System
    "SystemSettings", "SystemSettingsUpdate", "SystemSettingsResponse",
    
    # Security
    "SecuritySettings", "SecuritySettingsUpdate", "SecuritySettingsResponse",
    
    # Notifications
    "NotificationSettings", "NotificationSettingsUpdate", "NotificationSettingsResponse",
    
    # Backup
    "BackupSettings", "BackupSettingsUpdate", "BackupResponse",
    "BackupListItem", "BackupsListResponse",
    
    # All
    "AllSettingsResponse",
    
    # Credentials
    "CredentialsInfoResponse",
    
    # Reset
    "ResetSettingsResponse",
    
    # Import/Export
    "ExportSettingsResponse", "ImportSettingsResponse", "ValidateSettingsResponse",
    
    # Health
    "SettingsHealthResponse"
]
