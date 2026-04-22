#!/usr/bin/env python3
"""Audit schemas"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class AuditStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class AuditLogBase(BaseModel):
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: AuditStatus = AuditStatus.SUCCESS


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AuditStatsResponse(BaseModel):
    total_events: int
    today_events: int
    unique_users: int
    error_events: int
    top_actions: List[dict]
    recent_activity: List[dict]
