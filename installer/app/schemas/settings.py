#!/usr/bin/env python3
"""Settings schemas"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class TransportType(str, Enum):
    UDP = "udp"
    TCP = "tcp"
    TLS = "tls"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ==================== PBX Settings ====================
class PBXSettings(BaseModel):
    host: str = "192.168.1.10"
    port: int = 5060
    extension: str = "gochs"
    username: str = "gochs"
    password: str = ""
    transport: TransportType = TransportType.UDP
    max_channels: int = 20
    codecs: List[str] = ["ulaw", "alaw"]
    register_enabled: bool = True


class PBXSettingsUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    extension: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    transport: Optional[TransportType] = None
    max_channels: Optional[int] = None
    codecs: Optional[List[str]] = None
    register_enabled: Optional[bool] = None


class PBXStatusResponse(BaseModel):
    registered: bool
    message: Optional[str] = None


class PBXTestResponse(BaseModel):
    success: bool
    error: Optional[str] = None


# ==================== System Settings ====================
class SystemSettings(BaseModel):
    app_name: str = "ГО-ЧС Информирование"
    timezone: str = "Europe/Moscow"
    log_level: LogLevel = LogLevel.INFO
    max_concurrent_calls: int = 20
    recording_retention_days: int = 90
    backup_enabled: bool = True
    backup_time: str = "02:00"


class SystemSettingsUpdate(BaseModel):
    app_name: Optional[str] = None
    timezone: Optional[str] = None
    log_level: Optional[LogLevel] = None
    max_concurrent_calls: Optional[int] = None
    recording_retention_days: Optional[int] = None
    backup_enabled: Optional[bool] = None
    backup_time: Optional[str] = None


# ==================== Security Settings ====================
class SecuritySettings(BaseModel):
    jwt_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    password_min_length: int = 8
    require_special_chars: bool = True
    session_timeout_minutes: int = 30


class SecuritySettingsUpdate(BaseModel):
    jwt_expire_minutes: Optional[int] = None
    refresh_token_expire_days: Optional[int] = None
    max_login_attempts: Optional[int] = None
    lockout_minutes: Optional[int] = None
    password_min_length: Optional[int] = None
    require_special_chars: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None


# ==================== Notification Settings ====================
class NotificationSettings(BaseModel):
    email_enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    admin_email: str = ""
    notify_on_campaign_complete: bool = True
    notify_on_system_error: bool = True


class NotificationSettingsUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    admin_email: Optional[str] = None
    notify_on_campaign_complete: Optional[bool] = None
    notify_on_system_error: Optional[bool] = None
