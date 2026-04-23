#!/usr/bin/env python3
"""Pydantic schemas - ПОЛНЫЙ ИМПОРТ ВСЕХ СХЕМ"""

import logging

logger = logging.getLogger(__name__)

# ============================================================================
# AUTH SCHEMAS
# ============================================================================
try:
    from app.schemas.auth import (
        Token,
        TokenData,
        UserCreate,
        UserResponse,
        LoginRequest,
        RefreshTokenRequest,
        LogoutResponse,
        PasswordChangeRequest,
        PasswordResetRequest,
    )
    AUTH_SCHEMAS = [
        "Token", "TokenData", "UserCreate", "UserResponse", "LoginRequest",
        "RefreshTokenRequest", "LogoutResponse", "PasswordChangeRequest", "PasswordResetRequest"
    ]
except ImportError as e:
    logger.warning(f"Auth schemas not available: {e}")
    Token = None
    TokenData = None
    UserCreate = None
    UserResponse = None
    LoginRequest = None
    RefreshTokenRequest = None
    LogoutResponse = None
    PasswordChangeRequest = None
    PasswordResetRequest = None
    AUTH_SCHEMAS = []

# ============================================================================
# USER SCHEMAS
# ============================================================================
try:
    from app.schemas.user import (
        User,
        UserListResponse,
        UserUpdateRequest,
        UserRole,
    )
    USER_SCHEMAS = ["User", "UserListResponse", "UserUpdateRequest", "UserRole"]
except ImportError:
    User = None
    UserListResponse = None
    UserUpdateRequest = None
    UserRole = None
    USER_SCHEMAS = []

# ============================================================================
# CAMPAIGN SCHEMAS
# ============================================================================
try:
    from app.schemas.campaign import (
        CampaignCreate,
        CampaignUpdate,
        CampaignResponse,
        CampaignStatus,
        CampaignListResponse,
        CampaignStartRequest,
        CampaignStopRequest,
        CampaignStats,
    )
    CAMPAIGN_SCHEMAS = [
        "CampaignCreate", "CampaignUpdate", "CampaignResponse", "CampaignStatus",
        "CampaignListResponse", "CampaignStartRequest", "CampaignStopRequest", "CampaignStats"
    ]
except ImportError:
    CampaignCreate = None
    CampaignUpdate = None
    CampaignResponse = None
    CampaignStatus = None
    CampaignListResponse = None
    CampaignStartRequest = None
    CampaignStopRequest = None
    CampaignStats = None
    CAMPAIGN_SCHEMAS = []

# ============================================================================
# CONTACT SCHEMAS
# ============================================================================
try:
    from app.schemas.contact import (
        ContactCreate,
        ContactUpdate,
        ContactResponse,
        ContactListResponse,
        ContactImportResponse,
    )
    CONTACT_SCHEMAS = [
        "ContactCreate", "ContactUpdate", "ContactResponse",
        "ContactListResponse", "ContactImportResponse"
    ]
except ImportError:
    ContactCreate = None
    ContactUpdate = None
    ContactResponse = None
    ContactListResponse = None
    ContactImportResponse = None
    CONTACT_SCHEMAS = []

# ============================================================================
# GROUP SCHEMAS
# ============================================================================
try:
    from app.schemas.group import (
        GroupCreate,
        GroupUpdate,
        GroupResponse,
        GroupListResponse,
        GroupMembersRequest,
    )
    GROUP_SCHEMAS = [
        "GroupCreate", "GroupUpdate", "GroupResponse",
        "GroupListResponse", "GroupMembersRequest"
    ]
except ImportError:
    GroupCreate = None
    GroupUpdate = None
    GroupResponse = None
    GroupListResponse = None
    GroupMembersRequest = None
    GROUP_SCHEMAS = []

# ============================================================================
# SCENARIO SCHEMAS
# ============================================================================
try:
    from app.schemas.scenario import (
        ScenarioCreate,
        ScenarioUpdate,
        ScenarioResponse,
        ScenarioListResponse,
        ScenarioAudioUploadResponse,
    )
    SCENARIO_SCHEMAS = [
        "ScenarioCreate", "ScenarioUpdate", "ScenarioResponse",
        "ScenarioListResponse", "ScenarioAudioUploadResponse"
    ]
except ImportError:
    ScenarioCreate = None
    ScenarioUpdate = None
    ScenarioResponse = None
    ScenarioListResponse = None
    ScenarioAudioUploadResponse = None
    SCENARIO_SCHEMAS = []

# ============================================================================
# INBOUND SCHEMAS
# ============================================================================
try:
    from app.schemas.inbound import (
        InboundCallCreate,
        InboundCallResponse,
        InboundCallListResponse,
        InboundRecordingResponse,
    )
    INBOUND_SCHEMAS = [
        "InboundCallCreate", "InboundCallResponse",
        "InboundCallListResponse", "InboundRecordingResponse"
    ]
except ImportError:
    InboundCallCreate = None
    InboundCallResponse = None
    InboundCallListResponse = None
    InboundRecordingResponse = None
    INBOUND_SCHEMAS = []

# ============================================================================
# PLAYBOOK SCHEMAS
# ============================================================================
try:
    from app.schemas.playbook import (
        PlaybookCreate,
        PlaybookUpdate,
        PlaybookResponse,
        PlaybookListResponse,
        PlaybookActivateRequest,
    )
    PLAYBOOK_SCHEMAS = [
        "PlaybookCreate", "PlaybookUpdate", "PlaybookResponse",
        "PlaybookListResponse", "PlaybookActivateRequest"
    ]
except ImportError:
    PlaybookCreate = None
    PlaybookUpdate = None
    PlaybookResponse = None
    PlaybookListResponse = None
    PlaybookActivateRequest = None
    PLAYBOOK_SCHEMAS = []

# ============================================================================
# SETTINGS SCHEMAS
# ============================================================================
try:
    from app.schemas.settings import (
        # PBX
        PBXSettings,
        PBXSettingsUpdate,
        PBXSettingsResponse,
        PBXStatusResponse,
        PBXTestResponse,
        PBXReloadResponse,
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
        LogLevel,
    )
    SETTINGS_SCHEMAS = [
        "PBXSettings", "PBXSettingsUpdate", "PBXSettingsResponse",
        "PBXStatusResponse", "PBXTestResponse", "PBXReloadResponse", "PBXApplyResponse",
        "SystemSettings", "SystemSettingsUpdate", "SystemSettingsResponse",
        "SecuritySettings", "SecuritySettingsUpdate", "SecuritySettingsResponse",
        "NotificationSettings", "NotificationSettingsUpdate", "NotificationSettingsResponse",
        "AllSettingsResponse", "CredentialsInfoResponse",
        "BackupResponse", "BackupListItem", "BackupsListResponse",
        "ResetSettingsResponse", "TransportType", "LogLevel"
    ]
except ImportError as e:
    logger.warning(f"Settings schemas not available: {e}")
    PBXSettings = None
    PBXSettingsUpdate = None
    PBXSettingsResponse = None
    PBXStatusResponse = None
    PBXTestResponse = None
    PBXReloadResponse = None
    PBXApplyResponse = None
    SystemSettings = None
    SystemSettingsUpdate = None
    SystemSettingsResponse = None
    SecuritySettings = None
    SecuritySettingsUpdate = None
    SecuritySettingsResponse = None
    NotificationSettings = None
    NotificationSettingsUpdate = None
    NotificationSettingsResponse = None
    AllSettingsResponse = None
    CredentialsInfoResponse = None
    BackupResponse = None
    BackupListItem = None
    BackupsListResponse = None
    ResetSettingsResponse = None
    TransportType = None
    LogLevel = None
    SETTINGS_SCHEMAS = []

# ============================================================================
# AUDIT SCHEMAS
# ============================================================================
try:
    from app.schemas.audit import (
        AuditStatus,
        AuditLogBase,
        AuditLogCreate,
        AuditLogUpdate,
        AuditLogResponse,
        AuditStatsResponse,
        DailyStatsResponse,
        UserActivityResponse,
        AuditLogFilterParams,
        AuditLogListResponse,
        ClearOldLogsResponse,
    )
    AUDIT_SCHEMAS = [
        "AuditStatus", "AuditLogBase", "AuditLogCreate", "AuditLogUpdate",
        "AuditLogResponse", "AuditStatsResponse", "DailyStatsResponse",
        "UserActivityResponse", "AuditLogFilterParams", "AuditLogListResponse",
        "ClearOldLogsResponse"
    ]
except ImportError as e:
    logger.warning(f"Audit schemas not available: {e}")
    AuditStatus = None
    AuditLogBase = None
    AuditLogCreate = None
    AuditLogUpdate = None
    AuditLogResponse = None
    AuditStatsResponse = None
    DailyStatsResponse = None
    UserActivityResponse = None
    AuditLogFilterParams = None
    AuditLogListResponse = None
    ClearOldLogsResponse = None
    AUDIT_SCHEMAS = []

# ============================================================================
# MONITORING SCHEMAS
# ============================================================================
try:
    from app.schemas.monitoring import (
        HealthCheckResponse,
        SystemStatsResponse,
        ServiceStatusResponse,
        MetricsResponse,
    )
    MONITORING_SCHEMAS = [
        "HealthCheckResponse", "SystemStatsResponse",
        "ServiceStatusResponse", "MetricsResponse"
    ]
except ImportError:
    HealthCheckResponse = None
    SystemStatsResponse = None
    ServiceStatusResponse = None
    MetricsResponse = None
    MONITORING_SCHEMAS = []

# ============================================================================
# COMMON SCHEMAS
# ============================================================================
try:
    from app.schemas.common import (
        PaginationParams,
        PaginatedResponse,
        SortParams,
        FilterParams,
        ErrorResponse,
        SuccessResponse,
    )
    COMMON_SCHEMAS = [
        "PaginationParams", "PaginatedResponse", "SortParams",
        "FilterParams", "ErrorResponse", "SuccessResponse"
    ]
except ImportError:
    PaginationParams = None
    PaginatedResponse = None
    SortParams = None
    FilterParams = None
    ErrorResponse = None
    SuccessResponse = None
    COMMON_SCHEMAS = []

# ============================================================================
# ЭКСПОРТ ВСЕХ СХЕМ
# ============================================================================

__all__ = []

__all__.extend(AUTH_SCHEMAS)
__all__.extend(USER_SCHEMAS)
__all__.extend(CAMPAIGN_SCHEMAS)
__all__.extend(CONTACT_SCHEMAS)
__all__.extend(GROUP_SCHEMAS)
__all__.extend(SCENARIO_SCHEMAS)
__all__.extend(INBOUND_SCHEMAS)
__all__.extend(PLAYBOOK_SCHEMAS)
__all__.extend(SETTINGS_SCHEMAS)
__all__.extend(AUDIT_SCHEMAS)
__all__.extend(MONITORING_SCHEMAS)
__all__.extend(COMMON_SCHEMAS)

# Убираем дубликаты
__all__ = list(dict.fromkeys(__all__))


# ============================================================================
# ОЧИСТКА None ЗНАЧЕНИЙ
# ============================================================================
def _cleanup_none_exports():
    """Удаляет None значения из глобального пространства"""
    import sys
    frame = sys._getframe(1)
    globals_dict = frame.f_globals
    
    keys_to_remove = []
    for key, value in list(globals_dict.items()):
        if value is None and key in __all__:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del globals_dict[key]
        if key in __all__:
            __all__.remove(key)

_cleanup_none_exports()
