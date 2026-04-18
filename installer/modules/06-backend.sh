#!/bin/bash

################################################################################
# Модуль: 06-backend.sh
# Назначение: Установка и настройка FastAPI бэкенда
################################################################################

source "${UTILS_DIR}/common.sh"

MODULE_NAME="06-backend"
MODULE_DESCRIPTION="FastAPI Backend для ГО-ЧС Информирование"

install() {
    log_step "Установка FastAPI бэкенда"
    
    # Проверка зависимостей
    check_dependencies
    
    # Создание структуры бэкенда
    log_info "Создание структуры приложения..."
    create_backend_structure
    
    # Создание основного кода приложения
    create_main_application
    
    # Создание API эндпоинтов
    create_api_endpoints
    
    # Создание сервисов
    create_services
    
    # Создание моделей базы данных
    create_models
    
    # Создание схем Pydantic
    create_schemas
    
    # Создание задач Celery
    create_tasks
    
    # Создание конфигурации
    create_configuration
    
    # Создание systemd служб
    create_systemd_services
    
    # Запуск служб
    start_services
    
    # Создание тестового скрипта
    create_test_script
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "API доступен по адресу: http://localhost:8000"
    log_info "Документация API: http://localhost:8000/docs"
    
    return 0
}

check_dependencies() {
    log_info "Проверка зависимостей..."
    
    # Проверка Python окружения
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        log_error "Python окружение не установлено. Сначала выполните модуль 02-python"
        return 1
    fi
    
    # Проверка PostgreSQL
    if ! systemctl is-active --quiet postgresql; then
        log_error "PostgreSQL не запущен. Сначала выполните модуль 03-db"
        return 1
    fi
    
    # Проверка Redis
    if ! systemctl is-active --quiet redis-server; then
        log_error "Redis не запущен. Сначала выполните модуль 04-redis"
        return 1
    fi
    
    # Проверка Asterisk
    if ! systemctl is-active --quiet asterisk; then
        log_error "Asterisk не запущен. Сначала выполните модуль 05-asterisk"
        return 1
    fi
    
    log_info "Все зависимости удовлетворены"
}

create_backend_structure() {
    log_info "Создание структуры директорий..."
    
    # Основные директории
    mkdir -p "$INSTALL_DIR/app"/{core,api,models,schemas,services,tasks,utils}
    
    # API эндпоинты
    mkdir -p "$INSTALL_DIR/app/api"/{v1,auth}
    
    # Сервисы
    mkdir -p "$INSTALL_DIR/app/services"/{asterisk,dialer,inbound,tts,stt,reports,security}
    
    # Утилиты
    mkdir -p "$INSTALL_DIR/app/utils"
    
    # Установка прав
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/app"
}

create_main_application() {
    log_info "Создание основного приложения..."
    
    # main.py
    cat > "$INSTALL_DIR/app/main.py" << 'EOF'
#!/usr/bin/env python3
"""
ГО-ЧС Информирование - Главный модуль FastAPI приложения
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_router
from app.core.redis_client import redis_client
from app.core.logging_config import setup_logging
from app.services.asterisk.asterisk_service import asterisk_service

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    # Запуск
    logger.info("Запуск ГО-ЧС Информирование...")
    
    # Подключение к Redis
    await redis_client.connect()
    
    # Подключение к Asterisk AMI
    await asterisk_service.connect()
    
    # Создание таблиц БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Завершение
    logger.info("Завершение работы ГО-ЧС Информирование...")
    await asterisk_service.disconnect()
    await redis_client.disconnect()


# Создание приложения
app = FastAPI(
    title="ГО-ЧС Информирование",
    description="Система оповещения и информирования",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1")

# Монтирование статических файлов
app.mount("/recordings", StaticFiles(directory=settings.RECORDINGS_DIR), name="recordings")


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "name": "ГО-ЧС Информирование",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья системы"""
    health_status = {
        "status": "healthy",
        "database": await check_database(),
        "redis": await check_redis(),
        "asterisk": await check_asterisk()
    }
    
    if all(health_status.values()):
        return health_status
    else:
        return JSONResponse(status_code=503, content=health_status)


async def check_database():
    """Проверка подключения к БД"""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False


async def check_redis():
    """Проверка подключения к Redis"""
    try:
        return await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        return False


async def check_asterisk():
    """Проверка подключения к Asterisk"""
    try:
        return await asterisk_service.is_connected()
    except Exception as e:
        logger.error(f"Asterisk check failed: {e}")
        return False


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=4,
        log_level="info"
    )
EOF

    # core/config.py
    cat > "$INSTALL_DIR/app/core/config.py" << EOF
#!/usr/bin/env python3
"""
Конфигурация приложения
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    APP_NAME: str = "ГО-ЧС Информирование"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "$(generate_password)"
    
    # Сервер
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://$DOMAIN_OR_IP"]
    
    # База данных
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "$POSTGRES_DB"
    POSTGRES_USER: str = "$POSTGRES_USER"
    POSTGRES_PASSWORD: str = "$POSTGRES_PASSWORD"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = $REDIS_PORT
    REDIS_PASSWORD: str = "$REDIS_PASSWORD"
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # JWT
    JWT_SECRET_KEY: str = "$(generate_password)"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Asterisk
    ASTERISK_HOST: str = "localhost"
    ASTERISK_AMI_PORT: int = $ASTERISK_AMI_PORT
    ASTERISK_AMI_USER: str = "$ASTERISK_AMI_USER"
    ASTERISK_AMI_PASSWORD: str = "$ASTERISK_AMI_PASSWORD"
    ASTERISK_ARI_URL: str = "http://localhost:8088/ari"
    ASTERISK_ARI_USER: str = "gochs"
    ASTERISK_ARI_PASSWORD: str = "$ASTERISK_AMI_PASSWORD"
    
    # TTS
    TTS_MODEL_PATH: str = "$INSTALL_DIR/models/tts"
    TTS_LANGUAGE: str = "ru"
    TTS_VOICE: str = "ruslan"
    
    # STT (Vosk)
    STT_MODEL_PATH: str = "$INSTALL_DIR/models/vosk/model-ru"
    STT_SAMPLE_RATE: int = 16000
    
    # Пути
    INSTALL_DIR: str = "$INSTALL_DIR"
    RECORDINGS_DIR: str = "$INSTALL_DIR/recordings"
    PLAYBOOKS_DIR: str = "$INSTALL_DIR/playbooks"
    GENERATED_VOICE_DIR: str = "$INSTALL_DIR/generated_voice"
    LOGS_DIR: str = "$INSTALL_DIR/logs"
    
    # Лимиты
    MAX_CONCURRENT_CALLS: int = 20
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_INTERVAL_SECONDS: int = 300
    MAX_RECORDING_DURATION: int = 300
    
    # Безопасность
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    PASSWORD_MIN_LENGTH: int = 8
    
    class Config:
        env_file = "$INSTALL_DIR/.env"
        case_sensitive = True


settings = Settings()
EOF

    # core/database.py
    cat > "$INSTALL_DIR/app/core/database.py" << 'EOF'
#!/usr/bin/env python3
"""
Настройка подключения к базе данных
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Создание движка
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)

# Создание сессии
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для моделей
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Получение сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
EOF

    # core/redis_client.py
    cat > "$INSTALL_DIR/app/core/redis_client.py" << 'EOF'
#!/usr/bin/env python3
"""
Redis клиент
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
from app.core.config import settings


class RedisClient:
    """Клиент для работы с Redis"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Подключение к Redis"""
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        await self.client.ping()
    
    async def disconnect(self):
        """Отключение от Redis"""
        if self.client:
            await self.client.close()
    
    async def ping(self) -> bool:
        """Проверка соединения"""
        try:
            return await self.client.ping()
        except:
            return False
    
    async def set(self, key: str, value: Any, expire: int = None):
        """Сохранение значения"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=expire)
    
    async def get(self, key: str) -> Optional[str]:
        """Получение значения"""
        return await self.client.get(key)
    
    async def delete(self, key: str):
        """Удаление ключа"""
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        return await self.client.exists(key) > 0
    
    async def publish(self, channel: str, message: Any):
        """Публикация сообщения"""
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        await self.client.publish(channel, message)


redis_client = RedisClient()
EOF

    # core/logging_config.py
    cat > "$INSTALL_DIR/app/core/logging_config.py" << 'EOF'
#!/usr/bin/env python3
"""
Настройка логирования
"""

import logging
import logging.config
from app.core.config import settings


def setup_logging():
    """Настройка логирования"""
    
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG" if settings.DEBUG else "INFO",
                "formatter": "detailed",
                "filename": f"{settings.LOGS_DIR}/app.log",
                "maxBytes": 104857600,  # 100 MB
                "backupCount": 10
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": f"{settings.LOGS_DIR}/error.log",
                "maxBytes": 104857600,
                "backupCount": 10
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file", "error_file"],
                "level": "DEBUG" if settings.DEBUG else "INFO",
                "propagate": True
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(LOGGING_CONFIG)
EOF

    log_info "Основное приложение создано"
}

create_api_endpoints() {
    log_info "Создание API эндпоинтов..."
    
    # api/v1/__init__.py
    cat > "$INSTALL_DIR/app/api/v1/__init__.py" << 'EOF'
#!/usr/bin/env python3
"""
API v1 роутер
"""

from fastapi import APIRouter
from app.api.v1 import (
    auth,
    users,
    contacts,
    groups,
    scenarios,
    campaigns,
    inbound,
    playbooks,
    settings,
    monitoring
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(inbound.router, prefix="/inbound", tags=["inbound"])
api_router.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
EOF

    # api/v1/auth.py
    cat > "$INSTALL_DIR/app/api/v1/auth.py" << 'EOF'
#!/usr/bin/env python3
"""
Аутентификация и авторизация
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Optional

from app.core.database import get_db
from app.services.security.auth_service import AuthService
from app.schemas.auth import Token, UserCreate, UserResponse
from app.core.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему"""
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(
        form_data.username,
        form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Обновление токена"""
    auth_service = AuthService(db)
    new_tokens = await auth_service.refresh_access_token(refresh_token)
    
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh токен"
        )
    
    return new_tokens


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Выход из системы"""
    auth_service = AuthService(db)
    await auth_service.revoke_token(token)
    return {"message": "Успешный выход из системы"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Получение информации о текущем пользователе"""
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(token)
    return user
EOF

    # api/v1/campaigns.py
    cat > "$INSTALL_DIR/app/api/v1/campaigns.py" << 'EOF'
#!/usr/bin/env python3
"""
Управление кампаниями обзвона
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.services.dialer.campaign_service import CampaignService
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    CampaignStatus
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=CampaignResponse)
async def create_campaign(
    campaign_data: CampaignCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создание новой кампании обзвона"""
    campaign_service = CampaignService(db)
    campaign = await campaign_service.create_campaign(
        campaign_data,
        current_user.id
    )
    
    # Запуск в фоне если нужно
    if campaign_data.start_immediately:
        background_tasks.add_task(
            campaign_service.start_campaign,
            campaign.id
        )
    
    return campaign


@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка кампаний"""
    campaign_service = CampaignService(db)
    campaigns = await campaign_service.list_campaigns(
        status=status,
        skip=skip,
        limit=limit
    )
    return campaigns


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о кампании"""
    campaign_service = CampaignService(db)
    campaign = await campaign_service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    return campaign


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Запуск кампании"""
    campaign_service = CampaignService(db)
    
    # Проверка прав
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    campaign = await campaign_service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    
    background_tasks.add_task(
        campaign_service.start_campaign,
        campaign_id
    )
    
    return {"message": "Кампания запущена"}


@router.post("/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: UUID,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Остановка кампании"""
    campaign_service = CampaignService(db)
    
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    await campaign_service.stop_campaign(campaign_id, force)
    return {"message": "Кампания остановлена"}


@router.get("/{campaign_id}/status", response_model=CampaignStatus)
async def get_campaign_status(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение статуса кампании"""
    campaign_service = CampaignService(db)
    status = await campaign_service.get_campaign_status(campaign_id)
    return status
EOF

    log_info "API эндпоинты созданы"
}

create_services() {
    log_info "Создание сервисов..."
    
    # services/asterisk/asterisk_service.py
    cat > "$INSTALL_DIR/app/services/asterisk/asterisk_service.py" << 'EOF'
#!/usr/bin/env python3
"""
Сервис для работы с Asterisk
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from Asterisk import Manager
import aiohttp
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class AsteriskService:
    """Сервис для управления Asterisk"""
    
    def __init__(self):
        self.manager: Optional[Manager.Manager] = None
        self.connected = False
        self.event_handlers = {}
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Подключение к Asterisk AMI"""
        try:
            self.manager = Manager.Manager(
                (settings.ASTERISK_HOST, settings.ASTERISK_AMI_PORT),
                settings.ASTERISK_AMI_USER,
                settings.ASTERISK_AMI_PASSWORD
            )
            
            # Проверка подключения
            response = await self._send_action({'Action': 'Ping'})
            if response and response.get('Response') == 'Success':
                self.connected = True
                logger.info("Подключено к Asterisk AMI")
                
                # Запуск мониторинга событий
                self._monitor_task = asyncio.create_task(self._monitor_events())
            else:
                logger.error("Не удалось подключиться к Asterisk AMI")
                
        except Exception as e:
            logger.error(f"Ошибка подключения к Asterisk: {e}")
            self.connected = False
    
    async def disconnect(self):
        """Отключение от Asterisk"""
        if self._monitor_task:
            self._monitor_task.cancel()
        
        if self.manager:
            self.manager.close()
            self.connected = False
            logger.info("Отключено от Asterisk AMI")
    
    async def _send_action(self, action: Dict[str, Any]) -> Optional[Dict]:
        """Отправка действия в AMI"""
        if not self.manager:
            return None
        
        try:
            response = self.manager.send_action(action)
            return response
        except Exception as e:
            logger.error(f"Ошибка отправки AMI действия: {e}")
            return None
    
    async def _monitor_events(self):
        """Мониторинг событий Asterisk"""
        while self.connected:
            try:
                event = self.manager.get_event()
                if event:
                    await self._handle_event(event)
            except Exception as e:
                logger.error(f"Ошибка получения события: {e}")
            await asyncio.sleep(0.1)
    
    async def _handle_event(self, event: Dict[str, Any]):
        """Обработка события Asterisk"""
        event_type = event.get('Event')
        
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                await handler(event)
    
    def register_event_handler(self, event_type: str, handler):
        """Регистрация обработчика событий"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def originate_call(
        self,
        destination: str,
        scenario_id: str,
        call_id: str,
        caller_id: str = "ГО-ЧС <1000>",
        timeout: int = 40
    ) -> Optional[str]:
        """Инициация исходящего звонка"""
        
        action = {
            'Action': 'Originate',
            'Channel': f'PJSIP/{destination}@freepbx-endpoint',
            'CallerID': caller_id,
            'Context': 'gochs-dialer',
            'Exten': 's',
            'Priority': 1,
            'Variable': f'SCENARIO_ID={scenario_id},CALL_ID={call_id}',
            'Timeout': str(timeout * 1000),  # в миллисекундах
            'Async': 'true'
        }
        
        response = await self._send_action(action)
        
        if response and response.get('Response') == 'Success':
            unique_id = response.get('UniqueID')
            logger.info(f"Звонок инициирован: {unique_id} -> {destination}")
            return unique_id
        else:
            logger.error(f"Ошибка инициации звонка: {response}")
            return None
    
    async def hangup_channel(self, channel: str) -> bool:
        """Завершение звонка"""
        action = {
            'Action': 'Hangup',
            'Channel': channel
        }
        
        response = await self._send_action(action)
        return response and response.get('Response') == 'Success'
    
    async def get_channel_status(self, channel: str) -> Optional[Dict]:
        """Получение статуса канала"""
        action = {
            'Action': 'Status',
            'Channel': channel
        }
        
        response = await self._send_action(action)
        return response
    
    async def get_active_channels(self) -> List[Dict]:
        """Получение списка активных каналов"""
        action = {
            'Action': 'CoreShowChannels'
        }
        
        response = await self._send_action(action)
        channels = []
        
        if response:
            for key, value in response.items():
                if key.startswith('Event'):
                    channels.append(value)
        
        return channels
    
    async def is_connected(self) -> bool:
        """Проверка подключения"""
        if not self.connected:
            return False
        
        response = await self._send_action({'Action': 'Ping'})
        return response and response.get('Response') == 'Success'
    
    async def get_sip_peers(self) -> List[Dict]:
        """Получение списка SIP пиров"""
        action = {
            'Action': 'PJSIPShowEndpoints'
        }
        
        response = await self._send_action(action)
        peers = []
        
        if response:
            for key, value in response.items():
                if key.startswith('Event'):
                    peers.append(value)
        
        return peers
    
    async def reload_config(self, module: str = None) -> bool:
        """Перезагрузка конфигурации"""
        action = {
            'Action': 'Command',
            'Command': f'module reload {module}' if module else 'core reload'
        }
        
        response = await self._send_action(action)
        return response and 'Success' in str(response)


# Глобальный экземпляр сервиса
asterisk_service = AsteriskService()
EOF

    # services/dialer/dialer_service.py
    cat > "$INSTALL_DIR/app/services/dialer/dialer_service.py" << 'EOF'
#!/usr/bin/env python3
"""
Сервис массового обзвона
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
import json

from app.services.asterisk.asterisk_service import asterisk_service
from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class DialerService:
    """Сервис для массового обзвона"""
    
    def __init__(self):
        self.active_campaigns: Dict[UUID, asyncio.Task] = {}
        self.call_queues: Dict[UUID, List[str]] = {}
        self.max_concurrent_calls = settings.MAX_CONCURRENT_CALLS
    
    async def start_campaign(self, campaign_id: UUID, contacts: List[Dict], scenario_id: UUID):
        """Запуск кампании обзвона"""
        
        if campaign_id in self.active_campaigns:
            logger.warning(f"Кампания {campaign_id} уже запущена")
            return
        
        # Создание очереди звонков
        call_queue = []
        for contact in contacts:
            phone = contact.get('mobile_number') or contact.get('internal_number')
            if phone:
                call_queue.append(json.dumps({
                    'contact_id': str(contact['id']),
                    'phone': phone,
                    'name': contact.get('full_name', '')
                }))
        
        # Сохранение очереди в Redis
        queue_key = f"campaign:{campaign_id}:queue"
        await redis_client.client.rpush(queue_key, *call_queue)
        
        # Запуск задачи обзвона
        task = asyncio.create_task(
            self._process_campaign(campaign_id, scenario_id)
        )
        self.active_campaigns[campaign_id] = task
        
        logger.info(f"Кампания {campaign_id} запущена, контактов: {len(call_queue)}")
    
    async def _process_campaign(self, campaign_id: UUID, scenario_id: UUID):
        """Обработка кампании"""
        
        queue_key = f"campaign:{campaign_id}:queue"
        active_calls = {}
        semaphore = asyncio.Semaphore(self.max_concurrent_calls)
        
        try:
            while True:
                # Проверка статуса кампании
                status = await self._get_campaign_status(campaign_id)
                if status == 'stopped':
                    logger.info(f"Кампания {campaign_id} остановлена")
                    break
                
                # Получение следующего контакта из очереди
                contact_data = await redis_client.client.lpop(queue_key)
                if not contact_data:
                    # Очередь пуста, проверяем повторные вызовы
                    retry_key = f"campaign:{campaign_id}:retry"
                    contact_data = await redis_client.client.lpop(retry_key)
                    
                    if not contact_data:
                        # Все звонки выполнены
                        logger.info(f"Кампания {campaign_id} завершена")
                        break
                
                contact = json.loads(contact_data)
                
                # Запуск звонка с ограничением параллельных вызовов
                async with semaphore:
                    call_id = str(uuid4())
                    task = asyncio.create_task(
                        self._make_call(campaign_id, scenario_id, contact, call_id)
                    )
                    active_calls[call_id] = task
                
                # Очистка завершенных задач
                done_calls = []
                for cid, task in active_calls.items():
                    if task.done():
                        done_calls.append(cid)
                
                for cid in done_calls:
                    del active_calls[cid]
                
                # Небольшая пауза между инициацией звонков
                await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Ошибка обработки кампании {campaign_id}: {e}")
        finally:
            # Ожидание завершения активных звонков
            if active_calls:
                await asyncio.gather(*active_calls.values(), return_exceptions=True)
            
            # Очистка
            del self.active_campaigns[campaign_id]
            await redis_client.delete(queue_key)
    
    async def _make_call(
        self,
        campaign_id: UUID,
        scenario_id: UUID,
        contact: Dict,
        call_id: str
    ):
        """Выполнение звонка"""
        
        phone = contact['phone']
        contact_id = contact['contact_id']
        
        logger.info(f"Звонок на {phone} (контакт: {contact_id})")
        
        # Сохранение информации о звонке в Redis
        call_key = f"call:{call_id}"
        await redis_client.set(call_key, {
            'campaign_id': str(campaign_id),
            'contact_id': contact_id,
            'phone': phone,
            'status': 'dialing',
            'started_at': datetime.now().isoformat()
        }, expire=3600)
        
        # Инициация звонка через Asterisk
        unique_id = await asterisk_service.originate_call(
            destination=phone,
            scenario_id=str(scenario_id),
            call_id=call_id
        )
        
        if unique_id:
            # Ожидание завершения звонка
            result = await self._wait_for_call_completion(call_id, unique_id)
            
            # Обработка результата
            await self._handle_call_result(campaign_id, contact, result)
        else:
            logger.error(f"Не удалось инициировать звонок на {phone}")
            await self._handle_call_result(campaign_id, contact, {'status': 'failed'})
    
    async def _wait_for_call_completion(self, call_id: str, unique_id: str) -> Dict:
        """Ожидание завершения звонка"""
        
        max_wait = 300  # 5 минут максимум
        check_interval = 1
        
        for _ in range(max_wait):
            await asyncio.sleep(check_interval)
            
            # Проверка статуса канала
            channels = await asterisk_service.get_active_channels()
            channel_active = any(ch.get('UniqueID') == unique_id for ch in channels)
            
            if not channel_active:
                # Звонок завершен
                call_data = await redis_client.get(f"call:{call_id}")
                if call_data:
                    return json.loads(call_data)
                break
        
        return {'status': 'timeout'}
    
    async def _handle_call_result(self, campaign_id: UUID, contact: Dict, result: Dict):
        """Обработка результата звонка"""
        
        status = result.get('status', 'unknown')
        
        # Проверка необходимости повторного звонка
        if status in ['busy', 'no_answer', 'failed']:
            retry_count = contact.get('retry_count', 0)
            
            if retry_count < settings.MAX_RETRY_ATTEMPTS:
                contact['retry_count'] = retry_count + 1
                
                # Добавление в очередь повторных звонков
                retry_key = f"campaign:{campaign_id}:retry"
                await redis_client.client.rpush(
                    retry_key,
                    json.dumps(contact)
                )
                
                logger.info(f"Добавлен повторный звонок для {contact['phone']} (попытка {retry_count + 1})")
        
        # Сохранение результата в БД
        await self._save_call_result(campaign_id, contact, result)
    
    async def _save_call_result(self, campaign_id: UUID, contact: Dict, result: Dict):
        """Сохранение результата звонка в БД"""
        # TODO: Реализовать сохранение в БД
        pass
    
    async def _get_campaign_status(self, campaign_id: UUID) -> str:
        """Получение статуса кампании из Redis"""
        status_key = f"campaign:{campaign_id}:status"
        status = await redis_client.get(status_key)
        return status or 'running'
    
    async def stop_campaign(self, campaign_id: UUID, force: bool = False):
        """Остановка кампании"""
        
        status_key = f"campaign:{campaign_id}:status"
        await redis_client.set(status_key, 'stopped', expire=3600)
        
        if force and campaign_id in self.active_campaigns:
            # Принудительная остановка
            task = self.active_campaigns[campaign_id]
            task.cancel()
            
            # Завершение активных звонков
            channels = await asterisk_service.get_active_channels()
            for channel in channels:
                if f"campaign:{campaign_id}" in str(channel):
                    await asterisk_service.hangup_channel(channel.get('Channel', ''))
        
        logger.info(f"Кампания {campaign_id} остановлена (force={force})")


# Глобальный экземпляр сервиса
dialer_service = DialerService()
EOF

    log_info "Сервисы созданы"
}

create_models() {
    log_info "Создание моделей базы данных..."
    
    # models/user.py
    cat > "$INSTALL_DIR/app/models/user.py" << 'EOF'
#!/usr/bin/env python3
"""
Модель пользователя
"""

from sqlalchemy import Column, String, Boolean, DateTime, UUID
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="operator")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
EOF

    # models/contact.py
    cat > "$INSTALL_DIR/app/models/contact.py" << 'EOF'
#!/usr/bin/env python3
"""
Модель контакта
"""

from sqlalchemy import Column, String, Boolean, DateTime, UUID, Text
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    department = Column(String(100))
    position = Column(String(100))
    internal_number = Column(String(10))
    mobile_number = Column(String(20))
    email = Column(String(255))
    is_active = Column(Boolean, default=True)
    comment = Column(Text)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
EOF

    # models/campaign.py
    cat > "$INSTALL_DIR/app/models/campaign.py" << 'EOF'
#!/usr/bin/env python3
"""
Модель кампании обзвона
"""

from sqlalchemy import Column, String, Integer, DateTime, UUID, ForeignKey
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("notification_scenarios.id"))
    status = Column(String(50), default="pending")
    priority = Column(Integer, default=5)
    max_retries = Column(Integer, default=3)
    retry_interval = Column(Integer, default=300)
    max_channels = Column(Integer, default=20)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
EOF

    log_info "Модели созданы"
}

create_schemas() {
    log_info "Создание Pydantic схем..."
    
    # schemas/auth.py
    cat > "$INSTALL_DIR/app/schemas/auth.py" << 'EOF'
#!/usr/bin/env python3
"""
Схемы для аутентификации
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    role: Optional[str] = "operator"


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str
EOF

    # schemas/campaign.py
    cat > "$INSTALL_DIR/app/schemas/campaign.py" << 'EOF'
#!/usr/bin/env python3
"""
Схемы для кампаний
"""

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CampaignCreate(BaseModel):
    name: str
    scenario_id: UUID
    group_ids: List[UUID]
    priority: Optional[int] = 5
    max_retries: Optional[int] = 3
    retry_interval: Optional[int] = 300
    max_channels: Optional[int] = 20
    start_immediately: Optional[bool] = False


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    priority: Optional[int] = None
    max_retries: Optional[int] = None
    retry_interval: Optional[int] = None
    max_channels: Optional[int] = None


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    scenario_id: UUID
    status: str
    priority: int
    max_retries: int
    retry_interval: int
    max_channels: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CampaignStatus(BaseModel):
    id: UUID
    status: str
    total_contacts: int
    completed_calls: int
    failed_calls: int
    pending_calls: int
    progress_percent: float
EOF

    log_info "Схемы созданы"
}

create_tasks() {
    log_info "Создание Celery задач..."
    
    # tasks/celery_app.py
    cat > "$INSTALL_DIR/app/tasks/celery_app.py" << 'EOF'
#!/usr/bin/env python3
"""
Celery приложение для фоновых задач
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "gochs_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.dialer_tasks",
        "app.tasks.tts_tasks",
        "app.tasks.stt_tasks",
        "app.tasks.cleanup_tasks"
    ]
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_routes={
        "app.tasks.dialer_tasks.*": {"queue": "default"},
        "app.tasks.tts_tasks.*": {"queue": "high_priority"},
        "app.tasks.stt_tasks.*": {"queue": "stt"},
    }
)
EOF

    # tasks/dialer_tasks.py
    cat > "$INSTALL_DIR/app/tasks/dialer_tasks.py" << 'EOF'
#!/usr/bin/env python3
"""
Задачи для обзвона
"""

import asyncio
import logging
from typing import List, Dict, Any
from uuid import UUID

from app.tasks.celery_app import celery_app
from app.services.dialer.dialer_service import dialer_service

logger = logging.getLogger(__name__)


@celery_app.task(name="start_campaign_task")
def start_campaign_task(campaign_id: str, contacts: List[Dict], scenario_id: str):
    """Запуск кампании обзвона"""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            dialer_service.start_campaign(
                UUID(campaign_id),
                contacts,
                UUID(scenario_id)
            )
        )
        return {"status": "started", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Ошибка запуска кампании {campaign_id}: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="stop_campaign_task")
def stop_campaign_task(campaign_id: str, force: bool = False):
    """Остановка кампании"""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            dialer_service.stop_campaign(UUID(campaign_id), force)
        )
        return {"status": "stopped", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Ошибка остановки кампании {campaign_id}: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="retry_failed_calls_task")
def retry_failed_calls_task(campaign_id: str):
    """Повторная обработка неудачных звонков"""
    # TODO: Реализовать
    pass
EOF

    log_info "Celery задачи созданы"
}

create_configuration() {
    log_info "Создание конфигурационных файлов..."
    
    # .env файл
    cat > "$INSTALL_DIR/app/.env" << EOF
# GO-CHS Backend Environment
GOCHS_ENV=production
DEBUG=false
SECRET_KEY=$(generate_password)
JWT_SECRET_KEY=$(generate_password)

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis
REDIS_HOST=localhost
REDIS_PORT=$REDIS_PORT
REDIS_PASSWORD=$REDIS_PASSWORD

# Asterisk
ASTERISK_HOST=localhost
ASTERISK_AMI_PORT=$ASTERISK_AMI_PORT
ASTERISK_AMI_USER=$ASTERISK_AMI_USER
ASTERISK_AMI_PASSWORD=$ASTERISK_AMI_PASSWORD
EOF

    chown "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/app/.env"
    chmod 600 "$INSTALL_DIR/app/.env"
}

create_systemd_services() {
    log_info "Создание systemd служб..."
    
    # gochs-api.service
    cat > /etc/systemd/system/gochs-api.service << EOF
[Unit]
Description=ГО-ЧС API Service
After=network.target postgresql.service redis-server.service asterisk.service
Wants=postgresql.service redis-server.service asterisk.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR/app
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/api.log
StandardError=append:$INSTALL_DIR/logs/api_error.log

[Install]
WantedBy=multi-user.target
EOF

    # gochs-worker.service
    cat > /etc/systemd/system/gochs-worker.service << EOF
[Unit]
Description=ГО-ЧС Celery Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR/app
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4 -Q default,high_priority,stt
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/worker.log
StandardError=append:$INSTALL_DIR/logs/worker_error.log

[Install]
WantedBy=multi-user.target
EOF

    # gochs-scheduler.service
    cat > /etc/systemd/system/gochs-scheduler.service << EOF
[Unit]
Description=ГО-ЧС Celery Beat Scheduler
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR/app
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/celery -A app.tasks.celery_app beat --loglevel=info
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/scheduler.log
StandardError=append:$INSTALL_DIR/logs/scheduler_error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
}

start_services() {
    log_info "Запуск служб бэкенда..."
    
    systemctl enable gochs-api.service
    systemctl enable gochs-worker.service
    systemctl enable gochs-scheduler.service
    
    systemctl start gochs-api.service
    systemctl start gochs-worker.service
    systemctl start gochs-scheduler.service
    
    # Ожидание запуска
    sleep 5
    
    if systemctl is-active --quiet gochs-api.service; then
        log_info "API сервис запущен"
    else
        log_error "Ошибка запуска API сервиса"
    fi
}

create_test_script() {
    log_info "Создание тестового скрипта..."
    
    cat > "$INSTALL_DIR/scripts/test_backend.py" << 'EOF'
#!/usr/bin/env python3
"""
Тестирование бэкенда
"""

import sys
sys.path.append('/opt/gochs-informing')

import asyncio
import aiohttp
import json


async def test_api():
    """Тестирование API эндпоинтов"""
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Проверка здоровья
        async with session.get(f"{base_url}/health") as resp:
            health = await resp.json()
            print(f"Health check: {health}")
        
        # Проверка документации
        async with session.get(f"{base_url}/docs") as resp:
            print(f"Documentation: {resp.status}")
        
        # Тест логина
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        async with session.post(f"{base_url}/api/v1/auth/login", data=login_data) as resp:
            if resp.status == 200:
                token_data = await resp.json()
                print(f"Login successful: {token_data.get('token_type')}")
            else:
                print(f"Login failed: {resp.status}")


if __name__ == "__main__":
    asyncio.run(test_api())
EOF

    chmod +x "$INSTALL_DIR/scripts/test_backend.py"
    chown "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts/test_backend.py"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Остановка служб
    systemctl stop gochs-api.service
    systemctl stop gochs-worker.service
    systemctl stop gochs-scheduler.service
    
    systemctl disable gochs-api.service
    systemctl disable gochs-worker.service
    systemctl disable gochs-scheduler.service
    
    # Удаление файлов служб
    rm -f /etc/systemd/system/gochs-*.service
    systemctl daemon-reload
    
    # Удаление кода
    read -p "Удалить код бэкенда? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR/app"
        log_info "Код бэкенда удален"
    fi
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка служб
    for service in gochs-api gochs-worker gochs-scheduler; do
        if systemctl is-active --quiet $service.service; then
            log_info "Сервис $service: активен"
        else
            log_warn "Сервис $service: не активен"
            status=1
        fi
    done
    
    # Проверка API
    if curl -s http://localhost:8000/health > /dev/null; then
        log_info "API эндпоинт: доступен"
        
        HEALTH=$(curl -s http://localhost:8000/health)
        log_info "  $(echo $HEALTH | python3 -m json.tool 2>/dev/null || echo $HEALTH)"
    else
        log_error "API эндпоинт: недоступен"
        status=1
    fi
    
    return $status
}

# Обработка аргументов
case "${1:-}" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    status)
        check_status
        ;;
    restart)
        systemctl restart gochs-api gochs-worker gochs-scheduler
        ;;
    logs)
        journalctl -u gochs-api -f
        ;;
    test)
        python3 "$INSTALL_DIR/scripts/test_backend.py"
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|restart|logs|test}"
        exit 1
        ;;
esac
