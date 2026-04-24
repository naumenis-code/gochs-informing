#!/usr/bin/env python3
"""
API v1 router - ПРАВИЛЬНЫЕ ПРЕФИКСЫ ДЛЯ ВСЕХ МОДУЛЕЙ
Соответствует ТЗ, разделы 10, 19, 22, 23

Маршруты API:
- /api/v1/auth/*       — Аутентификация и авторизация
- /api/v1/users/*      — Управление пользователями
- /api/v1/contacts/*   — Управление контактами
- /api/v1/groups/*     — Управление группами
- /api/v1/scenarios/*  — Сценарии оповещения
- /api/v1/campaigns/*  — Кампании обзвона
- /api/v1/inbound/*    — Входящие звонки
- /api/v1/playbooks/*  — Плейбуки входящих звонков
- /api/v1/settings/*   — Системные настройки
- /api/v1/monitoring/* — Мониторинг и статистика
- /api/v1/audit/*      — Журнал аудита
- /api/v1/reports/*    — Отчеты
- /api/v1/health       — Проверка здоровья
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# ============================================================================
# ГЛАВНЫЙ РОУТЕР V1
# ============================================================================

api_router = APIRouter()

# Счетчики для итоговой статистики
registered_modules = 0
failed_modules = 0


# ============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ РЕГИСТРАЦИИ
# ============================================================================

def register_module(
    module_name: str,
    prefix: str,
    tags: list,
    required: bool = False
) -> bool:
    """
    Безопасная регистрация модуля в роутере
    
    Args:
        module_name: имя модуля (для импорта из endpoints)
        prefix: URL префикс
        tags: теги для Swagger
        required: обязательный модуль (создавать заглушку при ошибке)
        
    Returns:
        True если модуль зарегистрирован успешно
    """
    global registered_modules, failed_modules
    
    try:
        # Динамический импорт модуля
        module = __import__(
            f"app.api.v1.endpoints.{module_name}",
            fromlist=["router"]
        )
        
        if hasattr(module, 'router'):
            api_router.include_router(
                module.router,
                prefix=prefix,
                tags=tags
            )
            registered_modules += 1
            logger.info(f"✓ {module_name:15} → {prefix:20} [{', '.join(tags)}]")
            return True
        else:
            logger.error(f"✗ {module_name}: модуль не содержит 'router'")
            failed_modules += 1
            
            if required:
                _create_stub_module(module_name, prefix, tags)
            
            return False
            
    except ImportError as e:
        logger.warning(f"✗ {module_name}: не найден ({e})")
        failed_modules += 1
        
        if required:
            _create_stub_module(module_name, prefix, tags)
        
        return False


def _create_stub_module(module_name: str, prefix: str, tags: list):
    """
    Создание заглушки для обязательного модуля
    
    Используется только для критически важных модулей (audit, auth)
    """
    logger.warning(f"  → Создание заглушки для {module_name} {prefix}")
    
    from fastapi import APIRouter as StubRouter, Query, HTTPException
    from typing import Optional
    from datetime import datetime
    
    stub = StubRouter()
    
    @stub.get("/", tags=tags)
    async def stub_list():
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
            "message": f"Модуль {module_name} не загружен (stub)"
        }
    
    @stub.get("/{item_id}", tags=tags)
    async def stub_get(item_id: str):
        raise HTTPException(
            status_code=503,
            detail=f"Модуль {module_name} недоступен"
        )
    
    @stub.post("/", tags=tags)
    async def stub_create():
        raise HTTPException(
            status_code=503,
            detail=f"Модуль {module_name} недоступен"
        )
    
    @stub.get("/stats/summary", tags=tags)
    async def stub_stats():
        return {"message": f"Статистика {module_name} недоступна"}
    
    api_router.include_router(stub, prefix=prefix, tags=tags)
    logger.warning(f"✓ {module_name:15} → {prefix:20} [STUB] [{', '.join(tags)}]")


# ============================================================================
# РЕГИСТРАЦИЯ ВСЕХ МОДУЛЕЙ
# ============================================================================

logger.info("=" * 70)
logger.info("Регистрация API модулей v1")
logger.info("=" * 70)

# --------------------------------------------------------------------------
# 1. AUTH — Аутентификация (ОБЯЗАТЕЛЬНЫЙ)
# --------------------------------------------------------------------------
register_module(
    module_name="auth",
    prefix="/auth",
    tags=["authentication"],
    required=True
)

# --------------------------------------------------------------------------
# 2. USERS — Пользователи (ОБЯЗАТЕЛЬНЫЙ)
# --------------------------------------------------------------------------
register_module(
    module_name="users",
    prefix="/users",
    tags=["users"],
    required=True
)

# --------------------------------------------------------------------------
# 3. CONTACTS — Контакты
# --------------------------------------------------------------------------
register_module(
    module_name="contacts",
    prefix="/contacts",
    tags=["contacts"]
)

# --------------------------------------------------------------------------
# 4. GROUPS — Группы контактов
# --------------------------------------------------------------------------
register_module(
    module_name="groups",
    prefix="/groups",
    tags=["groups"]
)

# --------------------------------------------------------------------------
# 5. SCENARIOS — Сценарии оповещения
# --------------------------------------------------------------------------
register_module(
    module_name="scenarios",
    prefix="/scenarios",
    tags=["scenarios"]
)

# --------------------------------------------------------------------------
# 6. CAMPAIGNS — Кампании обзвона
# --------------------------------------------------------------------------
register_module(
    module_name="campaigns",
    prefix="/campaigns",
    tags=["campaigns"]
)

# --------------------------------------------------------------------------
# 7. INBOUND — Входящие звонки
# --------------------------------------------------------------------------
register_module(
    module_name="inbound",
    prefix="/inbound",
    tags=["inbound"]
)

# --------------------------------------------------------------------------
# 8. PLAYBOOKS — Плейбуки
# --------------------------------------------------------------------------
register_module(
    module_name="playbooks",
    prefix="/playbooks",
    tags=["playbooks"]
)

# --------------------------------------------------------------------------
# 9. SETTINGS — Настройки системы
# --------------------------------------------------------------------------
register_module(
    module_name="settings",
    prefix="/settings",
    tags=["settings"]
)

# --------------------------------------------------------------------------
# 10. MONITORING — Мониторинг
# --------------------------------------------------------------------------
register_module(
    module_name="monitoring",
    prefix="/monitoring",
    tags=["monitoring"]
)

# --------------------------------------------------------------------------
# 11. AUDIT — Журнал аудита (ОБЯЗАТЕЛЬНЫЙ)
# --------------------------------------------------------------------------
register_module(
    module_name="audit",
    prefix="/audit",
    tags=["audit"],
    required=True
)

# --------------------------------------------------------------------------
# 12. REPORTS — Отчеты
# --------------------------------------------------------------------------
register_module(
    module_name="reports",
    prefix="/reports",
    tags=["reports"]
)

# --------------------------------------------------------------------------
# 13. HEALTH — Проверка здоровья (без префикса)
# --------------------------------------------------------------------------
try:
    from app.api.v1.endpoints import health
    if hasattr(health, 'router'):
        api_router.include_router(health.router, tags=["health"])
        registered_modules += 1
        logger.info(f"✓ health          → (без префикса)     [health]")
    else:
        logger.warning("✗ health: модуль не содержит 'router'")
        failed_modules += 1
except ImportError:
    logger.warning("✗ health: не найден")
    failed_modules += 1


# ============================================================================
# ИТОГОВАЯ СТАТИСТИКА
# ============================================================================

total_routes = len(api_router.routes)
logger.info("=" * 70)
logger.info(f"РЕГИСТРАЦИЯ ЗАВЕРШЕНА")
logger.info(f"  Модулей зарегистрировано: {registered_modules}")
logger.info(f"  Модулей не загружено:     {failed_modules}")
logger.info(f"  Всего маршрутов:          {total_routes}")
logger.info("=" * 70)

# Вывод всех маршрутов (для отладки)
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Зарегистрированные маршруты:")
    for route in api_router.routes:
        logger.debug(f"  {route.methods if hasattr(route, 'methods') else 'GET':10} {route.path}")


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = ["api_router"]
