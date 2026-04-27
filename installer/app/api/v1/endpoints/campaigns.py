#!/usr/bin/env python3
"""
API эндпоинты для управления кампаниями обзвона
Соответствует ТЗ, разделы 13, 14, 15, 16

Функционал:
- Создание кампании обзвона
- Запуск/остановка/пауза
- Выбор сценария и групп контактов
- Настройка повторов
- Статусы звонков
- Статистика кампании
"""
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ПОЛУЧЕНИЕ СПИСКА КАМПАНИЙ
# ============================================================================

@router.get("/")
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение списка кампаний обзвона
    
    Доступ: admin, operator, viewer
    """
    conditions = ["1=1"]
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if status:
        conditions.append("c.status = :status")
        params["status"] = status
    if search:
        conditions.append("c.name ILIKE :search")
        params["search"] = f"%{search}%"
    
    where = " AND ".join(conditions)
    
    try:
        r = await db.execute(text(f"SELECT COUNT(*) FROM campaigns c WHERE {where}"), params)
        total = r.scalar() or 0
        
        r = await db.execute(
            text(f"""
                SELECT c.*, ns.name as scenario_name 
                FROM campaigns c 
                LEFT JOIN notification_scenarios ns ON c.scenario_id = ns.id
                WHERE {where}
                ORDER BY c.created_at DESC 
                LIMIT :limit OFFSET :offset
            """),
            params
        )
        
        items = []
        for row in r.fetchall():
            items.append({
                "id": str(row.id),
                "name": row.name,
                "scenario_id": str(row.scenario_id) if row.scenario_id else None,
                "scenario_name": row.scenario_name,
                "status": row.status or "pending",
                "priority": row.priority or 5,
                "max_retries": row.max_retries or 3,
                "retry_interval": row.retry_interval or 300,
                "max_channels": row.max_channels or 20,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "created_by": str(row.created_by) if row.created_by else None,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================================
# ПОЛУЧЕНИЕ АКТИВНЫХ КАМПАНИЙ
# ============================================================================

@router.get("/active")
async def get_active_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получение активных кампаний (для Dashboard)
    
    Доступ: все авторизованные
    """
    try:
        r = await db.execute(
            text("""
                SELECT c.*, ns.name as scenario_name 
                FROM campaigns c 
                LEFT JOIN notification_scenarios ns ON c.scenario_id = ns.id
                WHERE c.status IN ('running', 'pending')
                ORDER BY c.priority ASC, c.created_at DESC
                LIMIT 10
            """)
        )
        
        campaigns = []
        for row in r.fetchall():
            # Считаем прогресс
            progress = 0
            total_contacts = 0
            completed_calls = 0
            failed_calls = 0
            
            try:
                cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id"), {"id": row.id})
                total_contacts = cr.scalar() or 0
                cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id AND status='answered'"), {"id": row.id})
                completed_calls = cr.scalar() or 0
                cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id AND status='failed'"), {"id": row.id})
                failed_calls = cr.scalar() or 0
                progress = int((completed_calls / total_contacts) * 100) if total_contacts > 0 else 0
            except Exception:
                pass
            
            campaigns.append({
                "id": str(row.id),
                "name": row.name,
                "scenario_name": row.scenario_name,
                "status": row.status,
                "priority": row.priority or 5,
                "total_contacts": total_contacts,
                "completed_calls": completed_calls,
                "failed_calls": failed_calls,
                "in_progress_calls": total_contacts - completed_calls - failed_calls,
                "progress_percent": progress
            })
        
        return {"campaigns": campaigns, "total": len(campaigns)}
        
    except Exception as e:
        logger.error(f"Error active campaigns: {e}")
        return {"campaigns": [], "total": 0}


# ============================================================================
# ПОЛУЧЕНИЕ КАМПАНИИ ПО ID
# ============================================================================

@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение кампании по ID"""
    r = await db.execute(
        text("""
            SELECT c.*, ns.name as scenario_name 
            FROM campaigns c 
            LEFT JOIN notification_scenarios ns ON c.scenario_id = ns.id
            WHERE c.id = :id
        """),
        {"id": campaign_id}
    )
    row = r.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    
    # Получаем группы кампании
    groups = []
    try:
        gr = await db.execute(
            text("""
                SELECT cg.id, cg.name, cg.color 
                FROM contact_groups cg 
                JOIN campaign_groups cg2 ON cg.id = cg2.group_id 
                WHERE cg2.campaign_id = :id
            """),
            {"id": campaign_id}
        )
        for g in gr.fetchall():
            groups.append({"id": str(g.id), "name": g.name, "color": g.color})
    except Exception:
        pass
    
    # Статистика звонков
    total_contacts = 0
    completed_calls = 0
    failed_calls = 0
    try:
        cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id"), {"id": campaign_id})
        total_contacts = cr.scalar() or 0
        cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id AND status='answered'"), {"id": campaign_id})
        completed_calls = cr.scalar() or 0
        cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id AND status='failed'"), {"id": campaign_id})
        failed_calls = cr.scalar() or 0
    except Exception:
        pass
    
    progress = int((completed_calls / total_contacts) * 100) if total_contacts > 0 else 0
    
    return {
        "id": str(row.id),
        "name": row.name,
        "scenario_id": str(row.scenario_id) if row.scenario_id else None,
        "scenario_name": row.scenario_name,
        "status": row.status or "pending",
        "priority": row.priority or 5,
        "max_retries": row.max_retries or 3,
        "retry_interval": row.retry_interval or 300,
        "max_channels": row.max_channels or 20,
        "groups": groups,
        "total_contacts": total_contacts,
        "completed_calls": completed_calls,
        "failed_calls": failed_calls,
        "pending_calls": total_contacts - completed_calls - failed_calls,
        "progress_percent": progress,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "created_by": str(row.created_by) if row.created_by else None,
        "created_at": row.created_at.isoformat() if row.created_at else None
    }


# ============================================================================
# СОЗДАНИЕ КАМПАНИИ
# ============================================================================

@router.post("/", status_code=201)
async def create_campaign(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Создание новой кампании обзвона
    
    Доступ: admin, operator
    
    Поля:
    - name: название
    - scenario_id: ID сценария
    - group_ids: список ID групп
    - priority: приоритет (1-10, по умолчанию 5)
    - max_retries: максимум повторов (по умолчанию 3)
    - retry_interval: интервал между повторами в секундах (по умолчанию 300)
    - max_channels: максимум одновременных звонков (по умолчанию 20)
    - start_immediately: запустить сразу (по умолчанию false)
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="Название кампании обязательно")
    
    try:
        r = await db.execute(
            text("""
                INSERT INTO campaigns (name, scenario_id, status, priority, max_retries, retry_interval, max_channels, created_by)
                VALUES (:n, :s, 'pending', :p, :mr, :ri, :mc, :cb)
                RETURNING id, created_at
            """),
            {
                "n": data["name"],
                "s": data.get("scenario_id"),
                "p": data.get("priority", 5),
                "mr": data.get("max_retries", 3),
                "ri": data.get("retry_interval", 300),
                "mc": data.get("max_channels", 20),
                "cb": current_user.get("id")
            }
        )
        row = r.fetchone()
        campaign_id = row.id
        
        # Добавляем группы
        group_ids = data.get("group_ids", [])
        for gid in group_ids:
            try:
                await db.execute(
                    text("INSERT INTO campaign_groups (campaign_id, group_id) VALUES (:cid, :gid) ON CONFLICT DO NOTHING"),
                    {"cid": campaign_id, "gid": gid}
                )
            except Exception:
                pass
        
        # Добавляем контакты из групп в попытки вызовов
        for gid in group_ids:
            try:
                cr = await db.execute(
                    text("""
                        SELECT c.id, c.mobile_number, c.internal_number
                        FROM contacts c
                        JOIN contact_group_members cgm ON c.id = cgm.contact_id
                        WHERE cgm.group_id = :gid AND cgm.is_active = true 
                          AND c.is_active = true AND c.is_archived = false
                    """),
                    {"gid": gid}
                )
                for contact in cr.fetchall():
                    phone = contact.mobile_number or contact.internal_number
                    if phone:
                        await db.execute(
                            text("""
                                INSERT INTO call_attempts (campaign_id, contact_id, phone_number, status)
                                VALUES (:cid, :ctid, :ph, 'queued')
                                ON CONFLICT DO NOTHING
                            """),
                            {"cid": campaign_id, "ctid": contact.id, "ph": phone}
                        )
            except Exception as e:
                logger.warning(f"Error adding contacts from group {gid}: {e}")
        
        await db.commit()
        
        logger.info(f"Создана кампания: {data['name']}")
        
        result = {
            "id": str(campaign_id),
            "name": data["name"],
            "scenario_id": data.get("scenario_id"),
            "status": "pending",
            "priority": data.get("priority", 5),
            "max_retries": data.get("max_retries", 3),
            "retry_interval": data.get("retry_interval", 300),
            "max_channels": data.get("max_channels", 20),
            "groups": [{"id": gid} for gid in group_ids],
            "start_immediately": data.get("start_immediately", False),
            "created_at": row.created_at.isoformat()
        }
        
        # Автозапуск если нужно
        if data.get("start_immediately"):
            background_tasks.add_task(
                _start_campaign_async, str(campaign_id), db
            )
            result["status"] = "running"
        
        return result
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания: {str(e)}")


async def _start_campaign_async(campaign_id: str, db: AsyncSession):
    """Фоновый запуск кампании"""
    try:
        await db.execute(
            text("UPDATE campaigns SET status='running', started_at=NOW() WHERE id=:id"),
            {"id": campaign_id}
        )
        await db.commit()
        logger.info(f"Campaign {campaign_id} started")
    except Exception as e:
        logger.error(f"Error starting campaign {campaign_id}: {e}")


# ============================================================================
# ЗАПУСК КАМПАНИИ
# ============================================================================

@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Запуск кампании обзвона
    
    Доступ: admin, operator
    Меняет статус на 'running'
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    r = await db.execute(text("SELECT status FROM campaigns WHERE id=:id"), {"id": campaign_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    if row.status == "running":
        raise HTTPException(status_code=400, detail="Кампания уже запущена")
    
    background_tasks.add_task(_start_campaign_async, campaign_id, db)
    
    return {"message": "Кампания запущена", "status": "running"}


# ============================================================================
# ОСТАНОВКА КАМПАНИИ
# ============================================================================

@router.post("/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: str,
    force: bool = Query(False, description="Экстренная остановка"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Остановка кампании
    
    Доступ: admin, operator
    
    - force=False: мягкая остановка (новые звонки не запускаются, активные завершаются)
    - force=True: экстренная остановка (все звонки прерываются)
    """
    if current_user["role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    r = await db.execute(text("SELECT status FROM campaigns WHERE id=:id"), {"id": campaign_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    
    if force:
        await db.execute(
            text("UPDATE campaigns SET status='stopped', completed_at=NOW() WHERE id=:id"),
            {"id": campaign_id}
        )
        await db.execute(
            text("UPDATE call_attempts SET status='cancelled' WHERE campaign_id=:id AND status IN ('queued','dialing')"),
            {"id": campaign_id}
        )
    else:
        await db.execute(
            text("UPDATE campaigns SET status='stopped', completed_at=NOW() WHERE id=:id"),
            {"id": campaign_id}
        )
    
    await db.commit()
    
    action = "экстренно остановлена" if force else "остановлена"
    return {"message": f"Кампания {action}", "status": "stopped"}


# ============================================================================
# СТАТУС КАМПАНИИ
# ============================================================================

@router.get("/{campaign_id}/status")
async def get_campaign_status(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получение детального статуса кампании"""
    r = await db.execute(text("SELECT * FROM campaigns WHERE id=:id"), {"id": campaign_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    
    # Статистика
    total = 0
    answered = 0
    failed = 0
    try:
        cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id"), {"id": campaign_id})
        total = cr.scalar() or 0
        cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id AND status='answered'"), {"id": campaign_id})
        answered = cr.scalar() or 0
        cr = await db.execute(text("SELECT COUNT(*) FROM call_attempts WHERE campaign_id=:id AND status='failed'"), {"id": campaign_id})
        failed = cr.scalar() or 0
    except Exception:
        pass
    
    return {
        "id": str(row.id),
        "status": row.status or "pending",
        "total_contacts": total,
        "completed_calls": answered,
        "failed_calls": failed,
        "pending_calls": total - answered - failed,
        "progress_percent": int((answered / total) * 100) if total > 0 else 0
    }
