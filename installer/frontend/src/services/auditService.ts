import api from './api';

export interface AuditLog {
  id: string;
  user_id: string;
  user_name: string;
  user_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details: any;
  ip_address: string;
  user_agent: string;
  created_at: string;
  status: 'success' | 'warning' | 'error';
}

export interface AuditStats {
  total_events: number;
  today_events: number;
  unique_users: number;
  error_events: number;
  top_actions: Array<{ action: string; count: number }>;
  recent_activity: Array<{ time: string; description: string }>;
}

export interface AuditFilterParams {
  skip?: number;
  limit?: number;
  action?: string;
  entity_type?: string;
  user_name?: string;
  start_date?: string;
  end_date?: string;
}

export const auditService = {
  async getAuditLogs(params: AuditFilterParams): Promise<{ items: AuditLog[]; total: number }> {
    const response = await api.get('/audit/logs', { params });
    return response.data;
  },

  async getAuditStats(): Promise<AuditStats> {
    const response = await api.get('/audit/stats');
    return response.data;
  },

  async getAuditLog(id: string): Promise<AuditLog> {
    const response = await api.get(`/audit/logs/${id}`);
    return response.data;
  },

  async exportAuditLogs(filters: Partial<AuditFilterParams>): Promise<Blob> {
    const response = await api.get('/audit/export', {
      params: filters,
      responseType: 'blob',
    });
    return response.data;
  },

  async clearOldLogs(days: number = 90): Promise<void> {
    await api.delete('/audit/logs', { params: { older_than_days: days } });
  },

  async getUserActivity(userId: string): Promise<AuditLog[]> {
    const response = await api.get(`/audit/users/${userId}/activity`);
    return response.data;
  },
};
