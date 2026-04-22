cat > /opt/gochs-informing/installer/app/schemas/__init__.py << 'EOF'
#!/usr/bin/env python3
"""Pydantic schemas"""

from app.schemas.auth import (
    Token, TokenData, UserCreate, UserResponse, LoginRequest
)
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignStatus
)
from app.schemas.settings import (
    PBXSettings, PBXSettingsUpdate, PBXStatusResponse, PBXTestResponse,
    SystemSettings, SystemSettingsUpdate,
    SecuritySettings, SecuritySettingsUpdate,
    NotificationSettings, NotificationSettingsUpdate,
    AllSettingsResponse
)
from app.schemas.audit import (
    AuditLogResponse, AuditStatsResponse, AuditLogCreate
)

__all__ = [
    "Token", "TokenData", "UserCreate", "UserResponse", "LoginRequest",
    "CampaignCreate", "CampaignUpdate", "CampaignResponse", "CampaignStatus",
    "PBXSettings", "PBXSettingsUpdate", "PBXStatusResponse", "PBXTestResponse",
    "SystemSettings", "SystemSettingsUpdate",
    "SecuritySettings", "SecuritySettingsUpdate",
    "NotificationSettings", "NotificationSettingsUpdate",
    "AllSettingsResponse",
    "AuditLogResponse", "AuditStatsResponse", "AuditLogCreate"
]
EOF
