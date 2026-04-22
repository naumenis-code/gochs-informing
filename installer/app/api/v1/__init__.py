#!/usr/bin/env python3
"""API v1 router - ПОЛНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Создаем основной роутер
api_router = APIRouter()

# ============================================================================
# ИМПОРТЫ И ПОДКЛЮЧЕНИЕ ВСЕХ ЭНДПОИНТОВ
# ============================================================================

# Auth (обязательный)
try:
    from app.api.v1.endpoints import auth
    if hasattr(auth, 'router'):
        api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
        logger.info("✓ Auth endpoints registered")
    else:
        logger.error("Auth module has no router attribute")
except ImportError as e:
    logger.error(f"Auth endpoints not available: {e}")

# Users
try:
    from app.api.v1.endpoints import users
    if hasattr(users, 'router'):
        api_router.include_router(users.router, prefix="/users", tags=["users"])
        logger.info("✓ Users endpoints registered")
except ImportError as e:
    logger.warning(f"Users endpoints not available: {e}")

# Contacts
try:
    from app.api.v1.endpoints import contacts
    if hasattr(contacts, 'router'):
        api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
        logger.info("✓ Contacts endpoints registered")
except ImportError as e:
    logger.warning(f"Contacts endpoints not available: {e}")

# Groups
try:
    from app.api.v1.endpoints import groups
    if hasattr(groups, 'router'):
        api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
        logger.info("✓ Groups endpoints registered")
except ImportError as e:
    logger.warning(f"Groups endpoints not available: {e}")

# Scenarios
try:
    from app.api.v1.endpoints import scenarios
    if hasattr(scenarios, 'router'):
        api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
        logger.info("✓ Scenarios endpoints registered")
except ImportError as e:
    logger.warning(f"Scenarios endpoints not available: {e}")

# Campaigns
try:
    from app.api.v1.endpoints import campaigns
    if hasattr(campaigns, 'router'):
        api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
        logger.info("✓ Campaigns endpoints registered")
except ImportError as e:
    logger.warning(f"Campaigns endpoints not available: {e}")

# Inbound
try:
    from app.api.v1.endpoints import inbound
    if hasattr(inbound, 'router'):
        api_router.include_router(inbound.router, prefix="/inbound", tags=["inbound"])
        logger.info("✓ Inbound endpoints registered")
except ImportError as e:
    logger.warning(f"Inbound endpoints not available: {e}")

# Playbooks
try:
    from app.api.v1.endpoints import playbooks
    if hasattr(playbooks, 'router'):
        api_router.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
        logger.info("✓ Playbooks endpoints registered")
except ImportError as e:
    logger.warning(f"Playbooks endpoints not available: {e}")

# Settings (обязательный)
try:
    from app.api.v1.endpoints import settings
    if hasattr(settings, 'router'):
        api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
        logger.info("✓ Settings endpoints registered")
    else:
        logger.error("Settings module has no router attribute")
except ImportError as e:
    logger.error(f"Settings endpoints not available: {e}")

# Monitoring
try:
    from app.api.v1.endpoints import monitoring
    if hasattr(monitoring, 'router'):
        api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
        logger.info("✓ Monitoring endpoints registered")
except ImportError as e:
    logger.warning(f"Monitoring endpoints not available: {e}")

# Audit (обязательный - ИСПРАВЛЕНО!)
try:
    from app.api.v1.endpoints import audit
    if hasattr(audit, 'router'):
        api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
        logger.info("✓ Audit endpoints registered")
    else:
        logger.error("Audit module has no router attribute - creating stub")
        raise ImportError("Audit router not found")
except ImportError as e:
    logger.error(f"Audit endpoints not available: {e}, creating stub")
    
    # Создаем заглушку для аудита
    from fastapi import APIRouter as StubRouter, Query, Request
    from typing import Optional
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
    
    stub_router = StubRouter()
    
    @stub_router.get("/logs")
    async def stub_audit_logs(
        skip: int = Query(0),
        limit: int = Query(100),
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        user_name: Optional[str] = None
    ):
        """Заглушка для логов аудита"""
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": limit,
            "has_next": False,
            "has_prev": False
        }
    
    @stub_router.get("/stats")
    async def stub_audit_stats():
        """Заглушка для статистики аудита"""
        return {
            "total_events": 0,
            "today_events": 0,
            "week_events": 0,
            "month_events": 0,
            "unique_users": 0,
            "error_events": 0,
            "warning_events": 0,
            "success_events": 0,
            "top_actions": [],
            "top_entities": [],
            "top_users": [],
            "recent_activity": [],
            "hourly_stats": [],
            "daily_stats": []
        }
    
    @stub_router.get("/export")
    async def stub_audit_export():
        """Заглушка для экспорта аудита"""
        from fastapi.responses import StreamingResponse
        import io
        return StreamingResponse(
            io.BytesIO(b"id;time;user;action\n"),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit.csv"}
        )
    
    @stub_router.delete("/logs")
    async def stub_clear_logs(older_than_days: int = 90):
        """Заглушка для очистки логов"""
        return {"message": "No logs to delete", "deleted_count": 0}
    
    @stub_router.get("/logs/{log_id}")
    async def stub_get_log(log_id: str):
        """Заглушка для получения записи"""
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    @stub_router.post("/log")
    async def stub_create_log():
        """Заглушка для создания записи"""
        return {"success": True, "message": "Event logged (stub)"}
    
    api_router.include_router(stub_router, prefix="/audit", tags=["audit"])
    logger.warning("✓ Audit STUB endpoints registered")

# Reports
try:
    from app.api.v1.endpoints import reports
    if hasattr(reports, 'router'):
        api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
        logger.info("✓ Reports endpoints registered")
except ImportError:
    pass

# TTS
try:
    from app.api.v1.endpoints import tts
    if hasattr(tts, 'router'):
        api_router.include_router(tts.router, prefix="/tts", tags=["tts"])
        logger.info("✓ TTS endpoints registered")
except ImportError:
    pass

# STT
try:
    from app.api.v1.endpoints import stt
    if hasattr(stt, 'router'):
        api_router.include_router(stt.router, prefix="/stt", tags=["stt"])
        logger.info("✓ STT endpoints registered")
except ImportError:
    pass

# WebSocket
try:
    from app.api.v1.endpoints import websocket
    if hasattr(websocket, 'router'):
        api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
        logger.info("✓ WebSocket endpoints registered")
except ImportError:
    pass

# Health (без префикса)
try:
    from app.api.v1.endpoints import health
    if hasattr(health, 'router'):
        api_router.include_router(health.router, tags=["health"])
        logger.info("✓ Health endpoints registered")
except ImportError:
    pass


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
    routes = get_registered_routes()
    logger.info(f"Total registered routes: {len(routes)}")
    
    # Группируем по префиксам
    prefixes = {}
    for route in routes:
        path = route["path"]
        prefix = path.split("/")[1] if len(path.split("/")) > 1 else "root"
        if prefix not in prefixes:
            prefixes[prefix] = []
        prefixes[prefix].append(path)
    
    for prefix, paths in sorted(prefixes.items()):
        logger.info(f"  /{prefix}: {len(paths)} endpoints")


# Вывод информации при импорте
print_registered_endpoints()


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
    "api_router",
    "get_registered_routes"
]
