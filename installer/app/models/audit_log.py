#!/usr/bin/env python3
"""Audit log model - полная версия"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Index, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class AuditLog(Base):
    """Модель журнала аудита"""
    
    __tablename__ = "audit_logs"
    
    # Основные поля
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Уникальный идентификатор записи")
    
    # Информация о пользователе
    user_id = Column(UUID(as_uuid=True), nullable=True, comment="ID пользователя (NULL для системных действий)")
    user_name = Column(String(255), nullable=True, comment="Имя пользователя для быстрого отображения")
    user_role = Column(String(50), nullable=True, comment="Роль пользователя на момент действия")
    
    # Информация о действии
    action = Column(String(100), nullable=False, comment="Тип действия (create, update, delete, login, logout, view, export, etc.)")
    entity_type = Column(String(50), nullable=True, comment="Тип объекта (user, campaign, contact, settings, etc.)")
    entity_id = Column(UUID(as_uuid=True), nullable=True, comment="ID объекта")
    entity_name = Column(String(255), nullable=True, comment="Имя/название объекта для быстрого отображения")
    
    # Детали
    details = Column(JSON, nullable=True, comment="Дополнительные детали в формате JSON")
    
    # Информация о запросе
    ip_address = Column(String(45), nullable=True, comment="IP адрес (IPv4 или IPv6)")
    user_agent = Column(Text, nullable=True, comment="User-Agent браузера")
    request_method = Column(String(10), nullable=True, comment="HTTP метод")
    request_path = Column(String(500), nullable=True, comment="Путь запроса")
    
    # Статус и результат
    status = Column(String(20), default="success", comment="Статус: success, warning, error")
    error_message = Column(Text, nullable=True, comment="Сообщение об ошибке если status=error")
    execution_time_ms = Column(Integer, nullable=True, comment="Время выполнения в миллисекундах")
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата и время создания")
    
    # Индексы для оптимизации поиска
    __table_args__ = (
        Index('idx_audit_logs_created_at', 'created_at'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_entity_type', 'entity_type'),
        Index('idx_audit_logs_status', 'status'),
        Index('idx_audit_logs_user_action', 'user_id', 'action'),
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user={self.user_name}, created_at={self.created_at})>"
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "id": str(self.id) if self.id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "user_name": self.user_name,
            "user_role": self.user_role,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "entity_name": self.entity_name,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "status": self.status,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def create_from_request(
        cls,
        user_id: uuid.UUID = None,
        user_name: str = None,
        user_role: str = None,
        action: str = "",
        entity_type: str = None,
        entity_id: uuid.UUID = None,
        entity_name: str = None,
        details: dict = None,
        request = None,
        status: str = "success",
        error_message: str = None,
        execution_time_ms: int = None
    ) -> "AuditLog":
        """Создание записи аудита из объекта request"""
        
        ip_address = None
        user_agent = None
        request_method = None
        request_path = None
        
        if request:
            # IP адрес
            if request.client:
                ip_address = request.client.host
            elif request.headers.get("x-forwarded-for"):
                ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()
            elif request.headers.get("x-real-ip"):
                ip_address = request.headers.get("x-real-ip")
            
            # User-Agent
            user_agent = request.headers.get("user-agent", "")
            
            # Метод и путь
            request_method = request.method
            request_path = request.url.path
        
        return cls(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            status=status,
            error_message=error_message,
            execution_time_ms=execution_time_ms
        )
