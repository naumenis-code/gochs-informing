#!/usr/bin/env python3
"""API v1 роутер - полная версия"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, contacts, groups, scenarios, 
    campaigns, inbound, playbooks, settings, 
    monitoring, audit
)

api_router = APIRouter()

# Аутентификация и пользователи
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Контакты и группы
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])

# Сценарии и кампании
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])

# Входящие и плейбуки
api_router.include_router(inbound.router, prefix="/inbound", tags=["inbound"])
api_router.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])

# Настройки и мониторинг
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])

# Аудит
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
