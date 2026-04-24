#!/usr/bin/env python3
"""
Сервис управления плейбуками ГО-ЧС Информирование
Соответствует ТЗ, раздел 19: Playbook входящих звонков

Функционал:
- CRUD операции с плейбуками
- Генерация аудио через TTS (Coqui TTS / espeak)
- Загрузка готовых аудиофайлов
- Клонирование плейбуков
- Управление активностью (только один активный)
- Тестирование плейбуков
- Статистика использования
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

# Настройки TTS
TTS_AVAILABLE = False
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
    logger.info("Coqui TTS доступен")
except ImportError:
    logger.warning("Coqui TTS не установлен. Будет использоваться espeak.")

# Поддерживаемые аудиоформаты
ALLOWED_AUDIO_FORMATS = ["wav", "mp3", "ogg"]
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ


class PlaybookService:
    """Сервис управления плейбуками"""
    
    def __init__(self, db: AsyncSession, install_dir: str = "/opt/gochs-informing"):
        self.db = db
        self.install_dir = install_dir
        self.playbooks_dir = os.path.join(install_dir, "playbooks")
        self.tts_model_path = os.path.join(install_dir, "app", "models", "tts")
        
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
        
        # Создание директории для плейбуков
        os.makedirs(self.playbooks_dir, exist_ok=True)
    
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
            is_active=False,  # Новый плейбук неактивен
            created_by=created_by,
        )
        
        self.db.add(playbook)
        await self.db.flush()
        
        # Генерация TTS аудио если нужно
        if playbook_data.greeting_source == "tts" and playbook_data.greeting_text:
            try:
                audio_path = await self._generate_tts(
                    text=playbook_data.greeting_text,
                    voice=playbook_data.tts_voice or "ru",
                    speed=playbook_data.tts_speed,
                    filename=f"playbook_{playbook.id}_greeting"
                )
                playbook.greeting_audio_path = audio_path
            except Exception as e:
                logger.error(f"Ошибка генерации TTS при создании: {e}")
        
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
        
        # Фильтры
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
        
        # Сортировка
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
        
        # Пагинация
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
        Обновление плейбука
        
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
        
        # Если изменился текст приветствия и источник TTS — перегенерировать аудио
        regenerate_tts = False
        if ('greeting_text' in update_dict or 'greeting_source' in update_dict):
            if update_dict.get('greeting_source', playbook.greeting_source) == 'tts':
                regenerate_tts = True
        
        for key, value in update_dict.items():
            if hasattr(playbook, key):
                setattr(playbook, key, value)
        
        # Инкремент версии
        playbook.version += 1
        playbook.updated_by = updated_by
        playbook.updated_at = datetime.now(timezone.utc)
        
        # Регенерация TTS
        if regenerate_tts and playbook.greeting_text:
            try:
                audio_path = await self._generate_tts(
                    text=playbook.greeting_text,
                    voice=playbook.tts_voice or "ru",
                    speed=playbook.tts_speed,
                    filename=f"playbook_{playbook.id}_greeting_v{playbook.version}"
                )
                playbook.greeting_audio_path = audio_path
            except Exception as e:
                logger.error(f"Ошибка регенерации TTS: {e}")
        
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
        
        # Нельзя удалить активный плейбук
        if playbook.is_active and not hard_delete:
            raise ValueError("Нельзя удалить активный плейбук. Сначала деактивируйте его.")
        
        if hard_delete:
            # Удаление аудиофайлов
            for audio_file in playbook.get_audio_files():
                if os.path.exists(audio_file['path']):
                    os.remove(audio_file['path'])
            
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
            
            # Деактивация всех остальных
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
    # TTS ГЕНЕРАЦИЯ
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
        
        # Имя файла
        filename = request.output_filename or f"playbook_{playbook_id}_tts_{uuid_module.uuid4().hex[:8]}"
        
        # Генерация
        audio_path = await self._generate_tts(
            text=text,
            voice=voice,
            speed=speed,
            filename=filename,
            overwrite=request.overwrite
        )
        
        # Получение информации о файле
        file_stats = os.stat(audio_path)
        duration = self._get_audio_duration(audio_path)
        
        result = {
            "success": True,
            "audio_path": audio_path,
            "duration_seconds": duration,
            "file_size_bytes": file_stats.st_size,
            "text_length": len(text),
            "voice": voice,
            "message": "Аудио успешно сгенерировано",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"TTS сгенерирован для плейбука {playbook.name}: {audio_path}")
        return result
    
    async def _generate_tts(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        filename: str = "tts_output",
        overwrite: bool = False
    ) -> str:
        """
        Генерация аудио через TTS
        
        Args:
            text: текст для озвучивания
            voice: голос
            speed: скорость речи
            filename: имя файла (без расширения)
            overwrite: перезаписать существующий
            
        Returns:
            Путь к аудиофайлу
        """
        output_path = os.path.join(self.playbooks_dir, f"{filename}.wav")
        
        # Проверка существования
        if os.path.exists(output_path) and not overwrite:
            return output_path
        
        # Попытка через Coqui TTS
        if self.tts:
            try:
                self.tts.tts_to_file(
                    text=text,
                    file_path=output_path,
                    speaker=voice,
                    speed=speed
                )
                logger.info(f"Аудио сгенерировано через Coqui TTS: {output_path}")
                return output_path
            except Exception as e:
                logger.warning(f"Ошибка Coqui TTS: {e}, пробуем espeak...")
        
        # Fallback через espeak
        return await self._generate_espeak(text, voice, speed, output_path)
    
    async def _generate_espeak(
        self,
        text: str,
        voice: str,
        speed: float,
        output_path: str
    ) -> str:
        """
        Генерация аудио через espeak (fallback)
        
        Args:
            text: текст
            voice: голос (ru = русский)
            speed: скорость (слов в минуту)
            output_path: путь для сохранения
            
        Returns:
            Путь к файлу
        """
        try:
            # Конвертация скорости (0.5-2.0 → 80-300 wpm)
            wpm = int(speed * 150)
            
            cmd = [
                'espeak',
                '-v', f'{voice}',
                '-s', str(wpm),
                '-p', '50',
                '-a', '100',
                '-w', output_path,
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
            
            logger.info(f"Аудио сгенерировано через espeak: {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Таймаут генерации аудио через espeak (60 сек)")
        except FileNotFoundError:
            raise RuntimeError("espeak не установлен. Установите: apt-get install espeak")
        except Exception as e:
            raise RuntimeError(f"Ошибка генерации аудио: {str(e)}")
    
    def _get_audio_duration(self, audio_path: str) -> Optional[float]:
        """Получить длительность аудиофайла (секунд)"""
        try:
            import wave
            with wave.open(audio_path, 'r') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)
        except Exception:
            try:
                # Попытка через ffprobe
                cmd = [
                    'ffprobe', '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    audio_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return float(result.stdout.strip())
            except Exception:
                pass
        return None
    
    # =========================================================================
    # ЗАГРУЗКА АУДИОФАЙЛОВ
    # =========================================================================
    
    async def upload_audio(
        self,
        playbook_id: UUID,
        file_content: bytes,
        original_filename: str,
        audio_type: str = "greeting",
        uploaded_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Загрузка аудиофайла для плейбука
        
        Args:
            playbook_id: ID плейбука
            file_content: содержимое файла
            original_filename: оригинальное имя файла
            audio_type: тип аудио (greeting, post_beep, closing)
            uploaded_by: кто загрузил
            
        Returns:
            Информация о загруженном файле
        """
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Плейбук с ID {playbook_id} не найден")
        
        # Проверка размера
        if len(file_content) > MAX_AUDIO_FILE_SIZE:
            raise ValueError(f"Размер файла превышает {MAX_AUDIO_FILE_SIZE // (1024*1024)} МБ")
        
        # Проверка формата
        ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else 'wav'
        if ext not in ALLOWED_AUDIO_FORMATS:
            raise ValueError(f"Неподдерживаемый формат: {ext}. Допустимые: {ALLOWED_AUDIO_FORMATS}")
        
        # Сохранение файла
        filename = f"playbook_{playbook_id}_{audio_type}_{uuid_module.uuid4().hex[:8]}.{ext}"
        file_path = os.path.join(self.playbooks_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Обновление плейбука
        if audio_type == "greeting":
            if playbook.greeting_audio_path and os.path.exists(playbook.greeting_audio_path):
                os.remove(playbook.greeting_audio_path)
            playbook.greeting_audio_path = file_path
            playbook.greeting_source = "uploaded"
        elif audio_type == "post_beep":
            if playbook.post_beep_audio_path and os.path.exists(playbook.post_beep_audio_path):
                os.remove(playbook.post_beep_audio_path)
            playbook.post_beep_audio_path = file_path
        elif audio_type == "closing":
            if playbook.closing_audio_path and os.path.exists(playbook.closing_audio_path):
                os.remove(playbook.closing_audio_path)
            playbook.closing_audio_path = file_path
        
        playbook.updated_by = uploaded_by
        playbook.version += 1
        playbook.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        
        # Информация о файле
        duration = self._get_audio_duration(file_path)
        file_stats = os.stat(file_path)
        
        result = {
            "audio_path": file_path,
            "original_filename": original_filename,
            "file_size_bytes": file_stats.st_size,
            "format": ext,
            "duration_seconds": duration,
            "sample_rate": None,  # Можно добавить через ffprobe
            "channels": None,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
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
        """
        Клонирование плейбука
        
        Args:
            playbook_id: ID исходного плейбука
            clone_request: параметры клонирования
            cloned_by: кто клонирует
            
        Returns:
            Новый плейбук
        """
        source = await self.get_playbook(playbook_id)
        if not source:
            raise ValueError(f"Исходный плейбук с ID {playbook_id} не найден")
        
        # Создание нового плейбука
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
            if source.greeting_audio_path and os.path.exists(source.greeting_audio_path):
                new_path = await self._copy_audio_file(
                    source.greeting_audio_path,
                    f"playbook_{new_playbook.id}_greeting"
                )
                new_playbook.greeting_audio_path = new_path
            
            if source.post_beep_audio_path and os.path.exists(source.post_beep_audio_path):
                new_path = await self._copy_audio_file(
                    source.post_beep_audio_path,
                    f"playbook_{new_playbook.id}_post_beep"
                )
                new_playbook.post_beep_audio_path = new_path
            
            if source.closing_audio_path and os.path.exists(source.closing_audio_path):
                new_path = await self._copy_audio_file(
                    source.closing_audio_path,
                    f"playbook_{new_playbook.id}_closing"
                )
                new_playbook.closing_audio_path = new_path
        
        # Активация если нужно
        if clone_request.make_active:
            await self._deactivate_all_except(new_playbook.id)
            new_playbook.is_active = True
        
        await self.db.flush()
        await self.db.refresh(new_playbook)
        
        logger.info(f"Клонирован плейбук: {source.name} → {new_playbook.name}")
        return new_playbook
    
    async def _copy_audio_file(self, source_path: str, new_filename: str) -> str:
        """Копирование аудиофайла с новым именем"""
        ext = os.path.splitext(source_path)[1]
        new_path = os.path.join(self.playbooks_dir, f"{new_filename}{ext}")
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
        Тестирование плейбука (звонок на указанный номер)
        
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
        
        # Проверка наличия содержимого для теста
        if test_request.test_type in ["full", "greeting_only"]:
            if playbook.greeting_source == "none":
                raise ValueError("Плейбук не содержит приветствия")
            if playbook.greeting_source == "tts" and not playbook.greeting_text:
                raise ValueError("Текст приветствия не указан")
            if playbook.greeting_source == "uploaded" and not playbook.greeting_audio_path:
                raise ValueError("Аудиофайл приветствия не загружен")
        
        # Здесь должна быть интеграция с Asterisk для совершения тестового звонка
        # Пока возвращаем заглушку
        
        logger.info(f"Тестирование плейбука {playbook.name} на номер {test_request.test_number}")
        
        return {
            "success": True,
            "call_sid": f"test_{uuid_module.uuid4().hex[:8]}",
            "test_number": test_request.test_number,
            "duration_seconds": None,
            "recording_path": None,
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
        # Всего
        total = await self.db.execute(
            select(func.count(Playbook.id)).where(Playbook.is_archived == False)
        )
        total_count = total.scalar() or 0
        
        # Активных
        active = await self.db.execute(
            select(func.count(Playbook.id)).where(Playbook.is_active == True)
        )
        active_count = active.scalar() or 0
        
        # Шаблонов
        templates = await self.db.execute(
            select(func.count(Playbook.id)).where(
                and_(Playbook.is_template == True, Playbook.is_archived == False)
            )
        )
        template_count = templates.scalar() or 0
        
        # По категориям
        categories = await self.db.execute(
            select(Playbook.category, func.count(Playbook.id))
            .where(Playbook.is_archived == False)
            .group_by(Playbook.category)
        )
        by_category = {row[0] or "без категории": row[1] for row in categories}
        
        # По источникам
        sources = await self.db.execute(
            select(Playbook.greeting_source, func.count(Playbook.id))
            .where(Playbook.is_archived == False)
            .group_by(Playbook.greeting_source)
        )
        by_source = {row[0]: row[1] for row in sources}
        
        # Самый используемый
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
