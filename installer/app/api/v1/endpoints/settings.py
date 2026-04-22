#!/usr/bin/env python3
"""Settings endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db
from app.api.deps import get_current_admin_user
from app.services.settings_service import SettingsService
from app.services.asterisk.asterisk_service import asterisk_service
from app.schemas.settings import (
    PBXSettings, PBXSettingsUpdate,
    SystemSettings, SystemSettingsUpdate,
    SecuritySettings, SecuritySettingsUpdate,
    NotificationSettings, NotificationSettingsUpdate,
    PBXStatusResponse, PBXTestResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== PBX Settings ====================
@router.get("/pbx", response_model=PBXSettings)
async def get_pbx_settings(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    return await service.get_pbx_settings()


@router.put("/pbx", response_model=PBXSettings)
async def update_pbx_settings(
    data: PBXSettingsUpdate,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    settings = await service.update_pbx_settings(data, current_user.id)
    
    # Перезагружаем PJSIP в фоне
    try:
        await asterisk_service.reload_pjsip()
    except Exception as e:
        logger.error(f"Failed to reload PJSIP: {e}")
    
    return settings


@router.get("/pbx/status", response_model=PBXStatusResponse)
async def check_pbx_status(
    current_user = Depends(get_current_admin_user)
):
    try:
        registered = await asterisk_service.check_registration()
        return PBXStatusResponse(registered=registered)
    except Exception as e:
        return PBXStatusResponse(registered=False, message=str(e))


@router.post("/pbx/test", response_model=PBXTestResponse)
async def test_pbx_connection(
    data: PBXSettingsUpdate,
    current_user = Depends(get_current_admin_user)
):
    from app.services.pbx.pbx_service import PBXService
    
    try:
        pbx_service = PBXService()
        result = await pbx_service.test_connection(data.dict())
        return PBXTestResponse(success=result.success, error=result.error)
    except Exception as e:
        return PBXTestResponse(success=False, error=str(e))


@router.post("/pbx/reload")
async def reload_pbx_config(
    current_user = Depends(get_current_admin_user)
):
    try:
        await asterisk_service.reload_pjsip()
        return {"message": "PJSIP configuration reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== System Settings ====================
@router.get("/system", response_model=SystemSettings)
async def get_system_settings(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    return await service.get_system_settings()


@router.put("/system", response_model=SystemSettings)
async def update_system_settings(
    data: SystemSettingsUpdate,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    return await service.update_system_settings(data, current_user.id)


# ==================== Security Settings ====================
@router.get("/security", response_model=SecuritySettings)
async def get_security_settings(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    return await service.get_security_settings()


@router.put("/security", response_model=SecuritySettings)
async def update_security_settings(
    data: SecuritySettingsUpdate,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    return await service.update_security_settings(data, current_user.id)


# ==================== Notification Settings ====================
@router.get("/notifications", response_model=NotificationSettings)
async def get_notification_settings(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    return await service.get_notification_settings()


@router.put("/notifications", response_model=NotificationSettings)
async def update_notification_settings(
    data: NotificationSettingsUpdate,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    service = SettingsService(db)
    return await service.update_notification_settings(data, current_user.id)


# ==================== Backup ====================
@router.post("/backup")
async def create_backup(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.backup_service import BackupService
    
    backup_service = BackupService(db)
    backup_id = await backup_service.create_backup(current_user.id)
    
    return {"backup_id": backup_id, "created_at": datetime.now().isoformat()}


@router.get("/backups")
async def list_backups(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.backup_service import BackupService
    
    backup_service = BackupService(db)
    return await backup_service.list_backups()


@router.post("/backup/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.backup_service import BackupService
    
    backup_service = BackupService(db)
    await backup_service.restore_backup(backup_id, current_user.id)
    
    return {"message": "Backup restored successfully"}
