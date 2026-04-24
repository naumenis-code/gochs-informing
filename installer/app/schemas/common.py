#!/usr/bin/env python3
"""
Общие Pydantic схемы для ГО-ЧС Информирование
Используются всеми остальными схемами для пагинации, ответов, фильтрации
"""

from typing import TypeVar, Generic, List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from uuid import UUID

T = TypeVar('T')


# ============================================================================
# ПАГИНАЦИЯ
# ============================================================================

class PaginationParams(BaseModel):
    """Параметры пагинации для запросов списков"""
    page: int = Field(
        default=1,
        ge=1,
        description="Номер страницы (начиная с 1)"
    )
    page_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Размер страницы (1-500)"
    )
    
    @property
    def offset(self) -> int:
        """Вычислить offset для SQL запроса"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Лимит для SQL запроса"""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Стандартный ответ с пагинацией"""
    items: List[T] = Field(
        default_factory=list,
        description="Список элементов на текущей странице"
    )
    total: int = Field(
        default=0,
        description="Общее количество элементов"
    )
    page: int = Field(
        default=1,
        description="Текущая страница"
    )
    page_size: int = Field(
        default=50,
        description="Размер страницы"
    )
    total_pages: int = Field(
        default=0,
        description="Общее количество страниц"
    )
    has_next: bool = Field(
        default=False,
        description="Есть ли следующая страница"
    )
    has_prev: bool = Field(
        default=False,
        description="Есть ли предыдущая страница"
    )
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        page_size: int = 50
    ) -> "PaginatedResponse[T]":
        """Фабричный метод для создания пагинированного ответа"""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


# ============================================================================
# БАЗОВЫЕ ОТВЕТЫ
# ============================================================================

class MessageResponse(BaseModel):
    """Простой ответ с сообщением"""
    message: str = Field(
        ...,
        description="Текст сообщения"
    )
    success: bool = Field(
        default=True,
        description="Успешность операции"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Время создания ответа"
    )


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    detail: str = Field(
        ...,
        description="Описание ошибки"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Код ошибки"
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Тип ошибки (validation, auth, server, etc)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Время возникновения ошибки"
    )
    path: Optional[str] = Field(
        default=None,
        description="Путь запроса, вызвавшего ошибку"
    )


class SuccessResponse(BaseModel):
    """Ответ об успешной операции с данными"""
    success: bool = Field(default=True, description="Успешность")
    data: Optional[Any] = Field(default=None, description="Данные ответа")
    message: Optional[str] = Field(default=None, description="Сообщение")


class IDResponse(BaseModel):
    """Ответ с ID созданного/обновленного объекта"""
    id: UUID = Field(..., description="ID объекта")
    message: str = Field(default="Операция выполнена успешно")


class BulkOperationResult(BaseModel):
    """Результат массовой операции (импорт/экспорт/удаление)"""
    total_processed: int = Field(
        ...,
        description="Всего обработано записей"
    )
    success_count: int = Field(
        default=0,
        description="Успешно обработано"
    )
    error_count: int = Field(
        default=0,
        description="С ошибками"
    )
    skipped_count: int = Field(
        default=0,
        description="Пропущено (дубликаты и т.п.)"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Список ошибок [{row, error, field}]"
    )
    message: str = Field(
        default="",
        description="Сводное сообщение о результате"
    )
    execution_time_ms: Optional[int] = Field(
        default=None,
        description="Время выполнения операции (мс)"
    )


# ============================================================================
# ФИЛЬТРАЦИЯ И СОРТИРОВКА
# ============================================================================

class SortParams(BaseModel):
    """Параметры сортировки"""
    field: str = Field(
        ...,
        description="Поле для сортировки"
    )
    direction: str = Field(
        default="asc",
        description="Направление сортировки (asc/desc)"
    )
    
    @field_validator('direction')
    def validate_direction(cls, v: str) -> str:
        """Валидация направления сортировки"""
        v = v.lower()
        if v not in ['asc', 'desc']:
            raise ValueError('direction должен быть asc или desc')
        return v


class FilterOperator(str):
    """Операторы фильтрации"""
    EQ = "eq"          # равно
    NEQ = "neq"        # не равно
    GT = "gt"          # больше
    GTE = "gte"        # больше или равно
    LT = "lt"          # меньше
    LTE = "lte"        # меньше или равно
    LIKE = "like"      # содержит
    ILIKE = "ilike"    # содержит (без учета регистра)
    IN = "in"          # в списке
    NOT_IN = "not_in"  # не в списке
    IS_NULL = "is_null"      # NULL
    IS_NOT_NULL = "is_not_null"  # NOT NULL
    BETWEEN = "between"  # между датами/числами


class FilterParam(BaseModel):
    """Параметр фильтрации"""
    field: str = Field(..., description="Поле для фильтрации")
    operator: str = Field(default="eq", description="Оператор фильтрации")
    value: Any = Field(..., description="Значение для сравнения")
    
    @field_validator('operator')
    def validate_operator(cls, v: str) -> str:
        """Валидация оператора"""
        valid_operators = [
            "eq", "neq", "gt", "gte", "lt", "lte",
            "like", "ilike", "in", "not_in",
            "is_null", "is_not_null", "between"
        ]
        if v not in valid_operators:
            raise ValueError(f'Недопустимый оператор: {v}. Допустимые: {valid_operators}')
        return v


class SearchParams(BaseModel):
    """Параметры поиска"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Поисковый запрос"
    )
    fields: Optional[List[str]] = Field(
        default=None,
        description="Поля для поиска (если None — поиск по всем текстовым)"
    )
    exact_match: bool = Field(
        default=False,
        description="Точное совпадение"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Учитывать регистр"
    )


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ СХЕМЫ
# ============================================================================

class SelectOption(BaseModel):
    """Опция для select/выпадающих списков (frontend)"""
    value: str = Field(..., description="Значение")
    label: str = Field(..., description="Отображаемое название")
    disabled: bool = Field(default=False, description="Отключена ли опция")
    color: Optional[str] = Field(default=None, description="Цвет опции (HEX)")
    icon: Optional[str] = Field(default=None, description="Иконка (emoji или код)")
    description: Optional[str] = Field(default=None, description="Дополнительное описание")
    count: Optional[int] = Field(default=None, description="Количество связанных объектов")


class DateRangeParams(BaseModel):
    """Параметры диапазона дат"""
    start_date: Optional[datetime] = Field(
        default=None,
        description="Начальная дата (включительно)"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Конечная дата (включительно)"
    )
    
    @field_validator('end_date')
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Проверка, что end_date >= start_date"""
        start_date = info.data.get('start_date')
        if v and start_date and v < start_date:
            raise ValueError('end_date должен быть больше или равен start_date')
        return v


class TimeRangeParams(BaseModel):
    """Параметры временного диапазона (в течение дня)"""
    start_time: Optional[str] = Field(
        default="00:00",
        description="Начальное время (HH:MM)",
        pattern=r'^\d{2}:\d{2}$'
    )
    end_time: Optional[str] = Field(
        default="23:59",
        description="Конечное время (HH:MM)",
        pattern=r'^\d{2}:\d{2}$'
    )


class ExportParams(BaseModel):
    """Параметры экспорта данных"""
    format: str = Field(
        default="csv",
        description="Формат экспорта (csv, xlsx, json)"
    )
    fields: Optional[List[str]] = Field(
        default=None,
        description="Поля для экспорта (если None — все)"
    )
    include_archived: bool = Field(
        default=False,
        description="Включать архивные записи"
    )
    encoding: str = Field(
        default="utf-8",
        description="Кодировка файла"
    )
    
    @field_validator('format')
    def validate_format(cls, v: str) -> str:
        """Валидация формата"""
        valid_formats = ['csv', 'xlsx', 'json']
        if v.lower() not in valid_formats:
            raise ValueError(f'Недопустимый формат. Допустимые: {valid_formats}')
        return v.lower()


# ============================================================================
# СХЕМЫ ДЛЯ ФАЙЛОВ
# ============================================================================

class FileUploadResponse(BaseModel):
    """Ответ после загрузки файла"""
    filename: str = Field(..., description="Имя файла")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    path: str = Field(..., description="Путь к сохраненному файлу")
    size_bytes: int = Field(..., description="Размер файла в байтах")
    mime_type: Optional[str] = Field(default=None, description="MIME тип")
    uploaded_at: datetime = Field(
        default_factory=datetime.now,
        description="Время загрузки"
    )


class AudioFileInfo(BaseModel):
    """Информация об аудиофайле"""
    path: str = Field(..., description="Путь к файлу")
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Длительность в секундах"
    )
    format: Optional[str] = Field(default=None, description="Формат (wav, mp3)")
    sample_rate: Optional[int] = Field(default=None, description="Частота дискретизации")
    channels: Optional[int] = Field(default=None, description="Количество каналов")
    size_bytes: Optional[int] = Field(default=None, description="Размер в байтах")


# ============================================================================
# СХЕМЫ СТАТИСТИКИ
# ============================================================================

class StatsOverview(BaseModel):
    """Общая статистика системы"""
    total_contacts: int = Field(default=0, description="Всего контактов")
    active_contacts: int = Field(default=0, description="Активных контактов")
    total_groups: int = Field(default=0, description="Всего групп")
    total_campaigns: int = Field(default=0, description="Всего кампаний")
    active_campaigns: int = Field(default=0, description="Активных кампаний")
    total_calls_today: int = Field(default=0, description="Звонков сегодня")
    answered_calls_today: int = Field(default=0, description="Отвеченных сегодня")
    total_recordings: int = Field(default=0, description="Всего записей")
    storage_used_mb: float = Field(default=0.0, description="Занято места (МБ)")


class CountItem(BaseModel):
    """Элемент для статистики по категориям"""
    name: str = Field(..., description="Название")
    count: int = Field(..., description="Количество")
    percentage: Optional[float] = Field(default=None, description="Процент от общего")


class StatsByCategory(BaseModel):
    """Статистика по категориям"""
    total: int = Field(..., description="Общее количество")
    items: List[CountItem] = Field(default_factory=list, description="Распределение")


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def paginate_items(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 50
) -> PaginatedResponse:
    """
    Вспомогательная функция для пагинации списка
    
    Args:
        items: список элементов
        total: общее количество
        page: текущая страница
        page_size: размер страницы
    
    Returns:
        PaginatedResponse с элементами
    """
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


def success_message(message: str, data: Any = None) -> SuccessResponse:
    """Создать ответ об успехе"""
    return SuccessResponse(success=True, message=message, data=data)


def error_detail(detail: str, error_code: str = None, error_type: str = None) -> ErrorResponse:
    """Создать ответ об ошибке"""
    return ErrorResponse(
        detail=detail,
        error_code=error_code,
        error_type=error_type,
        timestamp=datetime.now()
    )


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# Допустимые форматы файлов для импорта контактов
IMPORT_FORMATS = ["csv", "xlsx", "xls"]

# Допустимые форматы аудиофайлов
AUDIO_FORMATS = ["wav", "mp3", "ogg", "flac"]

# Максимальный размер файла для импорта (10 МБ)
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024

# Максимальный размер аудиофайла (50 МБ)
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024

# Допустимые форматы экспорта
EXPORT_FORMATS = ["csv", "xlsx", "json"]
