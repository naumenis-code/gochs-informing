#!/usr/bin/env python3
"""
API эндпоинты для управления плейбуками ГО-ЧС Информирование
Соответствует ТЗ, раздел 19: Playbook входящих звонков

Функционал:
- CRUD операции с плейбуками
- Генерация аудио через TTS (с конвертацией в телефонный формат 8000 Гц)
- Загрузка готовых аудиофайлов
- Клонирование плейбуков
- Управление активностью
- Тестирование плейбуков
- Статистика использования
"""

import logging
import os
from typing import Optional, List
from uuid import UUID

from fastapi import (
    Path,
    APIRouter, Depends, HTTPException, status, Query,
    Request, UploadFile, File
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.services.playbook_service import PlaybookService
from app.schemas.playbook import (
    PlaybookCreate, PlaybookUpdate, PlaybookStatusUpdate,
    PlaybookResponse, PlaybookListResponse,
    PlaybookCloneRequest, TTSGenerateRequest, TTSGenerateResponse,
    AudioUploadResponse, PlaybookTestRequest, PlaybookTestResponse,
    GreetingSource, PlaybookCategory
)
from app.schemas.common import (
    PaginatedResponse, MessageResponse, IDResponse,
    PaginationParams
)
from app.models.user import User
from app.utils.audit_helper import log_action

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ============================================================================

def _playbook_to_response(playbook) -> PlaybookResponse:
    """Преобразование модели Playbook в схему ответа"""
    return PlaybookResponse(
        id=playbook.id,
        name=playbook.name,
        description=playbook.description,
        category=playbook.category,
        greeting_text=playbook.greeting_text,
        greeting_audio_path=playbook.greeting_audio_path,
        greeting_source=playbook.greeting_source,
        post_beep_text=playbook.post_beep_text,
        post_beep_audio_path=playbook.post_beep_audio_path,
        closing_text=playbook.closing_text,
        closing_audio_path=playbook.closing_audio_path,
        beep_duration=playbook.beep_duration or 1.0,
        pause_before_beep=playbook.pause_before_beep or 0.5,
        max_recording_duration=playbook.max_recording_duration or 300,
        min_recording_duration=playbook.min_recording_duration or 3,
        greeting_repeat=playbook.greeting_repeat or 1,
        repeat_interval=playbook.repeat_interval or 0.0,
        total_duration=playbook.total_duration,
        language=playbook.language or "ru",
        tts_voice=playbook.tts_voice,
        tts_speed=playbook.tts_speed or 1.0,
        is_active=playbook.is_active,
        is_archived=playbook.is_archived,
        is_template=playbook.is_template,
        version=playbook.version or 1,
        usage_count=playbook.usage_count or 0,
        last_used_at=playbook.last_used_at,
        created_by=playbook.created_by,
        updated_by=playbook.updated_by,
        created_at=playbook.created_at,
        updated_at=playbook.updated_at,
        audio_files=playbook.get_audio_files() if hasattr(playbook, 'get_audio_files') else [],
    )


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА ПЛЕЙБУКОВ
# ============================================================================

@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="Получить список плейбуков",
    description="Возвращает список плейбуков с пагинацией и фильтрацией."
)
async def list_playbooks(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, min_length=1, description="Поиск по названию/описанию"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    is_active: Optional[bool] = Query(None, description="Только активные/неактивные"),
    is_template: Optional[bool] = Query(None, description="Только шаблоны"),
    greeting_source: Optional[str] = Query(None, description="Фильтр по источнику: tts, uploaded, none"),
    sort_field: str = Query("created_at", description="Поле сортировки"),
    sort_direction: str = Query("desc", description="Направление (asc/desc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка плейбуков с фильтрацией
    
    Доступно: admin, operator, viewer
    """
    try:
        service = PlaybookService(db)
        result = await service.list_playbooks(
            pagination=pagination,
            search=search,
            category=category,
            is_active=is_active,
            is_template=is_template,
            greeting_source=greeting_source,
            sort_field=sort_field,
            sort_direction=sort_direction
        )
        return result
        
    except Exception as e:
        logger.error(f"Ошибка получения списка плейбуков: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения списка: {str(e)}"
        )


# ============================================================================
# ПОЛУЧЕНИЕ АКТИВНОГО ПЛЕЙБУКА
# ============================================================================

@router.get(
    "/active",
    response_model=PlaybookResponse,
    summary="Получить активный плейбук",
    description="Возвращает текущий активный плейбук для входящих звонков."
)
async def get_active_playbook(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение активного плейбука"""
    service = PlaybookService(db)
    playbook = await service.get_active_playbook()
    
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Нет активного плейбука. Активируйте один из существующих."
        )
    
    return _playbook_to_response(playbook)


# ============================================================================
# ПОЛУЧЕНИЕ ПЛЕЙБУКА ПО ID
# ============================================================================

@router.get(
    "/{playbook_id}",
    response_model=PlaybookResponse,
    summary="Получить плейбук по ID",
    description="Возвращает детальную информацию о плейбуке."
)
async def get_playbook(
    playbook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение плейбука по ID"""
    service = PlaybookService(db)
    playbook = await service.get_playbook(playbook_id)
    
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Плейбук с ID {playbook_id} не найден"
        )
    
    return _playbook_to_response(playbook)


# ============================================================================
# СКАЧИВАНИЕ АУДИОФАЙЛА ПЛЕЙБУКА
# ============================================================================

@router.get(
    "/{playbook_id}/audio/{audio_type}",
    summary="Скачать аудиофайл плейбука",
    description="Возвращает аудиофайл указанного типа (greeting, post_beep, closing)."
)
async def download_playbook_audio(
    playbook_id: UUID,
    audio_type: str = Path(..., description="Тип аудио: greeting, post_beep, closing"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Скачивание аудиофайла плейбука
    
    Типы:
    - greeting: приветствие
    - post_beep: после сигнала
    - closing: завершение
    """
    service = PlaybookService(db)
    playbook = await service.get_playbook(playbook_id)
    
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Плейбук с ID {playbook_id} не найден"
        )
    
    # Определение пути к файлу
    audio_path = None
    if audio_type == "greeting":
        audio_path = playbook.greeting_audio_path
    elif audio_type == "post_beep":
        audio_path = playbook.post_beep_audio_path
    elif audio_type == "closing":
        audio_path = playbook.closing_audio_path
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неизвестный тип аудио: {audio_type}. Допустимые: greeting, post_beep, closing"
        )
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Аудиофайл типа '{audio_type}' не найден"
        )
    
    return FileResponse(
        audio_path,
        media_type="audio/wav",
        filename=f"playbook_{playbook_id}_{audio_type}.wav"
    )


# ============================================================================
# СОЗДАНИЕ ПЛЕЙБУКА
# ============================================================================

@router.post(
    "/",
    response_model=PlaybookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый плейбук",
    description="Создает новый плейбук. Только для администраторов."
)
async def create_playbook(
    playbook_data: PlaybookCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Создание нового плейбука
    
    Требует роль: admin
    
    При greeting_source='tts' аудио генерируется автоматически
    и конвертируется в телефонный формат (8000 Гц, mono, 16-bit PCM).
    """
    try:
        service = PlaybookService(db)
        playbook = await service.create_playbook(
            playbook_data=playbook_data,
            created_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_created",
            entity_type="playbook",
            entity_id=playbook.id,
            entity_name=playbook.name,
            details={
                "category": playbook.category,
                "greeting_source": playbook.greeting_source,
                "has_tts": playbook.greeting_source == "tts",
                "is_active": playbook.is_active,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return _playbook_to_response(playbook)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка создания плейбука: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания: {str(e)}"
        )


# ============================================================================
# СОЗДАНИЕ ПЛЕЙБУКА ИЗ ШАБЛОНА
# ============================================================================

@router.post(
    "/from-template/{template_name}",
    response_model=PlaybookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать плейбук из шаблона",
    description="Создает новый плейбук на основе предопределенного шаблона."
)
async def create_playbook_from_template(
    template_name: str = Path(..., description="Имя шаблона: default, emergency, short"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Создание плейбука из шаблона
    
    Доступные шаблоны:
    - default: Стандартное приветствие
    - emergency: Экстренное оповещение (с повтором)
    - short: Короткое приветствие
    """
    valid_templates = ["default", "emergency", "short"]
    if template_name not in valid_templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неизвестный шаблон: {template_name}. Допустимые: {valid_templates}"
        )
    
    try:
        service = PlaybookService(db)
        playbook = await service.create_from_template(
            template_name=template_name,
            created_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_created_from_template",
            entity_type="playbook",
            entity_id=playbook.id,
            entity_name=playbook.name,
            details={"template": template_name},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return _playbook_to_response(playbook)
        
    except Exception as e:
        logger.error(f"Ошибка создания из шаблона: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {str(e)}"
        )


# ============================================================================
# ОБНОВЛЕНИЕ ПЛЕЙБУКА
# ============================================================================

@router.patch(
    "/{playbook_id}",
    response_model=PlaybookResponse,
    summary="Обновить плейбук",
    description="Обновляет данные плейбука. Только для администраторов."
)
async def update_playbook(
    playbook_id: UUID,
    update_data: PlaybookUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Обновление плейбука
    
    Требует роль: admin
    
    При изменении текста приветствия и greeting_source='tts'
    аудио генерируется заново.
    """
    try:
        service = PlaybookService(db)
        playbook = await service.update_playbook(
            playbook_id=playbook_id,
            update_data=update_data,
            updated_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_updated",
            entity_type="playbook",
            entity_id=playbook.id,
            entity_name=playbook.name,
            details={
                "updated_fields": update_data.model_dump(exclude_unset=True, exclude_none=True),
                "new_version": playbook.version,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return _playbook_to_response(playbook)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка обновления плейбука: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления: {str(e)}"
        )


# ============================================================================
# ИЗМЕНЕНИЕ СТАТУСА ПЛЕЙБУКА
# ============================================================================

@router.post(
    "/{playbook_id}/status",
    response_model=PlaybookResponse,
    summary="Изменить статус плейбука",
    description="Активирует, деактивирует, архивирует или делает шаблоном."
)
async def change_playbook_status(
    playbook_id: UUID,
    status_update: PlaybookStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Изменение статуса плейбука
    
    Действия:
    - activate: сделать активным (остальные деактивируются)
    - deactivate: деактивировать
    - archive: архивировать
    - restore: восстановить из архива
    - make_template: сделать шаблоном
    
    Только один плейбук может быть активным одновременно.
    """
    try:
        service = PlaybookService(db)
        playbook = await service.change_status(
            playbook_id=playbook_id,
            status_update=status_update,
            performed_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action=f"playbook_{status_update.action}",
            entity_type="playbook",
            entity_id=playbook.id,
            entity_name=playbook.name,
            details={"action": status_update.action, "reason": status_update.reason},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return _playbook_to_response(playbook)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# УДАЛЕНИЕ ПЛЕЙБУКА
# ============================================================================

@router.delete(
    "/{playbook_id}",
    response_model=MessageResponse,
    summary="Удалить/архивировать плейбук",
    description="Удаляет или архивирует плейбук. Только для администраторов."
)
async def delete_playbook(
    playbook_id: UUID,
    hard_delete: bool = Query(False, description="Полное удаление (False = архивирование)"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Удаление/архивирование плейбука
    
    Требует роль: admin
    
    Активный плейбук нельзя удалить (сначала деактивируйте).
    При полном удалении также удаляются аудиофайлы.
    """
    try:
        service = PlaybookService(db)
        await service.delete_playbook(
            playbook_id=playbook_id,
            deleted_by=current_user.id,
            hard_delete=hard_delete
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_deleted" if hard_delete else "playbook_archived",
            entity_type="playbook",
            entity_id=playbook_id,
            details={"hard_delete": hard_delete},
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        action_text = "удален" if hard_delete else "архивирован"
        return MessageResponse(
            message=f"Плейбук успешно {action_text}",
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# ГЕНЕРАЦИЯ TTS
# ============================================================================

@router.post(
    "/{playbook_id}/generate-tts",
    response_model=TTSGenerateResponse,
    summary="Сгенерировать аудио через TTS",
    description="Генерирует аудио из текста с конвертацией в телефонный формат 8000 Гц."
)
async def generate_tts(
    playbook_id: UUID,
    tts_request: TTSGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Генерация аудио через TTS
    
    Требует роль: admin
    
    Аудио автоматически конвертируется в формат Asterisk:
    - 8000 Гц
    - Mono
    - 16-bit PCM
    - Частотный фильтр 200-3400 Гц
    
    Голоса:
    - ru_male: мужской (русский)
    - ru_female: женский (русский)
    
    Скорость: 0.5 - 2.0 (1.0 = нормальная)
    """
    try:
        service = PlaybookService(db)
        
        # Проверка существования плейбука
        playbook = await service.get_playbook(playbook_id)
        if not playbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Плейбук с ID {playbook_id} не найден"
            )
        
        result = await service.generate_tts(
            playbook_id=playbook_id,
            request=tts_request,
            generated_by=current_user.id
        )
        
        # Обновление плейбука — сохраняем путь к аудио
        if result.get("audio_path"):
            playbook.greeting_audio_path = result["audio_path"]
            playbook.greeting_source = "tts"
            playbook.updated_by = current_user.id
            await db.flush()
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_tts_generated",
            entity_type="playbook",
            entity_id=playbook_id,
            entity_name=playbook.name,
            details={
                "text_length": len(tts_request.text),
                "voice": tts_request.voice or playbook.tts_voice,
                "speed": tts_request.speed or playbook.tts_speed,
                "output_file": result.get("audio_path"),
            },
            ip_address=request.client.host if request else None,
            status="success" if result.get("success") else "error"
        )
        
        return TTSGenerateResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка генерации TTS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка генерации TTS: {str(e)}"
        )


# ============================================================================
# ЗАГРУЗКА АУДИОФАЙЛА
# ============================================================================

@router.post(
    "/{playbook_id}/upload-audio",
    response_model=AudioUploadResponse,
    summary="Загрузить аудиофайл для плейбука",
    description="Загружает WAV/MP3/OGG файл с автоматической конвертацией."
)
async def upload_audio(
    playbook_id: UUID,
    file: UploadFile = File(..., description="Аудиофайл (WAV, MP3, OGG)"),
    audio_type: str = Path("greeting", description="Тип: greeting, post_beep, closing"),
    auto_convert: bool = Query(True, description="Автоконвертация в формат Asterisk"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Загрузка аудиофайла для плейбука
    
    Требует роль: admin
    
    Поддерживаемые форматы: WAV, MP3, OGG, FLAC
    Максимальный размер: 50 МБ
    
    При auto_convert=True (по умолчанию):
    - Файл конвертируется в WAV 8000 Гц mono 16-bit
    - Применяется телефонный фильтр (200-3400 Гц)
    - Нормализуется громкость
    """
    # Проверка формата
    filename = file.filename or "audio.wav"
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    allowed_formats = ["wav", "mp3", "ogg", "flac"]
    if ext not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат: .{ext}. Допустимые: {allowed_formats}"
        )
    
    # Проверка размера
    content = await file.read()
    max_size = 50 * 1024 * 1024  # 50 МБ
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Размер файла ({len(content) // (1024*1024)} МБ) превышает максимальный (50 МБ)"
        )
    
    try:
        service = PlaybookService(db)
        
        result = await service.upload_audio(
            playbook_id=playbook_id,
            file_content=content,
            original_filename=filename,
            audio_type=audio_type,
            uploaded_by=current_user.id,
            auto_convert=auto_convert
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_audio_uploaded",
            entity_type="playbook",
            entity_id=playbook_id,
            details={
                "filename": filename,
                "audio_type": audio_type,
                "file_size": result.get("file_size_bytes"),
                "duration": result.get("duration_seconds"),
                "sample_rate": result.get("sample_rate"),
                "converted": result.get("converted", False),
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return AudioUploadResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки аудио: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки: {str(e)}"
        )


# ============================================================================
# КЛОНИРОВАНИЕ ПЛЕЙБУКА
# ============================================================================

@router.post(
    "/{playbook_id}/clone",
    response_model=PlaybookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Клонировать плейбук",
    description="Создает копию существующего плейбука."
)
async def clone_playbook(
    playbook_id: UUID,
    clone_request: PlaybookCloneRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Клонирование плейбука
    
    Требует роль: admin
    
    Создает полную копию плейбука с новым именем.
    При copy_audio_files=True копируются все аудиофайлы.
    """
    try:
        service = PlaybookService(db)
        new_playbook = await service.clone_playbook(
            playbook_id=playbook_id,
            clone_request=clone_request,
            cloned_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_cloned",
            entity_type="playbook",
            entity_id=new_playbook.id,
            entity_name=new_playbook.name,
            details={
                "source_id": str(playbook_id),
                "new_name": clone_request.new_name,
                "copied_audio": clone_request.copy_audio_files,
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return _playbook_to_response(new_playbook)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# ТЕСТИРОВАНИЕ ПЛЕЙБУКА
# ============================================================================

@router.post(
    "/{playbook_id}/test",
    response_model=PlaybookTestResponse,
    summary="Тестировать плейбук",
    description="Совершает тестовый звонок по указанному номеру."
)
async def test_playbook(
    playbook_id: UUID,
    test_request: PlaybookTestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Тестирование плейбука
    
    Требует роль: admin
    
    Совершает тестовый звонок на указанный номер
    для проверки работы плейбука.
    
    Типы тестов:
    - full: полный (приветствие + сигнал + запись)
    - greeting_only: только приветствие
    - beep_only: только сигнал
    """
    try:
        service = PlaybookService(db)
        result = await service.test_playbook(
            playbook_id=playbook_id,
            test_request=test_request,
            tested_by=current_user.id
        )
        
        await log_action(
            db=db,
            user_id=current_user.id,
            user_name=current_user.username,
            user_role=current_user.role,
            action="playbook_tested",
            entity_type="playbook",
            entity_id=playbook_id,
            entity_name=result.get("playbook_name"),
            details={
                "test_number": test_request.test_number,
                "test_type": test_request.test_type,
                "call_sid": result.get("call_sid"),
            },
            ip_address=request.client.host if request else None,
            status="success"
        )
        
        return PlaybookTestResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get(
    "/stats/summary",
    summary="Получить статистику по плейбукам",
    description="Возвращает сводную статистику."
)
async def get_playbook_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение статистики по плейбукам"""
    service = PlaybookService(db)
    stats = await service.get_stats()
    return stats


# ============================================================================
# КАТЕГОРИИ И НАСТРОЙКИ
# ============================================================================

@router.get(
    "/categories/list",
    summary="Получить список категорий плейбуков",
    description="Возвращает доступные категории с иконками и цветами."
)
async def get_categories():
    """Список категорий плейбуков"""
    from app.schemas.playbook import PLAYBOOK_CATEGORIES
    return {"categories": PLAYBOOK_CATEGORIES}


@router.get(
    "/tts-voices/list",
    summary="Получить список доступных голосов TTS",
    description="Возвращает доступные голоса для синтеза речи."
)
async def get_tts_voices():
    """Список доступных голосов TTS"""
    from app.schemas.playbook import TTS_VOICES
    return {"voices": TTS_VOICES}


@router.get(
    "/templates/list",
    summary="Получить список шаблонов плейбуков",
    description="Возвращает предопределенные шаблоны для создания плейбуков."
)
async def get_templates():
    """Список шаблонов плейбуков"""
    from app.schemas.playbook import PLAYBOOK_TEMPLATES
    return {"templates": PLAYBOOK_TEMPLATES}
