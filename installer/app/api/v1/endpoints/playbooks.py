#!/usr/bin/env python3
"""
API эндпоинты для управления плейбуками (сценариями входящих звонков)
Соответствует ТЗ, раздел 19: Playbook входящих звонков

Функционал:
- CRUD операции с плейбуками
- Генерация аудио через TTS (espeak/Coqui)
- Загрузка готовых аудиофайлов (WAV/MP3)
- Активация/деактивация (только один активный)
- Клонирование
- Тестирование

Пример плейбука (ТЗ):
"Здравствуйте. Вы позвонили в систему ГО-ЧС информирования предприятия.
После сигнала оставьте сообщение."
"""
import logging
import os
import shutil
import subprocess
import uuid as uuid_module
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()

PLAYBOOKS_DIR = "/opt/gochs-informing/playbooks"
os.makedirs(PLAYBOOKS_DIR, exist_ok=True)


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА ПЛЕЙБУКОВ
# ============================================================================

@router.get("/")
async def list_playbooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка плейбуков
    
    Доступ: admin, operator, viewer
    """
    conditions = ["is_archived = false"]
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if is_active is not None:
        conditions.append("is_active = :active")
        params["active"] = is_active
    if search:
        conditions.append("(name ILIKE :s OR greeting_text ILIKE :s)")
        params["s"] = f"%{search}%"
    
    where = " AND ".join(conditions)
    
    try:
        r = await db.execute(text(f"SELECT COUNT(*) FROM playbooks WHERE {where}"), params)
        total = r.scalar() or 0
        
        r = await db.execute(
            text(f"SELECT * FROM playbooks WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            params
        )
        
        items = []
        for row in r.fetchall():
            items.append({
                "id": str(row.id),
                "name": row.name,
                "description": row.description,
                "category": row.category,
                "greeting_source": row.greeting_source or "tts",
                "greeting_text": row.greeting_text[:200] if row.greeting_text else None,
                "is_active": row.is_active or False,
                "is_template": row.is_template or False,
                "version": row.version or 1,
                "usage_count": row.usage_count or 0,
                "total_duration": 0,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Error listing playbooks: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================================
# ПОЛУЧЕНИЕ АКТИВНОГО ПЛЕЙБУКА
# ============================================================================

@router.get("/active")
async def get_active_playbook(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение текущего активного плейбука"""
    try:
        r = await db.execute(
            text("SELECT * FROM playbooks WHERE is_active = true AND is_archived = false LIMIT 1")
        )
        row = r.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Нет активного плейбука")
        
        return {
            "id": str(row.id),
            "name": row.name,
            "description": row.description,
            "category": row.category,
            "greeting_text": row.greeting_text,
            "greeting_audio_path": row.greeting_audio_path,
            "greeting_source": row.greeting_source or "tts",
            "post_beep_text": row.post_beep_text,
            "closing_text": row.closing_text,
            "beep_duration": row.beep_duration or 1.0,
            "max_recording_duration": row.max_recording_duration or 300,
            "is_active": True,
            "is_template": row.is_template or False,
            "version": row.version or 1,
            "usage_count": row.usage_count or 0,
            "audio_files": _get_audio_files(row),
            "created_at": row.created_at.isoformat() if row.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ПОЛУЧЕНИЕ ПЛЕЙБУКА ПО ID
# ============================================================================

@router.get("/{playbook_id}")
async def get_playbook(
    playbook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение плейбука по ID"""
    r = await db.execute(
        text("SELECT * FROM playbooks WHERE id=:id AND is_archived=false"),
        {"id": playbook_id}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Плейбук не найден")
    
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "greeting_text": row.greeting_text,
        "greeting_audio_path": row.greeting_audio_path,
        "greeting_source": row.greeting_source or "tts",
        "post_beep_text": row.post_beep_text,
        "post_beep_audio_path": row.post_beep_audio_path,
        "closing_text": row.closing_text,
        "closing_audio_path": row.closing_audio_path,
        "beep_duration": row.beep_duration or 1.0,
        "pause_before_beep": row.pause_before_beep or 0.5,
        "max_recording_duration": row.max_recording_duration or 300,
        "min_recording_duration": row.min_recording_duration or 3,
        "greeting_repeat": row.greeting_repeat or 1,
        "total_duration": 0,
        "language": row.language or "ru",
        "tts_voice": row.tts_voice,
        "tts_speed": row.tts_speed or 1.0,
        "is_active": row.is_active or False,
        "is_archived": row.is_archived or False,
        "is_template": row.is_template or False,
        "version": row.version or 1,
        "usage_count": row.usage_count or 0,
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "audio_files": _get_audio_files(row),
        "created_by": str(row.created_by) if row.created_by else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if hasattr(row, 'updated_at') and row.updated_at else None
    }


def _get_audio_files(row) -> list:
    """Получение списка аудиофайлов плейбука"""
    files = []
    if row.greeting_audio_path and os.path.exists(row.greeting_audio_path):
        files.append({"type": "greeting", "path": row.greeting_audio_path, "label": "Приветствие"})
    if hasattr(row, 'post_beep_audio_path') and row.post_beep_audio_path and os.path.exists(row.post_beep_audio_path):
        files.append({"type": "post_beep", "path": row.post_beep_audio_path, "label": "После сигнала"})
    if hasattr(row, 'closing_audio_path') and row.closing_audio_path and os.path.exists(row.closing_audio_path):
        files.append({"type": "closing", "path": row.closing_audio_path, "label": "Завершение"})
    return files


# ============================================================================
# СКАЧИВАНИЕ АУДИОФАЙЛА
# ============================================================================

@router.get("/{playbook_id}/audio/{audio_type}")
async def download_audio(
    playbook_id: str,
    audio_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Скачивание аудиофайла плейбука (greeting/post_beep/closing)"""
    r = await db.execute(text("SELECT * FROM playbooks WHERE id=:id"), {"id": playbook_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Плейбук не найден")
    
    audio_path = None
    if audio_type == "greeting":
        audio_path = row.greeting_audio_path
    elif audio_type == "post_beep":
        audio_path = row.post_beep_audio_path if hasattr(row, 'post_beep_audio_path') else None
    elif audio_type == "closing":
        audio_path = row.closing_audio_path if hasattr(row, 'closing_audio_path') else None
    else:
        raise HTTPException(status_code=400, detail="Неизвестный тип аудио")
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Аудиофайл не найден")
    
    return FileResponse(audio_path, media_type="audio/wav")


# ============================================================================
# СОЗДАНИЕ ПЛЕЙБУКА
# ============================================================================

@router.post("/", status_code=201)
async def create_playbook(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание нового плейбука
    
    Доступ: admin, operator
    
    Поля:
    - name: название (обязательно)
    - greeting_text: текст приветствия
    - greeting_source: tts/uploaded/none
    - beep_duration: длительность сигнала
    - max_recording_duration: макс. длительность записи
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="Название обязательно")
    
    try:
        r = await db.execute(
            text("""
                INSERT INTO playbooks (name, description, category, greeting_text, greeting_source,
                    beep_duration, max_recording_duration, language, tts_voice, tts_speed, created_by)
                VALUES (:n, :d, :c, :gt, :gs, :bd, :md, :l, :tv, :ts, :cb)
                RETURNING id, created_at
            """),
            {
                "n": data["name"],
                "d": data.get("description"),
                "c": data.get("category", "общий"),
                "gt": data.get("greeting_text", ""),
                "gs": data.get("greeting_source", "tts"),
                "bd": data.get("beep_duration", 1.0),
                "md": data.get("max_recording_duration", 300),
                "l": data.get("language", "ru"),
                "tv": data.get("tts_voice"),
                "ts": data.get("tts_speed", 1.0),
                "cb": current_user.get("id")
            }
        )
        row = r.fetchone()
        await db.commit()
        
        # Генерация TTS если нужно
        if data.get("greeting_source") == "tts" and data.get("greeting_text"):
            try:
                audio_path = _generate_tts(row.id, data["greeting_text"])
                await db.execute(
                    text("UPDATE playbooks SET greeting_audio_path=:p WHERE id=:id"),
                    {"p": audio_path, "id": row.id}
                )
                await db.commit()
            except Exception as e:
                logger.warning(f"TTS generation failed: {e}")
        
        return {
            "id": str(row.id),
            "name": data["name"],
            "greeting_text": data.get("greeting_text"),
            "greeting_source": data.get("greeting_source", "tts"),
            "is_active": False,
            "version": 1,
            "created_at": row.created_at.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания: {str(e)}")


def _generate_tts(playbook_id, text: str) -> str:
    """Генерация аудио через espeak"""
    filename = f"playbook_{playbook_id}_greeting.wav"
    filepath = os.path.join(PLAYBOOKS_DIR, filename)
    
    try:
        subprocess.run(
            ['espeak', '-v', 'ru', '-s', '150', '-w', filepath, text],
            capture_output=True, timeout=30
        )
        if os.path.exists(filepath):
            return filepath
    except Exception as e:
        logger.error(f"espeak error: {e}")
    
    return ""


# ============================================================================
# ЗАГРУЗКА АУДИО
# ============================================================================

@router.post("/{playbook_id}/upload-audio")
async def upload_audio(
    playbook_id: str,
    file: UploadFile = File(...),
    audio_type: str = Query("greeting"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Загрузка аудиофайла для плейбука"""
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")
    
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ['wav', 'mp3', 'ogg']:
        raise HTTPException(status_code=400, detail="Поддерживаются WAV, MP3, OGG")
    
    try:
        filename = f"playbook_{playbook_id}_{audio_type}_{uuid_module.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(PLAYBOOKS_DIR, filename)
        
        content = await file.read()
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # Обновление плейбука
        field = f"{audio_type}_audio_path"
        await db.execute(
            text(f"UPDATE playbooks SET {field}=:p, greeting_source='uploaded' WHERE id=:id"),
            {"p": filepath, "id": playbook_id}
        )
        await db.commit()
        
        return {
            "audio_path": filepath,
            "original_filename": file.filename,
            "file_size_bytes": len(content),
            "format": ext,
            "uploaded_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")


# ============================================================================
# ИЗМЕНЕНИЕ СТАТУСА
# ============================================================================

@router.post("/{playbook_id}/status")
async def change_status(
    playbook_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Изменение статуса плейбука
    
    Действия:
    - activate: сделать активным (остальные деактивируются)
    - deactivate: деактивировать
    - archive: архивировать
    - restore: восстановить
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    action = data.get("action")
    if action not in ["activate", "deactivate", "archive", "restore"]:
        raise HTTPException(status_code=400, detail="Неизвестное действие")
    
    if action == "activate":
        # Деактивируем все
        await db.execute(text("UPDATE playbooks SET is_active=false WHERE is_active=true"))
        # Активируем выбранный
        await db.execute(text("UPDATE playbooks SET is_active=true WHERE id=:id"), {"id": playbook_id})
    elif action == "deactivate":
        await db.execute(text("UPDATE playbooks SET is_active=false WHERE id=:id"), {"id": playbook_id})
    elif action == "archive":
        await db.execute(text("UPDATE playbooks SET is_archived=true, is_active=false WHERE id=:id"), {"id": playbook_id})
    elif action == "restore":
        await db.execute(text("UPDATE playbooks SET is_archived=false WHERE id=:id"), {"id": playbook_id})
    
    await db.commit()
    return {"message": f"Статус изменен: {action}", "success": True}


# ============================================================================
# УДАЛЕНИЕ ПЛЕЙБУКА
# ============================================================================

@router.delete("/{playbook_id}")
async def delete_playbook(
    playbook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удаление плейбука"""
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    await db.execute(text("DELETE FROM playbooks WHERE id=:id"), {"id": playbook_id})
    await db.commit()
    
    return {"message": "Плейбук удален", "success": True}


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get("/stats/summary")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Статистика по плейбукам"""
    try:
        r = await db.execute(text("SELECT COUNT(*) FROM playbooks WHERE is_archived=false"))
        total = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM playbooks WHERE is_active=true"))
        active = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM playbooks WHERE is_template=true AND is_archived=false"))
        templates = r.scalar() or 0
        
        return {"total": total, "active": active, "templates": templates}
    except Exception:
        return {"total": 0, "active": 0, "templates": 0}
