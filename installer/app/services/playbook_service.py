#!/usr/bin/env python3
"""
Сервис управления плейбуками ГО-ЧС Информирование
Соответствует ТЗ, раздел 19: Playbook входящих звонков

Функционал:
- CRUD операции с плейбуками
- Генерация аудио через TTS (Coqui TTS / espeak) с конвертацией в телефонный формат
- Загрузка готовых аудиофайлов с проверкой и конвертацией при необходимости
- Клонирование плейбуков
- Управление активностью (только один активный)
- Тестирование плейбуков
- Статистика использования

Телефонный формат аудио (Asterisk):
- Частота дискретизации: 8000 Гц
- Каналы: 1 (mono)
- Битность: 16-bit signed PCM
- Частотный диапазон: 200-3400 Гц (телефонный)
"""

import logging
import os
import shutil
import subprocess
import uuid as uuid_module
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook import Playbook
from app.schemas.playbook import (
    PlaybookCreate, PlaybookUpdate, PlaybookStatusUpdate,
    TTSGenerateRequest, PlaybookCloneRequest, PlaybookTestRequest
)
from app.schemas.common import PaginatedResponse, PaginationParams

logger = logging.getLogger(__name__)

# =============================================================================
# КОНСТАНТЫ АУДИО ДЛЯ ASTERISK
# =============================================================================

# Стандартный телефонный формат для Asterisk
ASTERISK_SAMPLE_RATE = 8000      # 8000 Гц (телефонный стандарт)
ASTERISK_CHANNELS = 1            # Mono
ASTERISK_BIT_DEPTH = 16          # 16-bit PCM
ASTERISK_CODEC = "pcm_s16le"     # PCM 16-bit signed little-endian
ASTERISK_HIGHPASS = 200          # Частотный фильтр: нижняя граница (Гц)
ASTERISK_LOWPASS = 3400          # Частотный фильтр: верхняя граница (Гц)

# Поддерживаемые форматы для загрузки
ALLOWED_AUDIO_FORMATS = ["wav", "mp3", "ogg", "flac"]
# Максимальный размер файла (50 МБ)
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024

# =============================================================================
# TTS ДОСТУПНОСТЬ
# =============================================================================

TTS_AVAILABLE = False
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
    logger.info("Coqui TTS доступен")
except ImportError:
    logger.warning("Coqui TTS не установлен. Будет использоваться espeak.")


class PlaybookService:
    """Сервис управления плейбуками"""
    
    def __init__(self, db: AsyncSession, install_dir: str = "/opt/gochs-informing"):
        self.db = db
        self.install_dir = install_dir
        self.playbooks_dir = os.path.join(install_dir, "playbooks")
        self.generated_voice_dir = os.path.join(install_dir, "generated_voice")
        self.recordings_dir = os.path.join(install_dir, "recordings")
        self.tts_model_path = os.path.join(install_dir, "app", "models", "tts")
        
        # Создание директорий
        os.makedirs(self.playbooks_dir, exist_ok=True)
        os.makedirs(self.generated_voice_dir, exist_ok=True)
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        # Инициализация TTS
        self.tts = None
        if TTS_AVAILABLE:
            try:
                self.tts = TTS(
                    model_path=self.tts_model_path,
                    config_path=os.path.join(self.tts_model_path, "config.json"),
                    progress_bar=False
                )
                logger.info("Модель Coqui TTS загружена")
            except Exception as e:
                logger.error(f"Ошибка загрузки модели TTS: {e}")
                self.tts = None
        
        # Проверка доступности инструментов конвертации
        self._check_audio_tools()
    
    # =========================================================================
    # ПРОВЕРКА ИНСТРУМЕНТОВ
    # =========================================================================
    
    def _check_audio_tools(self):
        """Проверка доступности инструментов для работы с аудио"""
        # Проверка ffmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            self.ffmpeg_available = result.returncode == 0
            if self.ffmpeg_available:
                logger.info("ffmpeg доступен")
            else:
                logger.warning("ffmpeg не найден")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.ffmpeg_available = False
            logger.warning("ffmpeg не найден")
        
        # Проверка sox
        try:
            result = subprocess.run(['sox', '--version'], capture_output=True, timeout=5)
            self.sox_available = result.returncode == 0
            if self.sox_available:
                logger.info("sox доступен")
            else:
                logger.warning("sox не найден")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.sox_available = False
            logger.warning("sox не найден")
        
        # Проверка espeak
        try:
            result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
            self.espeak_available = result.returncode == 0
            if self.espeak_available:
                logger.info("espeak доступен")
            else:
                logger.warning("espeak не найден")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.espeak_available = False
            logger.warning("espeak не найден")
        
        if not self.ffmpeg_available and not self.sox_available:
            logger.warning(
                "Ни ffmpeg, ни sox не найдены. "
                "Аудио может быть в неподходящем для Asterisk формате. "
                "Установите: apt-get install ffmpeg sox"
            )
    
    # =========================================================================
    # CRUD ОПЕРАЦИИ
    # =========================================================================
    
    async def create_playbook(
        self,
        playbook_data: PlaybookCreate,
        created_by: Optional[UUID] = None
    ) -> Playbook:
        """
        Создание нового плейбука
        
        Args:
            playbook_data: данные плейбука
            created_by: ID создателя
            
        Returns:
            Созданный плейбук
        """
        playbook = Playbook(
            name=playbook_data.name,
            description=playbook_data.description,
            category=playbook_data.category,
            greeting_text=playbook_data.greeting_text,
            greeting_source=playbook_data.greeting_source,
            post_beep_text=playbook_data.post_beep_text,
            closing_text=playbook_data.closing_text,
            beep_duration=playbook_data.beep_duration,
            pause_before_beep=playbook_data.pause_before_beep,
            max_recording_duration=playbook_data.max_recording_duration,
            min_recording_duration=playbook_data.min_recording_duration,
            greeting_repeat=playbook_data.greeting_repeat,
            repeat_interval=playbook_data.repeat_interval,
            language=playbook_data.language,
            tts_voice=playbook_data.tts_voice,
            tts_speed=playbook_data.tts_speed,
            is_template=playbook_data.is_template,
            is_active=False,
            created_by=created_by,
        )
        
        self.db.add(playbook)
        await self.db.flush()
        
        # Генерация TTS аудио если нужно
        if playbook_data.greeting_source == "tts" and playbook_data.greeting_text:
            try:
                audio_path = await self._generate_tts_asterisk(
                    text=playbook_data.greeting_text,
                    voice=playbook_data.tts_voice or "ru",
                    speed=playbook_data.tts_speed or 1.0,
                    filename=f"playbook_{playbook.id}_greeting"
                )
                playbook.greeting_audio_path = audio_path
            except Exception as e:
                logger.error(f"Ошибка генерации TTS при создании плейбука: {e}")
        
        # Активация если нужно
        if playbook_data.is_active:
            await self._deactivate_all_except(playbook.id)
            playbook.is_active = True
        
        await self.db.flush()
        await self.db.refresh(playbook)
        
        logger.info(f"Создан плейбук: {playbook.name} (ID: {playbook.id})")
        return playbook
    
    async def get_playbook(self, playbook_id: UUID) -> Optional[Playbook]:
        """Получить плейбук по ID"""
        result = await self.db.execute(
            select(Playbook).where(
                and_(Playbook.id == playbook_id, Playbook.is_archived == False)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_active_playbook(self) -> Optional[Playbook]:
        """Получить активный плейбук"""
        result = await self.db.execute(
            select(Playbook).where(
                and_(Playbook.is_active == True, Playbook.is_archived == False)
            )
        )
        return result.scalar_one_or_none()
    
    async def list_playbooks(
        self,
        pagination: PaginationParams = PaginationParams(),
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_template: Optional[bool] = None,
        greeting_source: Optional[str] = None,
        sort_field: str = "created_at",
        sort_direction: str = "desc"
    ) -> PaginatedResponse:
        """
        Получить список плейбуков с фильтрацией
        
        Args:
            pagination: параметры пагинации
            search: поиск по названию/описанию
            category: фильтр по категории
            is_active: только активные/неактивные
            is_template: только шаблоны
            greeting_source: фильтр по источнику приветствия
            sort_field: поле сортировки
            sort_direction: направление
            
        Returns:
            PaginatedResponse со списком плейбуков
        """
        query = select(Playbook).where(Playbook.is_archived == False)
        count_query = select(func.count(Playbook.id)).where(Playbook.is_archived == False)
        
        filters = []
        
        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Playbook.name.ilike(search_term),
                    Playbook.description.ilike(search_term),
                    Playbook.greeting_text.ilike(search_term),
                )
            )
        
        if category:
            filters.append(Playbook.category == category)
        
        if is_active is not None:
            filters.append(Playbook.is_active == is_active)
        
        if is_template is not None:
            filters.append(Playbook.is_template == is_template)
        
        if greeting_source:
            filters.append(Playbook.greeting_source == greeting_source)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        allowed_sort_fields = [
            "name", "category", "is_active", "version",
            "usage_count", "created_at", "updated_at"
        ]
        if sort_field not in allowed_sort_fields:
            sort_field = "created_at"
        
        sort_column = getattr(Playbook, sort_field)
        if sort_direction == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await self.db.execute(query)
        playbooks = result.scalars().all()
        
        items = []
        for pb in playbooks:
            items.append({
                "id": str(pb.id),
                "name": pb.name,
                "description": pb.description,
                "category": pb.category,
                "greeting_source": pb.greeting_source,
                "is_active": pb.is_active,
                "is_template": pb.is_template,
                "is_archived": pb.is_archived,
                "version": pb.version,
                "usage_count": pb.usage_count,
                "total_duration": pb.total_duration,
                "language": pb.language,
                "created_at": pb.created_at.isoformat() if pb.created_at else None,
                "updated_at": pb.updated_at.isoformat() if pb.updated_at else None,
            })
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    
    async def update_playbook(
        self,
        playbook_id: UUID,
        update_data: PlaybookUpdate,
        updated_by: Optional[UUID] = None
    ) -> Playbook:
        """
        Обновление плейбука с перегенерацией TTS при изменении текста
        
        Args:
            playbook_id: ID плейбука
            update_data: данные для обновления
            updated_by: кто обновляет
            
        Returns:
            Обновленный плейбук
        """
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Плейбук с ID {playbook_id} не найден")
        
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Проверка необходимости перегенерации TTS
        regenerate_greeting = False
        old_text = playbook.greeting_text
        old_source = playbook.greeting_source
        old_voice = playbook.tts_voice
        old_speed = playbook.tts_speed
        
        for key, value in update_dict.items():
            if hasattr(playbook, key):
                setattr(playbook, key, value)
        
        # Определяем, нужно ли перегенерировать
        new_text = update_dict.get('greeting_text', old_text)
        new_source = update_dict.get('greeting_source', old_source)
        new_voice = update_dict.get('tts_voice', old_voice)
        new_speed = update_dict.get('tts_speed', old_speed)
        
        if new_source == "tts" and new_text:
            if (new_text != old_text or 
                new_voice != old_voice or 
                new_speed != old_speed or
                old_source != "tts"):
                regenerate_greeting = True
        
        # Инкремент версии
        playbook.version += 1
        playbook.updated_by = updated_by
        playbook.updated_at = datetime.now(timezone.utc)
        
        # Перегенерация TTS
        if regenerate_greeting:
            try:
                # Удаление старого файла
                if playbook.greeting_audio_path and os.path.exists(playbook.greeting_audio_path):
                    os.remove(playbook.greeting_audio_path)
                
                audio_path = await self._generate_tts_asterisk(
                    text=new_text,
                    voice=new_voice or "ru",
                    speed=new_speed or 1.0,
                    filename=f"playbook_{playbook.id}_greeting_v{playbook.version}"
                )
                playbook.greeting_audio_path = audio_path
                logger.info(f"TTS перегенерирован для плейбука {playbook.name}")
            except Exception as e:
                logger.error(f"Ошибка перегенерации TTS: {e}")
        
        await self.db.flush()
        await self.db.refresh(playbook)
        
        logger.info(f"Обновлен плейбук: {playbook.name} (v{playbook.version})")
        return playbook
    
    async def delete_playbook(
        self,
        playbook_id: UUID,
        deleted_by: Optional[UUID] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Удаление плейбука
        
        Args:
            playbook_id: ID плейбука
            deleted_by: кто удаляет
            hard_delete: полное удаление
            
        Returns:
            True если удален
        """
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Плейбук с ID {playbook_id} не найден")
        
        if playbook.is_active and not hard_delete:
            raise ValueError("Нельзя удалить активный плейбук. Сначала деактивируйте его.")
        
        if hard_delete:
            # Удаление аудиофайлов
            for audio_file in playbook.get_audio_files():
                if audio_file.get('path') and os.path.exists(audio_file['path']):
                    try:
                        os.remove(audio_file['path'])
                    except Exception as e:
                        logger.warning(f"Не удалось удалить файл {audio_file['path']}: {e}")
            
            await self.db.delete(playbook)
            logger.info(f"Плейбук полностью удален: {playbook.name}")
        else:
            playbook.is_archived = True
            playbook.is_active = False
            playbook.updated_by = deleted_by
            playbook.updated_at = datetime.now(timezone.utc)
            logger.info(f"Плейбук архивирован: {playbook.name}")
        
        await self.db.flush()
        return True
    
    # =========================================================================
    # УПРАВЛЕНИЕ СТАТУСОМ
    # =========================================================================
    
    async def change_status(
        self,
        playbook_id: UUID,
        status_update: PlaybookStatusUpdate,
        performed_by: UUID
    ) -> Playbook:
        """
        Изменение статуса плейбука
        
        Args:
            playbook_id: ID плейбука
            status_update: новый статус
            performed_by: кто выполняет
            
        Returns:
            Обновленный плейбук
        """
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Плейбук с ID {playbook_id} не найден")
        
        action = status_update.action
        
        if action == "activate":
            # Проверка наличия содержимого
            if playbook.greeting_source == "none":
                raise ValueError("Нельзя активировать плейбук без приветствия")
            if playbook.greeting_source == "tts" and not playbook.greeting_text:
                raise ValueError("Для TTS необходимо указать текст приветствия")
            if playbook.greeting_source == "uploaded" and not playbook.greeting_audio_path:
                raise ValueError("Не загружен аудиофайл приветствия")
            if playbook.greeting_audio_path and not os.path.exists(playbook.greeting_audio_path):
                raise ValueError(f"Аудиофайл не найден: {playbook.greeting_audio_path}")
            
            # Проверка формата аудиофайла
            if playbook.greeting_audio_path:
                audio_info = self._get_audio_info(playbook.greeting_audio_path)
                if audio_info:
                    sample_rate = audio_info.get('sample_rate', 0)
                    if sample_rate and sample_rate != ASTERISK_SAMPLE_RATE:
                        logger.warning(
                            f"Аудиофайл имеет частоту {sample_rate} Гц, "
                            f"ожидается {ASTERISK_SAMPLE_RATE} Гц. "
                            "Может потребоваться транскодирование Asterisk."
                        )
            
            await self._deactivate_all_except(playbook_id)
            playbook.is_active = True
            
        elif action == "deactivate":
            playbook.is_active = False
            
        elif action == "archive":
            if playbook.is_active:
                raise ValueError("Сначала деактивируйте плейбук")
            playbook.is_archived = True
            
        elif action == "restore":
            playbook.is_archived = False
            
        elif action == "make_template":
            playbook.is_template = True
            playbook.is_active = False
        
        playbook.updated_by = performed_by
        playbook.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(playbook)
        
        logger.info(f"Изменен статус плейбука: {playbook.name} → {action}")
        return playbook
    
    async def _deactivate_all_except(self, except_id: UUID):
        """Деактивировать все плейбуки кроме указанного"""
        await self.db.execute(
            update(Playbook)
            .where(and_(Playbook.is_active == True, Playbook.id != except_id))
            .values(is_active=False)
        )
    
    # =========================================================================
    # TTS ГЕНЕРАЦИЯ (С КОНВЕРТАЦИЕЙ В ТЕЛЕФОННЫЙ ФОРМАТ)
    # =========================================================================
    
    async def generate_tts(
        self,
        playbook_id: UUID,
        request: TTSGenerateRequest,
        generated_by: UUID
    ) -> Dict[str, Any]:
        """
        Генерация аудио через TTS для плейбука
        
        Args:
            playbook_id: ID плейбука
            request: параметры генерации
            generated_by: кто генерирует
            
        Returns:
            Информация о сгенерированном файле
        """
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Плейбук с ID {playbook_id} не найден")
        
        text = request.text
        voice = request.voice or playbook.tts_voice or "ru"
        speed = request.speed or playbook.tts_speed or 1.0
        
        filename = request.output_filename or f"playbook_{playbook_id}_tts_{uuid_module.uuid4().hex[:8]}"
        
        # Генерация с конвертацией в телефонный формат
        audio_path = await self._generate_tts_asterisk(
            text=text,
            voice=voice,
            speed=speed,
            filename=filename,
            overwrite=request.overwrite
        )
        
        # Информация о файле
        audio_info = self._get_audio_info(audio_path)
        file_stats = os.stat(audio_path) if os.path.exists(audio_path) else None
        
        result = {
            "success": True,
            "audio_path": audio_path,
            "duration_seconds": audio_info.get('duration') if audio_info else None,
            "sample_rate": audio_info.get('sample_rate') if audio_info else None,
            "channels": audio_info.get('channels') if audio_info else None,
            "bit_depth": audio_info.get('bit_depth') if audio_info else None,
            "file_size_bytes": file_stats.st_size if file_stats else None,
            "text_length": len(text),
            "voice": voice,
            "speed": speed,
            "message": "Аудио успешно сгенерировано в телефонном формате (8000 Гц, mono, 16-bit PCM)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"TTS сгенерирован для плейбука {playbook.name}: {audio_path}")
        return result
    
    async def _generate_tts_asterisk(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        filename: str = "tts_output",
        overwrite: bool = False
    ) -> str:
        """
        Генерация аудио с конвертацией в телефонный формат для Asterisk
        
        Формат:
        - WAV PCM 16-bit signed little-endian
        - 8000 Гц
        - Mono
        - Частотный диапазон: 200-3400 Гц (телефонный фильтр)
        
        Args:
            text: текст для озвучивания
            voice: голос
            speed: скорость речи
            filename: имя файла (без расширения)
            overwrite: перезаписать существующий
            
        Returns:
            Путь к аудиофайлу в формате Asterisk
        """
        output_path = os.path.join(self.playbooks_dir, f"{filename}.wav")
        
        # Проверка существования
        if os.path.exists(output_path) and not overwrite:
            logger.info(f"Аудиофайл уже существует: {output_path}")
            return output_path
        
        # Временный файл для генерации
        temp_path = os.path.join(self.playbooks_dir, f"{filename}_temp_raw.wav")
        
        generated = False
        
        # Способ 1: Coqui TTS
        if self.tts and not generated:
            try:
                self.tts.tts_to_file(
                    text=text,
                    file_path=temp_path,
                    speaker=voice,
                    speed=speed
                )
                generated = True
                logger.info(f"Аудио сгенерировано через Coqui TTS: {temp_path}")
            except Exception as e:
                logger.warning(f"Ошибка Coqui TTS: {e}")
        
        # Способ 2: espeak (fallback)
        if not generated and self.espeak_available:
            try:
                temp_path = await self._generate_espeak_raw(text, voice, speed, temp_path)
                generated = True
                logger.info(f"Аудио сгенерировано через espeak: {temp_path}")
            except Exception as e:
                logger.warning(f"Ошибка espeak: {e}")
        
        if not generated:
            raise RuntimeError("Не удалось сгенерировать аудио ни одним способом")
        
        # Конвертация в телефонный формат
        try:
            self._convert_to_asterisk_format(temp_path, output_path)
            logger.info(f"Аудио сконвертировано в формат Asterisk: {output_path}")
        except Exception as e:
            logger.error(f"Ошибка конвертации: {e}")
            # Используем исходный файл если конвертация не удалась
            if os.path.exists(temp_path) and temp_path != output_path:
                shutil.move(temp_path, output_path)
                logger.warning(f"Использован исходный файл без конвертации: {output_path}")
        
        # Удаление временного файла
        if os.path.exists(temp_path) and temp_path != output_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass
        
        return output_path
    
    async def _generate_espeak_raw(
        self,
        text: str,
        voice: str,
        speed: float,
        output_path: str
    ) -> str:
        """
        Генерация аудио через espeak (без конвертации)
        
        Args:
            text: текст
            voice: голос (ru = русский)
            speed: скорость (0.5-2.0)
            output_path: путь для сохранения
            
        Returns:
            Путь к файлу
        """
        wpm = int(speed * 150)  # Конвертация скорости в слов/мин
        
        cmd = [
            'espeak',
            '-v', f'{voice}',
            '-s', str(wpm),
            '-p', '50',           # Высота тона
            '-a', '100',          # Громкость
            '-w', output_path,    # WAV выход
            text
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"espeak error: {result.stderr}")
        
        return output_path
    
    def _convert_to_asterisk_format(
        self,
        input_path: str,
        output_path: str
    ) -> None:
        """
        Конвертация аудио в телефонный формат для Asterisk
        
        Параметры:
        - Частота: 8000 Гц
        - Каналы: 1 (mono)
        - Битность: 16-bit PCM
        - Фильтр: 200-3400 Гц (телефонный диапазон)
        - Нормализация громкости
        
        Args:
            input_path: исходный файл
            output_path: файл для сохранения
        """
        # Способ 1: через ffmpeg (наилучшее качество)
        if self.ffmpeg_available:
            self._convert_with_ffmpeg(input_path, output_path)
            return
        
        # Способ 2: через sox
        if self.sox_available:
            self._convert_with_sox(input_path, output_path)
            return
        
        # Способ 3: простое копирование (без конвертации)
        logger.warning("Нет инструментов для конвертации. Копируем файл без изменений.")
        shutil.copy2(input_path, output_path)
    
    def _convert_with_ffmpeg(self, input_path: str, output_path: str) -> None:
        """
        Конвертация через ffmpeg
        
        Команда:
        ffmpeg -i input.wav \
               -ar 8000 \           # 8000 Гц
               -ac 1 \              # Mono
               -sample_fmt s16 \    # 16-bit signed
               -acodec pcm_s16le \  # PCM кодек
               -af "highpass=f=200,lowpass=f=3400,volume=1.5" \  # Телефонный фильтр + усиление
               -y \                 # Перезапись
               output.wav
        """
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-ar', str(ASTERISK_SAMPLE_RATE),
            '-ac', str(ASTERISK_CHANNELS),
            '-sample_fmt', 's16',
            '-acodec', ASTERISK_CODEC,
            '-af', f'highpass=f={ASTERISK_HIGHPASS},lowpass=f={ASTERISK_LOWPASS},volume=1.5',
            '-y',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr}")
        
        logger.info(
            f"Конвертация ffmpeg: {os.path.basename(input_path)} "
            f"→ {ASTERISK_SAMPLE_RATE}Hz mono 16-bit PCM"
        )
    
    def _convert_with_sox(self, input_path: str, output_path: str) -> None:
        """
        Конвертация через sox (fallback)
        
        Команда:
        sox input.wav -r 8000 -c 1 -b 16 output.wav \
            highpass 200 lowpass 3400 gain -n -3
        """
        cmd = [
            'sox',
            input_path,
            '-r', str(ASTERISK_SAMPLE_RATE),
            '-c', str(ASTERISK_CHANNELS),
            '-b', str(ASTERISK_BIT_DEPTH),
            output_path,
            'highpass', str(ASTERISK_HIGHPASS),
            'lowpass', str(ASTERISK_LOWPASS),
            'gain', '-n', '-3',
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"sox error: {result.stderr}")
        
        logger.info(
            f"Конвертация sox: {os.path.basename(input_path)} "
            f"→ {ASTERISK_SAMPLE_RATE}Hz mono {ASTERISK_BIT_DEPTH}-bit"
        )
    
    def _get_audio_info(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию об аудиофайле
        
        Args:
            audio_path: путь к файлу
            
        Returns:
            Словарь с информацией или None
        """
        if not os.path.exists(audio_path):
            return None
        
        info = {
            'path': audio_path,
            'size_bytes': os.path.getsize(audio_path),
        }
        
        # Попытка через ffprobe
        if self.ffmpeg_available:
            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-select_streams', 'a:0',
                    '-show_entries',
                    'stream=sample_rate,channels,duration,codec_name,bit_rate',
                    '-of', 'csv=p=0',
                    audio_path
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(',')
                    if len(parts) >= 4:
                        info['sample_rate'] = int(parts[0]) if parts[0] else None
                        info['channels'] = int(parts[1]) if parts[1] else None
                        info['duration'] = float(parts[2]) if parts[2] else None
                        info['codec'] = parts[3] if parts[3] else None
                    return info
            except Exception as e:
                logger.warning(f"Ошибка ffprobe: {e}")
        
        # Попытка через Python wave (только для WAV)
        try:
            import wave
            with wave.open(audio_path, 'r') as wf:
                info['sample_rate'] = wf.getframerate()
                info['channels'] = wf.getnchannels()
                info['bit_depth'] = wf.getsampwidth() * 8
                info['duration'] = wf.getnframes() / wf.getframerate()
            return info
        except Exception:
            pass
        
        return info
    
    # =========================================================================
    # ЗАГРУЗКА АУДИОФАЙЛОВ (С ПРОВЕРКОЙ И КОНВЕРТАЦИЕЙ)
    # =========================================================================
    
    async def upload_audio(
        self,
        playbook_id: UUID,
        file_content: bytes,
        original_filename: str,
        audio_type: str = "greeting",
        uploaded_by: Optional[UUID] = None,
        auto_convert: bool = True
    ) -> Dict[str, Any]:
        """
        Загрузка аудиофайла для плейбука
        
        Args:
            playbook_id: ID плейбука
            file_content: содержимое файла
            original_filename: оригинальное имя файла
            audio_type: тип аудио (greeting, post_beep, closing)
            uploaded_by: кто загрузил
            auto_convert: автоматически конвертировать в формат Asterisk
            
        Returns:
            Информация о загруженном файле
        """
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Плейбук с ID {playbook_id} не найден")
        
        # Проверка размера
        if len(file_content) > MAX_AUDIO_FILE_SIZE:
            raise ValueError(
                f"Размер файла ({len(file_content) // (1024*1024)} МБ) "
                f"превышает максимальный ({MAX_AUDIO_FILE_SIZE // (1024*1024)} МБ)"
            )
        
        # Проверка формата
        ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else 'wav'
        if ext not in ALLOWED_AUDIO_FORMATS:
            raise ValueError(f"Неподдерживаемый формат: .{ext}. Допустимые: {ALLOWED_AUDIO_FORMATS}")
        
        # Сохранение исходного файла
        raw_filename = f"playbook_{playbook_id}_{audio_type}_raw_{uuid_module.uuid4().hex[:8]}.{ext}"
        raw_path = os.path.join(self.playbooks_dir, raw_filename)
        
        with open(raw_path, 'wb') as f:
            f.write(file_content)
        
        # Конвертация в формат Asterisk (если нужно)
        final_filename = f"playbook_{playbook_id}_{audio_type}_{uuid_module.uuid4().hex[:8]}.wav"
        final_path = os.path.join(self.playbooks_dir, final_filename)
        
        if auto_convert and ext != 'wav':
            # Конвертация из mp3/ogg/flac в WAV для Asterisk
            try:
                self._convert_to_asterisk_format(raw_path, final_path)
                os.remove(raw_path)  # Удаляем исходный
            except Exception as e:
                logger.warning(f"Конвертация не удалась: {e}, используется исходный файл")
                final_path = raw_path
        elif ext == 'wav':
            # Проверка формата WAV
            audio_info = self._get_audio_info(raw_path)
            if audio_info and audio_info.get('sample_rate') != ASTERISK_SAMPLE_RATE:
                logger.info(
                    f"WAV имеет частоту {audio_info.get('sample_rate')} Гц, "
                    f"конвертируем в {ASTERISK_SAMPLE_RATE} Гц"
                )
                try:
                    self._convert_to_asterisk_format(raw_path, final_path)
                    os.remove(raw_path)
                except Exception as e:
                    logger.warning(f"Конвертация не удалась: {e}, используется исходный файл")
                    final_path = raw_path
            else:
                final_path = raw_path
        else:
            final_path = raw_path
        
        # Обновление плейбука
        if audio_type == "greeting":
            if playbook.greeting_audio_path and os.path.exists(playbook.greeting_audio_path):
                try:
                    os.remove(playbook.greeting_audio_path)
                except Exception:
                    pass
            playbook.greeting_audio_path = final_path
            playbook.greeting_source = "uploaded"
        elif audio_type == "post_beep":
            if playbook.post_beep_audio_path and os.path.exists(playbook.post_beep_audio_path):
                try:
                    os.remove(playbook.post_beep_audio_path)
                except Exception:
                    pass
            playbook.post_beep_audio_path = final_path
        elif audio_type == "closing":
            if playbook.closing_audio_path and os.path.exists(playbook.closing_audio_path):
                try:
                    os.remove(playbook.closing_audio_path)
                except Exception:
                    pass
            playbook.closing_audio_path = final_path
        
        playbook.updated_by = uploaded_by
        playbook.version += 1
        playbook.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        
        # Информация о файле
        audio_info = self._get_audio_info(final_path)
        file_stats = os.stat(final_path)
        
        result = {
            "audio_path": final_path,
            "original_filename": original_filename,
            "file_size_bytes": file_stats.st_size,
            "format": "wav",
            "duration_seconds": audio_info.get('duration') if audio_info else None,
            "sample_rate": audio_info.get('sample_rate') if audio_info else None,
            "channels": audio_info.get('channels') if audio_info else None,
            "bit_depth": audio_info.get('bit_depth') if audio_info else None,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "converted": (raw_path != final_path),
        }
        
        logger.info(f"Аудиофайл загружен для плейбука {playbook.name}: {original_filename}")
        return result
    
    # =========================================================================
    # КЛОНИРОВАНИЕ
    # =========================================================================
    
    async def clone_playbook(
        self,
        playbook_id: UUID,
        clone_request: PlaybookCloneRequest,
        cloned_by: UUID
    ) -> Playbook:
        """Клонирование плейбука"""
        source = await self.get_playbook(playbook_id)
        if not source:
            raise ValueError(f"Исходный плейбук с ID {playbook_id} не найден")
        
        new_playbook = Playbook(
            name=clone_request.new_name,
            description=f"Копия плейбука '{source.name}'",
            category=source.category,
            greeting_text=source.greeting_text,
            greeting_source=source.greeting_source,
            post_beep_text=source.post_beep_text,
            closing_text=source.closing_text,
            beep_duration=source.beep_duration,
            pause_before_beep=source.pause_before_beep,
            max_recording_duration=source.max_recording_duration,
            min_recording_duration=source.min_recording_duration,
            greeting_repeat=source.greeting_repeat,
            repeat_interval=source.repeat_interval,
            language=source.language,
            tts_voice=source.tts_voice,
            tts_speed=source.tts_speed,
            is_template=False,
            is_active=False,
            created_by=cloned_by,
        )
        
        self.db.add(new_playbook)
        await self.db.flush()
        
        # Копирование аудиофайлов
        if clone_request.copy_audio_files:
            for audio_type, source_path in [
                ("greeting", source.greeting_audio_path),
                ("post_beep", source.post_beep_audio_path),
                ("closing", source.closing_audio_path),
            ]:
                if source_path and os.path.exists(source_path):
                    try:
                        new_path = self._copy_audio_file(source_path, f"playbook_{new_playbook.id}_{audio_type}")
                        if audio_type == "greeting":
                            new_playbook.greeting_audio_path = new_path
                        elif audio_type == "post_beep":
                            new_playbook.post_beep_audio_path = new_path
                        elif audio_type == "closing":
                            new_playbook.closing_audio_path = new_path
                    except Exception as e:
                        logger.warning(f"Не удалось скопировать {audio_type}: {e}")
        
        if clone_request.make_active:
            await self._deactivate_all_except(new_playbook.id)
            new_playbook.is_active = True
        
        await self.db.flush()
        await self.db.refresh(new_playbook)
        
        logger.info(f"Клонирован плейбук: {source.name} → {new_playbook.name}")
        return new_playbook
    
    def _copy_audio_file(self, source_path: str, new_filename: str) -> str:
        """Копирование аудиофайла с новым именем"""
        ext = os.path.splitext(source_path)[1] or '.wav'
        new_path = os.path.join(self.playbooks_dir, f"{new_filename}_{uuid_module.uuid4().hex[:8]}{ext}")
        shutil.copy2(source_path, new_path)
        return new_path
    
    # =========================================================================
    # ТЕСТИРОВАНИЕ
    # =========================================================================
    
    async def test_playbook(
        self,
        playbook_id: UUID,
        test_request: PlaybookTestRequest,
        tested_by: UUID
    ) -> Dict[str, Any]:
        """
        Тестирование плейбука (звонок на указанный номер через Asterisk)
        
        Args:
            playbook_id: ID плейбука
            test_request: параметры теста
            tested_by: кто тестирует
            
        Returns:
            Результат тестирования
        """
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Плейбук с ID {playbook_id} не найден")
        
        # Проверка содержимого
        if test_request.test_type in ["full", "greeting_only"]:
            if playbook.greeting_source == "none":
                raise ValueError("Плейбук не содержит приветствия")
            if playbook.greeting_source == "tts" and not playbook.greeting_text:
                raise ValueError("Текст приветствия не указан")
            if playbook.greeting_source == "uploaded" and not playbook.greeting_audio_path:
                raise ValueError("Аудиофайл приветствия не загружен")
            if playbook.greeting_audio_path and not os.path.exists(playbook.greeting_audio_path):
                raise ValueError(f"Аудиофайл не найден: {playbook.greeting_audio_path}")
        
        # TODO: Интеграция с Asterisk AMI для совершения тестового звонка
        # Пока возвращаем информацию о том, что тест инициирован
        
        test_id = f"test_{uuid_module.uuid4().hex[:8]}"
        
        logger.info(
            f"Тестирование плейбука '{playbook.name}' "
            f"на номер {test_request.test_number} "
            f"(тип: {test_request.test_type})"
        )
        
        return {
            "success": True,
            "call_sid": test_id,
            "test_number": test_request.test_number,
            "playbook_name": playbook.name,
            "test_type": test_request.test_type,
            "greeting_source": playbook.greeting_source,
            "greeting_audio_path": playbook.greeting_audio_path,
            "greeting_duration": playbook.total_duration,
            "duration_seconds": None,  # Будет заполнено после звонка
            "recording_path": None,     # Будет заполнено после звонка
            "message": f"Тестовый звонок на {test_request.test_number} инициирован",
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }
    
    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================
    
    async def increment_usage(self, playbook_id: UUID):
        """Увеличить счетчик использования плейбука"""
        await self.db.execute(
            update(Playbook)
            .where(Playbook.id == playbook_id)
            .values(
                usage_count=Playbook.usage_count + 1,
                last_used_at=datetime.now(timezone.utc)
            )
        )
        await self.db.flush()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику по плейбукам"""
        total = await self.db.execute(
            select(func.count(Playbook.id)).where(Playbook.is_archived == False)
        )
        total_count = total.scalar() or 0
        
        active = await self.db.execute(
            select(func.count(Playbook.id)).where(Playbook.is_active == True)
        )
        active_count = active.scalar() or 0
        
        templates = await self.db.execute(
            select(func.count(Playbook.id)).where(
                and_(Playbook.is_template == True, Playbook.is_archived == False)
            )
        )
        template_count = templates.scalar() or 0
        
        categories = await self.db.execute(
            select(Playbook.category, func.count(Playbook.id))
            .where(Playbook.is_archived == False)
            .group_by(Playbook.category)
        )
        by_category = {row[0] or "без категории": row[1] for row in categories}
        
        sources = await self.db.execute(
            select(Playbook.greeting_source, func.count(Playbook.id))
            .where(Playbook.is_archived == False)
            .group_by(Playbook.greeting_source)
        )
        by_source = {row[0]: row[1] for row in sources}
        
        most_used = await self.db.execute(
            select(Playbook)
            .where(Playbook.is_archived == False)
            .order_by(Playbook.usage_count.desc())
            .limit(1)
        )
        most_used_pb = most_used.scalar_one_or_none()
        
        return {
            "total": total_count,
            "active": active_count,
            "inactive": total_count - active_count,
            "templates": template_count,
            "by_category": by_category,
            "by_source": by_source,
            "most_used": {
                "id": str(most_used_pb.id) if most_used_pb else None,
                "name": most_used_pb.name if most_used_pb else None,
                "usage_count": most_used_pb.usage_count if most_used_pb else 0,
            } if most_used_pb else None,
            "active_playbook": await self._get_active_info(),
        }
    
    async def _get_active_info(self) -> Optional[Dict[str, Any]]:
        """Информация об активном плейбуке"""
        active = await self.get_active_playbook()
        if not active:
            return None
        return {
            "id": str(active.id),
            "name": active.name,
            "greeting_source": active.greeting_source,
            "version": active.version,
            "usage_count": active.usage_count,
            "has_audio": bool(active.greeting_audio_path and os.path.exists(active.greeting_audio_path)),
        }
    
    # =========================================================================
    # ШАБЛОНЫ
    # =========================================================================
    
    async def create_from_template(
        self,
        template_name: str,
        created_by: UUID
    ) -> Playbook:
        """
        Создать плейбук из предопределенного шаблона
        
        Args:
            template_name: имя шаблона (default, emergency, short)
            created_by: кто создает
            
        Returns:
            Созданный плейбук
        """
        templates = {
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
        
        template = templates.get(template_name, templates["default"])
        
        playbook_data = PlaybookCreate(
            **template,
            greeting_source="tts",
            is_template=True,
            is_active=False,
        )
        
        return await self.create_playbook(playbook_data, created_by)
