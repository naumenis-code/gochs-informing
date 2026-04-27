from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """Получение текущего пользователя из токена"""
    if not token:
        return None
    
    # Простая проверка токена (без JWT, так как используем упрощенную схему)
    if not token.startswith("token_"):
        return None
    
    try:
        # Получаем первого активного пользователя с ролью admin
        result = await db.execute(
            text("SELECT id, email, username, full_name, role, is_active FROM users WHERE is_active = true LIMIT 1")
        )
        user = result.fetchone()
        
        if user:
            return {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active
            }
    except Exception:
        pass
    
    return None


async def get_current_active_user(
    current_user: Optional[Dict] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Получение текущего активного пользователя с проверкой"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return current_user


async def get_current_admin_user(
    current_user: Dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Получение текущего администратора"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
