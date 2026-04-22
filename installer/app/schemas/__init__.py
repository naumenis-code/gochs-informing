#!/usr/bin/env python3
"""Pydantic schemas - полная версия со всеми импортами"""

# ============================================================================
# AUTH SCHEMAS
# ============================================================================
from app.schemas.auth import (
    Token,
    TokenData,
    UserCreate,
    UserResponse,
    LoginRequest,
    RefreshTokenRequest,
    LogoutResponse
)

# ============================================================================
# CAMPAIGN SCHEMAS
# ============================================================================
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignStatus,
    CampaignListResponse,
    CampaignStartRequest,
    CampaignStopRequest
)

# ============================================================================
# CONTACT SCHEMAS
# ============================================================================
try:
    from app.schemas.contact import (
        ContactCreate,
        ContactUpdate,
        ContactResponse,
        ContactListResponse
    )
except ImportError:
    pass

# ============================================================================
# GROUP SCHEMAS
# ============================================================================
try:
    from app.schemas.group import (
        GroupCreate,
        GroupUpdate,
        GroupResponse,
        GroupListResponse
    )
except ImportError:
    pass

# ============================================================================
# SCENARIO SCHEMAS
# ============================================================================
try:
    from app.schemas.scenario import (
        ScenarioCreate,
        ScenarioUpdate,
        ScenarioResponse,
        ScenarioListResponse
    )
except ImportError:
    pass

# ============================================================================
# SETTINGS SCHEMAS
# ============================================================================
from app.schemas.settings import (
    # PBX
    PBXSettings,
    PBXSettingsUpdate,
    PBXSettingsResponse,
    PBXStatusResponse,
    PBXTestResponse,
    PBXReloadResponse,
    PBXRestartResponse,
    PBXApplyResponse,
    # System
    SystemSettings,
    SystemSettingsUpdate,
    SystemSettingsResponse,
    # Security
    SecuritySettings,
    SecuritySettingsUpdate,
    SecuritySettingsResponse,
    # Notifications
    NotificationSettings,
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    # All
    AllSettingsResponse,
    # Credentials
    CredentialsInfoResponse,
    # Backup
    BackupResponse,
    BackupListItem,
    BackupsListResponse,
    # Reset
    ResetSettingsResponse,
    # Enums
    TransportType,
    LogLevel
)

# ============================================================================
# AUDIT SCHEMAS
# ============================================================================
from app.schemas.audit import (
    # Status enum
    AuditStatus,
    # Base schemas
    AuditLogBase,
    AuditLogCreate,
    AuditLogUpdate,
    AuditLogResponse,
    # Stats schemas
    AuditStatsResponse,
    DailyStatsResponse,
    UserActivityResponse,
    # Filter schemas
    AuditLogFilterParams,
    AuditLogListResponse,
    # Response schemas
    ClearOldLogsResponse
)

# ============================================================================
# MONITORING SCHEMAS
# ============================================================================
try:
    from app.schemas.monitoring import (
        HealthCheckResponse,
        SystemStatsResponse,
        ServiceStatusResponse
    )
except ImportError:
    pass

# ============================================================================
# INBOUND SCHEMAS
# ============================================================================
try:
    from app.schemas.inbound import (
        InboundCallCreate,
        InboundCallResponse,
        InboundCallListResponse
    )
except ImportError:
    pass

# ============================================================================
# PLAYBOOK SCHEMAS
# ============================================================================
try:
    from app.schemas.playbook import (
        PlaybookCreate,
        PlaybookUpdate,
        PlaybookResponse,
        PlaybookListResponse
    )
except ImportError:
    pass

# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Auth
    "Token",
    "TokenData",
    "UserCreate",
    "UserResponse",
    "LoginRequest",
    "RefreshTokenRequest",
    "LogoutResponse",
    
    # Campaign
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignResponse",
    "CampaignStatus",
    "CampaignListResponse",
    "CampaignStartRequest",
    "CampaignStopRequest",
    
    # Contact (if available)
    "ContactCreate",
    "ContactUpdate",
    "ContactResponse",
    "ContactListResponse",
    
    # Group (if available)
    "GroupCreate",
    "GroupUpdate",
    "GroupResponse",
    "GroupListResponse",
    
    # Scenario (if available)
    "ScenarioCreate",
    "ScenarioUpdate",
    "ScenarioResponse",
    "ScenarioListResponse",
    
    # Settings - PBX
    "PBXSettings",
    "PBXSettingsUpdate",
    "PBXSettingsResponse",
    "PBXStatusResponse",
    "PBXTestResponse",
    "PBXReloadResponse",
    "PBXRestartResponse",
    "PBXApplyResponse",
    
    # Settings - System
    "SystemSettings",
    "SystemSettingsUpdate",
    "SystemSettingsResponse",
    
    # Settings - Security
    "SecuritySettings",
    "SecuritySettingsUpdate",
    "SecuritySettingsResponse",
    
    # Settings - Notifications
    "NotificationSettings",
    "NotificationSettingsUpdate",
    "NotificationSettingsResponse",
    
    # Settings - Other
    "AllSettingsResponse",
    "CredentialsInfoResponse",
    "BackupResponse",
    "BackupListItem",
    "BackupsListResponse",
    "ResetSettingsResponse",
    
    # Settings - Enums
    "TransportType",
    "LogLevel",
    
    # Audit - Status
    "AuditStatus",
    
    # Audit - Base
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogUpdate",
    "AuditLogResponse",
    
    # Audit - Stats
    "AuditStatsResponse",
    "DailyStatsResponse",
    "UserActivityResponse",
    
    # Audit - Filter
    "AuditLogFilterParams",
    "AuditLogListResponse",
    
    # Audit - Response
    "ClearOldLogsResponse",
    
    # Monitoring (if available)
    "HealthCheckResponse",
    "SystemStatsResponse",
    "ServiceStatusResponse",
    
    # Inbound (if available)
    "InboundCallCreate",
    "InboundCallResponse",
    "InboundCallListResponse",
    
    # Playbook (if available)
    "PlaybookCreate",
    "PlaybookUpdate",
    "PlaybookResponse",
    "PlaybookListResponse",
]

# Убираем None значения из __all__ (для несуществующих модулей)
__all__ = [name for name in __all__ if name in globals()]
