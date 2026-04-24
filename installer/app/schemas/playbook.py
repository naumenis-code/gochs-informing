#!/usr/bin/env python3
"""
Pydantic схемы для плейбуков ГО-ЧС Информирование
Соответствует ТЗ, раздел 19: Playbook входящих звонков

Плейбук — сценарий обработки входящего звонка:
1. Автоответ
2. Приветственное сообщение
3. Сигнал (beep)
4. Запись сообщения
5. Сохранение WAV
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime
import re


# ============================================================================
# ЕНАМЫ
# ============================================================================

class GreetingSource(str):
    """Источник приветствия"""
    TTS = "tts"           # Синтез речи из текста
    UPLOADED = "uploaded" # Загруженный аудиофайл
    NONE = "none"         # Без приветствия


class PlaybookCategory(str):
    """Категории плейбуков"""
    GENERAL = "общий"
    EMERGENCY = "экстренный"
    TEST = "тестовый"
    SHORT = "короткий"
    INFO = "информационный"
    NIGHT = "ночной"


class PlaybookStatus(str):
    """Статусы плейбука"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TEMPLATE = "template"
    ARCHIVED = "archived"


# ============================================================================
# БАЗОВЫЕ СХЕМЫ
# ============================================================================

class PlaybookBase(BaseModel):
    """Базовая схема плейбука"""
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Название плейбука"
    )
    description: Optional[str] = Field(
        default=None,
        description="Описание плейбука (для чего используется)"
    )
    category: Optional[str] = Field(
        default="общий",
        description="Категория плейбука"
    )
    
    # =========================================================================
    # Приветственное сообщение
    # =========================================================================
    greeting_text: Optional[str] = Field(
        default=None,
        description="Текст приветствия (для TTS или как субтитры)"
    )
    greeting_source: str = Field(
        default="tts",
        description="Источник приветствия: tts, uploaded, none"
    )
    
    # =========================================================================
    # Сообщение после сигнала
    # =========================================================================
    post_beep_text: Optional[str] = Field(
        default=None,
        description="Текст после сигнала (инструкция)"
    )
    
    # =========================================================================
    # Завершающее сообщение
    # =========================================================================
    closing_text: Optional[str] = Field(
        default=None,
        description="Текст завершающего сообщения"
    )
    
    # =========================================================================
    # Настройки воспроизведения
    # =========================================================================
    beep_duration: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Длительность сигнала (секунд, 0.1-10.0)"
    )
    pause_before_beep: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Пауза перед сигналом (секунд, 0.0-5.0)"
    )
    max_recording_duration: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Максимальная длительность записи (секунд, 10-3600)"
    )
    min_recording_duration: int = Field(
        default=3,
        ge=1,
        le=60,
        description="Минимальная длительность записи (секунд, 1-60)"
    )
    greeting_repeat: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Количество повторов приветствия (0-10, 0 = без повтора)"
    )
    repeat_interval: float = Field(
        default=0.0,
        ge=0.0,
        le=30.0,
        description="Интервал между повторами (секунд)"
    )
    
    # =========================================================================
    # Языковые настройки
    # =========================================================================
    language: str = Field(
        default="ru",
        description="Язык плейбука (ru, en, ...)"
    )
    tts_voice: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Голос для TTS (например: ru_male, ru_female)"
    )
    tts_speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Скорость речи TTS (0.5 - 2.0)"
    )
    
    # =========================================================================
    # Валидаторы
    # =========================================================================
    
    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Валидация названия"""
        v = v.strip()
        if len(v) < 2:
            raise ValueError('Название должно содержать минимум 2 символа')
        if re.search(r'[<>@#$%^&*(){}\[\]\\|]', v):
            raise ValueError('Название содержит недопустимые символы')
        return v
    
    @field_validator('greeting_source')
    def validate_greeting_source(cls, v: str) -> str:
        """Валидация источника приветствия"""
        valid_sources = ['tts', 'uploaded', 'none']
        if v not in valid_sources:
            raise ValueError(f'Источник должен быть одним из: {valid_sources}')
        return v
    
    @field_validator('category')
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Валидация категории"""
        if v is None:
            return "общий"
        valid_categories = ['общий', 'экстренный', 'тестовый', 'короткий', 'информационный', 'ночной']
        if v not in valid_categories:
            raise ValueError(f'Категория должна быть одной из: {valid_categories}')
        return v
    
    @model_validator(mode='after')
    def validate_greeting_consistency(self):
        """Проверка согласованности приветствия"""
        if self.greeting_source == 'tts' and not self.greeting_text:
            raise ValueError('Для TTS необходимо указать текст приветствия')
        if self.greeting_source == 'uploaded' and self.greeting_text:
            # При загрузке файла текст опционален (как субтитры)
            pass
        if self.greeting_source == 'none':
            self.greeting_text = None
        return self
    
    @model_validator(mode='after')
    def validate_recording_duration(self):
        """Проверка длительности записи"""
        if self.min_recording_duration > self.max_recording_duration:
            raise ValueError('Минимальная длительность не может превышать максимальную')
        return self


class PlaybookCreate(PlaybookBase):
    """Схема для создания плейбука"""
    is_template: bool = Field(
        default=False,
        description="Создать как шаблон"
    )
    is_active: bool = Field(
        default=False,
        description="Сделать активным сразу после создания"
    )
    
    @model_validator(mode='after')
    def warn_if_activate_without_content(self):
        """Предупреждение: активация без содержимого"""
        if self.is_active and self.greeting_source == 'none':
            raise ValueError(
                'Нельзя активировать плейбук без приветствия. '
                'Добавьте текст или загрузите аудиофайл.'
            )
        return self


class PlaybookUpdate(BaseModel):
    """Схема для обновления плейбука (все поля опциональны)"""
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Новое название"
    )
    description: Optional[str] = Field(
        default=None,
        description="Новое описание"
    )
    category: Optional[str] = Field(
        default=None,
        description="Новая категория"
    )
    greeting_text: Optional[str] = Field(
        default=None,
        description="Новый текст приветствия"
    )
    greeting_source: Optional[str] = Field(
        default=None,
        description="Новый источник: tts, uploaded, none"
    )
    post_beep_text: Optional[str] = Field(
        default=None,
        description="Новый текст после сигнала"
    )
    closing_text: Optional[str] = Field(
        default=None,
        description="Новый текст завершения"
    )
    beep_duration: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=10.0
    )
    pause_before_beep: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0
    )
    max_recording_duration: Optional[int] = Field(
        default=None,
        ge=10,
        le=3600
    )
    min_recording_duration: Optional[int] = Field(
        default=None,
        ge=1,
        le=60
    )
    greeting_repeat: Optional[int] = Field(
        default=None,
        ge=0,
        le=10
    )
    repeat_interval: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=30.0
    )
    language: Optional[str] = Field(default=None)
    tts_voice: Optional[str] = Field(default=None, max_length=50)
    tts_speed: Optional[float] = Field(default=None, ge=0.5, le=2.0)
    is_template: Optional[bool] = Field(default=None)


class PlaybookStatusUpdate(BaseModel):
    """Схема для изменения статуса плейбука"""
    action: str = Field(
        ...,
        description="Действие: activate, deactivate, archive, restore, make_template"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Причина изменения (для аудита)"
    )
    
    @field_validator('action')
    def validate_action(cls, v: str) -> str:
        valid_actions = ['activate', 'deactivate', 'archive', 'restore', 'make_template']
        if v not in valid_actions:
            raise ValueError(f'Действие должно быть одним из: {valid_actions}')
        return v


# ============================================================================
# СХЕМЫ ДЛЯ TTS ГЕНЕРАЦИИ
# ============================================================================

class TTSGenerateRequest(BaseModel):
    """Запрос на генерацию аудио через TTS"""
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Текст для озвучивания"
    )
    voice: Optional[str] = Field(
        default=None,
        description="Голос (если None — используется голос из плейбука)"
    )
    speed: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=2.0,
        description="Скорость речи"
    )
    output_filename: Optional[str] = Field(
        default=None,
        description="Имя выходного файла (без расширения)"
    )
    overwrite: bool = Field(
        default=False,
        description="Перезаписать существующий файл"
    )


class TTSGenerateResponse(BaseModel):
    """Ответ после генерации TTS"""
    success: bool = Field(..., description="Успешно")
    audio_path: Optional[str] = Field(None, description="Путь к аудиофайлу")
    duration_seconds: Optional[float] = Field(None, description="Длительность")
    file_size_bytes: Optional[int] = Field(None, description="Размер файла")
    text_length: int = Field(..., description="Длина текста")
    voice: str = Field(..., description="Использованный голос")
    message: Optional[str] = Field(None, description="Сообщение")
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Время генерации"
    )


# ============================================================================
# СХЕМЫ ДЛЯ ЗАГРУЗКИ АУДИОФАЙЛОВ
# ============================================================================

class AudioUploadResponse(BaseModel):
    """Ответ после загрузки аудиофайла"""
    audio_path: str = Field(..., description="Путь к сохраненному файлу")
    original_filename: str = Field(..., description="Оригинальное имя")
    file_size_bytes: int = Field(..., description="Размер (байт)")
    format: str = Field(..., description="Формат (wav, mp3)")
    duration_seconds: Optional[float] = Field(None, description="Длительность")
    sample_rate: Optional[int] = Field(None, description="Частота дискретизации")
    channels: Optional[int] = Field(None, description="Каналы")
    uploaded_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# СХЕМЫ ОТВЕТОВ
# ============================================================================

class PlaybookResponse(BaseModel):
    """Схема ответа с данными плейбука"""
    id: UUID = Field(..., description="ID")
    name: str = Field(..., description="Название")
    description: Optional[str] = Field(None, description="Описание")
    category: Optional[str] = Field(None, description="Категория")
    
    # Содержимое
    greeting_text: Optional[str] = Field(None, description="Текст приветствия")
    greeting_audio_path: Optional[str] = Field(None, description="Аудиофайл приветствия")
    greeting_source: str = Field(..., description="Источник приветствия")
    post_beep_text: Optional[str] = Field(None, description="Текст после сигнала")
    post_beep_audio_path: Optional[str] = Field(None, description="Аудио после сигнала")
    closing_text: Optional[str] = Field(None, description="Текст завершения")
    closing_audio_path: Optional[str] = Field(None, description="Аудио завершения")
    
    # Настройки
    beep_duration: float = Field(..., description="Длительность сигнала")
    pause_before_beep: float = Field(..., description="Пауза перед сигналом")
    max_recording_duration: int = Field(..., description="Макс. длительность записи")
    min_recording_duration: int = Field(..., description="Мин. длительность записи")
    greeting_repeat: int = Field(..., description="Повторов приветствия")
    repeat_interval: float = Field(..., description="Интервал повторов")
    total_duration: float = Field(..., description="Общая длительность (расчетная)")
    
    # Язык
    language: str = Field(..., description="Язык")
    tts_voice: Optional[str] = Field(None, description="Голос TTS")
    tts_speed: float = Field(..., description="Скорость TTS")
    
    # Статус
    is_active: bool = Field(..., description="Активен")
    is_archived: bool = Field(..., description="В архиве")
    is_template: bool = Field(..., description="Шаблон")
    version: int = Field(..., description="Версия")
    
    # Статистика
    usage_count: int = Field(..., description="Использований")
    last_used_at: Optional[datetime] = Field(None, description="Последнее использование")
    
    # Аудит
    created_by: Optional[UUID] = Field(None, description="Кто создал")
    updated_by: Optional[UUID] = Field(None, description="Кто обновил")
    created_at: Optional[datetime] = Field(None, description="Создан")
    updated_at: Optional[datetime] = Field(None, description="Обновлен")
    
    # Аудиофайлы
    audio_files: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Список аудиофайлов [{type, path, label}]"
    )
    
    model_config = ConfigDict(from_attributes=True)
    
    @property
    def status_display(self) -> str:
        """Статус для отображения"""
        if self.is_archived:
            return "📦 Архив"
        elif self.is_active:
            return "✅ Активен"
        elif self.is_template:
            return "📋 Шаблон"
        else:
            return "❌ Неактивен"
    
    @property
    def greeting_source_display(self) -> str:
        """Источник приветствия для отображения"""
        sources = {
            "tts": "🎤 TTS (синтез речи)",
            "uploaded": "📁 Загруженный файл",
            "none": "⊘ Без приветствия",
        }
        return sources.get(self.greeting_source, self.greeting_source)


class PlaybookListResponse(BaseModel):
    """Краткая схема плейбука для списков"""
    id: UUID = Field(..., description="ID")
    name: str = Field(..., description="Название")
    category: Optional[str] = Field(None, description="Категория")
    greeting_source: str = Field(..., description="Источник приветствия")
    is_active: bool = Field(..., description="Активен")
    is_template: bool = Field(..., description="Шаблон")
    version: int = Field(..., description="Версия")
    usage_count: int = Field(..., description="Использований")
    total_duration: float = Field(..., description="Длительность")
    created_at: Optional[datetime] = Field(None, description="Создан")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# СХЕМЫ ДЛЯ КЛОНИРОВАНИЯ
# ============================================================================

class PlaybookCloneRequest(BaseModel):
    """Запрос на клонирование плейбука"""
    new_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Название нового плейбука"
    )
    copy_audio_files: bool = Field(
        default=True,
        description="Копировать аудиофайлы"
    )
    make_active: bool = Field(
        default=False,
        description="Сделать активным после клонирования"
    )


# ============================================================================
# СХЕМЫ ДЛЯ ТЕСТИРОВАНИЯ
# ============================================================================

class PlaybookTestRequest(BaseModel):
    """Запрос на тестирование плейбука"""
    test_number: str = Field(
        ...,
        description="Номер телефона для тестового звонка"
    )
    test_type: str = Field(
        default="full",
        description="Тип теста: full (полный), greeting_only (только приветствие), beep_only (только сигнал)"
    )
    
    @field_validator('test_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация тестового номера"""
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^(\+7|8|7)?\d{10}$', cleaned):
            raise ValueError('Неверный формат номера телефона')
        return v
    
    @field_validator('test_type')
    def validate_test_type(cls, v: str) -> str:
        valid_types = ['full', 'greeting_only', 'beep_only']
        if v not in valid_types:
            raise ValueError(f'Тип теста должен быть одним из: {valid_types}')
        return v


class PlaybookTestResponse(BaseModel):
    """Ответ после тестирования плейбука"""
    success: bool = Field(..., description="Успешно")
    call_sid: Optional[str] = Field(None, description="ID звонка")
    test_number: str = Field(..., description="Номер теста")
    duration_seconds: Optional[float] = Field(None, description="Длительность звонка")
    recording_path: Optional[str] = Field(None, description="Путь к записи")
    message: Optional[str] = Field(None, description="Сообщение")
    tested_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# Предопределенные шаблоны плейбуков
PLAYBOOK_TEMPLATES = {
    "default": {
        "name": "Стандартное приветствие",
        "category": "общий",
        "greeting_text": "Здравствуйте. Вы позвонили в систему ГО и ЧС информирования предприятия. После звукового сигнала оставьте ваше сообщение.",
        "beep_duration": 1.0,
        "pause_before_beep": 0.5,
        "max_recording_duration": 300,
        "min_recording_duration": 3,
        "greeting_repeat": 1,
    },
    "emergency": {
        "name": "Экстренное оповещение",
        "category": "экстренный",
        "greeting_text": "Внимание! Вы позвонили в экстренную службу оповещения. Говорите после сигнала.",
        "beep_duration": 0.5,
        "pause_before_beep": 0.3,
        "max_recording_duration": 120,
        "min_recording_duration": 2,
        "greeting_repeat": 2,
    },
    "short": {
        "name": "Короткое приветствие",
        "category": "короткий",
        "greeting_text": "ГО и ЧС. Оставьте сообщение после сигнала.",
        "beep_duration": 0.8,
        "pause_before_beep": 0.3,
        "max_recording_duration": 180,
        "min_recording_duration": 2,
        "greeting_repeat": 1,
    },
}

# Категории с цветами для UI
PLAYBOOK_CATEGORIES = [
    {"value": "общий", "label": "Общий", "color": "#3498db", "icon": "📞"},
    {"value": "экстренный", "label": "Экстренный", "color": "#e74c3c", "icon": "🚨"},
    {"value": "тестовый", "label": "Тестовый", "color": "#f1c40f", "icon": "🧪"},
    {"value": "короткий", "label": "Короткий", "color": "#2ecc71", "icon": "⚡"},
    {"value": "информационный", "label": "Информационный", "color": "#9b59b6", "icon": "ℹ️"},
    {"value": "ночной", "label": "Ночной режим", "color": "#34495e", "icon": "🌙"},
]

# Допустимые аудиоформаты
ALLOWED_AUDIO_FORMATS = ["wav", "mp3", "ogg"]

# Максимальный размер аудиофайла (50 МБ)
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024

# Доступные голоса TTS
TTS_VOICES = [
    {"value": "ru_male", "label": "Мужской (русский)"},
    {"value": "ru_female", "label": "Женский (русский)"},
    {"value": "ru_male_deep", "label": "Мужской низкий (русский)"},
    {"value": "ru_female_soft", "label": "Женский мягкий (русский)"},
]
