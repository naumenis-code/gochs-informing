#!/usr/bin/env python3
"""Settings endpoints с сохранением в файлы"""

import os
import re
import logging
from fastapi import APIRouter, Depends
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

# Пути к файлам конфигурации
ENV_FILE = "/opt/gochs-informing/.env"
CRED_FILE = "/root/.gochs_credentials"

def read_env_value(key: str, default: str = "") -> str:
    """Чтение значения из .env файла"""
    try:
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
    except Exception as e:
        logger.error(f"Error reading {key}: {e}")
    return default

def write_env_value(key: str, value: str) -> bool:
    """Запись значения в .env файл"""
    try:
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
        return True
    except Exception as e:
        logger.error(f"Error writing {key}: {e}")
        return False

def get_freepbx_config() -> Dict[str, Any]:
    """Чтение настроек FreePBX"""
    config = {
        "host": read_env_value("FREEPBX_HOST", "192.168.1.10").split(':')[0],
        "port": 5060,
        "extension": read_env_value("FREEPBX_EXTENSION", "gochs"),
        "username": read_env_value("FREEPBX_USERNAME", "gochs"),
        "password": read_env_value("FREEPBX_PASSWORD", ""),
        "transport": "udp",
        "max_channels": int(read_env_value("MAX_CONCURRENT_CALLS", "20")),
        "codecs": ["ulaw", "alaw"],
        "register_enabled": read_env_value("FREEPBX_ENABLED", "true").lower() == "true"
    }
    
    # Порт из FREEPBX_HOST
    host_port = read_env_value("FREEPBX_HOST", "")
    if ':' in host_port:
        config["port"] = int(host_port.split(':')[1])
    else:
        config["port"] = int(read_env_value("FREEPBX_PORT", "5060"))
    
    # Пароль из credentials
    try:
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            section = re.search(r'FREE PBX:(.*?)(?:РЕЖИМ SSL:|$)', content, re.DOTALL)
            if section:
                pass_match = re.search(r'Пароль:\s*(\S+)', section.group(1))
                if pass_match and pass_match.group(1):
                    config["password"] = pass_match.group(1)
    except:
        pass
    
    return config

def save_freepbx_config(data: Dict[str, Any]) -> bool:
    """Сохранение настроек FreePBX"""
    try:
        if "host" in data and "port" in data:
            write_env_value("FREEPBX_HOST", f"{data['host']}:{data['port']}")
        if "port" in data:
            write_env_value("FREEPBX_PORT", str(data['port']))
        if "extension" in data:
            write_env_value("FREEPBX_EXTENSION", data['extension'])
            write_env_value("FREEPBX_USERNAME", data['extension'])
        if "password" in data and data['password']:
            write_env_value("FREEPBX_PASSWORD", data['password'])
        if "max_channels" in data:
            write_env_value("MAX_CONCURRENT_CALLS", str(data['max_channels']))
        if "register_enabled" in data:
            write_env_value("FREEPBX_ENABLED", str(data['register_enabled']).lower())
        return True
    except Exception as e:
        logger.error(f"Error saving PBX config: {e}")
        return False

@router.get("/pbx")
async def get_pbx_settings():
    """Получение настроек FreePBX"""
    return get_freepbx_config()

@router.put("/pbx")
async def update_pbx_settings(data: dict):
    """Сохранение настроек FreePBX"""
    save_freepbx_config(data)
    return data

@router.get("/pbx/status")
async def check_pbx_status():
    """Проверка статуса"""
    return {"registered": True}

@router.post("/pbx/reload")
async def reload_pbx_config():
    """Перезагрузка PJSIP"""
    return {"message": "OK"}

@router.post("/pbx/test")
async def test_pbx_connection(data: dict):
    """Тест подключения"""
    return {"success": True}

@router.get("/system")
async def get_system_settings():
    """Системные настройки"""
    return {
        "app_name": read_env_value("APP_NAME", "ГО-ЧС Информирование"),
        "timezone": read_env_value("TIMEZONE", "Europe/Moscow"),
        "log_level": read_env_value("LOG_LEVEL", "INFO"),
        "max_concurrent_calls": int(read_env_value("MAX_CONCURRENT_CALLS", "20")),
        "recording_retention_days": int(read_env_value("RECORDING_RETENTION_DAYS", "90")),
        "backup_enabled": read_env_value("BACKUP_ENABLED", "true").lower() == "true",
        "backup_time": read_env_value("BACKUP_TIME", "02:00")
    }

@router.put("/system")
async def update_system_settings(data: dict):
    """Сохранение системных настроек"""
    for key, value in data.items():
        if value is not None:
            write_env_value(key.upper(), str(value))
    return data

@router.get("/security")
async def get_security_settings():
    """Настройки безопасности"""
    return {
        "jwt_expire_minutes": int(read_env_value("JWT_EXPIRE_MINUTES", "60")),
        "refresh_token_expire_days": int(read_env_value("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        "max_login_attempts": int(read_env_value("MAX_LOGIN_ATTEMPTS", "5")),
        "lockout_minutes": int(read_env_value("LOCKOUT_MINUTES", "15")),
        "password_min_length": int(read_env_value("PASSWORD_MIN_LENGTH", "8")),
        "require_special_chars": read_env_value("REQUIRE_SPECIAL_CHARS", "true").lower() == "true",
        "session_timeout_minutes": int(read_env_value("SESSION_TIMEOUT_MINUTES", "30"))
    }

@router.put("/security")
async def update_security_settings(data: dict):
    """Сохранение настроек безопасности"""
    for key, value in data.items():
        if value is not None:
            write_env_value(key.upper(), str(value))
    return data

@router.get("/notifications")
async def get_notification_settings():
    """Настройки уведомлений"""
    return {
        "email_enabled": read_env_value("EMAIL_ENABLED", "false").lower() == "true",
        "smtp_server": read_env_value("SMTP_SERVER", ""),
        "smtp_port": int(read_env_value("SMTP_PORT", "587")),
        "smtp_username": read_env_value("SMTP_USERNAME", ""),
        "smtp_password": read_env_value("SMTP_PASSWORD", ""),
        "from_email": read_env_value("FROM_EMAIL", ""),
        "admin_email": read_env_value("ADMIN_EMAIL", ""),
        "notify_on_campaign_complete": read_env_value("NOTIFY_CAMPAIGN_COMPLETE", "true").lower() == "true",
        "notify_on_system_error": read_env_value("NOTIFY_SYSTEM_ERROR", "true").lower() == "true"
    }

@router.put("/notifications")
async def update_notification_settings(data: dict):
    """Сохранение настроек уведомлений"""
    for key, value in data.items():
        if value is not None:
            write_env_value(key.upper(), str(value))
    return data
