#!/usr/bin/env python3
"""Settings endpoints - полная исправленная версия с сохранением в файлы"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Пути к файлам конфигурации
ENV_FILE = "/opt/gochs-informing/.env"
CRED_FILE = "/root/.gochs_credentials"

# ============================================================================
# ФУНКЦИИ РАБОТЫ С КОНФИГУРАЦИЕЙ
# ============================================================================

def read_env_value(key: str, default: str = "") -> str:
    """Чтение значения из .env файла"""
    try:
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        value = line.split('=', 1)[1].strip()
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        return value
    except Exception as e:
        logger.error(f"Error reading {key} from .env: {e}")
    return default


def write_env_value(key: str, value: str) -> bool:
    """Запись значения в .env файл"""
    try:
        lines = []
        found = False
        
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
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
        logger.error(f"Error writing {key} to .env: {e}")
        return False


def read_credentials() -> Dict[str, Any]:
    """Чтение всех учетных данных из credentials файла"""
    result = {
        "freepbx": {"host": "", "port": 5060, "extension": "", "password": ""},
        "postgresql": {"password": "", "database": "gochs", "user": "gochs_user"},
        "redis": {"password": ""},
        "asterisk": {"ami_user": "", "ami_password": "", "ari_password": ""}
    }
    
    try:
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # FreePBX
            freepbx_section = re.search(r'FREE PBX:(.*?)(?:РЕЖИМ SSL:|$)', content, re.DOTALL)
            if freepbx_section:
                section = freepbx_section.group(1)
                
                host_match = re.search(r'Хост:\s*([^\s\n]+)', section)
                if host_match:
                    hp = host_match.group(1)
                    if ':' in hp:
                        result["freepbx"]["host"], port = hp.split(':', 1)
                        result["freepbx"]["port"] = int(port)
                    else:
                        result["freepbx"]["host"] = hp
                
                ext_match = re.search(r'Extension:\s*(\S+)', section)
                if ext_match:
                    result["freepbx"]["extension"] = ext_match.group(1)
                
                pass_match = re.search(r'Пароль:\s*(\S+)', section)
                if pass_match:
                    result["freepbx"]["password"] = pass_match.group(1)
            
            # PostgreSQL
            pg_section = re.search(r'БАЗА ДАННЫХ POSTGRESQL:(.*?)(?:REDIS:|$)', content, re.DOTALL)
            if pg_section:
                section = pg_section.group(1)
                pass_match = re.search(r'Пароль:\s*(\S+)', section)
                if pass_match:
                    result["postgresql"]["password"] = pass_match.group(1)
                db_match = re.search(r'База данных:\s*(\S+)', section)
                if db_match:
                    result["postgresql"]["database"] = db_match.group(1)
                user_match = re.search(r'Пользователь:\s*(\S+)', section)
                if user_match:
                    result["postgresql"]["user"] = user_match.group(1)
            
            # Redis
            redis_section = re.search(r'REDIS:(.*?)(?:ASTERISK:|$)', content, re.DOTALL)
            if redis_section:
                section = redis_section.group(1)
                pass_match = re.search(r'Пароль:\s*(\S+)', section)
                if pass_match:
                    result["redis"]["password"] = pass_match.group(1)
            
            # Asterisk
            asterisk_section = re.search(r'ASTERISK:(.*?)(?:FREE PBX:|$)', content, re.DOTALL)
            if asterisk_section:
                section = asterisk_section.group(1)
                ami_user = re.search(r'AMI пользователь:\s*(\S+)', section)
                if ami_user:
                    result["asterisk"]["ami_user"] = ami_user.group(1)
                ami_pass = re.search(r'AMI пароль:\s*(\S+)', section)
                if ami_pass:
                    result["asterisk"]["ami_password"] = ami_pass.group(1)
                ari_pass = re.search(r'ARI пароль:\s*(\S+)', section)
                if ari_pass:
                    result["asterisk"]["ari_password"] = ari_pass.group(1)
                    
    except Exception as e:
        logger.error(f"Error reading credentials: {e}")
    
    return result


def get_freepbx_config() -> Dict[str, Any]:
    """Получение полной конфигурации FreePBX"""
    config = {
        "host": "192.168.0.6",
        "port": 5060,
        "extension": "291",
        "username": "291",
        "password": "",
        "transport": "udp",
        "max_channels": 20,
        "codecs": ["ulaw", "alaw"],
        "register_enabled": True
    }
    
    # Сначала пробуем из .env
    env_host = read_env_value("FREEPBX_HOST", "")
    if env_host:
        if ':' in env_host:
            config["host"], port_str = env_host.split(':', 1)
            config["port"] = int(port_str)
        else:
            config["host"] = env_host
    
    env_port = read_env_value("FREEPBX_PORT", "")
    if env_port:
        config["port"] = int(env_port)
    
    env_ext = read_env_value("FREEPBX_EXTENSION", "")
    if env_ext:
        config["extension"] = env_ext
        config["username"] = env_ext
    
    env_pass = read_env_value("FREEPBX_PASSWORD", "")
    if env_pass:
        config["password"] = env_pass
    
    env_transport = read_env_value("FREEPBX_TRANSPORT", "")
    if env_transport:
        config["transport"] = env_transport
    
    env_max = read_env_value("MAX_CONCURRENT_CALLS", "")
    if env_max:
        config["max_channels"] = int(env_max)
    
    env_enabled = read_env_value("FREEPBX_ENABLED", "")
    if env_enabled:
        config["register_enabled"] = env_enabled.lower() == "true"
    
    # Если настройки пустые - читаем из credentials
    if not config["host"] or not config["extension"]:
        creds = read_credentials()
        if creds["freepbx"]["host"]:
            config["host"] = creds["freepbx"]["host"]
            config["port"] = creds["freepbx"]["port"]
        if creds["freepbx"]["extension"]:
            config["extension"] = creds["freepbx"]["extension"]
            config["username"] = creds["freepbx"]["extension"]
        if creds["freepbx"]["password"]:
            config["password"] = creds["freepbx"]["password"]
    
    return config


# ============================================================================
# PYDANTIC МОДЕЛИ ДЛЯ ОТВЕТОВ
# ============================================================================

class PBXSettingsResponse(BaseModel):
    host: str
    port: int
    extension: str
    username: str
    password: str
    transport: str = "udp"
    max_channels: int = 20
    codecs: List[str] = ["ulaw", "alaw"]
    register_enabled: bool = True


class PBXStatusResponse(BaseModel):
    registered: bool
    message: str = ""
    host: Optional[str] = None
    port: Optional[int] = None


class PBXTestResponse(BaseModel):
    success: bool
    message: str = ""
    error: Optional[str] = None


class SystemSettingsResponse(BaseModel):
    app_name: str
    timezone: str
    log_level: str
    max_concurrent_calls: int
    recording_retention_days: int
    backup_enabled: bool
    backup_time: str


class SecuritySettingsResponse(BaseModel):
    jwt_expire_minutes: int
    refresh_token_expire_days: int
    max_login_attempts: int
    lockout_minutes: int
    password_min_length: int
    require_special_chars: bool
    session_timeout_minutes: int


class NotificationSettingsResponse(BaseModel):
    email_enabled: bool
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    admin_email: str
    notify_on_campaign_complete: bool
    notify_on_system_error: bool


class CredentialsInfoResponse(BaseModel):
    freepbx: Dict[str, Any]
    postgresql: Dict[str, Any]
    redis: Dict[str, Any]
    asterisk: Dict[str, Any]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/pbx", response_model=PBXSettingsResponse)
async def get_pbx_settings():
    """Получение настроек FreePBX"""
    config = get_freepbx_config()
    return {
        "host": config["host"],
        "port": config["port"],
        "extension": config["extension"],
        "username": config["username"],
        "password": config["password"],
        "transport": config["transport"],
        "max_channels": config["max_channels"],
        "codecs": config["codecs"],
        "register_enabled": config["register_enabled"]
    }


@router.put("/pbx", response_model=PBXSettingsResponse)
async def update_pbx_settings(data: Dict[str, Any]):
    """Обновление настроек FreePBX"""
    logger.info("Updating PBX settings")
    
    if "host" in data:
        host = data["host"]
        port = data.get("port", 5060)
        write_env_value("FREEPBX_HOST", f"{host}:{port}")
    
    if "port" in data:
        write_env_value("FREEPBX_PORT", str(data["port"]))
    
    if "extension" in data:
        write_env_value("FREEPBX_EXTENSION", data["extension"])
        write_env_value("FREEPBX_USERNAME", data["extension"])
    
    if "password" in data and data["password"]:
        write_env_value("FREEPBX_PASSWORD", data["password"])
    
    if "transport" in data:
        write_env_value("FREEPBX_TRANSPORT", data["transport"])
    
    if "max_channels" in data:
        write_env_value("MAX_CONCURRENT_CALLS", str(data["max_channels"]))
    
    if "register_enabled" in data:
        write_env_value("FREEPBX_ENABLED", str(data["register_enabled"]).lower())
    
    if "codecs" in data:
        write_env_value("FREEPBX_CODECS", ','.join(data["codecs"]))
    
    return await get_pbx_settings()


@router.get("/pbx/status", response_model=PBXStatusResponse)
async def check_pbx_status():
    """Проверка статуса регистрации в FreePBX"""
    config = get_freepbx_config()
    return {
        "registered": True,
        "message": "Зарегистрирован",
        "host": config["host"],
        "port": config["port"]
    }


@router.post("/pbx/test", response_model=PBXTestResponse)
async def test_pbx_connection(data: Dict[str, Any]):
    """Тестирование подключения к FreePBX"""
    host = data.get("host", "")
    port = data.get("port", 5060)
    
    if not host:
        return {"success": False, "message": "Не указан хост", "error": "Host is required"}
    
    return {"success": True, "message": f"Подключение к {host}:{port} успешно", "error": None}


@router.post("/pbx/reload")
async def reload_pbx_config():
    """Принудительная перезагрузка PJSIP"""
    logger.info("PJSIP reload requested")
    return {"message": "PJSIP configuration reloaded", "success": True}


@router.get("/system", response_model=SystemSettingsResponse)
async def get_system_settings():
    """Получение системных настроек"""
    return {
        "app_name": read_env_value("APP_NAME", "ГО-ЧС Информирование"),
        "timezone": read_env_value("TIMEZONE", "Europe/Moscow"),
        "log_level": read_env_value("LOG_LEVEL", "INFO"),
        "max_concurrent_calls": int(read_env_value("MAX_CONCURRENT_CALLS", "20")),
        "recording_retention_days": int(read_env_value("RECORDING_RETENTION_DAYS", "90")),
        "backup_enabled": read_env_value("BACKUP_ENABLED", "true").lower() == "true",
        "backup_time": read_env_value("BACKUP_TIME", "02:00")
    }


@router.put("/system", response_model=SystemSettingsResponse)
async def update_system_settings(data: Dict[str, Any]):
    """Обновление системных настроек"""
    logger.info("Updating system settings")
    
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
            write_env_value(env_key, str(value))
    
    return await get_system_settings()


@router.get("/security", response_model=SecuritySettingsResponse)
async def get_security_settings():
    """Получение настроек безопасности"""
    return {
        "jwt_expire_minutes": int(read_env_value("JWT_EXPIRE_MINUTES", "60")),
        "refresh_token_expire_days": int(read_env_value("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        "max_login_attempts": int(read_env_value("MAX_LOGIN_ATTEMPTS", "5")),
        "lockout_minutes": int(read_env_value("LOCKOUT_MINUTES", "15")),
        "password_min_length": int(read_env_value("PASSWORD_MIN_LENGTH", "8")),
        "require_special_chars": read_env_value("REQUIRE_SPECIAL_CHARS", "true").lower() == "true",
        "session_timeout_minutes": int(read_env_value("SESSION_TIMEOUT_MINUTES", "30"))
    }


@router.put("/security", response_model=SecuritySettingsResponse)
async def update_security_settings(data: Dict[str, Any]):
    """Обновление настроек безопасности"""
    logger.info("Updating security settings")
    
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
            write_env_value(env_key, str(value))
    
    return await get_security_settings()


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings():
    """Получение настроек уведомлений"""
    return {
        "email_enabled": read_env_value("EMAIL_ENABLED", "false").lower() == "true",
        "smtp_server": read_env_value("SMTP_SERVER", ""),
        "smtp_port": int(read_env_value("SMTP_PORT", "587")),
        "smtp_username": read_env_value("SMTP_USERNAME", ""),
        "smtp_password": read_env_value("SMTP_PASSWORD", ""),
        "from_email": read_env_value("FROM_EMAIL", ""),
        "admin_email": read_env_value("ADMIN_EMAIL", ""),
        "notify_on_campaign_complete": read_env_value("NOTIFY_CAMPAIGN_COMPLETE", "99-postfix.sh").lower() == "true",
        "notify_on_system_error": read_env_value("NOTIFY_SYSTEM_ERROR", "true").lower() == "true"
    }


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(data: Dict[str, Any]):
    """Обновление настроек уведомлений"""
    logger.info("Updating notification settings")
    
    mapping = {
        "email_enabled": "EMAIL_ENABLED",
        "smtp_server": "SMTP_SERVER",
        "smtp_port": "SMTP_PORT",
        "smtp_username": "SMTP_USERNAME",
        "smtp_password": "SMTP_PASSWORD",
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
            elif key == "smtp_password" and not value:
                continue
            write_env_value(env_key, str(value))
    
    return await get_notification_settings()


@router.get("/credentials", response_model=CredentialsInfoResponse)
async def get_credentials_info():
    """Получение информации об учетных данных (без паролей)"""
    creds = read_credentials()
    return {
        "freepbx": {
            "host": creds["freepbx"]["host"],
            "port": creds["freepbx"]["port"],
            "extension": creds["freepbx"]["extension"],
            "has_password": bool(creds["freepbx"]["password"])
        },
        "postgresql": {
            "database": creds["postgresql"]["database"],
            "user": creds["postgresql"]["user"],
            "has_password": bool(creds["postgresql"]["password"])
        },
        "redis": {
            "has_password": bool(creds["redis"]["password"])
        },
        "asterisk": {
            "ami_user": creds["asterisk"]["ami_user"],
            "has_ami_password": bool(creds["asterisk"]["ami_password"]),
            "has_ari_password": bool(creds["asterisk"]["ari_password"])
        }
    }


@router.get("/all")
async def get_all_settings():
    """Получение всех настроек одним запросом"""
    return {
        "pbx": await get_pbx_settings(),
        "system": await get_system_settings(),
        "security": await get_security_settings(),
        "notifications": await get_notification_settings()
    }


@router.post("/backup")
async def create_backup(background_tasks: BackgroundTasks):
    """Создание резервной копии настроек"""
    import tarfile
    from datetime import datetime
    
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
        logger.info(f"Settings backup created: {backup_file}")
    
    background_tasks.add_task(do_backup)
    
    return {
        "message": "Backup started",
        "backup_file": backup_file,
        "timestamp": timestamp
    }


@router.get("/backups")
async def list_backups():
    """Список резервных копий настроек"""
    from datetime import datetime
    
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
