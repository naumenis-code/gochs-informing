#!/usr/bin/env python3
"""
Models module - импорт всех моделей
Соответствует ТЗ, разделы 10, 19, 25
"""

# ============================================================================
# ИМПОРТ МОДЕЛЕЙ
# ============================================================================

# Пользователи
try:
    from app.models.user import User
except ImportError:
    User = None

# Сессии пользователей
try:
    from app.models.user_session import UserSession
except ImportError:
    UserSession = None

# Контакты
try:
    from app.models.contact import Contact
except ImportError:
    Contact = None

# Теги
try:
    from app.models.tag import Tag
except ImportError:
    Tag = None

# Связка контакт-тег (M2M)
try:
    from app.models.contact_tag import ContactTag
except ImportError:
    ContactTag = None

# Группы контактов
try:
    from app.models.contact_group import ContactGroup
except ImportError:
    ContactGroup = None

# Связка контакт-группа (M2M)
try:
    from app.models.contact_group_member import ContactGroupMember
except ImportError:
    ContactGroupMember = None

# Кампании
try:
    from app.models.campaign import Campaign
except ImportError:
    Campaign = None

# Сценарии оповещения
try:
    from app.models.notification_scenario import NotificationScenario
except ImportError:
    NotificationScenario = None

# Плейбуки (для входящих звонков)
try:
    from app.models.playbook import Playbook
except ImportError:
    Playbook = None

# Входящие звонки
try:
    from app.models.inbound_call import InboundCall
except ImportError:
    InboundCall = None

# Попытки вызовов
try:
    from app.models.call_attempt import CallAttempt
except ImportError:
    CallAttempt = None

# Аудит
try:
    from app.models.audit_log import AuditLog
except ImportError:
    AuditLog = None

# Настройки системы
try:
    from app.models.settings import Settings
except ImportError:
    Settings = None

# Настройки Asterisk
try:
    from app.models.asterisk_config import AsteriskConfig
except ImportError:
    AsteriskConfig = None

# Статистика звонков
try:
    from app.models.call_statistics import CallStatistics
except ImportError:
    CallStatistics = None


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
    # Пользователи и сессии
    "User",
    "UserSession",
    
    # Контакты и связи
    "Contact",
    "ContactGroup",
    "ContactGroupMember",
    "Tag",
    "ContactTag",
    
    # Оповещение
    "Campaign",
    "NotificationScenario",
    "Playbook",
    
    # Звонки
    "InboundCall",
    "CallAttempt",
    "CallStatistics",
    
    # Система
    "AuditLog",
    "Settings",
    "AsteriskConfig",
]

# Убираем None значения (для модулей, которые еще не созданы)
__all__ = [name for name in __all__ if globals().get(name) is not None]


# ============================================================================
# ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ
# ============================================================================

# Словарь с описанием каждой модели (для документации/отладки)
MODEL_DESCRIPTIONS = {
    "User": "Пользователи системы (администраторы, операторы)",
    "UserSession": "Сессии пользователей (JWT refresh tokens)",
    "Contact": "Контакты сотрудников для оповещения",
    "Tag": "Теги для категоризации контактов",
    "ContactTag": "Связь many-to-many: контакты <-> теги",
    "ContactGroup": "Группы контактов для массового обзвона",
    "ContactGroupMember": "Связь many-to-many: контакты <-> группы",
    "Campaign": "Кампании массового обзвона",
    "NotificationScenario": "Сценарии голосового оповещения",
    "Playbook": "Сценарии обработки входящих звонков",
    "InboundCall": "Входящие звонки и сообщения",
    "CallAttempt": "Попытки вызовов в рамках кампаний",
    "AuditLog": "Журнал аудита действий пользователей",
    "Settings": "Системные настройки",
    "AsteriskConfig": "Конфигурация подключения к Asterisk/FreePBX",
    "CallStatistics": "Статистика звонков",
}


def get_model_description(model_name: str) -> str:
    """Получить описание модели по имени"""
    return MODEL_DESCRIPTIONS.get(model_name, f"Модель {model_name}")


def get_all_models() -> dict:
    """Получить словарь всех доступных моделей {имя: класс}"""
    return {
        name: globals()[name]
        for name in __all__
        if globals().get(name) is not None
    }


def print_available_models():
    """Вывести список всех доступных моделей (для отладки)"""
    print("=" * 60)
    print("Доступные модели:")
    print("=" * 60)
    for name in __all__:
        model = globals().get(name)
        if model is not None:
            desc = MODEL_DESCRIPTIONS.get(name, "")
            print(f"  ✓ {name:<25} {desc}")
        else:
            print(f"  ✗ {name:<25} (не импортирована)")
    print("=" * 60)
