#!/usr/bin/env python3
"""Models module - импорт всех моделей"""

# ============================================================================
# ИМПОРТ МОДЕЛЕЙ
# ============================================================================

# Пользователи
try:
    from app.models.user import User
except ImportError:
    User = None

# Контакты
try:
    from app.models.contact import Contact
except ImportError:
    Contact = None

# Группы контактов
try:
    from app.models.contact_group import ContactGroup
except ImportError:
    ContactGroup = None

# Кампании
try:
    from app.models.campaign import Campaign
except ImportError:
    Campaign = None

# Сценарии
try:
    from app.models.scenario import Scenario
except ImportError:
    Scenario = None

# Плейбуки
try:
    from app.models.playbook import Playbook
except ImportError:
    Playbook = None

# Входящие звонки
try:
    from app.models.inbound_call import InboundCall
except ImportError:
    InboundCall = None

# Аудит
try:
    from app.models.audit_log import AuditLog
except ImportError:
    AuditLog = None

# Сессии пользователей
try:
    from app.models.user_session import UserSession
except ImportError:
    UserSession = None


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
    "User",
    "Contact",
    "ContactGroup",
    "Campaign",
    "Scenario",
    "Playbook",
    "InboundCall",
    "AuditLog",
    "UserSession",
]

# Убираем None значения
__all__ = [name for name in __all__ if globals().get(name) is not None]#!/usr/bin/env python3
"""Models module - импорт всех моделей"""

# ============================================================================
# ИМПОРТ МОДЕЛЕЙ
# ============================================================================

# Пользователи
try:
    from app.models.user import User
except ImportError:
    User = None

# Контакты
try:
    from app.models.contact import Contact
except ImportError:
    Contact = None

# Группы контактов
try:
    from app.models.contact_group import ContactGroup
except ImportError:
    ContactGroup = None

# Кампании
try:
    from app.models.campaign import Campaign
except ImportError:
    Campaign = None

# Сценарии
try:
    from app.models.scenario import Scenario
except ImportError:
    Scenario = None

# Плейбуки
try:
    from app.models.playbook import Playbook
except ImportError:
    Playbook = None

# Входящие звонки
try:
    from app.models.inbound_call import InboundCall
except ImportError:
    InboundCall = None

# Аудит
try:
    from app.models.audit_log import AuditLog
except ImportError:
    AuditLog = None

# Сессии пользователей
try:
    from app.models.user_session import UserSession
except ImportError:
    UserSession = None


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
    "User",
    "Contact",
    "ContactGroup",
    "Campaign",
    "Scenario",
    "Playbook",
    "InboundCall",
    "AuditLog",
    "UserSession",
]

# Убираем None значения
__all__ = [name for name in __all__ if globals().get(name) is not None]
