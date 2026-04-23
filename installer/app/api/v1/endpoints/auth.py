#!/usr/bin/env python3
"""Аутентификация - ПОЛНАЯ ВЕРСИЯ С ЛОГИРОВАНИЕМ ВХОДА/ВЫХОДА"""

import logging
import hashlib
import secrets
import json
import base64
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Query
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, EmailStr, Field, validator

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PASSWORD_MIN_LENGTH = 8
PASSWORD_HISTORY_SIZE = 5
SESSION_TIMEOUT_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REMEMBER_ME_EXPIRE_MINUTES = 1440  # 24 часа


# ============================================================================
# PYDANTIC МОДЕЛИ
# ============================================================================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[Dict[str, Any]] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    last_login: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Пароли не совпадают')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v, values):
        if 'old_password' in values and v == values['old_password']:
            raise ValueError('Новый пароль должен отличаться от старого')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать цифру')
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    message: str
    success: bool


# ============================================================================
# ФУНКЦИИ БЕЗОПАСНОСТИ
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    if not plain_password or not hashed_password:
        return False
    
    # BCrypt
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except ImportError:
            pass
        except Exception:
            return False
    
    # SHA256
    if len(hashed_password) == 64:
        return hashlib.sha256(plain_password.encode('utf-8')).hexdigest() == hashed_password
    
    # MD5 (для обратной совместимости)
    if len(hashed_password) == 32:
        return hashlib.md5(plain_password.encode('utf-8')).hexdigest() == hashed_password
    
    # Plain text
    return plain_password == hashed_password


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    except ImportError:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание access токена"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        **data,
        "exp": expire.timestamp(),
        "iat": datetime.utcnow().timestamp(),
        "jti": str(uuid.uuid4()),
        "type": "access"
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    token = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip("=")
    secret = getattr(settings, 'SECRET_KEY', 'gochs_secret_key_2024')
    signature = hashlib.sha256(f"{token}.{secret}".encode()).hexdigest()[:32]
    
    return f"{token}.{signature}"


def create_refresh_token(data: dict) -> str:
    """Создание refresh токена"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        **data,
        "exp": expire.timestamp(),
        "iat": datetime.utcnow().timestamp(),
        "jti": str(uuid.uuid4()),
        "type": "refresh"
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    token = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip("=")
    secret = getattr(settings, 'SECRET_KEY', 'gochs_secret_key_2024')
    signature = hashlib.sha256(f"{token}.refresh.{secret}".encode()).hexdigest()[:32]
    
    return f"{token}.{signature}"


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Проверка токена"""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        
        padded = parts[0] + "=="
        payload_str = base64.urlsafe_b64decode(padded.encode()).decode()
        payload = json.loads(payload_str)
        
        if payload.get("type") != token_type:
            return None
        
        if "exp" in payload:
            exp = datetime.fromtimestamp(payload["exp"])
            if datetime.utcnow() > exp:
                return None
        
        return payload
    except Exception:
        return None


def get_client_info(request: Request) -> Dict[str, Any]:
    """Получение информации о клиенте"""
    ip = None
    if request.client:
        ip = request.client.host
    elif request.headers.get("x-forwarded-for"):
        ip = request.headers.get("x-forwarded-for").split(",")[0].strip()
    
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent", "")
    }


# ============================================================================
# ФУНКЦИИ РАБОТЫ С БД
# ============================================================================

async def ensure_users_table(db: AsyncSession) -> bool:
    """Проверка и создание таблицы пользователей"""
    try:
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'operator',
                    is_active BOOLEAN DEFAULT true,
                    is_superuser BOOLEAN DEFAULT false,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
            
            await db.commit()
            logger.info("Users table created")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring users table: {e}")
        return False


async def ensure_sessions_table(db: AsyncSession) -> bool:
    """Проверка и создание таблицы сессий"""
    try:
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_sessions'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    session_token VARCHAR(500) NOT NULL,
                    refresh_token VARCHAR(500),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """))
            
            await db.commit()
            logger.info("Sessions table created")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring sessions table: {e}")
        return False


async def ensure_audit_table(db: AsyncSession) -> bool:
    """Проверка и создание таблицы аудита"""
    try:
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'audit_logs'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID,
                    user_name VARCHAR(255),
                    user_role VARCHAR(50),
                    action VARCHAR(100) NOT NULL,
                    entity_type VARCHAR(50),
                    entity_id UUID,
                    entity_name VARCHAR(255),
                    details JSONB,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    status VARCHAR(20) DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await db.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring audit table: {e}")
        return False


async def create_default_admin(db: AsyncSession) -> bool:
    """Создание администратора по умолчанию"""
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM users WHERE username = 'admin'"))
        count = result.scalar()
        
        if count == 0:
            hashed = hash_password("Admin123!")
            await db.execute(text("""
                INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                VALUES (gen_random_uuid(), 'admin@gochs.local', 'admin', 'Администратор', :hashed, 'admin', true, true, NOW(), NOW())
            """), {"hashed": hashed})
            await db.commit()
            logger.info("Default admin user created")
        
        return True
    except Exception as e:
        logger.error(f"Error creating default admin: {e}")
        return False


async def log_audit_event(
    db: AsyncSession,
    user_id: Optional[str] = None,
    user_name: Optional[str] = "system",
    user_role: Optional[str] = None,
    action: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success"
) -> bool:
    """Прямое логирование в аудит"""
    try:
        await db.execute(text("""
            INSERT INTO audit_logs 
            (user_id, user_name, user_role, action, entity_type, entity_id, ip_address, user_agent, status, created_at)
            VALUES (:user_id, :user_name, :user_role, :action, :entity_type, :entity_id, :ip_address, :user_agent, :status, NOW())
        """), {
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "status": status
        })
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
        return False


async def create_session(
    db: AsyncSession,
    user_id: str,
    session_token: str,
    refresh_token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    expires_in: int = SESSION_TIMEOUT_MINUTES
) -> bool:
    """Создание сессии"""
    try:
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in)
        
        await db.execute(text("""
            INSERT INTO user_sessions (user_id, session_token, refresh_token, ip_address, user_agent, expires_at)
            VALUES (:user_id, :session_token, :refresh_token, :ip_address, :user_agent, :expires_at)
        """), {
            "user_id": user_id,
            "session_token": session_token,
            "refresh_token": refresh_token,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "expires_at": expires_at
        })
        
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return False


async def revoke_session(db: AsyncSession, session_token: str) -> bool:
    """Отзыв сессии"""
    try:
        await db.execute(
            text("UPDATE user_sessions SET is_active = false WHERE session_token = :token"),
            {"token": session_token}
        )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error revoking session: {e}")
        return False


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """Получение текущего пользователя из токена"""
    if not token:
        return None
    
    payload = verify_token(token, "access")
    if not payload:
        return None
    
    result = await db.execute(
        text("SELECT id, email, username, full_name, role, is_active, is_superuser FROM users WHERE id = :id"),
        {"id": payload["user_id"]}
    )
    user = result.fetchone()
    
    if not user or not user.is_active:
        return None
    
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser
    }


async def get_current_active_user(
    current_user: Optional[Dict] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Получение текущего активного пользователя"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not current_user.get("is_active"):
        raise HTTPException(status_code=403, detail="User is inactive")
    return current_user


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему с логированием"""
    client_info = get_client_info(request)
    
    try:
        # Проверяем и создаем таблицы
        await ensure_users_table(db)
        await ensure_sessions_table(db)
        await ensure_audit_table(db)
        await create_default_admin(db)
        
        # Ищем пользователя
        result = await db.execute(
            text("""
                SELECT id, email, username, full_name, hashed_password, role, is_active, is_superuser,
                       login_attempts, locked_until
                FROM users 
                WHERE username = :username OR email = :email
            """),
            {"username": form_data.username, "email": form_data.username}
        )
        user = result.fetchone()
        
        if not user:
            await log_audit_event(
                db, action="login_failed", status="error",
                error_message="User not found", **client_info
            )
            raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
        
        # Проверяем блокировку
        if user.locked_until and datetime.utcnow() < user.locked_until:
            minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
            raise HTTPException(
                status_code=403,
                detail=f"Аккаунт заблокирован. Попробуйте через {minutes_left} мин."
            )
        
        # Проверяем пароль
        if not verify_password(form_data.password, user.hashed_password):
            new_attempts = (user.login_attempts or 0) + 1
            locked_until = None
            
            if new_attempts >= MAX_LOGIN_ATTEMPTS:
                locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            
            await db.execute(
                text("UPDATE users SET login_attempts = :attempts, locked_until = :locked WHERE id = :id"),
                {"attempts": new_attempts, "locked": locked_until, "id": user.id}
            )
            await db.commit()
            
            await log_audit_event(
                db, user_id=str(user.id), user_name=user.username, user_role=user.role,
                action="login_failed", status="error", error_message="Invalid password",
                **client_info
            )
            
            raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
        
        # Проверяем активность
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Пользователь заблокирован")
        
        # Сбрасываем счетчик попыток и обновляем last_login
        await db.execute(
            text("UPDATE users SET login_attempts = 0, locked_until = NULL, last_login = NOW() WHERE id = :id"),
            {"id": user.id}
        )
        
        # Определяем время жизни токена
        remember_me = form_data.scopes and "remember" in form_data.scopes
        expires_minutes = REMEMBER_ME_EXPIRE_MINUTES if remember_me else ACCESS_TOKEN_EXPIRE_MINUTES
        
        # Создаем токены
        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id), "username": user.username, "role": user.role},
            expires_delta=timedelta(minutes=expires_minutes)
        )
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        # Создаем сессию
        await create_session(
            db, str(user.id), access_token, refresh_token,
            client_info["ip_address"], client_info["user_agent"],
            expires_minutes
        )
        
        # Логируем успешный вход
        await log_audit_event(
            db, user_id=str(user.id), user_name=user.username, user_role=user.role,
            action="login", entity_type="user", entity_id=str(user.id),
            status="success", **client_info
        )
        
        await db.commit()
        
        logger.info(f"User logged in: {user.username}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_minutes * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_superuser": user.is_superuser
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Выход из системы с логированием"""
    client_info = get_client_info(request)
    
    if token:
        payload = verify_token(token, "access")
        if payload:
            await revoke_session(db, token)
            await log_audit_event(
                db, user_id=payload.get("user_id"), user_name=payload.get("username"),
                user_role=payload.get("role"), action="logout", status="success",
                **client_info
            )
    
    return {"message": "Successfully logged out", "success": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Информация о текущем пользователе"""
    result = await db.execute(
        text("""
            SELECT id, email, username, full_name, role, is_active, is_superuser, last_login
            FROM users WHERE id = :id
        """),
        {"id": current_user["id"]}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "last_login": user.last_login.isoformat() if user.last_login else None
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Обновление токена"""
    payload = verify_token(refresh_request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    result = await db.execute(
        text("SELECT user_id, is_active FROM user_sessions WHERE refresh_token = :token"),
        {"token": refresh_request.refresh_token}
    )
    session = result.fetchone()
    
    if not session or not session.is_active:
        raise HTTPException(status_code=401, detail="Session not found or inactive")
    
    result = await db.execute(
        text("SELECT email, username, role FROM users WHERE id = :id AND is_active = true"),
        {"id": session.user_id}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(session.user_id), "username": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    await db.execute(
        text("UPDATE user_sessions SET session_token = :new_token, last_activity = NOW() WHERE refresh_token = :refresh_token"),
        {"new_token": access_token, "refresh_token": refresh_request.refresh_token}
    )
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_request.refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/change-password")
async def change_password(
    request: Request,
    password_request: PasswordChangeRequest,
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Смена пароля"""
    client_info = get_client_info(request)
    
    result = await db.execute(
        text("SELECT hashed_password FROM users WHERE id = :id"),
        {"id": current_user["id"]}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(password_request.old_password, user.hashed_password):
        await log_audit_event(
            db, user_id=current_user["id"], user_name=current_user["username"],
            action="password_change_failed", status="error",
            error_message="Invalid old password", **client_info
        )
        raise HTTPException(status_code=400, detail="Неверный старый пароль")
    
    new_hashed = hash_password(password_request.new_password)
    
    await db.execute(
        text("UPDATE users SET hashed_password = :hashed WHERE id = :id"),
        {"hashed": new_hashed, "id": current_user["id"]}
    )
    await db.commit()
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        action="password_change", status="success", **client_info
    )
    
    return {"message": "Пароль успешно изменен", "success": True}


# ============================================================================
# СЛУЖЕБНЫЕ ЭНДПОИНТЫ
# ============================================================================

@router.post("/create-admin", include_in_schema=False)
async def create_admin_endpoint(
    username: str = "admin",
    password: str = "Admin123!",
    db: AsyncSession = Depends(get_db)
):
    """Создание/обновление администратора"""
    await ensure_users_table(db)
    
    hashed = hash_password(password)
    
    result = await db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username}
    )
    existing = result.fetchone()
    
    if existing:
        await db.execute(
            text("UPDATE users SET hashed_password = :hashed, is_active = true WHERE username = :username"),
            {"hashed": hashed, "username": username}
        )
    else:
        await db.execute(text("""
            INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
            VALUES (gen_random_uuid(), :email, :username, :full_name, :hashed, 'admin', true, true, NOW(), NOW())
        """), {
            "email": f"{username}@gochs.local",
            "username": username,
            "full_name": "Администратор",
            "hashed": hashed
        })
    
    await db.commit()
    
    return {"success": True, "message": f"User {username} created/updated"}


@router.get("/check-user/{username}", include_in_schema=False)
async def check_user(username: str, db: AsyncSession = Depends(get_db)):
    """Проверка существования пользователя"""
    await ensure_users_table(db)
    
    result = await db.execute(
        text("SELECT id, username, email, role, is_active FROM users WHERE username = :username OR email = :email"),
        {"username": username, "email": username}
    )
    user = result.fetchone()
    
    if user:
        return {
            "exists": True,
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
    return {"exists": False}
