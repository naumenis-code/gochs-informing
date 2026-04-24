#!/usr/bin/env python3
"""
Модель плейбука для ГО-ЧС Информирование
Соответствует ТЗ, раздел 19: Playbook входящих звонков

Плейбук — это сценарий/скрипт, который проигрывается при входящем звонке.
Содержит приветствие, инструкции и сигнал для записи сообщения.
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, 
    Index, UniqueConstraint, ForeignKey, Float, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Playbook(Base):
    """
    Модель плейбука — сценарий обработки входящего звонка
    
    Пример плейбука (ТЗ, раздел 19):
    "Здравствуйте. Вы позвонили в систему ГО-ЧС информирования предприятия.
    После сигнала оставьте сообщение."
    
    Компоненты плейбука:
    1. Приветственное сообщение (аудиофайл или TTS-текст)
    2. Пауза перед сигналом
    3. Звуковой сигнал (beep)
    4. Запись сообщения (максимальная длительность)
    5. Завершающее сообщение
    
    Особенности:
    - Можно создать из текста (TTS) или загрузить готовый WAV/MP3
    - Только Администратор может создавать/редактировать
    - Только один плейбук может быть активным одновременно
    - Поддержка нескольких языков (русский по умолчанию)
    - Аудит всех изменений
    """
    
    __tablename__ = "playbooks"
    __table_args__ = (
        Index("idx_playbooks_name", "name"),
        Index("idx_playbooks_is_active", "is_active"),
        Index("idx_playbooks_language", "language"),
        Index("idx_playbooks_created_at", "created_at"),
        Index("idx_playbooks_category", "category"),
        {"comment": "Плейбуки — сценарии обработки входящих звонков"}
    )
    
    # =========================================================================
    # Основные поля
    # =========================================================================
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Уникальный идентификатор плейбука"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название плейбука"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Описание плейбука (для чего используется)"
    )
    
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Категория (например: общий, экстренный, тестовый)"
    )
    
    # =========================================================================
    # Содержимое плейбука
    # =========================================================================
    
    # Текст приветствия (для TTS или как субтитры)
    greeting_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Текст приветственного сообщения"
    )
    
    # Путь к аудиофайлу приветствия (WAV/MP3)
    greeting_audio_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Путь к аудиофайлу приветствия (WAV/MP3)"
    )
    
    # Тип источника приветствия
    greeting_source: Mapped[str] = mapped_column(
        String(20),
        default="tts",
        nullable=False,
        comment="Источник приветствия: tts, uploaded, none"
    )
    
    # Текст после сигнала (опционально)
    post_beep_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Текст после сигнала (инструкция для звонящего)"
    )
    
    # Путь к аудиофайлу после сигнала
    post_beep_audio_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Путь к аудиофайлу после сигнала"
    )
    
    # Завершающее сообщение
    closing_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Текст завершающего сообщения"
    )
    
    closing_audio_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Путь к аудиофайлу завершающего сообщения"
    )
    
    # =========================================================================
    # Настройки воспроизведения
    # =========================================================================
    
    # Длительность сигнала (в секундах)
    beep_duration: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="Длительность звукового сигнала в секундах"
    )
    
    # Пауза перед сигналом (в секундах)
    pause_before_beep: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        nullable=False,
        comment="Пауза перед сигналом в секундах"
    )
    
    # Максимальная длительность записи сообщения (в секундах)
    max_recording_duration: Mapped[int] = mapped_column(
        Integer,
        default=300,
        nullable=False,
        comment="Максимальная длительность записи (секунд)"
    )
    
    # Минимальная длительность записи (в секундах)
    min_recording_duration: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="Минимальная длительность записи (секунд)"
    )
    
    # Количество повторов приветствия (0 = без повтора)
    greeting_repeat: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Количество повторов приветствия (0 = без повтора)"
    )
    
    # Интервал между повторами (секунд)
    repeat_interval: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Интервал между повторами приветствия (секунд)"
    )
    
    # =========================================================================
    # Языковые настройки
    # =========================================================================
    
    language: Mapped[str] = mapped_column(
        String(10),
        default="ru",
        nullable=False,
        comment="Язык плейбука (ru, en, ...)"
    )
    
    # Голос для TTS
    tts_voice: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Голос для TTS (например: ru_male, ru_female)"
    )
    
    # Скорость речи для TTS (1.0 = нормальная)
    tts_speed: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="Скорость речи TTS (0.5 - 2.0)"
    )
    
    # =========================================================================
    # Статусные поля
    # =========================================================================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Активен ли плейбук (используется для входящих звонков)"
    )
    
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="В архиве (мягкое удаление)"
    )
    
    is_template: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Является ли шаблоном (можно клонировать)"
    )
    
    # Версия плейбука (для отслеживания изменений)
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Версия плейбука"
    )
    
    # =========================================================================
    # Статистика использования
    # =========================================================================
    
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Количество использований (входящих звонков)"
    )
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата/время последнего использования"
    )
    
    # =========================================================================
    # Аудит и метаданные
    # =========================================================================
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто создал плейбук"
    )
    
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто последним обновил"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата/время создания"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Дата/время последнего обновления"
    )
    
    # =========================================================================
    # Связи (relationships)
    # =========================================================================
    
    # Создатель
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        backref="created_playbooks",
        lazy="selectin"
    )
    
    # Редактор
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
        backref="updated_playbooks",
        lazy="selectin"
    )
    
    # =========================================================================
    # Свойства (properties)
    # =========================================================================
    
    @property
    def has_greeting_audio(self) -> bool:
        """Есть ли аудиофайл приветствия"""
        return bool(self.greeting_audio_path)
    
    @property
    def has_post_beep_audio(self) -> bool:
        """Есть ли аудиофайл после сигнала"""
        return bool(self.post_beep_audio_path)
    
    @property
    def has_closing_audio(self) -> bool:
        """Есть ли аудиофайл завершения"""
        return bool(self.closing_audio_path)
    
    @property
    def total_duration(self) -> float:
        """
        Примерная общая длительность плейбука (секунд)
        (без учета записи сообщения)
        """
        duration = 0.0
        
        # Приветствие (примерная оценка: 5 слов/сек для русского)
        if self.greeting_text:
            words = len(self.greeting_text.split())
            duration += words / 5.0  # Примерно 5 слов в секунду
        elif self.has_greeting_audio:
            duration += 10.0  # Примерная оценка для аудио
        
        # Умножаем на количество повторов
        if self.greeting_repeat > 0:
            duration *= self.greeting_repeat
            duration += self.repeat_interval * (self.greeting_repeat - 1)
        
        # Пауза и сигнал
        duration += self.pause_before_beep + self.beep_duration
        
        # Пост-сигнал
        if self.post_beep_text and not self.has_post_beep_audio:
            words = len(self.post_beep_text.split())
            duration += words / 5.0
        
        # Завершение
        if self.closing_text and not self.has_closing_audio:
            words = len(self.closing_text.split())
            duration += words / 5.0
        
        return round(duration, 1)
    
    @property
    def status_display(self) -> str:
        """Статус для отображения"""
        if self.is_archived:
            return "Архив"
        elif self.is_active:
            return "Активен"
        elif self.is_template:
            return "Шаблон"
        else:
            return "Неактивен"
    
    @property
    def status_color(self) -> str:
        """Цвет статуса"""
        colors = {
            "Активен": "#2ecc71",
            "Неактивен": "#95a5a6",
            "Шаблон": "#3498db",
            "Архив": "#e74c3c",
        }
        return colors.get(self.status_display, "#95a5a6")
    
    @property
    def greeting_source_display(self) -> str:
        """Источник приветствия для отображения"""
        sources = {
            "tts": "🎤 TTS (синтез речи)",
            "uploaded": "📁 Загруженный файл",
            "none": "⊘ Без приветствия",
        }
        return sources.get(self.greeting_source, self.greeting_source)
    
    @property
    def is_deletable(self) -> bool:
        """Можно ли удалить (нельзя удалить активный)"""
        return not self.is_active
    
    # =========================================================================
    # Методы
    # =========================================================================
    
    def activate(self, activated_by: Optional[uuid.UUID] = None):
        """Активировать плейбук (деактивирует все остальные)"""
        self.is_active = True
        self.is_archived = False
        self.updated_by = activated_by
        self.updated_at = func.now()
    
    def deactivate(self, deactivated_by: Optional[uuid.UUID] = None):
        """Деактивировать плейбук"""
        self.is_active = False
        self.updated_by = deactivated_by
        self.updated_at = func.now()
    
    def soft_delete(self, deleted_by: Optional[uuid.UUID] = None):
        """Мягкое удаление (архивирование)"""
        if self.is_active:
            raise ValueError("Нельзя удалить активный плейбук. Сначала деактивируйте.")
        self.is_archived = True
        self.is_active = False
        self.updated_by = deleted_by
        self.updated_at = func.now()
    
    def restore(self, restored_by: Optional[uuid.UUID] = None):
        """Восстановление из архива"""
        self.is_archived = False
        self.updated_by = restored_by
        self.updated_at = func.now()
    
    def increment_usage(self):
        """Увеличить счетчик использования"""
        self.usage_count += 1
        self.last_used_at = func.now()
    
    def new_version(self):
        """Создать новую версию (инкремент)"""
        self.version += 1
    
    def clone(self, new_name: str, cloned_by: Optional[uuid.UUID] = None) -> dict:
        """
        Клонировать плейбук
        
        Returns:
            Словарь с данными для создания нового плейбука
        """
        return {
            "name": new_name,
            "description": f"Копия плейбука '{self.name}'",
            "category": self.category,
            "greeting_text": self.greeting_text,
            "greeting_audio_path": self.greeting_audio_path,
            "greeting_source": self.greeting_source,
            "post_beep_text": self.post_beep_text,
            "post_beep_audio_path": self.post_beep_audio_path,
            "closing_text": self.closing_text,
            "closing_audio_path": self.closing_audio_path,
            "beep_duration": self.beep_duration,
            "pause_before_beep": self.pause_before_beep,
            "max_recording_duration": self.max_recording_duration,
            "min_recording_duration": self.min_recording_duration,
            "greeting_repeat": self.greeting_repeat,
            "repeat_interval": self.repeat_interval,
            "language": self.language,
            "tts_voice": self.tts_voice,
            "tts_speed": self.tts_speed,
            "is_template": False,
            "is_active": False,
            "created_by": cloned_by,
        }
    
    def get_audio_files(self) -> List[dict]:
        """Получить список всех аудиофайлов плейбука"""
        files = []
        if self.greeting_audio_path:
            files.append({
                "type": "greeting",
                "path": self.greeting_audio_path,
                "label": "Приветствие",
            })
        if self.post_beep_audio_path:
            files.append({
                "type": "post_beep",
                "path": self.post_beep_audio_path,
                "label": "После сигнала",
            })
        if self.closing_audio_path:
            files.append({
                "type": "closing",
                "path": self.closing_audio_path,
                "label": "Завершение",
            })
        return files
    
    def to_dict(self, include_full_text: bool = False) -> dict:
        """Сериализация в словарь"""
        result = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            
            # Содержимое
            "greeting_text": self.greeting_text if include_full_text else 
                           (self.greeting_text[:100] + "..." if self.greeting_text and len(self.greeting_text) > 100 else self.greeting_text),
            "greeting_audio_path": self.greeting_audio_path,
            "greeting_source": self.greeting_source,
            "greeting_source_display": self.greeting_source_display,
            "post_beep_text": self.post_beep_text,
            "post_beep_audio_path": self.post_beep_audio_path,
            "closing_text": self.closing_text,
            "closing_audio_path": self.closing_audio_path,
            
            # Настройки
            "beep_duration": self.beep_duration,
            "pause_before_beep": self.pause_before_beep,
            "max_recording_duration": self.max_recording_duration,
            "min_recording_duration": self.min_recording_duration,
            "greeting_repeat": self.greeting_repeat,
            "repeat_interval": self.repeat_interval,
            "total_duration": self.total_duration,
            
            # Язык
            "language": self.language,
            "tts_voice": self.tts_voice,
            "tts_speed": self.tts_speed,
            
            # Статус
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "is_template": self.is_template,
            "version": self.version,
            "status_display": self.status_display,
            "status_color": self.status_color,
            
            # Статистика
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            
            # Аудит
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            
            # Аудиофайлы
            "audio_files": self.get_audio_files(),
        }
        return result
    
    @classmethod
    def create_from_template(
        cls,
        template_name: str = "default",
        created_by: Optional[uuid.UUID] = None
    ) -> "Playbook":
        """
        Создать плейбук из предопределенного шаблона
        
        Args:
            template_name: имя шаблона (default, emergency, short)
            created_by: ID создателя
            
        Returns:
            Новый экземпляр Playbook
        """
        templates = {
            "default": {
                "name": "Стандартное приветствие",
                "greeting_text": "Здравствуйте. Вы позвонили в систему ГО и ЧС информирования предприятия. После звукового сигнала оставьте ваше сообщение.",
                "category": "общий",
                "beep_duration": 1.0,
                "pause_before_beep": 0.5,
                "max_recording_duration": 300,
                "min_recording_duration": 3,
                "greeting_repeat": 1,
            },
            "emergency": {
                "name": "Экстренное оповещение",
                "greeting_text": "Внимание! Вы позвонили в экстренную службу оповещения. Говорите после сигнала.",
                "category": "экстренный",
                "beep_duration": 0.5,
                "pause_before_beep": 0.3,
                "max_recording_duration": 120,
                "min_recording_duration": 2,
                "greeting_repeat": 2,
            },
            "short": {
                "name": "Короткое приветствие",
                "greeting_text": "ГО и ЧС. Оставьте сообщение после сигнала.",
                "category": "короткий",
                "beep_duration": 0.8,
                "pause_before_beep": 0.3,
                "max_recording_duration": 180,
                "min_recording_duration": 2,
                "greeting_repeat": 1,
            },
        }
        
        template = templates.get(template_name, templates["default"])
        
        return cls(
            **template,
            greeting_source="tts",
            is_template=True,
            is_active=False,
            created_by=created_by,
        )
    
    def __repr__(self) -> str:
        return f"<Playbook(id={self.id}, name='{self.name}', active={self.is_active}, v{self.version})>"
    
    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"


# =============================================================================
# Предопределенные категории плейбуков
# =============================================================================

PLAYBOOK_CATEGORIES = [
    {"value": "общий", "label": "Общий", "color": "#3498db"},
    {"value": "экстренный", "label": "Экстренный", "color": "#e74c3c"},
    {"value": "тестовый", "label": "Тестовый", "color": "#f1c40f"},
    {"value": "короткий", "label": "Короткий", "color": "#2ecc71"},
    {"value": "информационный", "label": "Информационный", "color": "#9b59b6"},
    {"value": "ночной", "label": "Ночной режим", "color": "#34495e"},
]
