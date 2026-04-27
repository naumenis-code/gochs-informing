#!/usr/bin/env python3
"""
API эндпоинты для мониторинга системы
Соответствует ТЗ, разделы 17, 23, 31

Функционал:
- Состояние каналов АТС
- Статистика звонков
- Статус сервисов
- Системная информация
- Health check
"""
import logging
import os
import psutil
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Проверка здоровья системы
    
    Доступ: без авторизации
    """
    health = {
        "status": "healthy",
        "api": "online",
        "database": False,
        "redis": False,
        "asterisk": False,
        "pbx_registration": False
    }
    
    # Проверка БД
    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health["database"] = True
    except Exception:
        health["status"] = "degraded"
    
    # Проверка Redis
    try:
        from app.core.redis_client import redis_client
        if redis_client.client:
            await redis_client.client.ping()
            health["redis"] = True
    except Exception:
        pass
    
    # Проверка Asterisk
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", 5038))
        sock.close()
        if result == 0:
            health["asterisk"] = True
    except Exception:
        pass
    
    if not all([health["database"], health["redis"], health["asterisk"]]):
        health["status"] = "degraded"
    
    return health


# ============================================================================
# СТАТИСТИКА КАНАЛОВ (Панель управления)
# ============================================================================

@router.get("/channels/stats")
async def get_channel_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Статистика каналов АТС для Dashboard
    
    Показатели согласно ТЗ:
    - Всего каналов
    - Используется сейчас
    - Свободно
    - Использует ГО-ЧС
    - Входящих сейчас
    - Исходящих сейчас
    """
    try:
        # Пытаемся получить реальные данные из Asterisk AMI
        import socket
        
        total_channels = 50
        used_channels = 0
        gochs_channels = 0
        inbound_calls = 0
        outbound_calls = 0
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("127.0.0.1", 5038))
            
            # Login
            sock.send(b"Action: Login\r\nUsername: gochs_ami\r\nSecret: \r\n\r\n")
            sock.recv(1024)
            
            # Core Show Channels
            sock.send(b"Action: CoreShowChannels\r\n\r\n")
            data = b""
            for _ in range(10):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            
            # Подсчет каналов
            channels_text = data.decode('utf-8', errors='ignore')
            used_channels = channels_text.count("Event: CoreShowChannel")
            gochs_channels = channels_text.count("gochs")
            inbound_calls = channels_text.count("inbound")
            outbound_calls = channels_text.count("outbound")
            
            sock.send(b"Action: Logoff\r\n\r\n")
            sock.close()
        except Exception:
            pass
        
        # Считаем из БД
        try:
            r = await db.execute(text("SELECT COUNT(*) FROM campaigns WHERE status='running'"))
            active_campaigns = r.scalar() or 0
            
            r = await db.execute(
                text("SELECT COUNT(*) FROM inbound_calls WHERE started_at >= NOW() - INTERVAL '1 hour'")
            )
            recent_inbound = r.scalar() or 0
        except Exception:
            active_campaigns = 0
            recent_inbound = 0
        
        free_channels = total_channels - used_channels
        
        return {
            "total_channels": total_channels,
            "used_channels": used_channels,
            "free_channels": free_channels,
            "gochs_channels": gochs_channels,
            "inbound_calls": inbound_calls or recent_inbound,
            "outbound_calls": outbound_calls,
            "active_campaigns": 0
        }
        
    except Exception as e:
        logger.error(f"Channel stats error: {e}")
        return {
            "total_channels": 50,
            "used_channels": 0,
            "free_channels": 50,
            "gochs_channels": 0,
            "inbound_calls": 0,
            "outbound_calls": 0,
            "active_campaigns": 0
        }


# ============================================================================
# ПОСЛЕДНИЕ ВХОДЯЩИЕ (ДЛЯ DASHBOARD)
# ============================================================================

@router.get("/inbound/recent")
async def get_recent_inbound(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Последние входящие звонки для Dashboard
    
    Доступ: все авторизованные
    """
    try:
        r = await db.execute(
            text("""
                SELECT id, caller_number, caller_name, duration, status, started_at, 
                       CASE WHEN recording_path IS NOT NULL THEN true ELSE false END as has_recording,
                       CASE WHEN transcription IS NOT NULL THEN true ELSE false END as has_transcription
                FROM inbound_calls 
                ORDER BY started_at DESC 
                LIMIT :limit
            """),
            {"limit": limit}
        )
        
        calls = []
        for row in r.fetchall():
            calls.append({
                "id": str(row.id),
                "time": row.started_at.isoformat() if row.started_at else None,
                "caller_number": row.caller_number,
                "caller_name": row.caller_name,
                "duration": row.duration,
                "status": row.status or "unknown",
                "has_recording": row.has_recording,
                "has_transcription": row.has_transcription
            })
        
        return {"calls": calls, "total": len(calls)}
        
    except Exception as e:
        logger.error(f"Error recent inbound: {e}")
        return {"calls": [], "total": 0}


# ============================================================================
# СИСТЕМНАЯ ИНФОРМАЦИЯ
# ============================================================================

@router.get("/system")
async def get_system_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Системная информация (CPU, RAM, диск)
    
    Доступ: admin
    """
    if current_user["role"] != "admin":
        return {"error": "Только для администраторов"}
    
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/opt')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count()
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 1),
                "used_gb": round(memory.used / (1024**3), 1),
                "free_gb": round(memory.free / (1024**3), 1),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "percent": disk.percent
            },
            "uptime": None,
            "load_average": [round(x, 2) for x in psutil.getloadavg()] if hasattr(psutil, 'getloadavg') else []
        }
    except Exception as e:
        logger.error(f"System info error: {e}")
        return {"cpu": {}, "memory": {}, "disk": {}}


# ============================================================================
# СТАТУС СЕРВИСОВ
# ============================================================================

@router.get("/services")
async def get_services_status(
    current_user: dict = Depends(get_current_user)
):
    """Статус всех сервисов системы"""
    import subprocess
    
    services = ["postgresql", "redis-server", "asterisk", "gochs-api", "gochs-worker", "nginx"]
    result = {}
    
    for service in services:
        try:
            output = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5
            )
            result[service] = {
                "active": output.stdout.strip() == "active",
                "status": output.stdout.strip()
            }
        except Exception:
            result[service] = {"active": False, "status": "unknown"}
    
    return {"services": result}


# ============================================================================
# СТАТИСТИКА ЗВОНКОВ
# ============================================================================

@router.get("/calls")
async def get_call_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Общая статистика звонков"""
    try:
        # Исходящие
        r = await db.execute(text("SELECT COUNT(*) FROM call_attempts"))
        total_outbound = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE status='answered'"))
        answered_outbound = r.scalar() or 0
        
        r = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE status='failed'"))
        failed_outbound = r.scalar() or 0
        
        # Входящие
        r = await db.execute(text("SELECT COUNT(*) FROM inbound_calls"))
        total_inbound = r.scalar() or 0
        
        # Сегодня
        r = await db.execute(
            text("SELECT COUNT(*) FROM call_attempts WHERE created_at >= CURRENT_DATE")
        )
        today_outbound = r.scalar() or 0
        
        r = await db.execute(
            text("SELECT COUNT(*) FROM inbound_calls WHERE started_at >= CURRENT_DATE")
        )
        today_inbound = r.scalar() or 0
        
        return {
            "outbound": {
                "total": total_outbound,
                "answered": answered_outbound,
                "failed": failed_outbound,
                "today": today_outbound
            },
            "inbound": {
                "total": total_inbound,
                "today": today_inbound
            }
        }
        
    except Exception as e:
        logger.error(f"Call stats error: {e}")
        return {"outbound": {}, "inbound": {}}
