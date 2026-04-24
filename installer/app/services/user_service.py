#!/usr/bin/env python3
"""
Сервис управления пользователями ГО-ЧС Информирование
Соответствует ТЗ, раздел 22: Роли пользователей

Функционал:
- CRUD операции с пользователями
- Аутентификация и авторизация
- Управление ролями и правами
- Блокировка после неудачных попыток
- Аудит действий
"""

import logging
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserPasswordChange, UserPasswordReset,
    UserRole, UserStatus
)
from app.schemas.common import PaginatedResponse, BulkOperationResult

logger = logging.getLogger(__name__)

# Константы безопасности
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PASSWORD_HISTORY_SIZE = 5  # Хранить последние 5 паролей


class UserService:
    """Сервис управления пользователями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # CRUD ОПЕРАЦИИ
    # =========================================================================
    
    async def create_user(
        self,
        user_data: UserCreate,
        created_by: Optional[UUID] = None
    ) -> User:
        """
        Создание нового пользователя
        
        Args:
            user_data: данные нового пользователя
            created_by: ID создателя (администратора)
            
        Returns:
            Созданный пользователь
            
        Raises:
            ValueError: если пользователь с таким email/username уже существует
        """
        # Проверка уникальности email
        existing = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Пользователь с email '{user_data.email}' уже существует")
        
        # Проверка уникальности username
        existing = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Пользователь с логином '{user_data.username}' уже существует")
        
        # Создание пользователя
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role.value if hasattr(user_data.role, 'value') else user_data.role,
            is_active=True,
            is_superuser=(user_data.role == UserRole.ADMIN),
            created_by=created_by,
            password_changed_at=datetime.now(timezone.utc),
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        logger.info(f"Создан пользователь: {user.username} (роль: {user.role})")
        return user
    
    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Получить пользователя по ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по имени пользователя"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def list_users(
        self,
        page: int = 1,
        page_size: int = 50,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        sort_field: str = "created_at",
        sort_direction: str = "desc"
    ) -> PaginatedResponse:
        """
        Получить список пользователей с фильтрацией и пагинацией
        
        Args:
            page: номер страницы
            page_size: размер страницы
            role: фильтр по роли
            is_active: фильтр по активности
            search: поиск по имени/email/логину
            created_after: создан после
            created_before: создан до
            sort_field: поле сортировки
            sort_direction: направление сортировки
            
        Returns:
            PaginatedResponse со списком пользователей
        """
        # Базовый запрос
        query = select(User)
        count_query = select(func.count(User.id))
        
        # Фильтры
        filters = []
        
        if role:
            filters.append(User.role == role.value if hasattr(role, 'value') else role)
        if is_active is not None:
            filters.append(User.is_active == is_active)
        if search:
            search_filter = or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
        if created_after:
            filters.append(User.created_at >= created_after)
        if created_before:
            filters.append(User.created_at <= created_before)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Сортировка
        sort_column = getattr(User, sort_field, User.created_at)
        if sort_direction == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Общее количество
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Пагинация
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        # Формирование ответа
        items = [
            {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            for user in users
        ]
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    async def update_user(
        self,
        user_id: UUID,
        update_data: UserUpdate,
        updated_by: Optional[UUID] = None
    ) -> User:
        """
        Обновление данных пользователя
        
        Args:
            user_id: ID пользователя
            update_data: данные для обновления
            updated_by: кто обновляет
            
        Returns:
            Обновленный пользователь
            
        Raises:
            ValueError: если пользователь не найден
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"Пользователь с ID {user_id} не найден")
        
        # Обновление полей (только переданные)
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if 'email' in update_dict and update_dict['email'] != user.email:
            # Проверка уникальности нового email
            existing = await self.db.execute(
                select(User).where(
                    and_(User.email == update_dict['email'], User.id != user_id)
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Email '{update_dict['email']}' уже используется")
        
        if 'username' in update_dict and update_dict['username'] != user.username:
            # Проверка уникальности нового username
            existing = await self.db.execute(
                select(User).where(
                    and_(User.username == update_dict['username'], User.id != user_id)
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Логин '{update_dict['username']}' уже используется")
        
        for key, value in update_dict.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_by = updated_by
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        logger.info(f"Обновлен пользователь: {user.username} (поля: {list(update_dict.keys())})")
        return user
    
    async def delete_user(
        self,
        user_id: UUID,
        deleted_by: Optional[UUID] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Удаление пользователя
        
        Args:
            user_id: ID пользователя
            deleted_by: кто удаляет
            hard_delete: полное удаление (False = деактивация)
            
        Returns:
            True если удален
            
        Raises:
            ValueError: если пользователь не найден или это последний администратор
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"Пользователь с ID {user_id} не найден")
        
        # Проверка: нельзя удалить последнего администратора
        if user.role == UserRole.ADMIN.value:
            admin_count = await self.db.execute(
                select(func.count(User.id)).where(
                    and_(User.role == UserRole.ADMIN.value, User.is_active == True)
                )
            )
            if admin_count.scalar() <= 1:
                raise ValueError("Нельзя удалить последнего активного администратора")
        
        if hard_delete:
            await self.db.delete(user)
            logger.info(f"Пользователь полностью удален: {user.username}")
        else:
            user.is_active = False
            user.updated_by = deleted_by
            user.updated_at = datetime.now(timezone.utc)
            logger.info(f"Пользователь деактивирован: {user.username}")
        
        await self.db.flush()
        return True
    
    async def restore_user(
        self,
        user_id: UUID,
        restored_by: Optional[UUID] = None
    ) -> User:
        """
        Восстановление деактивированного пользователя
        
        Args:
            user_id: ID пользователя
            restored_by: кто восстанавливает
            
        Returns:
            Восстановленный пользователь
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"Пользователь с ID {user_id} не найден")
        
        user.is_active = True
        user.login_attempts = 0
        user.locked_until = None
        user.updated_by = restored_by
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        logger.info(f"Пользователь восстановлен: {user.username}")
        return user
    
    # =========================================================================
    # АУТЕНТИФИКАЦИЯ
    # =========================================================================
    
    async def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Аутентификация пользователя
        
        Args:
            username: имя пользователя или email
            password: пароль
            ip_address: IP адрес для аудита
            
        Returns:
            (User, None) — успешно
            (None, "error_message") — ошибка
        """
        # Поиск пользователя по email или username
        result = await self.db.execute(
            select(User).where(
                or_(User.email == username, User.username == username)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Попытка входа: пользователь '{username}' не найден")
            return None, "Неверное имя пользователя или пароль"
        
        # Проверка блокировки
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
            logger.warning(f"Попытка входа в заблокированный аккаунт: {user.username}")
            return None, f"Аккаунт заблокирован. Попробуйте через {remaining} мин."
        
        # Проверка активности
        if not user.is_active:
            logger.warning(f"Попытка входа в неактивный аккаунт: {user.username}")
            return None, "Аккаунт деактивирован"
        
        # Проверка пароля
        if not verify_password(password, user.hashed_password):
            # Увеличиваем счетчик неудачных попыток
            user.login_attempts += 1
            
            # Блокировка после MAX_LOGIN_ATTEMPTS
            if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                logger.warning(f"Аккаунт заблокирован: {user.username} ({user.login_attempts} попыток)")
                await self.db.flush()
                return None, f"Аккаунт заблокирован на {LOCKOUT_MINUTES} минут из-за {MAX_LOGIN_ATTEMPTS} неудачных попыток"
            
            await self.db.flush()
            logger.warning(f"Неверный пароль для пользователя: {user.username} (попытка {user.login_attempts})")
            return None, "Неверное имя пользователя или пароль"
        
        # Успешный вход
        user.login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        user.last_ip = ip_address
        user.login_count = (user.login_count or 0) + 1
        
        # Проверка необходимости смены пароля
        if user.force_password_change:
            await self.db.flush()
            return user, "Требуется смена пароля"
        
        await self.db.flush()
        logger.info(f"Успешный вход: {user.username} (роль: {user.role})")
        return user, None
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Смена пароля пользователем
        
        Args:
            user_id: ID пользователя
            current_password: текущий пароль
            new_password: новый пароль
            
        Returns:
            True если сменен
            
        Raises:
            ValueError: если неверный текущий пароль
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        
        # Проверка текущего пароля
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Неверный текущий пароль")
        
        # Проверка, что новый пароль не совпадает со старым
        if verify_password(new_password, user.hashed_password):
            raise ValueError("Новый пароль не должен совпадать с текущим")
        
        # Проверка истории паролей (если есть)
        if hasattr(user, 'password_history') and user.password_history:
            for old_hash in user.password_history[-PASSWORD_HISTORY_SIZE:]:
                if verify_password(new_password, old_hash):
                    raise ValueError("Пароль уже использовался ранее")
        
        # Сохранение старого пароля в историю
        if not hasattr(user, 'password_history') or user.password_history is None:
            user.password_history = []
        user.password_history.append(user.hashed_password)
        if len(user.password_history) > PASSWORD_HISTORY_SIZE:
            user.password_history = user.password_history[-PASSWORD_HISTORY_SIZE:]
        
        # Установка нового пароля
        user.hashed_password = get_password_hash(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        user.force_password_change = False
        
        await self.db.flush()
        logger.info(f"Пароль изменен для пользователя: {user.username}")
        return True
    
    async def reset_password(
        self,
        user_id: UUID,
        new_password: str,
        force_change: bool = True,
        reset_by: Optional[UUID] = None
    ) -> str:
        """
        Сброс пароля администратором
        
        Args:
            user_id: ID пользователя
            new_password: новый пароль
            force_change: требовать смену при следующем входе
            reset_by: кто сбросил
            
        Returns:
            Новый пароль (если сгенерирован автоматически)
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        
        user.hashed_password = get_password_hash(new_password)
        user.force_password_change = force_change
        user.login_attempts = 0
        user.locked_until = None
        user.password_changed_at = datetime.now(timezone.utc)
        user.updated_by = reset_by
        
        await self.db.flush()
        logger.info(f"Пароль сброшен для пользователя: {user.username} (кем: {reset_by})")
        return new_password
    
    # =========================================================================
    # УПРАВЛЕНИЕ РОЛЯМИ
    # =========================================================================
    
    async def change_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        changed_by: UUID
    ) -> User:
        """
        Изменение роли пользователя
        
        Args:
            user_id: ID пользователя
            new_role: новая роль
            changed_by: кто изменил
            
        Returns:
            Обновленный пользователь
            
        Raises:
            ValueError: если это последний администратор
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        
        old_role = user.role
        
        # Проверка: нельзя снять роль администратора с последнего админа
        if old_role == UserRole.ADMIN.value and new_role != UserRole.ADMIN:
            admin_count = await self.db.execute(
                select(func.count(User.id)).where(
                    and_(User.role == UserRole.ADMIN.value, User.is_active == True)
                )
            )
            if admin_count.scalar() <= 1:
                raise ValueError("Нельзя изменить роль последнего активного администратора")
        
        user.role = new_role.value if hasattr(new_role, 'value') else new_role
        user.is_superuser = (new_role == UserRole.ADMIN)
        user.updated_by = changed_by
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        logger.info(f"Роль пользователя изменена: {user.username} ({old_role} → {new_role})")
        return user
    
    async def unlock_user(
        self,
        user_id: UUID,
        unlocked_by: UUID
    ) -> User:
        """
        Разблокировка пользователя
        
        Args:
            user_id: ID пользователя
            unlocked_by: кто разблокировал
            
        Returns:
            Разблокированный пользователь
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        
        user.login_attempts = 0
        user.locked_until = None
        user.updated_by = unlocked_by
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        logger.info(f"Пользователь разблокирован: {user.username}")
        return user
    
    # =========================================================================
    # ПРОВЕРКИ И ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    async def is_admin(self, user_id: UUID) -> bool:
        """Проверить, является ли пользователь администратором"""
        user = await self.get_user(user_id)
        return user is not None and user.role == UserRole.ADMIN.value
    
    async def get_user_permissions(self, user_id: UUID) -> List[str]:
        """
        Получить список прав пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список строк прав
        """
        from app.schemas.user import ROLE_PERMISSIONS
        
        user = await self.get_user(user_id)
        if not user:
            return []
        
        role_perms = ROLE_PERMISSIONS.get(user.role, {})
        return role_perms.get("permissions", [])
    
    async def has_permission(self, user_id: UUID, permission: str) -> bool:
        """
        Проверить наличие права у пользователя
        
        Args:
            user_id: ID пользователя
            permission: строка права (например, "users:delete")
            
        Returns:
            True если право есть
        """
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Получить статистику по пользователям
        
        Returns:
            Словарь со статистикой
        """
        # Общее количество
        total = await self.db.execute(select(func.count(User.id)))
        total_count = total.scalar() or 0
        
        # Активных
        active = await self.db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_count = active.scalar() or 0
        
        # По ролям
        roles = await self.db.execute(
            select(User.role, func.count(User.id))
            .where(User.is_active == True)
            .group_by(User.role)
        )
        by_role = {row[0]: row[1] for row in roles}
        
        # Заблокированных
        locked = await self.db.execute(
            select(func.count(User.id)).where(
                and_(User.locked_until != None, User.locked_until > datetime.now(timezone.utc))
            )
        )
        locked_count = locked.scalar() or 0
        
        # С требованием смены пароля
        force_change = await self.db.execute(
            select(func.count(User.id)).where(User.force_password_change == True)
        )
        force_change_count = force_change.scalar() or 0
        
        # Последний созданный
        last_created = await self.db.execute(
            select(User).order_by(User.created_at.desc()).limit(1)
        )
        last_user = last_created.scalar_one_or_none()
        
        return {
            "total": total_count,
            "active": active_count,
            "inactive": total_count - active_count,
            "locked": locked_count,
            "force_password_change": force_change_count,
            "by_role": by_role,
            "last_created": {
                "id": str(last_user.id) if last_user else None,
                "username": last_user.username if last_user else None,
                "created_at": last_user.created_at.isoformat() if last_user and last_user.created_at else None,
            } if last_user else None,
        }
    
    async def bulk_update_users(
        self,
        user_ids: List[UUID],
        update_data: Dict[str, Any],
        updated_by: UUID
    ) -> BulkOperationResult:
        """
        Массовое обновление пользователей
        
        Args:
            user_ids: список ID пользователей
            update_data: данные для обновления
            updated_by: кто обновляет
            
        Returns:
            Результат операции
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                user = await self.get_user(user_id)
                if not user:
                    errors.append({"user_id": str(user_id), "error": "Пользователь не найден"})
                    error_count += 1
                    continue
                
                for key, value in update_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                
                user.updated_by = updated_by
                user.updated_at = datetime.now(timezone.utc)
                success_count += 1
                
            except Exception as e:
                errors.append({"user_id": str(user_id), "error": str(e)})
                error_count += 1
        
        await self.db.flush()
        
        return BulkOperationResult(
            total_processed=len(user_ids),
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            message=f"Обновлено: {success_count}, ошибок: {error_count}"
        )
