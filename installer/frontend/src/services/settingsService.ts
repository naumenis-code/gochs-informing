import api from './api';

export interface PBXSettings {
  host: string;
  port: number;
  extension: string;
  username: string;
  password: string;
  transport: 'udp' | 'tcp' | 'tls';
  max_channels: number;
  codecs: string[];
  register_enabled: boolean;
}

export interface SystemSettings {
  app_name: string;
  timezone: string;
  log_level: string;
  max_concurrent_calls: number;
  recording_retention_days: number;
  backup_enabled: boolean;
  backup_time: string;
}

export interface SecuritySettings {
  jwt_expire_minutes: number;
  refresh_token_expire_days: number;
  max_login_attempts: number;
  lockout_minutes: number;
  password_min_length: number;
  require_special_chars: boolean;
  session_timeout_minutes: number;
}

export interface NotificationSettings {
  email_enabled: boolean;
  smtp_server: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  from_email: string;
  admin_email: string;
  notify_on_campaign_complete: boolean;
  notify_on_system_error: boolean;
}

export const settingsService = {
  // PBX Settings
  async getPBXSettings(): Promise<PBXSettings> {
    const response = await api.get('/settings/pbx');
    return response.data;
  },

  async updatePBXSettings(data: Partial<PBXSettings>): Promise<PBXSettings> {
    const response = await api.put('/settings/pbx', data);
    return response.data;
  },

  async checkPBXStatus(): Promise<{ registered: boolean; message?: string }> {
    const response = await api.get('/settings/pbx/status');
    return response.data;
  },

  async testPBXConnection(data: PBXSettings): Promise<{ success: boolean; error?: string }> {
    const response = await api.post('/settings/pbx/test', data);
    return response.data;
  },

  async reloadAsteriskConfig(): Promise<void> {
    await api.post('/settings/pbx/reload');
  },

  // System Settings
  async getSystemSettings(): Promise<SystemSettings> {
    const response = await api.get('/settings/system');
    return response.data;
  },

  async updateSystemSettings(data: Partial<SystemSettings>): Promise<SystemSettings> {
    const response = await api.put('/settings/system', data);
    return response.data;
  },

  // Security Settings
  async getSecuritySettings(): Promise<SecuritySettings> {
    const response = await api.get('/settings/security');
    return response.data;
  },

  async updateSecuritySettings(data: Partial<SecuritySettings>): Promise<SecuritySettings> {
    const response = await api.put('/settings/security', data);
    return response.data;
  },

  // Notification Settings
  async getNotificationSettings(): Promise<NotificationSettings> {
    const response = await api.get('/settings/notifications');
    return response.data;
  },

  async updateNotificationSettings(data: Partial<NotificationSettings>): Promise<NotificationSettings> {
    const response = await api.put('/settings/notifications', data);
    return response.data;
  },

  // Backup
  async createBackup(): Promise<{ backup_id: string; created_at: string }> {
    const response = await api.post('/settings/backup');
    return response.data;
  },

  async restoreBackup(backupId: string): Promise<void> {
    await api.post(`/settings/backup/${backupId}/restore`);
  },

  async listBackups(): Promise<Array<{ id: string; created_at: string; size: number }>> {
    const response = await api.get('/settings/backups');
    return response.data;
  },
};
