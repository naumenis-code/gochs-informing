#!/usr/bin/env python3
"""API v1 router - ПРАВИЛЬНЫЕ ПРЕФИКСЫ ДЛЯ ВСЕХ МОДУЛЕЙ"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
api_router = APIRouter()

# ============================================================================
# AUTH - префикс /auth
# ============================================================================
try:
    from app.api.v1.endpoints import auth
    if hasattr(auth, 'router'):
        api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
        logger.info("✓ Auth endpoints registered at /auth")
    else:
        logger.error("Auth module has no router")
except ImportError as e:
    logger.error(f"Auth endpoints not available: {e}")

# ============================================================================
# USERS - префикс /users
# ============================================================================
try:
    from app.api.v1.endpoints import users
    if hasattr(users, 'router'):
        api_router.include_router(users.router, prefix="/users", tags=["users"])
        logger.info("✓ Users endpoints registered at /users")
except ImportError:
    pass

# ============================================================================
# CONTACTS - префикс /contacts
# ============================================================================
try:
    from app.api.v1.endpoints import contacts
    if hasattr(contacts, 'router'):
        api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
        logger.info("✓ Contacts endpoints registered at /contacts")
except ImportError:
    pass

# ============================================================================
# GROUPS - префикс /groups
# ============================================================================
try:
    from app.api.v1.endpoints import groups
    if hasattr(groups, 'router'):
        api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
        logger.info("✓ Groups endpoints registered at /groups")
except ImportError:
    pass

# ============================================================================
# SCENARIOS - префикс /scenarios
# ============================================================================
try:
    from app.api.v1.endpoints import scenarios
    if hasattr(scenarios, 'router'):
        api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
        logger.info("✓ Scenarios endpoints registered at /scenarios")
except ImportError:
    pass

# ============================================================================
# CAMPAIGNS - префикс /campaigns
# ============================================================================
try:
    from app.api.v1.endpoints import campaigns
    if hasattr(campaigns, 'router'):
        api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
        logger.info("✓ Campaigns endpoints registered at /campaigns")
except ImportError:
    pass

# ============================================================================
# INBOUND - префикс /inbound
# ============================================================================
try:
    from app.api.v1.endpoints import inbound
    if hasattr(inbound, 'router'):
        api_router.include_router(inbound.router, prefix="/inbound", tags=["inbound"])
        logger.info("✓ Inbound endpoints registered at /inbound")
except ImportError:
    pass

# ============================================================================
# PLAYBOOKS - префикс /playbooks
# ============================================================================
try:
    from app.api.v1.endpoints import playbooks
    if hasattr(playbooks, 'router'):
        api_router.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
        logger.info("✓ Playbooks endpoints registered at /playbooks")
except ImportError:
    pass

# ============================================================================
# SETTINGS - префикс /settings
# ============================================================================
try:
    from app.api.v1.endpoints import settings
    if hasattr(settings, 'router'):
        api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
        logger.info("✓ Settings endpoints registered at /settings")
    else:
        logger.error("Settings module has no router")
except ImportError as e:
    logger.error(f"Settings endpoints not available: {e}")

# ============================================================================
# MONITORING - префикс /monitoring
# ============================================================================
try:
    from app.api.v1.endpoints import monitoring
    if hasattr(monitoring, 'router'):
        api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
        logger.info("✓ Monitoring endpoints registered at /monitoring")
except ImportError:
    pass

# ============================================================================
# AUDIT - префикс /audit (ВАЖНО: не /auth!)
# ============================================================================
try:
    from app.api.v1.endpoints import audit
    if hasattr(audit, 'router'):
        api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
        logger.info("✓ Audit endpoints registered at /audit")
    else:
        logger.error("Audit module has no router - creating stub")
        raise ImportError("Audit router not found")
except ImportError as e:
    logger.error(f"Audit endpoints not available: {e}, creating stub")
    
    # Создаем заглушку для аудита
    from fastapi import APIRouter as StubRouter, Query
    from typing import Optional
    
    stub_router = StubRouter()
    
    @stub_router.get("/logs")
    async def stub_logs(skip: int = Query(0), limit: int = Query(100)):
        return {"items": [], "total": 0, "page": 1, "page_size": limit}
    
    @stub_router.get("/stats")
    async def stub_stats():
        return {"total_events": 0, "today_events": 0, "week_events": 0, "month_events": 0}
    
    @stub_router.get("/export")
    async def stub_export():
        from fastapi.responses import StreamingResponse
        import io
        return StreamingResponse(
            io.BytesIO(b"id;time;user;action\n"),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit.csv"}
        )
    
    @stub_router.post("/log")
    async def stub_log():
        return {"success": True, "message": "Event logged (stub)"}
    
    api_router.include_router(stub_router, prefix="/audit", tags=["audit"])
    logger.warning("✓ Audit STUB endpoints registered at /audit")

# ============================================================================
# REPORTS - префикс /reports
# ============================================================================
try:
    from app.api.v1.endpoints import reports
    if hasattr(reports, 'router'):
        api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
        logger.info("✓ Reports endpoints registered at /reports")
except ImportError:
    pass

# ============================================================================
# HEALTH - без префикса
# ============================================================================
try:
    from app.api.v1.endpoints import health
    if hasattr(health, 'router'):
        api_router.include_router(health.router, tags=["health"])
        logger.info("✓ Health endpoints registered")
except ImportError:
    pass

# ============================================================================
# ИТОГ
# ============================================================================
logger.info(f"API router configured with {len(api_router.routes)} routes")
