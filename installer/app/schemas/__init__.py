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
        UserCreate as AuthUserCreate,
        UserResponse as AuthUserResponse,
        LoginRequest,
        RefreshTokenRequest,
        LogoutResponse,
        PasswordChangeRequest,
        PasswordResetRequest,
    )
    AUTH_SCHEMAS = [
        "Token", "TokenData", "AuthUserCreate", "AuthUserResponse", "LoginRequest",
        "RefreshTokenRequest", "LogoutResponse", "PasswordChangeRequest", "PasswordResetRequest"
    ]
except ImportError as e:
    logger.warning(f"Auth schemas not available: {e}")
    Token = None
    TokenData = None
    AuthUserCreate = None
    AuthUserResponse = None
    LoginRequest = None
    RefreshTokenRequest = None
    LogoutResponse = None
    PasswordChangeRequest = None
    PasswordResetRequest = None
    AUTH_SCHEMAS = []

# ============================================================================
# USER SCHEMAS (НОВЫЕ - из 09)
# ============================================================================
try:
    from app.schemas.user import (
        UserRole,
        UserStatus,
        UserBase,
        UserCreate,
        UserUpdate,
        UserPasswordChange,
        UserPasswordReset,
        UserResponse as UserDetailResponse,
        UserListResponse,
        UserLoginResponse,
        UserFilterParams,
    )
    USER_SCHEMAS = [
        "UserRole", "UserStatus", "UserBase", "UserCreate", "UserUpdate",
        "UserPasswordChange", "UserPasswordReset", "UserDetailResponse",
        "UserListResponse", "UserLoginResponse", "UserFilterParams"
    ]
except ImportError as e:
    logger.warning(f"User schemas not available: {e}")
    UserRole = None
    UserStatus = None
    UserBase = None
    UserCreate = None
    UserUpdate = None
    UserPasswordChange = None
    UserPasswordReset = None
    UserDetailResponse = None
    UserListResponse = None
    UserLoginResponse = None
    UserFilterParams = None
    USER_SCHEMAS = []

# ============================================================================
# CONTACT SCHEMAS (НОВЫЕ - из 10)
# ============================================================================
try:
    from app.schemas.contact import (
        ContactBase,
        ContactCreate,
        ContactUpdate,
        ContactResponse,
        ContactListResponse,
        ContactTagInfo,
        ContactGroupInfo,
        ContactImportRow,
        ContactImportRequest,
        ContactExportRequest,
        ContactFilterParams,
        ContactBulkAction,
        ContactBulkDelete,
        ContactStats,
    )
    CONTACT_SCHEMAS = [
        "ContactBase", "ContactCreate", "ContactUpdate", "ContactResponse",
        "ContactListResponse", "ContactTagInfo", "ContactGroupInfo",
        "ContactImportRow", "ContactImportRequest", "ContactExportRequest",
        "ContactFilterParams", "ContactBulkAction", "ContactBulkDelete",
        "ContactStats"
    ]
except ImportError as e:
    logger.warning(f"Contact schemas not available: {e}")
    ContactBase = None
    ContactCreate = None
    ContactUpdate = None
    ContactResponse = None
    ContactListResponse = None
    ContactTagInfo = None
    ContactGroupInfo = None
    ContactImportRow = None
    ContactImportRequest = None
    ContactExportRequest = None
    ContactFilterParams = None
    ContactBulkAction = None
    ContactBulkDelete = None
    ContactStats = None
    CONTACT_SCHEMAS = []

# ============================================================================
# GROUP SCHEMAS (НОВЫЕ - из 11)
# ============================================================================
try:
    from app.schemas.group import (
        GroupBase,
        GroupCreate,
        GroupUpdate,
        GroupResponse,
        GroupListResponse,
        GroupDetailResponse,
        GroupMemberInfo,
        GroupFilterParams,
        GroupBulkAction,
        GroupMergeRequest,
        GroupStats,
        GroupDialerInfo,
        AddMembersRequest,
        RemoveMembersRequest,
        UpdateMemberRequest,
    )
    GROUP_SCHEMAS = [
        "GroupBase", "GroupCreate", "GroupUpdate", "GroupResponse",
        "GroupListResponse", "GroupDetailResponse", "GroupMemberInfo",
        "GroupFilterParams", "GroupBulkAction", "GroupMergeRequest",
        "GroupStats", "GroupDialerInfo", "AddMembersRequest",
        "RemoveMembersRequest", "UpdateMemberRequest"
    ]
except ImportError as e:
    logger.warning(f"Group schemas not available: {e}")
    GroupBase = None
    GroupCreate = None
    GroupUpdate = None
    GroupResponse = None
    GroupListResponse = None
    GroupDetailResponse = None
    GroupMemberInfo = None
    GroupFilterParams = None
    GroupBulkAction = None
    GroupMergeRequest = None
    GroupStats = None
    GroupDialerInfo = None
    AddMembersRequest = None
    RemoveMembersRequest = None
    UpdateMemberRequest = None
    GROUP_SCHEMAS = []

# ============================================================================
# PLAYBOOK SCHEMAS (НОВЫЕ - из 12)
# ============================================================================
try:
    from app.schemas.playbook import (
        GreetingSource,
        PlaybookCategory,
        PlaybookStatus,
        PlaybookBase,
        PlaybookCreate,
        PlaybookUpdate,
        PlaybookStatusUpdate,
        PlaybookResponse,
        PlaybookListResponse,
        PlaybookCloneRequest,
        TTSGenerateRequest,
        TTSGenerateResponse,
        AudioUploadResponse,
        PlaybookTestRequest,
        PlaybookTestResponse,
    )
    PLAYBOOK_SCHEMAS = [
        "GreetingSource", "PlaybookCategory", "PlaybookStatus",
        "PlaybookBase", "PlaybookCreate", "PlaybookUpdate",
        "PlaybookStatusUpdate", "PlaybookResponse", "PlaybookListResponse",
        "PlaybookCloneRequest", "TTSGenerateRequest", "TTSGenerateResponse",
        "AudioUploadResponse", "PlaybookTestRequest", "PlaybookTestResponse"
    ]
except ImportError as e:
    logger.warning(f"Playbook schemas not available: {e}")
    GreetingSource = None
    PlaybookCategory = None
    PlaybookStatus = None
    PlaybookBase = None
    PlaybookCreate = None
    PlaybookUpdate = None
    PlaybookStatusUpdate = None
    PlaybookResponse = None
    PlaybookListResponse = None
    PlaybookCloneRequest = None
    TTSGenerateRequest = None
    TTSGenerateResponse = None
    AudioUploadResponse = None
    PlaybookTestRequest = None
    PlaybookTestResponse = None
    PLAYBOOK_SCHEMAS = []

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
# SETTINGS SCHEMAS
# ============================================================================
try:
    from app.schemas.settings import (
        PBXSettings, PBXSettingsUpdate, PBXSettingsResponse,
        PBXStatusResponse, PBXTestResponse, PBXReloadResponse, PBXApplyResponse,
        SystemSettings, SystemSettingsUpdate, SystemSettingsResponse,
        SecuritySettings, SecuritySettingsUpdate, SecuritySettingsResponse,
        NotificationSettings, NotificationSettingsUpdate, NotificationSettingsResponse,
        AllSettingsResponse, CredentialsInfoResponse,
        BackupResponse, BackupListItem, BackupsListResponse,
        ResetSettingsResponse, TransportType, LogLevel,
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
        AuditStatus, AuditLogBase, AuditLogCreate, AuditLogUpdate,
        AuditLogResponse, AuditStatsResponse, DailyStatsResponse,
        UserActivityResponse, AuditLogFilterParams, AuditLogListResponse,
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
# COMMON SCHEMAS (НОВЫЕ - из 08)
# ============================================================================
try:
    from app.schemas.common import (
        PaginationParams,
        PaginatedResponse,
        MessageResponse,
        ErrorResponse,
        SuccessResponse,
        IDResponse,
        BulkOperationResult,
        SortParams,
        FilterParam,
        SearchParams,
        DateRangeParams,
        TimeRangeParams,
        ExportParams,
        FileUploadResponse,
        AudioFileInfo,
        SelectOption,
        StatsOverview,
        CountItem,
        StatsByCategory,
    )
    COMMON_SCHEMAS = [
        "PaginationParams", "PaginatedResponse", "MessageResponse",
        "ErrorResponse", "SuccessResponse", "IDResponse", "BulkOperationResult",
        "SortParams", "FilterParam", "SearchParams", "DateRangeParams",
        "TimeRangeParams", "ExportParams", "FileUploadResponse", "AudioFileInfo",
        "SelectOption", "StatsOverview", "CountItem", "StatsByCategory"
    ]
except ImportError as e:
    logger.warning(f"Common schemas not available: {e}")
    PaginationParams = None
    PaginatedResponse = None
    MessageResponse = None
    ErrorResponse = None
    SuccessResponse = None
    IDResponse = None
    BulkOperationResult = None
    SortParams = None
    FilterParam = None
    SearchParams = None
    DateRangeParams = None
    TimeRangeParams = None
    ExportParams = None
    FileUploadResponse = None
    AudioFileInfo = None
    SelectOption = None
    StatsOverview = None
    CountItem = None
    StatsByCategory = None
    COMMON_SCHEMAS = []

# ============================================================================
# ЭКСПОРТ ВСЕХ СХЕМ
# ============================================================================

__all__ = []

__all__.extend(AUTH_SCHEMAS)
__all__.extend(USER_SCHEMAS)
__all__.extend(CONTACT_SCHEMAS)
__all__.extend(GROUP_SCHEMAS)
__all__.extend(PLAYBOOK_SCHEMAS)
__all__.extend(CAMPAIGN_SCHEMAS)
__all__.extend(SCENARIO_SCHEMAS)
__all__.extend(INBOUND_SCHEMAS)
__all__.extend(SETTINGS_SCHEMAS)
__all__.extend(AUDIT_SCHEMAS)
__all__.extend(MONITORING_SCHEMAS)
__all__.extend(COMMON_SCHEMAS)

# Убираем дубликаты (сохраняя порядок)
__all__ = list(dict.fromkeys(__all__))


# ============================================================================
# ОЧИСТКА None ЗНАЧЕНИЙ
# ============================================================================
def _cleanup_none_exports():
    """Удаляет None значения из глобального пространства и __all__"""
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
    
    if keys_to_remove:
        logger.info(f"Removed {len(keys_to_remove)} unavailable schemas: {keys_to_remove}")

_cleanup_none_exports()


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_available_schemas() -> dict:
    """Получить словарь доступных схем по категориям"""
    categories = {
        "auth": AUTH_SCHEMAS,
        "user": USER_SCHEMAS,
        "contact": CONTACT_SCHEMAS,
        "group": GROUP_SCHEMAS,
        "playbook": PLAYBOOK_SCHEMAS,
        "campaign": CAMPAIGN_SCHEMAS,
        "scenario": SCENARIO_SCHEMAS,
        "inbound": INBOUND_SCHEMAS,
        "settings": SETTINGS_SCHEMAS,
        "audit": AUDIT_SCHEMAS,
        "monitoring": MONITORING_SCHEMAS,
        "common": COMMON_SCHEMAS,
    }
    
    result = {}
    for category, names in categories.items():
        available = [name for name in names if globals().get(name) is not None]
        if available:
            result[category] = available
    
    return result


def print_schemas_summary():
    """Вывести сводку по доступным схемам (для отладки)"""
    print("=" * 70)
    print("ДОСТУПНЫЕ PYDANTIC СХЕМЫ")
    print("=" * 70)
    
    available = get_available_schemas()
    total = 0
    
    for category, names in available.items():
        print(f"\n{category.upper()} ({len(names)}):")
        for name in names:
            schema = globals().get(name)
            if schema:
                doc = schema.__doc__ or ""
                doc_first_line = doc.strip().split('\n')[0] if doc else "-"
                print(f"  ✓ {name:<35} {doc_first_line[:40]}")
                total += 1
    
    print(f"\n{'=' * 70}")
    print(f"Всего доступно схем: {total}")
    print(f"Всего в __all__: {len(__all__)}")
    print(f"{'=' * 70}")
