#!/usr/bin/env python3
"""Audit log model - ПОЛНАЯ МОДЕЛЬ ТАБЛИЦЫ АУДИТА"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class AuditLog(Base):
    """Модель журнала аудита"""
    
    __tablename__ = "audit_logs"
    
    # ========================================================================
    # ОСНОВНЫЕ ПОЛЯ
    # ========================================================================
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Уникальный идентификатор записи"
    )
    
    # ========================================================================
    # ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ
    # ========================================================================
    
    user_id = Column(
        UUID(as_uuid=True), 
        nullable=True,
        comment="ID пользователя (NULL для системных действий)"
    )
    
    user_name = Column(
        String(255), 
        nullable=True,
        comment="Имя пользователя для быстрого отображения"
    )
    
    user_role = Column(
        String(50), 
        nullable=True,
        comment="Роль пользователя на момент действия"
    )
    
    # ========================================================================
    # ИНФОРМАЦИЯ О ДЕЙСТВИИ
    # ========================================================================
    
    action = Column(
        String(100), 
        nullable=False,
        comment="Тип действия (create, update, delete, login, logout, view, export, etc.)"
    )
    
    entity_type = Column(
        String(50), 
        nullable=True,
        comment="Тип объекта (user, campaign, contact, settings, etc.)"
    )
    
    entity_id = Column(
        UUID(as_uuid=True), 
        nullable=True,
        comment="ID объекта"
    )
    
    entity_name = Column(
        String(255), 
        nullable=True,
        comment="Имя/название объекта для быстрого отображения"
    )
    
    # ========================================================================
    # ДЕТАЛИ
    # ========================================================================
    
    details = Column(
        JSON, 
        nullable=True,
        comment="Дополнительные детали в формате JSON"
    )
    
    # ========================================================================
    # ИНФОРМАЦИЯ О ЗАПРОСЕ
    # ========================================================================
    
    ip_address = Column(
        String(45), 
        nullable=True,
        comment="IP адрес (IPv4 или IPv6)"
    )
    
    user_agent = Column(
        Text, 
        nullable=True,
        comment="User-Agent браузера"
    )
    
    request_method = Column(
        String(10), 
        nullable=True,
        comment="HTTP метод (GET, POST, PUT, DELETE, etc.)"
    )
    
    request_path = Column(
        String(500), 
        nullable=True,
        comment="Путь запроса"
    )
    
    # ========================================================================
    # СТАТУС И РЕЗУЛЬТАТ
    # ========================================================================
    
    status = Column(
        String(20), 
        default="success",
        comment="Статус: success, warning, error"
    )
    
    error_message = Column(
        Text, 
        nullable=True,
        comment="Сообщение об ошибке если status='error'"
    )
    
    execution_time_ms = Column(
        Integer, 
        nullable=True,
        comment="Время выполнения в миллисекундах"
    )
    
    # ========================================================================
    # ВРЕМЕННЫЕ МЕТКИ
    # ========================================================================
    
    created_at = Column(
        DateTime(timezone=False), 
        server_default=func.now(),
        comment="Дата и время создания"
    )
    
    # ========================================================================
    # ИНДЕКСЫ
    # ========================================================================
    
    __table_args__ = (
        Index('idx_audit_logs_created_at', 'created_at'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_user_name', 'user_name'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_entity_type', 'entity_type'),
        Index('idx_audit_logs_status', 'status'),
        Index('idx_audit_logs_user_action', 'user_id', 'action'),
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
    )
    
    # ========================================================================
    # МЕТОДЫ
    # ========================================================================
    
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
