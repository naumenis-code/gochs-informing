#!/bin/bash

################################################################################
# Модуль: 06-backend.sh
# Назначение: Установка и настройка FastAPI бэкенда
# Версия: 1.0.5 (полная исправленная версия)
################################################################################

# Определение путей
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Загрузка общих функций
if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

# Если common.sh не найден - определяем функции локально
if ! type log_info &>/dev/null; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}\n${BLUE}  $*${NC}\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"; }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() { local m="$1"; local f="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"; mkdir -p "$(dirname "$f")"; echo "$m:$(date +%s)" >> "$f"; }
    generate_password() { openssl rand -base64 16 2>/dev/null | tr -d "=+/" | cut -c1-16 || echo "Pass$(date +%s)"; }
    wait_for_service() { local s="$1"; local c=0; while ! systemctl is-active --quiet "$s" 2>/dev/null; do sleep 1; ((c++)); [[ $c -ge ${2:-30} ]] && return 1; done; return 0; }
fi

MODULE_NAME="06-backend"
MODULE_DESCRIPTION="FastAPI Backend для ГО-ЧС Информирование"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
    DOMAIN_OR_IP="${DOMAIN_OR_IP:-localhost}"
    POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(generate_password)}"
    REDIS_PASSWORD="${REDIS_PASSWORD:-$(generate_password)}"
    ASTERISK_AMI_PASSWORD="${ASTERISK_AMI_PASSWORD:-$(generate_password)}"
    ASTERISK_ARI_PASSWORD="${ASTERISK_ARI_PASSWORD:-$(generate_password)}"
    GOCHS_USER="${GOCHS_USER:-gochs}"
    GOCHS_GROUP="${GOCHS_GROUP:-gochs}"
    SECRET_KEY="${SECRET_KEY:-$(generate_password 32)}"
    JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(generate_password 32)}"
fi

install() {
    log_step "Установка FastAPI бэкенда"
    
    check_dependencies
    install_python_packages
    create_backend_structure
    create_main_application
    create_core_modules
    create_api_endpoints
    create_services
    create_models
    create_schemas
    create_tasks
    create_utils
    create_configuration
    create_alembic_migration
    create_systemd_services
    start_services
    create_test_script
    post_install_fixes
    
    mark_module_installed "$MODULE_NAME"
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "API доступен по адресу: http://localhost:8000"
    log_info "Документация API: http://localhost:8000/docs"
    
    return 0
}

check_dependencies() {
    log_info "Проверка зависимостей..."
    
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        log_error "Python окружение не установлено. Сначала выполните модуль 02-python"
        return 1
    fi
    
    if ! systemctl is-active --quiet postgresql; then
        log_error "PostgreSQL не запущен. Сначала выполните модуль 03-db"
        return 1
    fi
    
    if ! systemctl is-active --quiet redis-server; then
        log_error "Redis не запущен. Сначала выполните модуль 04-redis"
        return 1
    fi
    
    log_info "Все зависимости удовлетворены"
}

install_python_packages() {
    log_info "Установка Python пакетов..."
    
    source "$INSTALL_DIR/venv/bin/activate"
    
    pip install --upgrade pip --quiet
    pip install fastapi uvicorn[standard] --quiet
    pip install sqlalchemy asyncpg psycopg2-binary alembic --quiet
    pip install redis celery flower --quiet
    pip install pydantic pydantic-settings python-multipart --quiet
    pip install python-jose[cryptography] passlib[bcrypt] python-dotenv --quiet
    pip install httpx aiohttp requests --quiet
    pip install python-dateutil pytz click pyyaml --quiet
    pip install pyst2 py-asterisk panoramisk --quiet
    
    deactivate
    log_info "Python пакеты установлены"
}

create_backend_structure() {
    log_info "Создание структуры директорий..."
    
    local dirs=(
        "app"
        "app/core"
        "app/api"
        "app/api/v1"
        "app/api/v1/endpoints"
        "app/models"
        "app/schemas"
        "app/services"
        "app/services/asterisk"
        "app/services/dialer"
        "app/services/inbound"
        "app/services/tts"
        "app/services/stt"
        "app/services/reports"
        "app/services/security"
        "app/tasks"
        "app/utils"
        "app/alembic"
        "app/alembic/versions"
    )
    
    for dir in "${dirs[@]}"; do
        ensure_dir "$INSTALL_DIR/$dir"
        touch "$INSTALL_DIR/$dir/__init__.py"
    done
    
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/app"
}

create_main_application() {
    log_info "Создание основного приложения..."
    
    cat > "$INSTALL_DIR/app/main.py" << 'EOF'
#!/usr/bin/env python3
"""
ГО-ЧС Информирование - Главный модуль FastAPI приложения
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1 import api_router
from app.core.logging_config import setup_logging
from fastapi import WebSocket, WebSocketDisconnect

setup_logging()
logger = logging.getLogger(__name__)

# Пароль Redis (будет заменен при установке)
REDIS_PASSWORD = "changeme"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск ГО-ЧС Информирование...")
    
    # Подключение к Redis
    try:
        from app.core.redis_client import redis_client
        await redis_client.connect()
        logger.info("Redis подключен")
    except Exception as e:
        logger.error(f"Ошибка подключения к Redis: {e}")
    
    # Подключение к Asterisk
    try:
        from app.services.asterisk.asterisk_service import asterisk_service
        await asterisk_service.connect()
        logger.info("Asterisk AMI подключен")
    except Exception as e:
        logger.error(f"Ошибка подключения к Asterisk: {e}")
    
    yield
    
    logger.info("Завершение работы ГО-ЧС Информирование...")
    
    try:
        from app.services.asterisk.asterisk_service import asterisk_service
        await asterisk_service.disconnect()
    except:
        pass
    
    try:
        from app.core.redis_client import redis_client
        await redis_client.disconnect()
    except:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    description="Система оповещения и информирования",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# WebSocket поддержка
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/{path:path}")
async def websocket_path(websocket: WebSocket, path: str):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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
import os as _os
if _os.path.exists(settings.RECORDINGS_DIR):
    app.mount("/recordings", StaticFiles(directory=settings.RECORDINGS_DIR), name="recordings")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья системы"""
    from sqlalchemy import text
    health_status = {
        "status": "healthy",
        "database": False,
        "redis": False,
        "asterisk": False
    }
    
    # Проверка PostgreSQL
    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["database"] = True
    except Exception as e:
        logger.error(f"Database error: {e}")

    # Проверка Redis
    try:
        import redis.asyncio as redis
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=2
        )
        await r.ping()
        await r.close()
        health_status["redis"] = True
    except Exception as e:
        logger.error(f"Redis error: {e}")

    # Проверка Asterisk
    try:
        from app.services.asterisk.asterisk_service import asterisk_service
        if await asterisk_service.is_connected():
            health_status["asterisk"] = True
    except Exception as e:
        logger.error(f"Asterisk error: {e}")

    # Общий статус
    if not all([health_status["database"], health_status["redis"]]):
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/health")
async def api_health():
    """Эндпоинт для фронтенда (упрощённый)"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=4,
        log_level="info"
    )
EOF

    # Замена пароля Redis
    sed -i "s/REDIS_PASSWORD = .*/REDIS_PASSWORD = \"$REDIS_PASSWORD\"/" "$INSTALL_DIR/app/main.py"
}

create_core_modules() {
    log_info "Создание core модулей..."
    
    # config.py
    cat > "$INSTALL_DIR/app/core/config.py" << EOF
#!/usr/bin/env python3
"""Конфигурация приложения"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ГО-ЧС Информирование"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "$SECRET_KEY"
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]
    
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "gochs"
    POSTGRES_USER: str = "gochs_user"
    POSTGRES_PASSWORD: str = "$POSTGRES_PASSWORD"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "$REDIS_PASSWORD"
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    JWT_SECRET_KEY: str = "$JWT_SECRET_KEY"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    ASTERISK_HOST: str = "localhost"
    ASTERISK_AMI_PORT: int = 5038
    ASTERISK_AMI_USER: str = "gochs_ami"
    ASTERISK_AMI_PASSWORD: str = "$ASTERISK_AMI_PASSWORD"
    ASTERISK_ARI_URL: str = "http://localhost:8088/ari"
    ASTERISK_ARI_USER: str = "gochs"
    ASTERISK_ARI_PASSWORD: str = "$ASTERISK_ARI_PASSWORD"
    
    INSTALL_DIR: str = "$INSTALL_DIR"
    RECORDINGS_DIR: str = "$INSTALL_DIR/recordings"
    PLAYBOOKS_DIR: str = "$INSTALL_DIR/playbooks"
    GENERATED_VOICE_DIR: str = "$INSTALL_DIR/generated_voice"
    LOGS_DIR: str = "$INSTALL_DIR/logs"
    
    MAX_CONCURRENT_CALLS: int = 20
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_INTERVAL_SECONDS: int = 300
    MAX_RECORDING_DURATION: int = 300
    
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    
    class Config:
        env_file = "$INSTALL_DIR/.env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
EOF

    # database.py
    cat > "$INSTALL_DIR/app/core/database.py" << 'EOF'
#!/usr/bin/env python3
"""Настройка подключения к базе данных"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
EOF

    # redis_client.py
    cat > "$INSTALL_DIR/app/core/redis_client.py" << 'EOF'
#!/usr/bin/env python3
"""Redis клиент"""

import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    async def disconnect(self):
        if self.client:
            await self.client.close()
    
    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except:
            return False
    
    async def set(self, key: str, value: Any, expire: int = None):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=expire)
    
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)
    
    async def delete(self, key: str):
        await self.client.delete(key)
    
    async def publish(self, channel: str, message: Any):
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        await self.client.publish(channel, message)

redis_client = RedisClient()
EOF

    # logging_config.py
    cat > "$INSTALL_DIR/app/core/logging_config.py" << 'EOF'
#!/usr/bin/env python3
"""Настройка логирования"""

import logging
import logging.config
from app.core.config import settings

def setup_logging():
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
                "maxBytes": 104857600,
                "backupCount": 10
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": "DEBUG" if settings.DEBUG else "INFO",
                "propagate": True
            },
            "uvicorn": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
            "sqlalchemy": {"handlers": ["file"], "level": "WARNING", "propagate": False}
        }
    }
    logging.config.dictConfig(LOGGING_CONFIG)
EOF

    # security.py
    cat > "$INSTALL_DIR/app/core/security.py" << 'EOF'
#!/usr/bin/env python3
"""Безопасность"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except:
        return None
EOF

    log_info "Core модули созданы"
}

create_api_endpoints() {
    log_info "Создание API эндпоинтов..."
    
    # api/v1/__init__.py
    cat > "$INSTALL_DIR/app/api/v1/__init__.py" << 'EOF'
#!/usr/bin/env python3
"""API v1 роутер"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, contacts, groups, scenarios, campaigns, inbound, playbooks, settings, monitoring

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

    # api/deps.py
    cat > "$INSTALL_DIR/app/api/deps.py" << 'EOF'
#!/usr/bin/env python3
"""Зависимости для API"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user
EOF

    # Создание endpoints
    local endpoints=(
        "auth" "users" "contacts" "groups" "scenarios" "campaigns" "inbound" "playbooks" "settings" "monitoring"
    )
    
    for ep in "${endpoints[@]}"; do
        cat > "$INSTALL_DIR/app/api/v1/endpoints/${ep}.py" << EOF
#!/usr/bin/env python3
"""${ep} endpoints"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_${ep}():
    return {"message": "List of ${ep}"}

@router.get("/{item_id}")
async def get_${ep}(item_id: str):
    return {"id": item_id}
EOF
    done
    
    # auth.py (полная версия)
    cat > "$INSTALL_DIR/app/api/v1/endpoints/auth.py" << 'EOF'
#!/usr/bin/env python3
"""Аутентификация"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.core.database import get_db
from app.services.security.auth_service import AuthService
from app.schemas.auth import Token, UserResponse, LoginRequest
from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    refresh_token = auth_service.create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    new_tokens = await auth_service.refresh_access_token(refresh_token)
    if not new_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return new_tokens

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    await auth_service.revoke_token(token)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    return current_user
EOF

    # campaigns.py (полная версия)
    cat > "$INSTALL_DIR/app/api/v1/endpoints/campaigns.py" << 'EOF'
#!/usr/bin/env python3
"""Управление кампаниями"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.services.dialer.campaign_service import CampaignService
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate, CampaignStatus
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
    campaign_service = CampaignService(db)
    campaign = await campaign_service.create_campaign(campaign_data, current_user.id)
    
    if campaign_data.start_immediately:
        background_tasks.add_task(campaign_service.start_campaign, campaign.id)
    
    return campaign

@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    campaign_service = CampaignService(db)
    return await campaign_service.list_campaigns(status=status, skip=skip, limit=limit)

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    campaign_service = CampaignService(db)
    campaign = await campaign_service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    campaign_service = CampaignService(db)
    campaign = await campaign_service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    background_tasks.add_task(campaign_service.start_campaign, campaign_id)
    return {"message": "Campaign started"}

@router.post("/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: UUID,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    campaign_service = CampaignService(db)
    await campaign_service.stop_campaign(campaign_id, force)
    return {"message": "Campaign stopped"}

@router.get("/{campaign_id}/status", response_model=CampaignStatus)
async def get_campaign_status(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    campaign_service = CampaignService(db)
    return await campaign_service.get_campaign_status(campaign_id)
EOF

    # Создание __init__.py для endpoints
    touch "$INSTALL_DIR/app/api/v1/endpoints/__init__.py"
    
    log_info "API эндпоинты созданы"
}

create_services() {
    log_info "Создание сервисов..."
    
    # asterisk_service.py
    cat > "$INSTALL_DIR/app/services/asterisk/asterisk_service.py" << 'EOF'
#!/usr/bin/env python3
"""Сервис для работы с Asterisk"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class AsteriskService:
    def __init__(self):
        self.manager = None
        self.connected = False
        self.event_handlers = {}
    
    async def connect(self):
        try:
            from Asterisk import Manager
            self.manager = Manager.Manager(
                (settings.ASTERISK_HOST, settings.ASTERISK_AMI_PORT),
                settings.ASTERISK_AMI_USER,
                settings.ASTERISK_AMI_PASSWORD
            )
            response = self.manager.send_action({'Action': 'Ping'})
            if response and response.get('Response') == 'Success':
                self.connected = True
                logger.info("Connected to Asterisk AMI")
            else:
                logger.error("Failed to connect to Asterisk AMI")
        except Exception as e:
            logger.error(f"Asterisk connection error: {e}")
            self.connected = False
    
    async def disconnect(self):
        if self.manager:
            self.manager.close()
            self.connected = False
            logger.info("Disconnected from Asterisk AMI")
    
    async def is_connected(self) -> bool:
        return self.connected
    
    async def originate_call(
        self,
        destination: str,
        scenario_id: str,
        call_id: str,
        caller_id: str = "ГО-ЧС <1000>",
        timeout: int = 40
    ) -> Optional[str]:
        if not self.connected:
            logger.error("Not connected to Asterisk")
            return None
        
        try:
            action = {
                'Action': 'Originate',
                'Channel': f'PJSIP/{destination}@freepbx-endpoint',
                'CallerID': caller_id,
                'Context': 'gochs-dialer',
                'Exten': 's',
                'Priority': 1,
                'Variable': f'SCENARIO_ID={scenario_id},CALL_ID={call_id}',
                'Timeout': str(timeout * 1000),
                'Async': 'true'
            }
            response = self.manager.send_action(action)
            if response and response.get('Response') == 'Success':
                return response.get('UniqueID')
        except Exception as e:
            logger.error(f"Originate error: {e}")
        return None
    
    async def hangup_channel(self, channel: str) -> bool:
        if not self.connected:
            return False
        try:
            response = self.manager.send_action({'Action': 'Hangup', 'Channel': channel})
            return response and response.get('Response') == 'Success'
        except:
            return False
    
    async def get_active_channels(self) -> List[Dict]:
        if not self.connected:
            return []
        try:
            response = self.manager.send_action({'Action': 'CoreShowChannels'})
            channels = []
            if response:
                for key, value in response.items():
                    if key.startswith('Event'):
                        channels.append(value)
            return channels
        except:
            return []

asterisk_service = AsteriskService()
EOF

    # campaign_service.py
    cat > "$INSTALL_DIR/app/services/dialer/campaign_service.py" << 'EOF'
#!/usr/bin/env python3
"""Сервис управления кампаниями"""

import logging
import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from app.core.redis_client import redis_client
from app.services.asterisk.asterisk_service import asterisk_service

logger = logging.getLogger(__name__)

class CampaignService:
    def __init__(self, db):
        self.db = db
    
    async def create_campaign(self, data: Any, user_id: UUID) -> Dict:
        campaign_id = uuid4()
        return {
            "id": str(campaign_id),
            "name": data.name,
            "scenario_id": data.scenario_id,
            "status": "pending",
            "priority": data.priority,
            "max_retries": data.max_retries,
            "max_channels": data.max_channels,
            "created_by": str(user_id),
            "created_at": datetime.now().isoformat()
        }
    
    async def get_campaign(self, campaign_id: UUID) -> Optional[Dict]:
        return None
    
    async def list_campaigns(self, status: str = None, skip: int = 0, limit: int = 100) -> List[Dict]:
        return []
    
    async def start_campaign(self, campaign_id: UUID):
        logger.info(f"Starting campaign {campaign_id}")
        await redis_client.set(f"campaign:{campaign_id}:status", "running")
    
    async def stop_campaign(self, campaign_id: UUID, force: bool = False):
        logger.info(f"Stopping campaign {campaign_id} (force={force})")
        await redis_client.set(f"campaign:{campaign_id}:status", "stopped")
        
        if force:
            channels = await asterisk_service.get_active_channels()
            for channel in channels:
                if f"campaign:{campaign_id}" in str(channel):
                    await asterisk_service.hangup_channel(channel.get('Channel', ''))
    
    async def get_campaign_status(self, campaign_id: UUID) -> Dict:
        status = await redis_client.get(f"campaign:{campaign_id}:status") or "pending"
        return {
            "id": str(campaign_id),
            "status": status,
            "total_contacts": 0,
            "completed_calls": 0,
            "failed_calls": 0,
            "pending_calls": 0,
            "progress_percent": 0.0
        }
EOF

    # auth_service.py
    cat > "$INSTALL_DIR/app/services/security/auth_service.py" << 'EOF'
#!/usr/bin/env python3
"""Сервис аутентификации"""

import logging
from typing import Optional, Dict, Any
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, create_access_token as create_token, create_refresh_token as create_refresh, decode_token
from app.models.user import User

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where((User.username == username) | (User.email == username))
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def create_access_token(self, data: Dict, expires_delta: timedelta = None) -> str:
        return create_token(data, expires_delta)
    
    def create_refresh_token(self, data: Dict) -> str:
        return create_refresh(data)
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        email = payload.get("sub")
        if not email:
            return None
        
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return None
        
        new_access = self.create_access_token({"sub": user.email})
        new_refresh = self.create_refresh_token({"sub": user.email})
        
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }
    
    async def revoke_token(self, token: str):
        # В production нужно добавить в черный список
        pass
    
    async def get_current_user(self, token: str) -> Optional[User]:
        payload = decode_token(token)
        if not payload:
            return None
        
        email = payload.get("sub")
        if not email:
            return None
        
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
EOF

    log_info "Сервисы созданы"
}

create_models() {
    log_info "Создание моделей базы данных..."
    
    # user.py
    cat > "$INSTALL_DIR/app/models/user.py" << 'EOF'
#!/usr/bin/env python3
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
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

    # contact.py
    cat > "$INSTALL_DIR/app/models/contact.py" << 'EOF'
#!/usr/bin/env python3
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
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

    # campaign.py
    cat > "$INSTALL_DIR/app/models/campaign.py" << 'EOF'
#!/usr/bin/env python3
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    scenario_id = Column(UUID(as_uuid=True))
    status = Column(String(50), default="pending")
    priority = Column(Integer, default=5)
    max_retries = Column(Integer, default=3)
    retry_interval = Column(Integer, default=300)
    max_channels = Column(Integer, default=20)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
EOF

    # models __init__.py
    cat > "$INSTALL_DIR/app/models/__init__.py" << 'EOF'
#!/usr/bin/env python3
from app.models.user import User
from app.models.contact import Contact
from app.models.campaign import Campaign

__all__ = ["User", "Contact", "Campaign"]
EOF

    log_info "Модели созданы"
}

create_schemas() {
    log_info "Создание Pydantic схем..."
    
    # auth.py
    cat > "$INSTALL_DIR/app/schemas/auth.py" << 'EOF'
#!/usr/bin/env python3
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

    # campaign.py
    cat > "$INSTALL_DIR/app/schemas/campaign.py" << 'EOF'
#!/usr/bin/env python3
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

    # schemas __init__.py
    cat > "$INSTALL_DIR/app/schemas/__init__.py" << 'EOF'
#!/usr/bin/env python3
from app.schemas.auth import Token, TokenData, UserCreate, UserResponse, LoginRequest
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, CampaignStatus

__all__ = [
    "Token", "TokenData", "UserCreate", "UserResponse", "LoginRequest",
    "CampaignCreate", "CampaignUpdate", "CampaignResponse", "CampaignStatus"
]
EOF

    log_info "Схемы созданы"
}

create_tasks() {
    log_info "Создание Celery задач..."
    
    # celery_app.py
    cat > "$INSTALL_DIR/app/tasks/celery_app.py" << 'EOF'
#!/usr/bin/env python3
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

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
EOF

    # dialer_tasks.py
    cat > "$INSTALL_DIR/app/tasks/dialer_tasks.py" << 'EOF'
#!/usr/bin/env python3
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="start_campaign_task")
def start_campaign_task(campaign_id: str, contacts: list, scenario_id: str):
    logger.info(f"Starting campaign {campaign_id}")
    return {"status": "started", "campaign_id": campaign_id}

@celery_app.task(name="stop_campaign_task")
def stop_campaign_task(campaign_id: str, force: bool = False):
    logger.info(f"Stopping campaign {campaign_id}")
    return {"status": "stopped", "campaign_id": campaign_id}

@celery_app.task(name="retry_failed_calls_task")
def retry_failed_calls_task(campaign_id: str):
    logger.info(f"Retrying failed calls for campaign {campaign_id}")
    return {"status": "retry_scheduled", "campaign_id": campaign_id}
EOF

    # tts_tasks.py
    cat > "$INSTALL_DIR/app/tasks/tts_tasks.py" << 'EOF'
#!/usr/bin/env python3
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="generate_tts_task")
def generate_tts_task(text: str, voice: str = "ru", output_file: str = None):
    logger.info(f"Generating TTS for text: {text[:50]}...")
    return {"status": "completed", "output_file": output_file}
EOF

    # stt_tasks.py
    cat > "$INSTALL_DIR/app/tasks/stt_tasks.py" << 'EOF'
#!/usr/bin/env python3
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="transcribe_audio_task")
def transcribe_audio_task(audio_file: str, language: str = "ru"):
    logger.info(f"Transcribing audio: {audio_file}")
    return {"status": "completed", "text": ""}
EOF

    # cleanup_tasks.py
    cat > "$INSTALL_DIR/app/tasks/cleanup_tasks.py" << 'EOF'
#!/usr/bin/env python3
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="cleanup_old_recordings")
def cleanup_old_recordings(days: int = 90):
    logger.info(f"Cleaning up recordings older than {days} days")
    return {"status": "completed", "deleted": 0}
EOF

    # tasks __init__.py (ДОБАВЛЕНО)
    cat > "$INSTALL_DIR/app/tasks/__init__.py" << 'EOF'
#!/usr/bin/env python3
"""Celery задачи"""

from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
EOF

    log_info "Celery задачи созданы"
}

create_utils() {
    log_info "Создание утилит..."
    
    cat > "$INSTALL_DIR/app/utils/__init__.py" << 'EOF'
#!/usr/bin/env python3
"""Утилиты"""
EOF

    cat > "$INSTALL_DIR/app/utils/validators.py" << 'EOF'
#!/usr/bin/env python3
"""Валидаторы"""

import re

def validate_phone(phone: str) -> bool:
    clean = re.sub(r'\D', '', phone)
    return len(clean) in (10, 11)

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
EOF

    cat > "$INSTALL_DIR/app/utils/helpers.py" << 'EOF'
#!/usr/bin/env python3
"""Вспомогательные функции"""

import json
from datetime import datetime

def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def to_json(data: dict) -> str:
    return json.dumps(data, default=json_serial)
EOF

    log_info "Утилиты созданы"
}

create_configuration() {
    log_info "Создание конфигурационных файлов..."
    
    # .env файл
    cat > "$INSTALL_DIR/.env" << EOF
# GO-CHS Backend Environment
GOCHS_ENV=production
DEBUG=false

POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
ASTERISK_AMI_PASSWORD=$ASTERISK_AMI_PASSWORD
ASTERISK_ARI_PASSWORD=$ASTERISK_ARI_PASSWORD
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
EOF

    chown "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    
    log_info "Конфигурационные файлы созданы"
}

create_alembic_migration() {
    log_info "Создание миграции Alembic..."
    
    # alembic.ini
    cat > "$INSTALL_DIR/app/alembic.ini" << EOF
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql+asyncpg://gochs_user:$POSTGRES_PASSWORD@localhost:5432/gochs

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 88

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

    # env.py
    cat > "$INSTALL_DIR/app/alembic/env.py" << 'EOF'
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.database import Base
from app.models import User, Contact, Campaign

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF

    # versions/__init__.py
    touch "$INSTALL_DIR/app/alembic/versions/__init__.py"
    
    log_info "Миграция Alembic создана"
}

create_systemd_services() {
    log_info "Создание systemd служб..."

    # gochs-api.service (основной API)
    cat > /etc/systemd/system/gochs-api.service << EOF
[Unit]
Description=ГО-ЧС API Service
After=network.target postgresql.service redis-server.service asterisk.service
Wants=postgresql.service redis-server.service asterisk.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
TimeoutStartSec=60
StandardOutput=append:$INSTALL_DIR/logs/api.log
StandardError=append:$INSTALL_DIR/logs/api_error.log

[Install]
WantedBy=multi-user.target
EOF

    # gochs-worker.service (Celery worker) - ИСПРАВЛЕНО: создаётся корректно
    cat > /etc/systemd/system/gochs-worker.service << EOF
[Unit]
Description=ГО-ЧС Celery Worker
After=network.target redis-server.service postgresql.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
Restart=always
RestartSec=10

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
WorkingDirectory=$INSTALL_DIR
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

    # Создаем директорию для PID файла
    mkdir -p /run/gochs
    chown "$GOCHS_USER:$GOCHS_GROUP" /run/gochs 2>/dev/null || true

    systemctl daemon-reload
    log_info "Systemd службы созданы"
}

start_services() {
    log_info "Запуск служб бэкенда..."
    
    # Перезагружаем systemd
    systemctl daemon-reload
    
    # Включаем и запускаем API
    systemctl enable gochs-api.service
    systemctl restart gochs-api.service
    
    # Ждём запуска API
    sleep 5
    if systemctl is-active --quiet gochs-api.service; then
        log_info "✓ API сервис запущен"
    else
        log_error "✗ API сервис не запустился"
        journalctl -u gochs-api --no-pager -n 30
    fi
    
    # Включаем и запускаем Worker
    systemctl enable gochs-worker.service
    systemctl restart gochs-worker.service
    sleep 3
    
    if systemctl is-active --quiet gochs-worker.service; then
        log_info "✓ Worker сервис запущен"
    else
        log_warn "✗ Worker сервис не запустился"
        log_info "Проверьте логи: journalctl -u gochs-worker"
    fi
    
    # Включаем и запускаем Scheduler
    systemctl enable gochs-scheduler.service
    systemctl restart gochs-scheduler.service
    sleep 2
    
    if systemctl is-active --quiet gochs-scheduler.service; then
        log_info "✓ Scheduler сервис запущен"
    else
        log_warn "✗ Scheduler сервис не запустился"
    fi
}

create_test_script() {
    log_info "Создание тестового скрипта..."
    
    cat > "$INSTALL_DIR/scripts/test_backend.py" << 'EOF'
#!/usr/bin/env python3
"""Тестирование бэкенда"""

import sys
sys.path.append('/opt/gochs-informing')

import asyncio
import aiohttp
import json

async def test_api():
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        print("=== Тестирование API ===")
        
        # Health check
        async with session.get(f"{base_url}/health") as resp:
            health = await resp.json()
            print(f"Health: {json.dumps(health, indent=2)}")
        
        # Root
        async with session.get(f"{base_url}/") as resp:
            root = await resp.json()
            print(f"Root: {root}")
        
        # Docs
        async with session.get(f"{base_url}/docs") as resp:
            print(f"Documentation: {resp.status}")

if __name__ == "__main__":
    asyncio.run(test_api())
EOF

    chmod +x "$INSTALL_DIR/scripts/test_backend.py"
    chown "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/scripts/test_backend.py"
    
    log_info "Тестовый скрипт создан"
}

post_install_fixes() {
    log_info "Применение финальных настроек..."
    
    # Создать директорию для логов
    mkdir -p "$INSTALL_DIR/logs"
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/logs"
    chmod 755 "$INSTALL_DIR/logs"
    
    # Получить пароль Redis и обновить в main.py
    local redis_pass=$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')
    if [[ -n "$redis_pass" ]] && [[ -f "$INSTALL_DIR/app/main.py" ]]; then
        sed -i "s/REDIS_PASSWORD = .*/REDIS_PASSWORD = \"$redis_pass\"/" "$INSTALL_DIR/app/main.py"
        log_info "Пароль Redis добавлен в main.py"
    fi
    
    # Создание пользователя admin если нужно
    if id -u "$GOCHS_USER" &>/dev/null; then
        chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/app"
        chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/logs"
    fi
    
    # Перезапуск сервисов
    systemctl restart gochs-api gochs-worker gochs-scheduler 2>/dev/null || true
    
    # ============================================================
    # Создание пользователя admin в базе данных (через pgcrypto)
    # ============================================================
    log_info "Создание администратора в базе данных..."
    sleep 3
    
    # Загружаем пароль из .env если не задан
    if [[ -z "$POSTGRES_PASSWORD" ]] && [[ -f "$INSTALL_DIR/.env" ]]; then
        source "$INSTALL_DIR/.env"
    fi
    
    # Включаем pgcrypto
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U gochs_user -d gochs -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null
    
    # Создаём admin через pgcrypto (обходит проблему с bcrypt)
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U gochs_user -d gochs << 'EOF' 2>/dev/null
INSERT INTO users (email, username, full_name, hashed_password, role, is_superuser, is_active) 
VALUES ('admin@gochs.local', 'admin', 'Администратор', crypt('Admin123!', gen_salt('bf')), 'admin', TRUE, TRUE) 
ON CONFLICT (username) DO UPDATE SET hashed_password = crypt('Admin123!', gen_salt('bf'));
EOF

    if [[ $? -eq 0 ]]; then
        log_info "✓ Пользователь admin создан (пароль: Admin123!)"
    else
        log_warn "⚠ Не удалось создать пользователя admin"
    fi
    
    deactivate 2>/dev/null || true

    log_info "Финальные настройки применены"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    systemctl stop gochs-api gochs-worker gochs-scheduler gochs-websocket 2>/dev/null
    systemctl disable gochs-api gochs-worker gochs-scheduler gochs-websocket 2>/dev/null
    
    rm -f /etc/systemd/system/gochs-*.service
    systemctl daemon-reload
    
    read -p "Удалить код бэкенда? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR/app"
        rm -f "$INSTALL_DIR/.env"
        log_info "Код бэкенда удален"
    fi
    
    log_info "Модуль ${MODULE_NAME} удален"
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    for service in gochs-api gochs-worker gochs-scheduler; do
        if systemctl is-active --quiet $service; then
            log_info "✓ $service: активен"
        else
            log_warn "✗ $service: не активен"
            status=1
        fi
    done
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_info "✓ API: доступен"
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null | head -10
    else
        log_error "✗ API: недоступен"
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
    migrate)
        cd "$INSTALL_DIR/app"
        source "$INSTALL_DIR/venv/bin/activate"
        alembic upgrade head
        ;;
    clean)
        find "$INSTALL_DIR/app" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
        find "$INSTALL_DIR/app" -type f -name "*.pyc" -delete 2>/dev/null
        log_info "Очистка завершена"
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|restart|logs|test|migrate|clean}"
        exit 1
        ;;
esac
