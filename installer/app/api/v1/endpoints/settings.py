#!/usr/bin/env python3
"""Settings endpoints - ПОЛНАЯ ИТОГОВАЯ ВЕРСИЯ С ЛОГИРОВАНИЕМ В АУДИТ"""

import os
import re
import logging
import socket
import subprocess
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Пути к файлам конфигурации
ENV_FILE = "/opt/gochs-informing/.env"
CRED_FILE = "/opt/gochs-informing/.gochs_credentials"
ASTERISK_PJSIP_CONF = "/etc/asterisk/pjsip.conf"


# ============================================================================
# PYDANTIC MODELS
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
    extension: Optional[str] = None


class PBXTestResponse(BaseModel):
    success: bool
    message: str = ""
    error: Optional[str] = None


class PBXReloadResponse(BaseModel):
    message: str
    success: bool = True


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


# ============================================================================
# HELPER FUNCTIONS
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
    result = {"host": "", "port": 5060, "extension": "", "password": ""}
    try:
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            section = re.search(r'FREE PBX:(.*?)(?:РЕЖИМ SSL:|$)', content, re.DOTALL)
            if section:
                s = section.group(1)
                
                host_match = re.search(r'Хост:\s*([^\s\n]+)', s)
                if host_match:
                    hp = host_match.group(1)
                    if ':' in hp:
                        result["host"], port = hp.split(':', 1)
                        result["port"] = int(port)
                    else:
                        result["host"] = hp
                
                ext_match = re.search(r'Extension:\s*(\S+)', s)
                if ext_match:
                    result["extension"] = ext_match.group(1)
                
                pass_match = re.search(r'Пароль:\s*(\S+)', s)
                if pass_match:
                    result["password"] = pass_match.group(1)
    except Exception as e:
        logger.error(f"Error reading credentials: {e}")
    
    return result


def get_freepbx_config() -> Dict[str, Any]:
    """Получение полной конфигурации FreePBX"""
    # Базовые значения по умолчанию
    config = {
        "host": "192.168.1.10",
        "port": 5060,
        "extension": "gochs",
        "username": "gochs",
        "password": "",
        "transport": "udp",
        "max_channels": 20,
        "codecs": ["ulaw", "alaw"],
        "register_enabled": True
    }
    
    # Читаем из credentials (основной источник)
    creds = read_credentials()
    if creds["host"]:
        config["host"] = creds["host"]
        config["port"] = creds["port"]
    if creds["extension"]:
        config["extension"] = creds["extension"]
        config["username"] = creds["extension"]
    if creds["password"]:
        config["password"] = creds["password"]
    
    # Переопределяем из .env (приоритет выше)
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
    
    env_codecs = read_env_value("FREEPBX_CODECS", "")
    if env_codecs:
        config["codecs"] = env_codecs.split(',')
    
    return config


async def log_audit_event(action: str, details: Optional[Dict] = None, status: str = "success"):
    """Логирование изменений в аудит"""
    try:
        from app.api.v1.endpoints.audit import log_event
        from app.core.database import get_db
        async for db in get_db():
            await log_event(
                db=db,
                user_name="system",
                action=action,
                entity_type="settings",
                details=details,
                status=status
            )
            break
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")


def check_registration_status(config: Dict[str, Any]) -> Dict[str, Any]:
    """Проверка статуса исходящей регистрации на FreePBX"""
    result = {
        "registered": False,
        "message": "",
        "host": config["host"],
        "port": config["port"],
        "extension": config["extension"]
    }
    
    try:
        cmd = "sudo /usr/sbin/asterisk -rx 'pjsip show registrations' 2>&1"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        output = proc.stdout + proc.stderr
        
        for line in output.split('\n'):
            if 'freepbx-registration' in line:
                if 'Registered' in line:
                    result["registered"] = True
                    result["message"] = "Зарегистрирован"
                elif 'Rejected' in line:
                    result["message"] = "Отклонено (проверьте пароль)"
                elif 'AuthSent' in line:
                    result["message"] = "Ожидание аутентификации"
                elif 'Unregistered' in line:
                    result["message"] = "Не зарегистрирован"
                else:
                    result["message"] = "Статус не определен"
                return result
        
        result["message"] = "Регистрация не найдена в Asterisk"
            
    except subprocess.TimeoutExpired:
        result["message"] = "Таймаут запроса к Asterisk"
    except Exception as e:
        result["message"] = f"Ошибка: {str(e)}"
    
    return result


def update_asterisk_pjsip_config(config: Dict[str, Any]) -> bool:
    """Обновление конфигурации PJSIP в Asterisk"""
    try:
        if not os.path.exists(ASTERISK_PJSIP_CONF):
            return False
        
        with open(ASTERISK_PJSIP_CONF, 'r') as f:
            content = f.read()
        
        registration_section = f"""; =====================================================
; РЕГИСТРАЦИЯ НА FREE PBX (автоматически сгенерировано)
; =====================================================
[freepbx-registration]
type = registration
outbound_auth = freepbx-auth
server_uri = sip:{config['host']}:{config['port']}
client_uri = sip:{config['extension']}@{config['host']}:{config['port']}
contact_user = {config['extension']}
retry_interval = 30
expiration = 3600

[freepbx-auth]
type = auth
auth_type = userpass
username = {config['extension']}
password = {config['password']}
realm = asterisk

[freepbx]
type = endpoint
context = gochs-inbound
aors = freepbx-aor
outbound_auth = freepbx-auth
disallow = all
allow = {','.join(config['codecs'])}
dtmf_mode = rfc4733
rtp_symmetric = yes
force_rport = yes
rewrite_contact = yes
direct_media = no
callerid = "GOCHS" <{config['extension']}>
from_user = {config['extension']}
from_domain = {config['host']}

[freepbx-aor]
type = aor
contact = sip:{config['host']}:{config['port']}
max_contacts = 1
remove_existing = yes

[freepbx-identify]
type = identify
endpoint = freepbx
match = {config['host']}
"""
        
        pattern = r'; =+.*?РЕГИСТРАЦИЯ НА FREE PBX.*?\[freepbx-identify\][^\[]*'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, registration_section, content, flags=re.DOTALL)
        else:
            content += "\n" + registration_section
        
        with open(ASTERISK_PJSIP_CONF, 'w') as f:
            f.write(content)
        
        logger.info("Asterisk PJSIP config updated")
        return True
        
    except Exception as e:
        logger.error(f"Error updating PJSIP config: {e}")
        return False


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/pbx", response_model=PBXSettingsResponse)
async def get_pbx_settings():
    """Получение настроек FreePBX"""
    config = get_freepbx_config()
    await log_audit_event("view", {"section": "pbx"})
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
    """Обновление настроек FreePBX с сохранением и логированием"""
    logger.info("Updating PBX settings")
    
    # Сохраняем в .env
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
        write_env_value("FREEPBX_CODECS", ','.join(data["codecs"]) if isinstance(data["codecs"], list) else str(data["codecs"]))
    
    # Обновляем credentials файл
    try:
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE, 'r', encoding='utf-8') as f:
                cred_content = f.read()
            
            host_val = data.get("host", "192.168.1.10")
            port_val = data.get("port", 5060)
            ext_val = data.get("extension", "gochs")
            pass_val = data.get("password") or read_env_value("FREEPBX_PASSWORD", "")
            
            new_freepbx = f"""FREE PBX:
  Хост: {host_val}:{port_val}
  Extension: {ext_val}
  Пароль: {pass_val}
"""
            
            pattern = r'FREE PBX:.*?(?=РЕЖИМ SSL:|$)'
            cred_content = re.sub(pattern, new_freepbx, cred_content, flags=re.DOTALL)
            
            with open(CRED_FILE, 'w', encoding='utf-8') as f:
                f.write(cred_content)
            
            logger.info("Credentials file updated")
    except Exception as e:
        logger.error(f"Failed to update credentials: {e}")
    
    # Логируем в аудит
    changes = {k: v for k, v in data.items() if v is not None}
    await log_audit_event("update_settings", {"section": "pbx", "changes": changes})
    
    return await get_pbx_settings()


@router.post("/pbx/apply")
async def apply_pbx_settings(background_tasks: BackgroundTasks):
    """Применение настроек FreePBX к Asterisk"""
    config = get_freepbx_config()
    config_updated = update_asterisk_pjsip_config(config)
    
    def reload_task():
        subprocess.run(["sudo", "/usr/sbin/asterisk", "-rx", "pjsip reload"], 
                      capture_output=True, timeout=10)
    
    background_tasks.add_task(reload_task)
    
    status = check_registration_status(config)
    await log_audit_event("apply_settings", {"section": "pbx", "config_updated": config_updated})
    
    return {
        "message": "Настройки применены" if config_updated else "Ошибка применения",
        "config_updated": config_updated,
        "registration_status": status
    }


@router.get("/pbx/status", response_model=PBXStatusResponse)
async def check_pbx_status():
    """Проверка статуса регистрации в FreePBX"""
    config = get_freepbx_config()
    return check_registration_status(config)


@router.post("/pbx/test", response_model=PBXTestResponse)
async def test_pbx_connection(data: Dict[str, Any]):
    """Тестирование подключения к FreePBX"""
    host = data.get("host", "")
    port = data.get("port", 5060)
    
    if not host:
        return {"success": False, "message": "Не указан хост", "error": "Host is required"}
    
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


@router.post("/pbx/reload", response_model=PBXReloadResponse)
async def reload_pbx_config():
    """Принудительная перезагрузка PJSIP"""
    try:
        cmd = ["sudo", "/usr/sbin/asterisk", "-rx", "pjsip reload"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if proc.returncode == 0:
            await log_audit_event("reload", {"section": "pbx", "success": True})
            return {"message": "PJSIP reloaded successfully", "success": True}
        else:
            return {"message": f"Reload failed: {proc.stderr}", "success": False}
    except Exception as e:
        return {"message": f"Error: {str(e)}", "success": False}


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
    """Обновление системных настроек с логированием"""
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
    
    await log_audit_event("update_settings", {"section": "system"})
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
    """Обновление настроек безопасности с логированием"""
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
    
    await log_audit_event("update_settings", {"section": "security"})
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
        "notify_on_campaign_complete": read_env_value("NOTIFY_CAMPAIGN_COMPLETE", "true").lower() == "true",
        "notify_on_system_error": read_env_value("NOTIFY_SYSTEM_ERROR", "true").lower() == "true"
    }


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(data: Dict[str, Any]):
    """Обновление настроек уведомлений с логированием"""
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
    
    await log_audit_event("update_settings", {"section": "notifications"})
    return await get_notification_settings()


@router.get("/credentials")
async def get_credentials_info():
    """Получение информации об учетных данных (без паролей)"""
    creds = read_credentials()
    
    return {
        "freepbx": {
            "host": creds["host"],
            "port": int(creds["port"]) if creds["port"] else 5060,
            "extension": creds["extension"],
            "has_password": bool(creds["password"])
        }
    }


@router.post("/backup")
async def create_backup(background_tasks: BackgroundTasks):
    """Создание резервной копии настроек"""
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
        logger.info(f"Settings backup created: {backup_file}")
    
    background_tasks.add_task(do_backup)
    await log_audit_event("backup", {"file": backup_file})
    
    return {
        "message": "Backup started",
        "backup_file": backup_file,
        "timestamp": timestamp
    }


@router.get("/backups")
async def list_backups():
    """Список резервных копий настроек"""
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


@router.post("/reset")
async def reset_settings():
    """Сброс настроек к значениям по умолчанию"""
    default_settings = {
        "FREEPBX_HOST": "192.168.1.10:5060",
        "FREEPBX_PORT": "5060",
        "FREEPBX_EXTENSION": "gochs",
        "FREEPBX_USERNAME": "gochs",
        "FREEPBX_PASSWORD": "",
        "FREEPBX_TRANSPORT": "udp",
        "FREEPBX_ENABLED": "true",
        "MAX_CONCURRENT_CALLS": "20",
        "APP_NAME": "ГО-ЧС Информирование",
        "TIMEZONE": "Europe/Moscow",
        "LOG_LEVEL": "INFO",
        "RECORDING_RETENTION_DAYS": "90",
        "BACKUP_ENABLED": "true",
        "BACKUP_TIME": "02:00",
        "JWT_EXPIRE_MINUTES": "60",
        "REFRESH_TOKEN_EXPIRE_DAYS": "7",
        "MAX_LOGIN_ATTEMPTS": "5",
        "LOCKOUT_MINUTES": "15",
        "PASSWORD_MIN_LENGTH": "8",
        "REQUIRE_SPECIAL_CHARS": "true",
        "SESSION_TIMEOUT_MINUTES": "30",
        "EMAIL_ENABLED": "false",
        "SMTP_PORT": "587",
        "NOTIFY_CAMPAIGN_COMPLETE": "true",
        "NOTIFY_SYSTEM_ERROR": "true"
    }
    
    for key, value in default_settings.items():
        write_env_value(key, value)
    
    logger.info("Settings reset to defaults")
    await log_audit_event("reset_settings")
    return {"message": "Settings reset to defaults", "success": True}
