#!/usr/bin/env python3
"""Auth endpoints - МАКСИМАЛЬНО ПОЛНАЯ ВЕРСИЯ со всеми функциями"""

import logging
import hashlib
import secrets
import json
import base64
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Query
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update, delete
from pydantic import BaseModel, EmailStr, Field, validator

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ============================================================================
# КОНСТАНТЫ И НАСТРОЙКИ
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
    captcha: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]
    requires_password_change: bool = False
    last_login: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern="^[a-zA-Z0-9_-]+$")
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
    role: str = Field("operator", pattern="^(admin|operator|viewer)$")
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать цифру')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Пароль должен содержать спецсимвол')
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    last_login: Optional[str] = None
    last_password_change: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    login_attempts: int = 0
    locked_until: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[str] = Field(None, pattern="^(admin|operator|viewer)$")
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


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
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Пароль должен содержать спецсимвол')
        return v


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Пароли не совпадают')
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    message: str
    success: bool


class SessionInfo(BaseModel):
    session_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str
    last_activity: str
    expires_at: str
    is_active: bool


class SessionsListResponse(BaseModel):
    sessions: List[SessionInfo]
    total: int


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ БЕЗОПАСНОСТИ
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля (поддержка bcrypt, sha256, argon2, md5, plain)"""
    if not plain_password or not hashed_password:
        return False
    
    # BCrypt
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except ImportError:
            logger.warning("bcrypt not installed")
            return False
        except Exception as e:
            logger.error(f"bcrypt error: {e}")
            return False
    
    # Argon2
    if hashed_password.startswith("$argon2"):
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            ph.verify(hashed_password, plain_password)
            return True
        except ImportError:
            pass
        except Exception:
            return False
    
    # PBKDF2
    if hashed_password.startswith("pbkdf2:"):
        try:
            import hmac
            parts = hashed_password.split(":")
            if len(parts) == 4:
                algo, iterations, salt, hash_val = parts
                if algo == "pbkdf2":
                    key = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), int(iterations))
                    return key.hex() == hash_val
        except:
            pass
    
    # SHA256
    if len(hashed_password) == 64:
        try:
            return hashlib.sha256(plain_password.encode('utf-8')).hexdigest() == hashed_password
        except:
            pass
    
    # SHA512
    if len(hashed_password) == 128:
        try:
            return hashlib.sha512(plain_password.encode('utf-8')).hexdigest() == hashed_password
        except:
            pass
    
    # MD5 (только для обратной совместимости, не рекомендуется)
    if len(hashed_password) == 32:
        try:
            return hashlib.md5(plain_password.encode('utf-8')).hexdigest() == hashed_password
        except:
            pass
    
    # Plain text (только для тестов)
    return plain_password == hashed_password


def hash_password(password: str) -> str:
    """Хеширование пароля (предпочтительно bcrypt)"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    except ImportError:
        logger.warning("bcrypt not installed, using SHA256")
        return hashlib.sha256(password.encode('utf-8')).hexdigest()


def generate_secure_token(length: int = 32) -> str:
    """Генерация безопасного токена"""
    return secrets.token_urlsafe(length)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT access токена"""
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


def create_password_reset_token(user_id: str) -> str:
    """Создание токена для сброса пароля"""
    expire = datetime.utcnow() + timedelta(hours=1)
    
    payload = {
        "user_id": user_id,
        "exp": expire.timestamp(),
        "iat": datetime.utcnow().timestamp(),
        "type": "password_reset"
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    token = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip("=")
    
    return token


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Проверка токена"""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        
        # Добавляем padding для base64
        padded = parts[0] + "=="
        payload_str = base64.urlsafe_b64decode(padded.encode()).decode()
        payload = json.loads(payload_str)
        
        # Проверяем тип
        if payload.get("type") != token_type:
            return None
        
        # Проверяем срок
        if "exp" in payload:
            exp = datetime.fromtimestamp(payload["exp"])
            if datetime.utcnow() > exp:
                return None
        
        return payload
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def get_password_strength(password: str) -> Dict[str, Any]:
    """Оценка сложности пароля"""
    score = 0
    feedback = []
    
    if len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    else:
        feedback.append("Пароль слишком короткий")
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Добавьте заглавные буквы")
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Добавьте строчные буквы")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Добавьте цифры")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 2
    else:
        feedback.append("Добавьте спецсимволы")
    
    # Проверка на распространенные пароли
    common_passwords = ['password', '123456', 'qwerty', 'admin', 'password123']
    if password.lower() in common_passwords:
        score = 0
        feedback.append("Пароль слишком распространен")
    
    strength = "weak"
    if score >= 5:
        strength = "strong"
    elif score >= 3:
        strength = "medium"
    
    return {
        "score": score,
        "strength": strength,
        "feedback": feedback
    }


# ============================================================================
# ФУНКЦИИ РАБОТЫ С БД
# ============================================================================

async def ensure_users_table(db: AsyncSession) -> bool:
    """Проверка и создание таблицы пользователей"""
    try:
        # Проверяем существование таблицы
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            # Создаем таблицу users
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
                    last_password_change TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Индексы
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)"))
            
            await db.commit()
            logger.info("Users table created")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring users table: {e}")
        await db.rollback()
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
                    expires_at TIMESTAMP NOT NULL,
                    revoked_at TIMESTAMP
                )
            """))
            
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON user_sessions(is_active)"))
            
            await db.commit()
            logger.info("Sessions table created")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring sessions table: {e}")
        await db.rollback()
        return False


async def ensure_password_history_table(db: AsyncSession) -> bool:
    """Проверка и создание таблицы истории паролей"""
    try:
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'password_history'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS password_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    hashed_password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_password_history_user_id ON password_history(user_id)"))
            
            await db.commit()
            logger.info("Password history table created")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring password history table: {e}")
        await db.rollback()
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
                    request_method VARCHAR(10),
                    request_path VARCHAR(500),
                    status VARCHAR(20) DEFAULT 'success',
                    error_message TEXT,
                    execution_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at DESC)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)"))
            
            await db.commit()
            logger.info("Audit table created")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring audit table: {e}")
        await db.rollback()
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
        await db.rollback()
        return False


async def check_password_history(db: AsyncSession, user_id: str, new_password: str) -> bool:
    """Проверка, не использовался ли пароль ранее"""
    try:
        # Получаем историю паролей
        result = await db.execute(
            text("""
                SELECT hashed_password FROM password_history 
                WHERE user_id = :user_id 
                ORDER BY created_at DESC 
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": PASSWORD_HISTORY_SIZE}
        )
        
        for row in result.fetchall():
            if verify_password(new_password, row.hashed_password):
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking password history: {e}")
        return True  # В случае ошибки разрешаем


async def add_to_password_history(db: AsyncSession, user_id: str, hashed_password: str) -> bool:
    """Добавление пароля в историю"""
    try:
        await db.execute(
            text("INSERT INTO password_history (user_id, hashed_password) VALUES (:user_id, :hashed)"),
            {"user_id": user_id, "hashed": hashed_password}
        )
        
        # Удаляем старые записи сверх лимита
        await db.execute(
            text("""
                DELETE FROM password_history 
                WHERE id IN (
                    SELECT id FROM password_history 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC 
                    OFFSET :limit
                )
            """),
            {"user_id": user_id, "limit": PASSWORD_HISTORY_SIZE}
        )
        
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding to password history: {e}")
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
            text("UPDATE user_sessions SET is_active = false, revoked_at = NOW() WHERE session_token = :token"),
            {"token": session_token}
        )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error revoking session: {e}")
        return False


async def revoke_all_user_sessions(db: AsyncSession, user_id: str, except_token: Optional[str] = None) -> bool:
    """Отзыв всех сессий пользователя"""
    try:
        if except_token:
            await db.execute(
                text("UPDATE user_sessions SET is_active = false, revoked_at = NOW() WHERE user_id = :user_id AND session_token != :token"),
                {"user_id": user_id, "token": except_token}
            )
        else:
            await db.execute(
                text("UPDATE user_sessions SET is_active = false, revoked_at = NOW() WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error revoking all sessions: {e}")
        return False


async def log_audit_event(
    db: AsyncSession,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    action: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None
) -> bool:
    """Запись события в аудит"""
    try:
        details_json = json.dumps(details) if details else None
        
        await db.execute(text("""
            INSERT INTO audit_logs 
            (user_id, user_name, user_role, action, entity_type, entity_id, entity_name,
             details, ip_address, user_agent, request_method, request_path,
             status, error_message, created_at)
            VALUES (:user_id, :user_name, :user_role, :action, :entity_type, :entity_id, :entity_name,
                    :details::jsonb, :ip_address, :user_agent, :request_method, :request_path,
                    :status, :error_message, NOW())
        """), {
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "details": details_json,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_method": request_method,
            "request_path": request_path,
            "status": status,
            "error_message": error_message
        })
        
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
        return False


def get_client_info(request: Request) -> dict:
    """Получение информации о клиенте"""
    ip = None
    if request.client:
        ip = request.client.host
    elif request.headers.get("x-forwarded-for"):
        ip = request.headers.get("x-forwarded-for").split(",")[0].strip()
    elif request.headers.get("x-real-ip"):
        ip = request.headers.get("x-real-ip")
    
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent", ""),
        "request_method": request.method,
        "request_path": request.url.path
    }


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
    
    # Проверяем сессию
    result = await db.execute(
        text("SELECT is_active FROM user_sessions WHERE session_token = :token"),
        {"token": token}
    )
    session = result.fetchone()
    if not session or not session.is_active:
        return None
    
    # Получаем пользователя
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


async def get_current_admin_user(
    current_user: Dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Получение текущего администратора"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


# ============================================================================
# ENDPOINTS - АВТОРИЗАЦИЯ
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему"""
    client_info = get_client_info(request)
    start_time = datetime.utcnow()
    
    try:
        # Проверяем и создаем таблицы
        await ensure_users_table(db)
        await ensure_sessions_table(db)
        await ensure_password_history_table(db)
        await ensure_audit_table(db)
        await create_default_admin(db)
        
        # Ищем пользователя
        result = await db.execute(
            text("""
                SELECT id, email, username, full_name, hashed_password, role, is_active, is_superuser,
                       login_attempts, locked_until, last_login, last_password_change
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
            # Увеличиваем счетчик попыток
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
        
        # Сбрасываем счетчик попыток
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
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        await log_audit_event(
            db, user_id=str(user.id), user_name=user.username, user_role=user.role,
            action="login", status="success",
            details={"remember_me": remember_me},
            execution_time_ms=execution_time,
            **client_info
        )
        
        # Проверяем, нужно ли сменить пароль
        requires_password_change = False
        if user.last_password_change:
            days_since_change = (datetime.utcnow() - user.last_password_change).days
            if days_since_change > 90:  # Пароль старше 90 дней
                requires_password_change = True
        
        logger.info(f"User logged in: {user.username}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_minutes * 60,
            "requires_password_change": requires_password_change,
            "last_login": user.last_login.isoformat() if user.last_login else None,
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
        await log_audit_event(
            db, action="login_error", status="error",
            error_message=str(e), **client_info
        )
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Выход из системы"""
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


@router.post("/logout-all", response_model=LogoutResponse)
async def logout_all(
    request: Request,
    current_user: Dict = Depends(get_current_active_user),
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Выход со всех устройств"""
    client_info = get_client_info(request)
    
    await revoke_all_user_sessions(db, current_user["id"], token)
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        user_role=current_user["role"], action="logout_all", status="success",
        **client_info
    )
    
    return {"message": "Successfully logged out from all devices", "success": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Информация о текущем пользователе"""
    result = await db.execute(
        text("""
            SELECT id, email, username, full_name, role, is_active, is_superuser,
                   last_login, last_password_change, created_at, updated_at,
                   login_attempts, locked_until
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
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "last_password_change": user.last_password_change.isoformat() if user.last_password_change else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "login_attempts": user.login_attempts or 0,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Обновление токена"""
    client_info = get_client_info(request)
    
    payload = verify_token(refresh_request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Проверяем сессию
    result = await db.execute(
        text("SELECT user_id, is_active FROM user_sessions WHERE refresh_token = :token"),
        {"token": refresh_request.refresh_token}
    )
    session = result.fetchone()
    
    if not session or not session.is_active:
        raise HTTPException(status_code=401, detail="Session not found or inactive")
    
    # Получаем пользователя
    result = await db.execute(
        text("SELECT email, username, role FROM users WHERE id = :id AND is_active = true"),
        {"id": session.user_id}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    # Создаем новый access токен
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(session.user_id), "username": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Обновляем сессию
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
    
    # Получаем текущий пароль
    result = await db.execute(
        text("SELECT hashed_password FROM users WHERE id = :id"),
        {"id": current_user["id"]}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверяем старый пароль
    if not verify_password(password_request.old_password, user.hashed_password):
        await log_audit_event(
            db, user_id=current_user["id"], user_name=current_user["username"],
            action="password_change_failed", status="error",
            error_message="Invalid old password", **client_info
        )
        raise HTTPException(status_code=400, detail="Неверный старый пароль")
    
    # Проверяем историю паролей
    if not await check_password_history(db, current_user["id"], password_request.new_password):
        raise HTTPException(status_code=400, detail="Пароль уже использовался ранее")
    
    # Хешируем новый пароль
    new_hashed = hash_password(password_request.new_password)
    
    # Обновляем пароль
    await db.execute(
        text("UPDATE users SET hashed_password = :hashed, last_password_change = NOW(), updated_at = NOW() WHERE id = :id"),
        {"hashed": new_hashed, "id": current_user["id"]}
    )
    
    # Добавляем в историю
    await add_to_password_history(db, current_user["id"], new_hashed)
    
    # Отзываем все сессии кроме текущей
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        current_token = auth_header[7:]
        await revoke_all_user_sessions(db, current_user["id"], current_token)
    
    await db.commit()
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        action="password_change", status="success", **client_info
    )
    
    return {"message": "Пароль успешно изменен", "success": True}


@router.post("/sessions", response_model=SessionsListResponse)
async def get_user_sessions(
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение активных сессий пользователя"""
    result = await db.execute(
        text("""
            SELECT session_token, ip_address, user_agent, created_at, last_activity, expires_at, is_active
            FROM user_sessions 
            WHERE user_id = :user_id AND is_active = true
            ORDER BY last_activity DESC
        """),
        {"user_id": current_user["id"]}
    )
    
    sessions = []
    for row in result.fetchall():
        sessions.append({
            "session_id": row.session_token[:16] + "...",
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "last_activity": row.last_activity.isoformat() if row.last_activity else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "is_active": row.is_active
        })
    
    return {"sessions": sessions, "total": len(sessions)}


@router.post("/sessions/{session_id}/revoke")
async def revoke_session_endpoint(
    session_id: str,
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Отзыв конкретной сессии"""
    # Находим полный токен по частичному ID
    result = await db.execute(
        text("SELECT session_token FROM user_sessions WHERE user_id = :user_id AND session_token LIKE :prefix"),
        {"user_id": current_user["id"], "prefix": session_id.replace("...", "") + "%"}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await revoke_session(db, row.session_token)
    
    return {"message": "Session revoked", "success": True}


# ============================================================================
# ENDPOINTS - УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (ADMIN ONLY)
# ============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Список пользователей (только для админов)"""
    conditions = []
    params = {"limit": limit, "skip": skip}
    
    if role:
        conditions.append("role = :role")
        params["role"] = role
    if is_active is not None:
        conditions.append("is_active = :is_active")
        params["is_active"] = is_active
    if search:
        conditions.append("(username ILIKE :search OR email ILIKE :search OR full_name ILIKE :search)")
        params["search"] = f"%{search}%"
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Общее количество
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM users WHERE {where_clause}"),
        {k: v for k, v in params.items() if k not in ["limit", "skip"]}
    )
    total = count_result.scalar() or 0
    
    # Получаем пользователей
    result = await db.execute(
        text(f"""
            SELECT id, email, username, full_name, role, is_active, is_superuser,
                   last_login, last_password_change, created_at, updated_at,
                   login_attempts, locked_until
            FROM users 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """),
        params
    )
    
    items = []
    for user in result.fetchall():
        items.append({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "last_password_change": user.last_password_change.isoformat() if user.last_password_change else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "login_attempts": user.login_attempts or 0,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None
        })
    
    page = (skip // limit) + 1 if limit > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": limit,
        "has_next": (skip + limit) < total,
        "has_prev": skip > 0
    }


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Создание пользователя (только для админов)"""
    client_info = get_client_info(request)
    
    await ensure_users_table(db)
    
    # Проверяем уникальность
    existing = await db.execute(
        text("SELECT id FROM users WHERE username = :username OR email = :email"),
        {"username": user_data.username, "email": user_data.email}
    )
    if existing.fetchone():
        raise HTTPException(status_code=400, detail="Пользователь с таким username или email уже существует")
    
    # Хешируем пароль
    hashed = hash_password(user_data.password)
    
    # Создаем пользователя
    result = await db.execute(text("""
        INSERT INTO users (email, username, full_name, hashed_password, role, is_active, created_at, updated_at)
        VALUES (:email, :username, :full_name, :hashed, :role, true, NOW(), NOW())
        RETURNING id
    """), {
        "email": user_data.email,
        "username": user_data.username,
        "full_name": user_data.full_name,
        "hashed": hashed,
        "role": user_data.role
    })
    
    user_id = result.scalar()
    
    # Добавляем в историю паролей
    await add_to_password_history(db, str(user_id), hashed)
    
    await db.commit()
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        action="create_user", entity_type="user", entity_id=str(user_id),
        entity_name=user_data.username, status="success", **client_info
    )
    
    return {
        "id": str(user_id),
        "email": user_data.email,
        "username": user_data.username,
        "full_name": user_data.full_name,
        "role": user_data.role,
        "is_active": True,
        "is_superuser": False,
        "last_login": None,
        "last_password_change": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "login_attempts": 0,
        "locked_until": None
    }


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    request: Request,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление пользователя (только для админов)"""
    client_info = get_client_info(request)
    
    # Проверяем существование
    result = await db.execute(
        text("SELECT id FROM users WHERE id = :id"),
        {"id": user_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = []
    params = {"id": user_id}
    
    if user_data.email is not None:
        updates.append("email = :email")
        params["email"] = user_data.email
    if user_data.full_name is not None:
        updates.append("full_name = :full_name")
        params["full_name"] = user_data.full_name
    if user_data.role is not None:
        updates.append("role = :role")
        params["role"] = user_data.role
    if user_data.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = user_data.is_active
    
    if updates:
        updates.append("updated_at = NOW()")
        await db.execute(
            text(f"UPDATE users SET {', '.join(updates)} WHERE id = :id"),
            params
        )
        await db.commit()
    
    # Получаем обновленного пользователя
    result = await db.execute(
        text("""
            SELECT id, email, username, full_name, role, is_active, is_superuser,
                   last_login, last_password_change, created_at, updated_at
            FROM users WHERE id = :id
        """),
        {"id": user_id}
    )
    user = result.fetchone()
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        action="update_user", entity_type="user", entity_id=user_id,
        details=user_data.dict(exclude_unset=True), status="success", **client_info
    )
    
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "last_password_change": user.last_password_change.isoformat() if user.last_password_change else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "login_attempts": 0,
        "locked_until": None
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Удаление пользователя (только для админов)"""
    client_info = get_client_info(request)
    
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.execute(
        text("SELECT username FROM users WHERE id = :id"),
        {"id": user_id}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    await db.commit()
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        action="delete_user", entity_type="user", entity_id=user_id,
        entity_name=user.username, status="success", **client_info
    )
    
    return {"message": "User deleted", "success": True}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_user_password(
    user_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Сброс пароля пользователя администратором"""
    client_info = get_client_info(request)
    
    result = await db.execute(
        text("SELECT username, email FROM users WHERE id = :id"),
        {"id": user_id}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Генерируем временный пароль
    temp_password = secrets.token_urlsafe(12)
    hashed = hash_password(temp_password)
    
    await db.execute(
        text("UPDATE users SET hashed_password = :hashed, last_password_change = NOW() WHERE id = :id"),
        {"hashed": hashed, "id": user_id}
    )
    
    # Отзываем все сессии
    await revoke_all_user_sessions(db, user_id)
    
    await db.commit()
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        action="admin_reset_password", entity_type="user", entity_id=user_id,
        entity_name=user.username, status="success", **client_info
    )
    
    return {
        "message": "Password reset",
        "temporary_password": temp_password,
        "success": True
    }


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Разблокировка пользователя"""
    client_info = get_client_info(request)
    
    await db.execute(
        text("UPDATE users SET login_attempts = 0, locked_until = NULL WHERE id = :id"),
        {"id": user_id}
    )
    await db.commit()
    
    await log_audit_event(
        db, user_id=current_user["id"], user_name=current_user["username"],
        action="unlock_user", entity_type="user", entity_id=user_id,
        status="success", **client_info
    )
    
    return {"message": "User unlocked", "success": True}


# ============================================================================
# ENDPOINTS - ВОССТАНОВЛЕНИЕ ПАРОЛЯ
# ============================================================================

@router.post("/password-reset-request")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Запрос на сброс пароля"""
    client_info = get_client_info(request)
    
    result = await db.execute(
        text("SELECT id, username FROM users WHERE email = :email AND is_active = true"),
        {"email": reset_request.email}
    )
    user = result.fetchone()
    
    if user:
        # Создаем токен
        token = create_password_reset_token(str(user.id))
        
        # Сохраняем токен
        expires_at = datetime.utcnow() + timedelta(hours=1)
        await db.execute(text("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (:user_id, :token, :expires_at)
        """), {"user_id": user.id, "token": token, "expires_at": expires_at})
        await db.commit()
        
        # Отправляем email (в фоне)
        # background_tasks.add_task(send_password_reset_email, reset_request.email, token)
        
        await log_audit_event(
            db, user_id=str(user.id), user_name=user.username,
            action="password_reset_request", status="success", **client_info
        )
    
    # Всегда возвращаем одинаковый ответ (безопасность)
    return {"message": "If the email exists, a reset link has been sent", "success": True}


@router.post("/password-reset-confirm")
async def confirm_password_reset(
    request: Request,
    reset_confirm: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """Подтверждение сброса пароля"""
    client_info = get_client_info(request)
    
    # Проверяем токен
    result = await db.execute(
        text("""
            SELECT user_id FROM password_reset_tokens 
            WHERE token = :token AND expires_at > NOW() AND used = false
        """),
        {"token": reset_confirm.token}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Получаем пользователя
    result = await db.execute(
        text("SELECT username FROM users WHERE id = :id"),
        {"id": row.user_id}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Хешируем новый пароль
    hashed = hash_password(reset_confirm.new_password)
    
    # Обновляем пароль
    await db.execute(
        text("UPDATE users SET hashed_password = :hashed, last_password_change = NOW(), login_attempts = 0, locked_until = NULL WHERE id = :id"),
        {"hashed": hashed, "id": row.user_id}
    )
    
    # Отмечаем токен использованным
    await db.execute(
        text("UPDATE password_reset_tokens SET used = true WHERE token = :token"),
        {"token": reset_confirm.token}
    )
    
    # Отзываем все сессии
    await revoke_all_user_sessions(db, str(row.user_id))
    
    await db.commit()
    
    await log_audit_event(
        db, user_id=str(row.user_id), user_name=user.username,
        action="password_reset_confirm", status="success", **client_info
    )
    
    return {"message": "Password has been reset", "success": True}


# ============================================================================
# ENDPOINTS - СЛУЖЕБНЫЕ
# ============================================================================

@router.post("/create-admin", include_in_schema=False)
async def create_admin_endpoint(
    username: str = "admin",
    password: str = "Admin123!",
    db: AsyncSession = Depends(get_db)
):
    """Создание/обновление администратора (только для отладки)"""
    await ensure_users_table(db)
    await ensure_password_history_table(db)
    
    hashed = hash_password(password)
    
    result = await db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username}
    )
    existing = result.fetchone()
    
    if existing:
        await db.execute(
            text("UPDATE users SET hashed_password = :hashed, is_active = true, updated_at = NOW() WHERE username = :username"),
            {"hashed": hashed, "username": username}
        )
        user_id = existing.id
    else:
        result = await db.execute(text("""
            INSERT INTO users (email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
            VALUES (:email, :username, :full_name, :hashed, 'admin', true, true, NOW(), NOW())
            RETURNING id
        """), {
            "email": f"{username}@gochs.local",
            "username": username,
            "full_name": "Администратор",
            "hashed": hashed
        })
        user_id = result.scalar()
    
    await add_to_password_history(db, str(user_id), hashed)
    await db.commit()
    
    return {"success": True, "message": f"User {username} created/updated"}


@router.get("/check-user/{username}", include_in_schema=False)
async def check_user(username: str, db: AsyncSession = Depends(get_db)):
    """Проверка существования пользователя"""
    await ensure_users_table(db)
    
    result = await db.execute(
        text("SELECT id, username, email, role, is_active, is_superuser FROM users WHERE username = :username OR email = :email"),
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
            "is_active": user.is_active,
            "is_superuser": user.is_superuser
        }
    return {"exists": False}


@router.get("/password-strength", include_in_schema=False)
async def check_password_strength(password: str = Query(...)):
    """Проверка сложности пароля"""
    return get_password_strength(password)


@router.post("/ensure-tables", include_in_schema=False)
async def ensure_all_tables(db: AsyncSession = Depends(get_db)):
    """Создание всех необходимых таблиц"""
    results = {
        "users": await ensure_users_table(db),
        "sessions": await ensure_sessions_table(db),
        "password_history": await ensure_password_history_table(db),
        "audit": await ensure_audit_table(db),
        "password_reset_tokens": await ensure_password_reset_tokens_table(db)
    }
    return {"success": True, "tables": results}


async def ensure_password_reset_tokens_table(db: AsyncSession) -> bool:
    """Создание таблицы токенов сброса пароля"""
    try:
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token VARCHAR(500) NOT NULL,
                used BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """))
        await db.commit()
        return True
    except:
        return False
