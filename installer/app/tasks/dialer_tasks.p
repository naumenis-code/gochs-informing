#!/usr/bin/env python3
"""
Задачи для массового обзвона (Celery tasks)
Интегрируется с существующей архитектурой без изменений
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

# Константы для статусов звонков
CALL_STATUS = {
    'PENDING': 'pending',           # В очереди
    'DIALING': 'dialing',           # Набирается
    'ANSWERED': 'answered',         # Ответил
    'COMPLETED': 'completed',       # Завершён успешно
    'BUSY': 'busy',                 # Занято
    'NOANSWER': 'noanswer',         # Не ответил
    'FAILED': 'failed',             # Ошибка
    'CANCELLED': 'cancelled',       # Отменён
}

# Ключи Redis для хранения состояния
REDIS_PREFIX = "gochs:dialer"
CAMPAIGN_KEY = f"{REDIS_PREFIX}:campaign:{{campaign_id}}"
CAMPAIGN_QUEUE = f"{REDIS_PREFIX}:campaign:{{campaign_id}}:queue"
CAMPAIGN_ACTIVE = f"{REDIS_PREFIX}:campaign:{{campaign_id}}:active"
CAMPAIGN_STATS = f"{REDIS_PREFIX}:campaign:{{campaign_id}}:stats"


# ============================================================================
# ОСНОВНЫЕ ЗАДАЧИ
# ============================================================================

@celery_app.task(name="start_campaign_task", bind=True, max_retries=3)
def start_campaign_task(self, campaign_id: str, contacts: List[Dict], scenario_id: str):
    """
    Запуск кампании обзвона
    
    Args:
        campaign_id: ID кампании
        contacts: Список контактов [{id, phone, name}, ...]
        scenario_id: ID сценария для воспроизведения
    """
    logger.info(f"Запуск кампании {campaign_id} с {len(contacts)} контактами")
    
    try:
        # Инициализация статистики кампании
        redis_client.set(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:total", len(contacts))
        redis_client.set(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:completed", 0)
        redis_client.set(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:failed", 0)
        redis_client.set(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:pending", len(contacts))
        
        # Получаем настройки кампании из Redis или БД
        campaign_config = _get_campaign_config(campaign_id)
        max_channels = campaign_config.get('max_channels', 20)
        max_retries = campaign_config.get('max_retries', 3)
        retry_interval = campaign_config.get('retry_interval', 300)
        
        # Сохраняем конфигурацию в Redis
        redis_client.set(
            f"{CAMPAIGN_KEY.format(campaign_id=campaign_id)}:config",
            json.dumps({
                'max_channels': max_channels,
                'max_retries': max_retries,
                'retry_interval': retry_interval,
                'scenario_id': scenario_id,
                'status': 'running',
                'started_at': datetime.now().isoformat()
            })
        )
        
        # Помещаем контакты в очередь
        for contact in contacts:
            contact_data = {
                'contact_id': contact.get('id'),
                'phone': contact.get('mobile_number') or contact.get('phone'),
                'name': contact.get('full_name', ''),
                'attempt': 1,
                'campaign_id': campaign_id,
                'scenario_id': scenario_id,
            }
            
            redis_client.rpush(
                f"{CAMPAIGN_QUEUE.format(campaign_id=campaign_id)}",
                json.dumps(contact_data)
            )
        
        # Запускаем воркеры для обработки очереди
        active_count = redis_client.get(
            f"{CAMPAIGN_ACTIVE.format(campaign_id=campaign_id)}:count"
        ) or 0
        
        workers_to_start = min(max_channels - int(active_count), len(contacts))
        
        for _ in range(workers_to_start):
            process_campaign_queue.delay(campaign_id)
        
        logger.info(f"Кампания {campaign_id} запущена, {workers_to_start} воркеров")
        
        return {"status": "started", "campaign_id": campaign_id, "contacts": len(contacts)}
        
    except Exception as e:
        logger.error(f"Ошибка запуска кампании {campaign_id}: {e}")
        self.retry(exc=e, countdown=60)


@celery_app.task(name="stop_campaign_task", bind=True)
def stop_campaign_task(self, campaign_id: str, force: bool = False):
    """
    Остановка кампании обзвона
    
    Args:
        campaign_id: ID кампании
        force: True - жёсткая остановка (сброс активных звонков)
    """
    logger.info(f"Остановка кампании {campaign_id} (force={force})")
    
    try:
        # Обновляем статус в Redis
        config = json.loads(
            redis_client.get(f"{CAMPAIGN_KEY.format(campaign_id=campaign_id)}:config") or "{}"
        )
        config['status'] = 'stopped'
        config['stopped_at'] = datetime.now().isoformat()
        redis_client.set(
            f"{CAMPAIGN_KEY.format(campaign_id=campaign_id)}:config",
            json.dumps(config)
        )
        
        # Очищаем очередь
        redis_client.delete(f"{CAMPAIGN_QUEUE.format(campaign_id=campaign_id)}")
        
        if force:
            # Жёсткая остановка - сбрасываем активные звонки
            _hangup_active_calls(campaign_id)
        
        # Обновляем статус в БД
        _update_campaign_status_in_db(campaign_id, 'stopped')
        
        logger.info(f"Кампания {campaign_id} остановлена")
        return {"status": "stopped", "campaign_id": campaign_id}
        
    except Exception as e:
        logger.error(f"Ошибка остановки кампании {campaign_id}: {e}")
        self.retry(exc=e, countdown=30)


@celery_app.task(name="retry_failed_calls_task")
def retry_failed_calls_task(campaign_id: str):
    """
    Повтор неудачных звонков кампании
    """
    logger.info(f"Повтор неудачных звонков для кампании {campaign_id}")
    
    # Получаем список неудачных звонков из БД
    failed_calls = _get_failed_calls(campaign_id)
    
    config = json.loads(
        redis_client.get(f"{CAMPAIGN_KEY.format(campaign_id=campaign_id)}:config") or "{}"
    )
    max_retries = config.get('max_retries', 3)
    
    retried = 0
    for call in failed_calls:
        if call['attempt'] < max_retries:
            # Помещаем обратно в очередь с увеличенной попыткой
            contact_data = {
                'contact_id': call['contact_id'],
                'phone': call['phone'],
                'name': call.get('name', ''),
                'attempt': call['attempt'] + 1,
                'campaign_id': campaign_id,
                'scenario_id': config.get('scenario_id'),
            }
            redis_client.rpush(
                f"{CAMPAIGN_QUEUE.format(campaign_id=campaign_id)}",
                json.dumps(contact_data)
            )
            retried += 1
    
    # Запускаем воркеры если нужно
    if retried > 0:
        active_count = int(redis_client.get(
            f"{CAMPAIGN_ACTIVE.format(campaign_id=campaign_id)}:count"
        ) or 0)
        max_channels = config.get('max_channels', 20)
        workers_to_start = min(max_channels - active_count, retried)
        
        for _ in range(workers_to_start):
            process_campaign_queue.delay(campaign_id)
    
    return {"status": "retry_scheduled", "campaign_id": campaign_id, "retried": retried}


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ЗАДАЧИ
# ============================================================================

@celery_app.task(name="process_campaign_queue", bind=True, soft_time_limit=3600)
def process_campaign_queue(self, campaign_id: str):
    """
    Воркер для обработки очереди кампании
    Запускается для каждого активного канала
    """
    logger.debug(f"Воркер для кампании {campaign_id} запущен")
    
    # Увеличиваем счётчик активных воркеров
    active_key = f"{CAMPAIGN_ACTIVE.format(campaign_id=campaign_id)}:count"
    redis_client.incr(active_key)
    
    try:
        while True:
            # Проверяем статус кампании
            config = json.loads(
                redis_client.get(f"{CAMPAIGN_KEY.format(campaign_id=campaign_id)}:config") or "{}"
            )
            
            if config.get('status') != 'running':
                logger.info(f"Кампания {campaign_id} не запущена, воркер останавливается")
                break
            
            # Берём следующий контакт из очереди
            contact_json = redis_client.lpop(
                f"{CAMPAIGN_QUEUE.format(campaign_id=campaign_id)}"
            )
            
            if not contact_json:
                # Очередь пуста
                logger.debug(f"Очередь кампании {campaign_id} пуста")
                break
            
            contact = json.loads(contact_json)
            
            # Уменьшаем счётчик pending
            redis_client.decr(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:pending")
            
            # Совершаем звонок
            result = _make_call(contact)
            
            # Обрабатываем результат
            _handle_call_result(campaign_id, contact, result)
            
            # Небольшая пауза между звонками
            import time
            time.sleep(0.5)
            
    except SoftTimeLimitExceeded:
        logger.warning(f"Воркер для кампании {campaign_id} превысил время выполнения")
    except Exception as e:
        logger.error(f"Ошибка в воркере кампании {campaign_id}: {e}")
    finally:
        # Уменьшаем счётчик активных воркеров
        redis_client.decr(active_key)
        logger.debug(f"Воркер для кампании {campaign_id} завершён")


@celery_app.task(name="update_campaign_stats")
def update_campaign_stats(campaign_id: str):
    """
    Обновление статистики кампании в БД
    """
    stats = {
        'total': int(redis_client.get(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:total") or 0),
        'completed': int(redis_client.get(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:completed") or 0),
        'failed': int(redis_client.get(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:failed") or 0),
        'pending': int(redis_client.llen(f"{CAMPAIGN_QUEUE.format(campaign_id=campaign_id)}") or 0),
    }
    
    # Сохраняем в БД (асинхронно через отдельный поток)
    _save_campaign_stats_to_db(campaign_id, stats)
    
    return stats


# ============================================================================
# ВНУТРЕННИЕ ФУНКЦИИ (не Celery-задачи)
# ============================================================================

def _get_campaign_config(campaign_id: str) -> Dict[str, Any]:
    """
    Получение конфигурации кампании из БД или значений по умолчанию
    """
    # В реальной реализации - запрос к БД
    # Сейчас возвращаем значения по умолчанию
    return {
        'max_channels': 20,
        'max_retries': 3,
        'retry_interval': 300,
    }


def _make_call(contact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Совершение звонка через Asterisk AMI
    
    Returns:
        {'status': 'answered'|'busy'|'noanswer'|'failed', 'duration': int, 'error': str}
    """
    try:
        # Импортируем здесь чтобы избежать циклических зависимостей
        from app.services.asterisk.asterisk_service import asterisk_service
        
        # Формируем параметры звонка
        destination = contact['phone']
        scenario_id = contact.get('scenario_id')
        call_id = str(uuid4())
        caller_id = f"ГО-ЧС <{settings.ASTERISK_AMI_USER}>"
        
        logger.info(f"Звонок на {destination} (call_id={call_id})")
        
        # Вызов Asterisk
        result = asterisk_service.originate_call(
            destination=destination,
            scenario_id=scenario_id,
            call_id=call_id,
            caller_id=caller_id,
            timeout=settings.NOTIFICATION_DIAL_TIMEOUT
        )
        
        if result:
            return {
                'status': 'answered',
                'call_id': call_id,
                'channel': result
            }
        else:
            return {
                'status': 'failed',
                'error': 'Failed to originate call'
            }
            
    except Exception as e:
        logger.error(f"Ошибка звонка на {contact.get('phone')}: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }


def _handle_call_result(campaign_id: str, contact: Dict, result: Dict):
    """
    Обработка результата звонка
    """
    attempt = contact.get('attempt', 1)
    
    if result['status'] == 'answered':
        # Успешный звонок
        redis_client.incr(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:completed")
        _save_call_attempt(campaign_id, contact, 'completed', result)
        
    elif result['status'] in ['busy', 'noanswer']:
        # Нужен повтор
        config = json.loads(
            redis_client.get(f"{CAMPAIGN_KEY.format(campaign_id=campaign_id)}:config") or "{}"
        )
        max_retries = config.get('max_retries', 3)
        
        if attempt < max_retries:
            # Планируем повтор с задержкой
            retry_interval = config.get('retry_interval', 300)
            contact['attempt'] = attempt + 1
            
            # Используем экспоненциальную задержку
            delay = retry_interval * (2 ** (attempt - 1))
            
            # Планируем отложенную задачу
            retry_call.apply_async(
                args=[campaign_id, contact],
                countdown=delay
            )
            
            logger.info(f"Запланирован повтор для {contact['phone']} через {delay}с")
        else:
            # Достигнут лимит попыток
            redis_client.incr(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:failed")
            _save_call_attempt(campaign_id, contact, 'failed', result)
            
    else:
        # Ошибка
        redis_client.incr(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:failed")
        _save_call_attempt(campaign_id, contact, 'failed', result)
    
    # Обновляем статистику в БД периодически
    completed = int(redis_client.get(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:completed") or 0)
    if completed % 10 == 0:  # Каждые 10 звонков
        update_campaign_stats.delay(campaign_id)


@celery_app.task(name="retry_call")
def retry_call(campaign_id: str, contact: Dict):
    """
    Отложенный повторный звонок
    """
    logger.info(f"Повторный звонок на {contact['phone']} (попытка {contact['attempt']})")
    
    # Помещаем обратно в очередь
    redis_client.rpush(
        f"{CAMPAIGN_QUEUE.format(campaign_id=campaign_id)}",
        json.dumps(contact)
    )
    
    redis_client.incr(f"{CAMPAIGN_STATS.format(campaign_id=campaign_id)}:pending")
    
    # Запускаем воркер если нужно
    config = json.loads(
        redis_client.get(f"{CAMPAIGN_KEY.format(campaign_id=campaign_id)}:config") or "{}"
    )
    active_count = int(redis_client.get(
        f"{CAMPAIGN_ACTIVE.format(campaign_id=campaign_id)}:count"
    ) or 0)
    
    if active_count < config.get('max_channels', 20):
        process_campaign_queue.delay(campaign_id)


def _hangup_active_calls(campaign_id: str):
    """
    Принудительное завершение активных звонков кампании
    """
    try:
        from app.services.asterisk.asterisk_service import asterisk_service
        
        # Получаем список активных каналов
        active_channels = asterisk_service.get_active_channels()
        
        # Ищем каналы, связанные с кампанией
        for channel in active_channels:
            channel_name = channel.get('Channel', '')
            if f"campaign:{campaign_id}" in channel_name:
                asterisk_service.hangup_channel(channel_name)
                logger.info(f"Сброшен канал {channel_name}")
                
    except Exception as e:
        logger.error(f"Ошибка при сбросе звонков: {e}")


def _save_call_attempt(campaign_id: str, contact: Dict, status: str, result: Dict):
    """
    Сохранение попытки звонка в БД
    """
    # TODO: Реализовать сохранение в PostgreSQL
    # Сейчас просто логируем
    logger.info(f"Звонок {contact['phone']}: {status}")


def _update_campaign_status_in_db(campaign_id: str, status: str):
    """
    Обновление статуса кампании в БД
    """
    # TODO: Реализовать обновление в PostgreSQL
    logger.info(f"Статус кампании {campaign_id} обновлён на {status}")


def _get_failed_calls(campaign_id: str) -> List[Dict]:
    """
    Получение списка неудачных звонков из БД
    """
    # TODO: Реализовать запрос к PostgreSQL
    return []


def _save_campaign_stats_to_db(campaign_id: str, stats: Dict):
    """
    Сохранение статистики кампании в БД
    """
    # TODO: Реализовать сохранение в PostgreSQL
    logger.info(f"Статистика кампании {campaign_id}: {stats}")
