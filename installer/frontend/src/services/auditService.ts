import api from './api';

// ============================================================================
// TYPES
// ============================================================================

export interface AuditLog {
  id: string;
  user_id: string | null;
  user_name: string | null;
  user_role: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  entity_name: string | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  user_agent: string | null;
  request_method: string | null;
  request_path: string | null;
  status: 'success' | 'warning' | 'error';
  error_message: string | null;
  execution_time_ms: number | null;
  created_at: string;
}

export interface AuditStats {
  total_events: number;
  today_events: number;
  week_events: number;
  month_events: number;
  unique_users: number;
  error_events: number;
  warning_events: number;
  success_events: number;
  top_actions: Array<{ action: string; count: number }>;
  top_entities: Array<{ entity_type: string; count: number }>;
  top_users: Array<{ user_name: string; user_role: string; count: number }>;
  recent_activity: Array<{
    time: string;
    user: string;
    action: string;
    entity_type: string;
    entity_name: string;
    status: string;
    ip_address: string;
    description: string;
  }>;
  hourly_stats?: Array<{ hour: number; count: number }>;
  daily_stats?: Array<{ date: string; total: number; success: number; warnings: number; errors: number }>;
}

export interface AuditLogsResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface AuditFilterParams {
  skip?: number;
  limit?: number;
  action?: string;
  entity_type?: string;
  user_name?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

export interface ClearOldLogsResponse {
  message: string;
  deleted_count: number;
  older_than_days: number;
  cutoff_date: string | null;
}

export interface UserActivityResponse {
  user_name: string;
  total_actions: number;
  first_action: string | null;
  last_action: string | null;
  actions_by_type: Record<string, number>;
  actions_by_entity: Record<string, number>;
  logs: AuditLog[];
}

export interface DailySummaryResponse {
  days: number;
  start_date: string;
  daily_stats: Array<{
    date: string;
    total: number;
    success: number;
    warnings: number;
    errors: number;
  }>;
}

export interface CreateAuditLogRequest {
  user_id?: string;
  user_name?: string;
  user_role?: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  entity_name?: string;
  details?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  status?: 'success' | 'warning' | 'error';
}

// ============================================================================
// SERVICE
// ============================================================================

export const auditService = {
  // ==========================================================================
  // LOGS
  // ==========================================================================

  /**
   * Получение списка записей аудита с фильтрацией
   */
  async getAuditLogs(params: AuditFilterParams): Promise<AuditLogsResponse> {
    const response = await api.get('/audit/logs', { params });
    return response.data;
  },

  /**
   * Получение детальной информации о записи аудита
   */
  async getAuditLog(id: string): Promise<AuditLog> {
    const response = await api.get(`/audit/logs/${id}`);
    return response.data;
  },

  /**
   * Создание записи аудита (для внутреннего использования)
   */
  async createAuditLog(data: CreateAuditLogRequest): Promise<{ success: boolean; message?: string }> {
    const response = await api.post('/audit/log', data);
    return response.data;
  },

  /**
   * Пакетное создание записей аудита
   */
  async createAuditLogsBatch(logs: CreateAuditLogRequest[]): Promise<{
    success: boolean;
    created_count: number;
    failed_count: number;
    errors: string[];
  }> {
    const response = await api.post('/audit/logs/batch', { logs });
    return response.data;
  },

  // ==========================================================================
  // STATISTICS
  // ==========================================================================

  /**
   * Получение статистики аудита
   */
  async getAuditStats(days?: number): Promise<AuditStats> {
    const params = days ? { days } : {};
    const response = await api.get('/audit/stats', { params });
    return response.data;
  },

  /**
   * Получение дневной сводки
   */
  async getDailySummary(days: number = 7): Promise<DailySummaryResponse> {
    const response = await api.get('/audit/summary/daily', { params: { days } });
    return response.data;
  },

  /**
   * Получение почасовой статистики
   */
  async getHourlyStats(date?: string): Promise<Array<{ hour: number; count: number }>> {
    const params = date ? { date } : {};
    const response = await api.get('/audit/stats/hourly', { params });
    return response.data;
  },

  // ==========================================================================
  // USER ACTIVITY
  // ==========================================================================

  /**
   * Получение активности конкретного пользователя
   */
  async getUserActivity(
    userName: string,
    limit: number = 50
  ): Promise<UserActivityResponse> {
    const response = await api.get(`/audit/users/${userName}/activity`, {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Получение списка активных пользователей
   */
  async getActiveUsers(days: number = 7): Promise<Array<{ user_name: string; count: number }>> {
    const response = await api.get('/audit/users/active', { params: { days } });
    return response.data;
  },

  // ==========================================================================
  // EXPORT
  // ==========================================================================

  /**
   * Экспорт журнала аудита в CSV
   */
  async exportAuditLogs(params: AuditFilterParams): Promise<Blob> {
    const response = await api.get('/audit/export', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Экспорт статистики в JSON
   */
  async exportAuditStats(days?: number): Promise<Blob> {
    const response = await api.get('/audit/stats/export', {
      params: { days },
      responseType: 'blob',
    });
    return response.data;
  },

  // ==========================================================================
  // CLEANUP
  // ==========================================================================

  /**
   * Удаление старых записей аудита
   */
  async clearOldLogs(olderThanDays: number = 90): Promise<ClearOldLogsResponse> {
    const response = await api.delete('/audit/logs', {
      params: { older_than_days: olderThanDays },
    });
    return response.data;
  },

  /**
   * Удаление записей по фильтру
   */
  async clearLogsByFilter(params: AuditFilterParams): Promise<{ deleted_count: number }> {
    const response = await api.delete('/audit/logs/filter', { params });
    return response.data;
  },

  // ==========================================================================
  // HEALTH
  // ==========================================================================

  /**
   * Проверка здоровья аудита (существует ли таблица, количество записей)
   */
  async getAuditHealth(): Promise<{
    table_exists: boolean;
    record_count: number;
    last_record_at: string | null;
    status: string;
  }> {
    const response = await api.get('/audit/health');
    return response.data;
  },

  /**
   * Проверка и создание таблицы аудита
   */
  async ensureAuditTable(): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/audit/ensure-table');
    return response.data;
  },

  // ==========================================================================
  // SEARCH
  // ==========================================================================

  /**
   * Поиск по всем полям аудита
   */
  async searchAuditLogs(
    query: string,
    limit: number = 100
  ): Promise<AuditLogsResponse> {
    const response = await api.get('/audit/search', {
      params: { q: query, limit },
    });
    return response.data;
  },

  // ==========================================================================
  // ACTIONS
  // ==========================================================================

  /**
   * Получение списка всех уникальных действий
   */
  async getUniqueActions(): Promise<string[]> {
    const response = await api.get('/audit/actions');
    return response.data;
  },

  /**
   * Получение списка всех уникальных типов сущностей
   */
  async getUniqueEntityTypes(): Promise<string[]> {
    const response = await api.get('/audit/entity-types');
    return response.data;
  },

  /**
   * Получение списка всех уникальных пользователей
   */
  async getUniqueUsers(): Promise<string[]> {
    const response = await api.get('/audit/users');
    return response.data;
  },

  // ==========================================================================
  // ANALYTICS
  // ==========================================================================

  /**
   * Получение аналитики по действиям за период
   */
  async getActionAnalytics(
    startDate: string,
    endDate: string
  ): Promise<Array<{ action: string; date: string; count: number }>> {
    const response = await api.get('/audit/analytics/actions', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },

  /**
   * Получение аналитики по пользователям за период
   */
  async getUserAnalytics(
    startDate: string,
    endDate: string
  ): Promise<Array<{ user_name: string; date: string; count: number }>> {
    const response = await api.get('/audit/analytics/users', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },

  /**
   * Получение тепловой карты активности по часам
   */
  async getActivityHeatmap(days: number = 7): Promise<{
    days: string[];
    hours: number[];
    data: number[][];
  }> {
    const response = await api.get('/audit/analytics/heatmap', {
      params: { days },
    });
    return response.data;
  },
};

// ============================================================================
// EXPORT
// ============================================================================

export default auditService;
