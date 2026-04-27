#!/usr/bin/env python3
"""Models module"""

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

# Плейбуки
try:
    from app.models.playbook import Playbook
except ImportError:
    Playbook = None

# Аудит
try:
    from app.models.audit_log import AuditLog
except ImportError:
    AuditLog = None

__all__ = [name for name in ["User", "Contact", "ContactGroup", "Playbook", "AuditLog"] 
           if globals().get(name) is not None]
