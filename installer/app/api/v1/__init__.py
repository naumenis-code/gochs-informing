#!/usr/bin/env python3
"""API v1 router - ПОЛНАЯ версия со всеми эндпоинтами и обработкой ошибок"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# ============================================================================
# ИМПОРТЫ МОДУЛЕЙ С ОБРАБОТКОЙ ОШИБОК
# ============================================================================

# Auth
try:
    from app.api.v1.endpoints import auth
    AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Auth endpoints not available: {e}")
    auth = None
    AUTH_AVAILABLE = False

# Users
try:
    from app.api.v1.endpoints import users
    USERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Users endpoints not available: {e}")
    users = None
    USERS_AVAILABLE = False

# Contacts
try:
    from app.api.v1.endpoints import contacts
    CONTACTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Contacts endpoints not available: {e}")
    contacts = None
    CONTACTS_AVAILABLE = False

# Groups
try:
    from app.api.v1.endpoints import groups
    GROUPS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Groups endpoints not available: {e}")
    groups = None
    GROUPS_AVAILABLE = False

# Scenarios
try:
    from app.api.v1.endpoints import scenarios
    SCENARIOS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Scenarios endpoints not available: {e}")
    scenarios = None
    SCENARIOS_AVAILABLE = False

# Campaigns
try:
    from app.api.v1.endpoints import campaigns
    CAMPAIGNS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Campaigns endpoints not available: {e}")
    campaigns = None
    CAMPAIGNS_AVAILABLE = False

# Inbound
try:
    from app.api.v1.endpoints import inbound
    INBOUND_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Inbound endpoints not available: {e}")
    inbound = None
    INBOUND_AVAILABLE = False

# Playbooks
try:
    from app.api.v1.endpoints import playbooks
    PLAYBOOKS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Playbooks endpoints not available: {e}")
    playbooks = None
    PLAYBOOKS_AVAILABLE = False

# Settings
try:
    from app.api.v1.endpoints import settings
    SETTINGS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Settings endpoints not available: {e}")
    settings = None
    SETTINGS_AVAILABLE = False

# Monitoring
try:
    from app.api.v1.endpoints import monitoring
    MONITORING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Monitoring endpoints not available: {e}")
    monitoring = None
    MONITORING_AVAILABLE = False

# Audit
try:
    from app.api.v1.endpoints import audit
    AUDIT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Audit endpoints not available: {e}")
    audit = None
    AUDIT_AVAILABLE = False

# Reports
try:
    from app.api.v1.endpoints import reports
    REPORTS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Reports endpoints not available: {e}")
    reports = None
    REPORTS_AVAILABLE = False

# TTS
try:
    from app.api.v1.endpoints import tts
    TTS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"TTS endpoints not available: {e}")
    tts = None
    TTS_AVAILABLE = False

# STT
try:
    from app.api.v1.endpoints import stt
    STT_AVAILABLE = True
except ImportError as e:
    logger.debug(f"STT endpoints not available: {e}")
    stt = None
    STT_AVAILABLE = False

# WebSocket
try:
    from app.api.v1.endpoints import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError as e:
    logger.debug(f"WebSocket endpoints not available: {e}")
    websocket = None
    WEBSOCKET_AVAILABLE = False

# Health
try:
    from app.api.v1.endpoints import health
    HEALTH_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Health endpoints not available: {e}")
    health = None
    HEALTH_AVAILABLE = False


# ============================================================================
# СОЗДАНИЕ РОУТЕРА
# ============================================================================

api_router = APIRouter()


# ============================================================================
# ПОДКЛЮЧЕНИЕ ЭНДПОИНТОВ
# ============================================================================

# Health (всегда первым, без префикса)
if HEALTH_AVAILABLE and health:
    try:
        api_router.include_router(health.router, tags=["health"])
        logger.info("✓ Health endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register health endpoints: {e}")

# Auth
if AUTH_AVAILABLE and auth:
    try:
        api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
        logger.info("✓ Auth endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register auth endpoints: {e}")

# Users
if USERS_AVAILABLE and users:
    try:
        api_router.include_router(users.router, prefix="/users", tags=["users"])
        logger.info("✓ Users endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register users endpoints: {e}")

# Contacts
if CONTACTS_AVAILABLE and contacts:
    try:
        api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
        logger.info("✓ Contacts endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register contacts endpoints: {e}")

# Groups
if GROUPS_AVAILABLE and groups:
    try:
        api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
        logger.info("✓ Groups endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register groups endpoints: {e}")

# Scenarios
if SCENARIOS_AVAILABLE and scenarios:
    try:
        api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
        logger.info("✓ Scenarios endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register scenarios endpoints: {e}")

# Campaigns
if CAMPAIGNS_AVAILABLE and campaigns:
    try:
        api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
        logger.info("✓ Campaigns endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register campaigns endpoints: {e}")

# Inbound
if INBOUND_AVAILABLE and inbound:
    try:
        api_router.include_router(inbound.router, prefix="/inbound", tags=["inbound"])
        logger.info("✓ Inbound endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register inbound endpoints: {e}")

# Playbooks
if PLAYBOOKS_AVAILABLE and playbooks:
    try:
        api_router.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
        logger.info("✓ Playbooks endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register playbooks endpoints: {e}")

# Settings
if SETTINGS_AVAILABLE and settings:
    try:
        api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
        logger.info("✓ Settings endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register settings endpoints: {e}")

# Monitoring
if MONITORING_AVAILABLE and monitoring:
    try:
        api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
        logger.info("✓ Monitoring endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register monitoring endpoints: {e}")

# Audit
if AUDIT_AVAILABLE and audit:
    try:
        api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
        logger.info("✓ Audit endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register audit endpoints: {e}")

# Reports
if REPORTS_AVAILABLE and reports:
    try:
        api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
        logger.info("✓ Reports endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register reports endpoints: {e}")

# TTS
if TTS_AVAILABLE and tts:
    try:
        api_router.include_router(tts.router, prefix="/tts", tags=["tts"])
        logger.info("✓ TTS endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register TTS endpoints: {e}")

# STT
if STT_AVAILABLE and stt:
    try:
        api_router.include_router(stt.router, prefix="/stt", tags=["stt"])
        logger.info("✓ STT endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register STT endpoints: {e}")

# WebSocket
if WEBSOCKET_AVAILABLE and websocket:
    try:
        api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
        logger.info("✓ WebSocket endpoints registered")
    except Exception as e:
        logger.error(f"Failed to register WebSocket endpoints: {e}")


# ============================================================================
# ДЕБАГ ИНФОРМАЦИЯ
# ============================================================================

def get_registered_routes() -> list:
    """Получение списка зарегистрированных маршрутов"""
    routes = []
    for route in api_router.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods) if route.methods else []
        })
    return routes


def print_registered_endpoints():
    """Вывод зарегистрированных эндпоинтов в лог"""
    available = []
    unavailable = []
    
    if AUTH_AVAILABLE: available.append("auth")
    else: unavailable.append("auth")
    
    if USERS_AVAILABLE: available.append("users")
    else: unavailable.append("users")
    
    if CONTACTS_AVAILABLE: available.append("contacts")
    else: unavailable.append("contacts")
    
    if GROUPS_AVAILABLE: available.append("groups")
    else: unavailable.append("groups")
    
    if SCENARIOS_AVAILABLE: available.append("scenarios")
    else: unavailable.append("scenarios")
    
    if CAMPAIGNS_AVAILABLE: available.append("campaigns")
    else: unavailable.append("campaigns")
    
    if INBOUND_AVAILABLE: available.append("inbound")
    else: unavailable.append("inbound")
    
    if PLAYBOOKS_AVAILABLE: available.append("playbooks")
    else: unavailable.append("playbooks")
    
    if SETTINGS_AVAILABLE: available.append("settings")
    else: unavailable.append("settings")
    
    if MONITORING_AVAILABLE: available.append("monitoring")
    else: unavailable.append("monitoring")
    
    if AUDIT_AVAILABLE: available.append("audit")
    else: unavailable.append("audit")
    
    if REPORTS_AVAILABLE: available.append("reports")
    else: unavailable.append("reports")
    
    if TTS_AVAILABLE: available.append("tts")
    else: unavailable.append("tts")
    
    if STT_AVAILABLE: available.append("stt")
    else: unavailable.append("stt")
    
    if WEBSOCKET_AVAILABLE: available.append("websocket")
    else: unavailable.append("websocket")
    
    if HEALTH_AVAILABLE: available.append("health")
    else: unavailable.append("health")
    
    logger.info(f"Available endpoints: {', '.join(available)}")
    if unavailable:
        logger.info(f"Unavailable endpoints: {', '.join(unavailable)}")


# Вывод информации при импорте
print_registered_endpoints()


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
    "api_router",
    "get_registered_routes",
    "AUTH_AVAILABLE",
    "USERS_AVAILABLE",
    "CONTACTS_AVAILABLE",
    "GROUPS_AVAILABLE",
    "SCENARIOS_AVAILABLE",
    "CAMPAIGNS_AVAILABLE",
    "INBOUND_AVAILABLE",
    "PLAYBOOKS_AVAILABLE",
    "SETTINGS_AVAILABLE",
    "MONITORING_AVAILABLE",
    "AUDIT_AVAILABLE",
    "REPORTS_AVAILABLE",
    "TTS_AVAILABLE",
    "STT_AVAILABLE",
    "WEBSOCKET_AVAILABLE",
    "HEALTH_AVAILABLE"
]
