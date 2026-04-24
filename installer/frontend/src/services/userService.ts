/**
 * API Сервис для управления пользователями ГО-ЧС Информирование
 * Соответствует ТЗ, раздел 22: Роли пользователей
 * 
 * Базовый URL: /api/v1/users
 */

import api from './api';
import type { AxiosResponse } from 'axios';

// ============================================================================
// ТИПЫ И ИНТЕРФЕЙСЫ
// ============================================================================

/** Роли пользователей */
export type UserRole = 'admin' | 'operator' | 'viewer';

/** Статусы пользователя */
export type UserStatus = 'active' | 'inactive' | 'locked' | 'pending';

/** Параметры пагинации */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

/** Ответ с пагинацией */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

/** Базовая информация о пользователе (для списков) */
export interface UserListItem {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
  created_at: string | null;
}

/** Полная информация о пользователе */
export interface UserDetail {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  last_login: string | null;
  login_attempts: number;
  force_password_change: boolean;
  created_at: string | null;
  updated_at: string | null;
  created_by: string | null;
  updated_by: string | null;
  total_campaigns: number;
  total_logins: number;
  account_locked_until: string | null;
}

/** Данные для создания пользователя */
export interface UserCreateData {
  email: string;
  username: string;
  full_name: string;
  password: string;
  password_confirm: string;
  role?: UserRole;
}

/** Данные для обновления пользователя */
export interface UserUpdateData {
  email?: string;
  username?: string;
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
}

/** Данные для смены пароля */
export interface PasswordChangeData {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

/** Данные для сброса пароля (администратором) */
export interface PasswordResetData {
  new_password: string;
  force_change?: boolean;
}

/** Параметры фильтрации пользователей */
export interface UserFilterParams extends PaginationParams {
  role?: UserRole;
  is_active?: boolean;
  search?: string;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
}

/** Статистика по пользователям */
export interface UserStats {
  total: number;
  active: number;
  inactive: number;
  locked: number;
  force_password_change: number;
  by_role: Record<string, number>;
  last_created: {
    id: string | null;
    username: string | null;
    created_at: string | null;
  } | null;
}

/** Результат массовой операции */
export interface BulkOperationResult {
  total_processed: number;
  success_count: number;
  error_count: number;
  skipped_count?: number;
  errors: Array<{
    user_id?: string;
    contact_id?: string;
    error: string;
  }>;
  message: string;
}

/** Права роли */
export interface RolePermissions {
  name: string;
  description: string;
  permissions: string[];
}

// ============================================================================
// API СЕРВИС
// ============================================================================

export const userService = {
  // =========================================================================
  // ПОЛУЧЕНИЕ СПИСКА
  // =========================================================================

  /**
   * Получить список пользователей с фильтрацией
   * Требует роль: admin
   */
  async getUsers(params: UserFilterParams = {}): Promise<PaginatedResponse<UserListItem>> {
    const response: AxiosResponse<PaginatedResponse<UserListItem>> = await api.get('/users/', { params });
    return response.data;
  },

  /**
   * Получить текущего пользователя
   */
  async getCurrentUser(): Promise<UserDetail> {
    const response: AxiosResponse<UserDetail> = await api.get('/users/me');
    return response.data;
  },

  /**
   * Получить пользователя по ID
   * Требует роль: admin
   */
  async getUser(userId: string): Promise<UserDetail> {
    const response: AxiosResponse<UserDetail> = await api.get(`/users/${userId}`);
    return response.data;
  },

  // =========================================================================
  // СОЗДАНИЕ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ
  // =========================================================================

  /**
   * Создать нового пользователя
   * Требует роль: admin
   */
  async createUser(data: UserCreateData): Promise<UserDetail> {
    const response: AxiosResponse<UserDetail> = await api.post('/users/', data);
    return response.data;
  },

  /**
   * Обновить пользователя
   * Требует роль: admin
   */
  async updateUser(userId: string, data: UserUpdateData): Promise<UserDetail> {
    const response: AxiosResponse<UserDetail> = await api.patch(`/users/${userId}`, data);
    return response.data;
  },

  /**
   * Удалить/деактивировать пользователя
   * Требует роль: admin
   */
  async deleteUser(userId: string, hardDelete: boolean = false): Promise<{ message: string; success: boolean }> {
    const response = await api.delete(`/users/${userId}`, {
      params: { hard_delete: hardDelete }
    });
    return response.data;
  },

  // =========================================================================
  // ПАРОЛИ
  // =========================================================================

  /**
   * Сменить свой пароль
   */
  async changeMyPassword(data: PasswordChangeData): Promise<{ message: string; success: boolean }> {
    const response = await api.post('/users/me/change-password', data);
    return response.data;
  },

  /**
   * Сбросить пароль пользователя (администратором)
   * Требует роль: admin
   */
  async resetUserPassword(userId: string, data: PasswordResetData): Promise<{ message: string; success: boolean }> {
    const response = await api.post(`/users/${userId}/reset-password`, data);
    return response.data;
  },

  // =========================================================================
  // РОЛИ И БЛОКИРОВКИ
  // =========================================================================

  /**
   * Изменить роль пользователя
   * Требует роль: admin
   */
  async changeUserRole(userId: string, newRole: UserRole): Promise<{ message: string; success: boolean }> {
    const response = await api.post(`/users/${userId}/change-role`, null, {
      params: { new_role: newRole }
    });
    return response.data;
  },

  /**
   * Разблокировать пользователя
   * Требует роль: admin
   */
  async unlockUser(userId: string): Promise<{ message: string; success: boolean }> {
    const response = await api.post(`/users/${userId}/unlock`);
    return response.data;
  },

  /**
   * Восстановить деактивированного пользователя
   * Требует роль: admin
   */
  async restoreUser(userId: string): Promise<{ message: string; success: boolean }> {
    const response = await api.post(`/users/${userId}/restore`);
    return response.data;
  },

  // =========================================================================
  // МАССОВЫЕ ОПЕРАЦИИ
  // =========================================================================

  /**
   * Массовое обновление пользователей
   * Требует роль: admin
   */
  async bulkUpdateUsers(userIds: string[], data: UserUpdateData): Promise<BulkOperationResult> {
    const response: AxiosResponse<BulkOperationResult> = await api.post(
      `/users/bulk-update?user_ids=${userIds.join('&user_ids=')}`,
      data
    );
    return response.data;
  },

  // =========================================================================
  // СТАТИСТИКА
  // =========================================================================

  /**
   * Получить статистику по пользователям
   * Требует роль: admin
   */
  async getUserStats(): Promise<UserStats> {
    const response: AxiosResponse<UserStats> = await api.get('/users/stats/summary');
    return response.data;
  },

  // =========================================================================
  // ВСПОМОГАТЕЛЬНЫЕ
  // =========================================================================

  /**
   * Получить список доступных ролей
   */
  async getRoles(): Promise<{ roles: Array<{ value: string; label: string; description: string }> }> {
    // Статические данные, т.к. эндпоинта нет
    return {
      roles: [
        { value: 'admin', label: '👑 Администратор', description: 'Полный доступ ко всем разделам системы' },
        { value: 'operator', label: '🔧 Оператор', description: 'Управление обзвоном, просмотр статусов и входящих' },
        { value: 'viewer', label: '👁 Наблюдатель', description: 'Только просмотр (без запуска обзвона)' },
      ]
    };
  },

  /**
   * Получить права для роли
   */
  async getRolePermissions(role: UserRole): Promise<RolePermissions> {
    const permissions: Record<UserRole, RolePermissions> = {
      admin: {
        name: 'Администратор',
        description: 'Полный доступ ко всем разделам системы',
        permissions: [
          'users:read', 'users:create', 'users:update', 'users:delete',
          'contacts:read', 'contacts:create', 'contacts:update', 'contacts:delete', 'contacts:import',
          'groups:read', 'groups:create', 'groups:update', 'groups:delete',
          'scenarios:read', 'scenarios:create', 'scenarios:update', 'scenarios:delete',
          'playbooks:read', 'playbooks:create', 'playbooks:update', 'playbooks:delete',
          'campaigns:read', 'campaigns:create', 'campaigns:start', 'campaigns:stop',
          'inbound:read', 'inbound:delete',
          'settings:read', 'settings:update',
          'audit:read', 'audit:export',
          'system:backup', 'system:restore',
        ]
      },
      operator: {
        name: 'Оператор',
        description: 'Управление обзвоном, просмотр статусов и входящих',
        permissions: [
          'contacts:read',
          'groups:read',
          'scenarios:read',
          'campaigns:read', 'campaigns:start', 'campaigns:stop',
          'inbound:read',
          'playbooks:read',
        ]
      },
      viewer: {
        name: 'Наблюдатель',
        description: 'Только просмотр (без запуска обзвона)',
        permissions: [
          'contacts:read',
          'groups:read',
          'scenarios:read',
          'campaigns:read',
          'inbound:read',
          'playbooks:read',
        ]
      }
    };
    
    return permissions[role] || permissions.viewer;
  },

  /**
   * Проверить сложность пароля
   */
  validatePasswordStrength(password: string): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (password.length < 8) {
      errors.push('Пароль должен быть не менее 8 символов');
    }
    if (!/\d/.test(password)) {
      errors.push('Пароль должен содержать хотя бы одну цифру');
    }
    if (!/[a-zA-Z]/.test(password)) {
      errors.push('Пароль должен содержать хотя бы одну букву');
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('Пароль должен содержать хотя бы одну заглавную букву');
    }
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) {
      errors.push('Пароль должен содержать хотя бы один спецсимвол');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  },

  /**
   * Получить цвет для роли
   */
  getRoleColor(role: UserRole): string {
    const colors: Record<UserRole, string> = {
      admin: '#e74c3c',
      operator: '#3498db',
      viewer: '#95a5a6',
    };
    return colors[role] || '#95a5a6';
  },

  /**
   * Получить цвет для статуса пользователя
   */
  getStatusColor(isActive: boolean, loginAttempts: number): string {
    if (loginAttempts >= 5) return '#e74c3c'; // заблокирован
    if (isActive) return '#2ecc71';            // активен
    return '#95a5a6';                           // неактивен
  },

  /**
   * Получить текст статуса
   */
  getStatusText(isActive: boolean, loginAttempts: number, accountLockedUntil: string | null): string {
    if (accountLockedUntil && new Date(accountLockedUntil) > new Date()) {
      return '🔒 Заблокирован';
    }
    if (loginAttempts >= 5) {
      return '🔒 Заблокирован';
    }
    if (isActive) {
      return '✅ Активен';
    }
    return '❌ Неактивен';
  },
};

export default userService;
