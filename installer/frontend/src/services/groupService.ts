/**
 * API Сервис для управления группами контактов ГО-ЧС Информирование
 * Соответствует ТЗ, раздел 10: Контактная база — группы
 * 
 * Базовый URL: /api/v1/groups
 */

import api from './api';
import type { AxiosResponse } from 'axios';

// ============================================================================
// ТИПЫ И ИНТЕРФЕЙСЫ
// ============================================================================

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

/** Участник группы */
export interface GroupMember {
  contact_id: string;
  contact_name: string;
  department: string | null;
  position: string | null;
  mobile_number: string | null;
  internal_number: string | null;
  email: string | null;
  is_active: boolean;
  role: string | null;
  priority: number;
  note: string | null;
  added_at: string | null;
  added_by: string | null;
}

/** Полная информация о группе */
export interface GroupDetail {
  id: string;
  name: string;
  description: string | null;
  color: string;
  is_active: boolean;
  is_archived: boolean;
  is_system: boolean;
  member_count: number;
  total_member_count: number;
  mobile_members_count: number;
  internal_members_count: number;
  default_priority: number;
  max_retries: number;
  created_by: string | null;
  updated_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  members: GroupMember[];
  members_by_department: Array<{ department: string; count: number }>;
  active_members: number;
  inactive_members: number;
}

/** Краткая информация о группе (для списков) */
export interface GroupListItem {
  id: string;
  name: string;
  description: string | null;
  color: string;
  is_active: boolean;
  is_system: boolean;
  member_count: number;
  default_priority: number;
  created_at: string | null;
}

/** Данные для создания группы */
export interface GroupCreateData {
  name: string;
  description?: string;
  color?: string;
  is_active?: boolean;
  default_priority?: number;
  max_retries?: number;
  contact_ids?: string[];
}

/** Данные для обновления группы */
export interface GroupUpdateData {
  name?: string;
  description?: string;
  color?: string;
  is_active?: boolean;
  default_priority?: number;
  max_retries?: number;
}

/** Данные для добавления участников */
export interface AddMembersData {
  contact_ids: string[];
  role?: string;
  priority?: number;
  reason?: string;
  note?: string;
}

/** Данные для удаления участников */
export interface RemoveMembersData {
  contact_ids: string[];
  hard_delete?: boolean;
  reason?: string;
}

/** Данные для обновления участника */
export interface UpdateMemberData {
  contact_id?: string;
  role?: string;
  priority?: number;
  is_active?: boolean;
  note?: string;
}

/** Параметры фильтрации групп */
export interface GroupFilterParams extends PaginationParams {
  search?: string;
  is_active?: boolean;
  is_system?: boolean;
  has_members?: boolean;
  min_members?: number;
  max_members?: number;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
}

/** Массовое действие с группами */
export interface GroupBulkActionData {
  group_ids: string[];
  action: 'activate' | 'deactivate' | 'archive' | 'delete';
  reason?: string;
}

/** Объединение групп */
export interface GroupMergeData {
  source_group_ids: string[];
  target_group_id?: string;
  new_group_name?: string;
  delete_source_groups?: boolean;
}

/** Результат массовой операции */
export interface BulkOperationResult {
  total_processed: number;
  success_count: number;
  error_count: number;
  skipped_count?: number;
  errors: Array<{
    contact_id?: string;
    group_id?: string;
    error: string;
  }>;
  message: string;
}

/** Список для обзвона */
export interface DialerListResponse {
  group_id: string;
  group_name: string;
  total_contacts: number;
  contacts: Array<{
    contact_id: string;
    name: string;
    phone: string;
    department: string | null;
    priority: number;
  }>;
}

/** Статистика по группам */
export interface GroupStats {
  total_groups: number;
  active_groups: number;
  system_groups: number;
  user_groups: number;
  archived_groups: number;
  total_memberships: number;
  avg_members_per_group: number;
  groups_without_members: number;
  largest_group: {
    name: string;
    count: number;
  } | null;
  by_priority: Array<{ priority: number; count: number }>;
}

// ============================================================================
// ПРЕДОПРЕДЕЛЕННЫЕ ЦВЕТА
// ============================================================================

export const GROUP_COLORS: Record<string, string> = {
  blue: '#3498db',
  green: '#2ecc71',
  red: '#e74c3c',
  orange: '#e67e22',
  purple: '#9b59b6',
  teal: '#1abc9c',
  yellow: '#f1c40f',
  pink: '#e91e63',
  indigo: '#3f51b5',
  grey: '#95a5a6',
  dark: '#34495e',
};

export const GROUP_COLOR_OPTIONS = Object.entries(GROUP_COLORS).map(([name, hex]) => ({
  value: hex,
  label: name.charAt(0).toUpperCase() + name.slice(1),
  color: hex,
}));

// ============================================================================
// API СЕРВИС
// ============================================================================

export const groupService = {
  // =========================================================================
  // ПОЛУЧЕНИЕ СПИСКА
  // =========================================================================

  /**
   * Получить список групп с фильтрацией
   */
  async getGroups(params: GroupFilterParams = {}): Promise<PaginatedResponse<GroupListItem>> {
    const response: AxiosResponse<PaginatedResponse<GroupListItem>> = await api.get('/groups/', { params });
    return response.data;
  },

  /**
   * Получить группу по ID с участниками
   */
  async getGroup(groupId: string, includeMembers: boolean = true): Promise<GroupDetail> {
    const response: AxiosResponse<GroupDetail> = await api.get(`/groups/${groupId}`, {
      params: { include_members: includeMembers }
    });
    return response.data;
  },

  // =========================================================================
  // СОЗДАНИЕ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ
  // =========================================================================

  /**
   * Создать новую группу
   * Требует роль: admin
   */
  async createGroup(data: GroupCreateData): Promise<GroupDetail> {
    const response: AxiosResponse<GroupDetail> = await api.post('/groups/', data);
    return response.data;
  },

  /**
   * Обновить группу
   * Требует роль: admin
   */
  async updateGroup(groupId: string, data: GroupUpdateData): Promise<GroupDetail> {
    const response: AxiosResponse<GroupDetail> = await api.patch(`/groups/${groupId}`, data);
    return response.data;
  },

  /**
   * Удалить/архивировать группу
   * Требует роль: admin
   */
  async deleteGroup(groupId: string, hardDelete: boolean = false): Promise<{ message: string; success: boolean }> {
    const response = await api.delete(`/groups/${groupId}`, {
      params: { hard_delete: hardDelete }
    });
    return response.data;
  },

  /**
   * Восстановить группу из архива
   * Требует роль: admin
   */
  async restoreGroup(groupId: string): Promise<{ message: string; success: boolean }> {
    const response = await api.post(`/groups/${groupId}/restore`);
    return response.data;
  },

  // =========================================================================
  // УПРАВЛЕНИЕ УЧАСТНИКАМИ
  // =========================================================================

  /**
   * Добавить участников в группу
   * Доступно: admin, operator
   */
  async addMembers(groupId: string, data: AddMembersData): Promise<BulkOperationResult> {
    const response: AxiosResponse<BulkOperationResult> = await api.post(`/groups/${groupId}/members`, data);
    return response.data;
  },

  /**
   * Быстро добавить одного контакта в группу
   * Доступно: admin, operator
   */
  async addSingleMember(
    groupId: string,
    contactId: string,
    priority: number = 5,
    role?: string
  ): Promise<{ message: string; success: boolean }> {
    const params: Record<string, any> = { priority };
    if (role) params.role = role;
    
    const response = await api.post(`/groups/${groupId}/members/${contactId}`, null, { params });
    return response.data;
  },

  /**
   * Удалить участников из группы
   * Доступно: admin, operator
   */
  async removeMembers(groupId: string, data: RemoveMembersData): Promise<BulkOperationResult> {
    const response: AxiosResponse<BulkOperationResult> = await api.delete(`/groups/${groupId}/members`, {
      data: data
    });
    return response.data;
  },

  /**
   * Обновить параметры участника в группе
   * Доступно: admin, operator
   */
  async updateMember(
    groupId: string,
    contactId: string,
    data: UpdateMemberData
  ): Promise<{ message: string; success: boolean }> {
    const response = await api.patch(`/groups/${groupId}/members/${contactId}`, data);
    return response.data;
  },

  /**
   * Получить список участников группы
   */
  async getMembers(
    groupId: string,
    activeOnly: boolean = true,
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<GroupMember>> {
    const params = {
      ...pagination,
      active_only: activeOnly,
    };
    const response: AxiosResponse<PaginatedResponse<GroupMember>> = await api.get(
      `/groups/${groupId}/members`,
      { params }
    );
    return response.data;
  },

  // =========================================================================
  // ОБЗВОН
  // =========================================================================

  /**
   * Получить список для обзвона
   * Доступно: admin, operator
   */
  async getDialerList(groupId: string, preferMobile: boolean = true): Promise<DialerListResponse> {
    const response: AxiosResponse<DialerListResponse> = await api.get(`/groups/${groupId}/dialer-list`, {
      params: { prefer_mobile: preferMobile }
    });
    return response.data;
  },

  // =========================================================================
  // МАССОВЫЕ ОПЕРАЦИИ
  // =========================================================================

  /**
   * Массовое действие с группами
   * Требует роль: admin
   */
  async bulkAction(data: GroupBulkActionData): Promise<BulkOperationResult> {
    const response: AxiosResponse<BulkOperationResult> = await api.post('/groups/bulk-action', data);
    return response.data;
  },

  /**
   * Объединить группы
   * Требует роль: admin
   */
  async mergeGroups(data: GroupMergeData): Promise<GroupDetail> {
    const response: AxiosResponse<GroupDetail> = await api.post('/groups/merge', data);
    return response.data;
  },

  // =========================================================================
  // СТАТИСТИКА
  // =========================================================================

  /**
   * Получить статистику по группам
   */
  async getGroupStats(): Promise<GroupStats> {
    const response: AxiosResponse<GroupStats> = await api.get('/groups/stats/summary');
    return response.data;
  },

  // =========================================================================
  // ВСПОМОГАТЕЛЬНЫЕ
  // =========================================================================

  /**
   * Получить список всех групп (для выпадающих списков)
   */
  async getAllGroupsForSelect(): Promise<Array<{ value: string; label: string; color: string; memberCount: number }>> {
    try {
      // Получаем все группы (до 500)
      const response = await this.getGroups({
        page_size: 500,
        is_active: true,
        sort_field: 'name',
        sort_direction: 'asc',
      });
      
      return response.items.map(group => ({
        value: group.id,
        label: `${group.name} (${group.member_count})`,
        color: group.color || '#3498db',
        memberCount: group.member_count,
      }));
    } catch {
      return [];
    }
  },

  /**
   * Проверить, является ли группа системной
   */
  isSystemGroup(groupName: string): boolean {
    const systemGroups = ['Все сотрудники', 'Руководство', 'Дежурная смена'];
    return systemGroups.includes(groupName);
  },

  /**
   * Получить цвет для статуса группы
   */
  getStatusColor(isActive: boolean, isArchived: boolean, isSystem: boolean): string {
    if (isArchived) return '#95a5a6';
    if (isSystem) return '#9b59b6';
    if (isActive) return '#2ecc71';
    return '#e74c3c';
  },

  /**
   * Получить текст статуса
   */
  getStatusText(isActive: boolean, isArchived: boolean, isSystem: boolean): string {
    if (isArchived) return '📦 В архиве';
    if (isSystem) return '🔒 Системная';
    if (isActive) return '✅ Активна';
    return '❌ Неактивна';
  },

  /**
   * Получить метку приоритета
   */
  getPriorityLabel(priority: number): string {
    const labels: Record<number, string> = {
      1: '🔴 Экстренный',
      2: '🟠 Высокий',
      3: '🟡 Повышенный',
      4: '🟢 Средний',
      5: '🔵 Обычный',
      6: '⚪ Низкий',
      7: '⚪ Очень низкий',
      8: '⚪ Минимальный',
      9: '⚪ Неважный',
      10: '⚪ Последний',
    };
    return labels[priority] || `Приоритет ${priority}`;
  },

  /**
   * Получить цвет приоритета
   */
  getPriorityColor(priority: number): string {
    if (priority <= 2) return '#e74c3c';
    if (priority <= 4) return '#e67e22';
    if (priority <= 6) return '#3498db';
    return '#95a5a6';
  },

  /**
   * Форматировать количество участников
   */
  formatMemberCount(count: number): string {
    if (count === 0) return 'Нет участников';
    
    const forms = ['участник', 'участника', 'участников'];
    const mod10 = count % 10;
    const mod100 = count % 100;
    
    let formIndex = 2; // множественное
    if (mod100 >= 11 && mod100 <= 19) {
      formIndex = 2;
    } else if (mod10 === 1) {
      formIndex = 0;
    } else if (mod10 >= 2 && mod10 <= 4) {
      formIndex = 1;
    }
    
    return `${count} ${forms[formIndex]}`;
  },
};

export default groupService;
