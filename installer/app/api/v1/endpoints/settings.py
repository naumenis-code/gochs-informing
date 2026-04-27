#!/usr/bin/env python3
"""
API эндпоинты для управления настройками системы
Соответствует ТЗ, разделы 8, 23, 29, 32

Функционал:
- Настройки подключения к FreePBX
- Системные настройки
- Настройки безопасности
- Настройки уведомлений
- Резервное копирование
- Просмотр учетных данных (без паролей)
"""
import logging
import os
import re
import socket
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()

ENV_FILE = "/opt/gochs-informing/.env"
CRED_FILE = "/root/.gochs_credentials"


def _read_env(key: str, default: str = "") -> str:
    """Чтение переменной из .env файла"""
    try:
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return default


def _write_env(key: str, value: str) -> None:
    """Запись переменной в .env файл"""
    lines = []
    found = False
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            lines = f.readlines()
    
    with open(ENV_FILE, 'w') as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}={value}\n")


# ============================================================================
# НАСТРОЙКИ FREEPBX
# ============================================================================

@router.get("/pbx")
async def get_pbx_settings():
    """
    Получение настроек подключения к FreePBX
    
    Доступ: admin
    """
    return {
        "host": _read_env("FREEPBX_HOST", "192.168.1.10"),
        "port": int(_read_env("FREEPBX_PORT", "5060")),
        "extension": _read_env("FREEPBX_EXTENSION", "gochs"),
        "username": _read_env("FREEPBX_USERNAME", "gochs"),
        "password": _read_env("FREEPBX_PASSWORD", ""),
        "transport": _read_env("FREEPBX_TRANSPORT", "udp"),
        "max_channels": int(_read_env("MAX_CONCURRENT_CALLS", "20")),
        "codecs": _read_env("FREEPBX_CODECS", "ulaw,alaw").split(","),
        "register_enabled": _read_env("FREEPBX_ENABLED", "true").lower() == "true"
    }


@router.put("/pbx")
async def update_pbx_settings(data: dict):
    """
    Обновление настроек FreePBX
    
    Доступ: admin
    После сохранения требуется перезагрузка PJSIP
    """
    mapping = {
        "host": "FREEPBX_HOST",
        "port": "FREEPBX_PORT",
        "extension": "FREEPBX_EXTENSION",
        "username": "FREEPBX_USERNAME",
        "password": "FREEPBX_PASSWORD",
        "transport": "FREEPBX_TRANSPORT",
        "max_channels": "MAX_CONCURRENT_CALLS",
        "register_enabled": "FREEPBX_ENABLED",
    }
    
    for key, env_key in mapping.items():
        if key in data and data[key] is not None:
            value = data[key]
            if isinstance(value, bool):
                value = str(value).lower()
            _write_env(env_key, str(value))
    
    if "codecs" in data:
        _write_env("FREEPBX_CODECS", ",".join(data["codecs"]) if isinstance(data["codecs"], list) else str(data["codecs"]))
    
    logger.info("PBX settings updated")
    return await get_pbx_settings()


@router.get("/pbx/status")
async def check_pbx_status():
    """
    Проверка статуса регистрации в FreePBX
    
    Доступ: admin
    """
    host = _read_env("FREEPBX_HOST", "192.168.1.10")
    port = int(_read_env("FREEPBX_PORT", "5060"))
    
    # Проверка через TCP
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return {
                "registered": True,
                "message": "Порт доступен",
                "host": host,
                "port": port,
                "extension": _read_env("FREEPBX_EXTENSION", "")
            }
    except Exception:
        pass
    
    return {
        "registered": False,
        "message": "Порт недоступен",
        "host": host,
        "port": port,
        "extension": _read_env("FREEPBX_EXTENSION", "")
    }


@router.post("/pbx/test")
async def test_pbx_connection(data: dict):
    """
    Тестирование подключения к FreePBX
    
    Доступ: admin
    """
    host = data.get("host", "192.168.1.10")
    port = int(data.get("port", 5060))
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return {"success": True, "message": f"Подключение к {host}:{port} успешно"}
        else:
            return {"success": False, "message": "Не удалось подключиться", "error": "Connection refused"}
    except Exception as e:
        return {"success": False, "message": "Ошибка подключения", "error": str(e)}


# ============================================================================
# СИСТЕМНЫЕ НАСТРОЙКИ
# ============================================================================

@router.get("/system")
async def get_system_settings():
    """Получение системных настроек"""
    return {
        "app_name": _read_env("APP_NAME", "ГО-ЧС Информирование"),
        "timezone": _read_env("TIMEZONE", "Europe/Moscow"),
        "log_level": _read_env("LOG_LEVEL", "INFO"),
        "max_concurrent_calls": int(_read_env("MAX_CONCURRENT_CALLS", "20")),
        "recording_retention_days": int(_read_env("RECORDING_RETENTION_DAYS", "90")),
        "backup_enabled": _read_env("BACKUP_ENABLED", "true").lower() == "true",
        "backup_time": _read_env("BACKUP_TIME", "02:00")
    }


@router.put("/system")
async def update_system_settings(data: dict):
    """Обновление системных настроек"""
    mapping = {
        "app_name": "APP_NAME",
        "timezone": "TIMEZONE",
        "log_level": "LOG_LEVEL",
        "max_concurrent_calls": "MAX_CONCURRENT_CALLS",
        "recording_retention_days": "RECORDING_RETENTION_DAYS",
        "backup_enabled": "BACKUP_ENABLED",
        "backup_time": "BACKUP_TIME"
    }
    
    for key, env_key in mapping.items():
        if key in data and data[key] is not None:
            value = data[key]
            if isinstance(value, bool):
                value = str(value).lower()
            _write_env(env_key, str(value))
    
    logger.info("System settings updated")
    return await get_system_settings()


# ============================================================================
# НАСТРОЙКИ БЕЗОПАСНОСТИ
# ============================================================================

@router.get("/security")
async def get_security_settings():
    """Получение настроек безопасности"""
    return {
        "jwt_expire_minutes": int(_read_env("JWT_EXPIRE_MINUTES", "60")),
        "refresh_token_expire_days": int(_read_env("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        "max_login_attempts": int(_read_env("MAX_LOGIN_ATTEMPTS", "5")),
        "lockout_minutes": int(_read_env("LOCKOUT_MINUTES", "15")),
        "password_min_length": int(_read_env("PASSWORD_MIN_LENGTH", "8")),
        "require_special_chars": _read_env("REQUIRE_SPECIAL_CHARS", "true").lower() == "true",
        "session_timeout_minutes": int(_read_env("SESSION_TIMEOUT_MINUTES", "30"))
    }


@router.put("/security")
async def update_security_settings(data: dict):
    """Обновление настроек безопасности"""
    mapping = {
        "jwt_expire_minutes": "JWT_EXPIRE_MINUTES",
        "refresh_token_expire_days": "REFRESH_TOKEN_EXPIRE_DAYS",
        "max_login_attempts": "MAX_LOGIN_ATTEMPTS",
        "lockout_minutes": "LOCKOUT_MINUTES",
        "password_min_length": "PASSWORD_MIN_LENGTH",
        "require_special_chars": "REQUIRE_SPECIAL_CHARS",
        "session_timeout_minutes": "SESSION_TIMEOUT_MINUTES"
    }
    
    for key, env_key in mapping.items():
        if key in data and data[key] is not None:
            value = data[key]
            if isinstance(value, bool):
                value = str(value).lower()
            _write_env(env_key, str(value))
    
    logger.info("Security settings updated")
    return await get_security_settings()


# ============================================================================
# НАСТРОЙКИ УВЕДОМЛЕНИЙ
# ============================================================================

@router.get("/notifications")
async def get_notification_settings():
    """Получение настроек уведомлений"""
    return {
        "email_enabled": _read_env("EMAIL_ENABLED", "false").lower() == "true",
        "smtp_server": _read_env("SMTP_SERVER", ""),
        "smtp_port": int(_read_env("SMTP_PORT", "587")),
        "smtp_username": _read_env("SMTP_USERNAME", ""),
        "smtp_password": _read_env("SMTP_PASSWORD", ""),
        "from_email": _read_env("FROM_EMAIL", ""),
        "admin_email": _read_env("ADMIN_EMAIL", ""),
        "notify_on_campaign_complete": _read_env("NOTIFY_CAMPAIGN_COMPLETE", "true").lower() == "true",
        "notify_on_system_error": _read_env("NOTIFY_SYSTEM_ERROR", "true").lower() == "true"
    }


@router.put("/notifications")
async def update_notification_settings(data: dict):
    """Обновление настроек уведомлений"""
    mapping = {
        "email_enabled": "EMAIL_ENABLED",
        "smtp_server": "SMTP_SERVER",
        "smtp_port": "SMTP_PORT",
        "smtp_username": "SMTP_USERNAME",
        "from_email": "FROM_EMAIL",
        "admin_email": "ADMIN_EMAIL",
        "notify_on_campaign_complete": "NOTIFY_CAMPAIGN_COMPLETE",
        "notify_on_system_error": "NOTIFY_SYSTEM_ERROR"
    }
    
    for key, env_key in mapping.items():
        if key in data and data[key] is not None:
            value = data[key]
            if isinstance(value, bool):
                value = str(value).lower()
            _write_env(env_key, str(value))
    
    if "smtp_password" in data and data["smtp_password"]:
        _write_env("SMTP_PASSWORD", data["smtp_password"])
    
    logger.info("Notification settings updated")
    return await get_notification_settings()


# ============================================================================
# УЧЕТНЫЕ ДАННЫЕ
# ============================================================================

@router.get("/credentials")
async def get_credentials_info():
    """
    Просмотр информации об учетных данных (без паролей)
    
    Доступ: admin
    """
    info = {"freepbx": {}, "postgresql": {}, "redis": {}, "asterisk": {}}
    
    # FreePBX
    info["freepbx"] = {
        "host": _read_env("FREEPBX_HOST", ""),
        "port": int(_read_env("FREEPBX_PORT", "5060")),
        "extension": _read_env("FREEPBX_EXTENSION", ""),
        "has_password": bool(_read_env("FREEPBX_PASSWORD", ""))
    }
    
    # PostgreSQL
    info["postgresql"] = {
        "database": "gochs",
        "user": "gochs_user",
        "has_password": True
    }
    
    # Redis
    info["redis"] = {
        "has_password": bool(_read_env("REDIS_PASSWORD", ""))
    }
    
    # Asterisk
    info["asterisk"] = {
        "ami_user": "gochs_ami",
        "has_ami_password": bool(_read_env("ASTERISK_AMI_PASSWORD", "")),
        "has_ari_password": bool(_read_env("ASTERISK_ARI_PASSWORD", ""))
    }
    
    return info


# ============================================================================
# РЕЗЕРВНОЕ КОПИРОВАНИЕ
# ============================================================================

@router.post("/backup")
async def create_backup(background_tasks: BackgroundTasks):
    """
    Создание резервной копии настроек
    
    Доступ: admin
    """
    import tarfile
    
    backup_dir = "/opt/gochs-informing/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{backup_dir}/settings_backup_{timestamp}.tar.gz"
    
    def do_backup():
        with tarfile.open(backup_file, "w:gz") as tar:
            if os.path.exists(ENV_FILE):
                tar.add(ENV_FILE, arcname=".env")
            if os.path.exists(CRED_FILE):
                tar.add(CRED_FILE, arcname="gochs_credentials")
        logger.info(f"Backup created: {backup_file}")
    
    background_tasks.add_task(do_backup)
    
    return {
        "message": "Резервное копирование запущено",
        "backup_file": backup_file,
        "timestamp": timestamp
    }


@router.get("/backups")
async def list_backups():
    """Список резервных копий"""
    backup_dir = "/opt/gochs-informing/backups"
    backups = []
    
    if os.path.exists(backup_dir):
        for f in sorted(os.listdir(backup_dir), reverse=True):
            if f.startswith("settings_backup_") and f.endswith(".tar.gz"):
                filepath = os.path.join(backup_dir, f)
                stat = os.stat(filepath)
                backups.append({
                    "name": f,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": filepath
                })
    
    return {"backups": backups[:10]}
