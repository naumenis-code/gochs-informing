import api from './api';

// ============================================================================
// TYPES
// ============================================================================

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

export interface PBXStatusResponse {
  registered: boolean;
  message: string;
  host: string | null;
  port: number | null;
  extension: string | null;
}

export interface PBXTestResponse {
  success: boolean;
  message: string;
  error: string | null;
}

export interface PBXReloadResponse {
  message: string;
  success: boolean;
}

export interface PBXApplyResponse {
  message: string;
  config_updated: boolean;
  registration_status: PBXStatusResponse | null;
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

export interface AllSettingsResponse {
  pbx: PBXSettings;
  system: SystemSettings;
  security: SecuritySettings;
  notifications: NotificationSettings;
}

export interface CredentialsInfoResponse {
  freepbx: {
    host: string;
    port: number;
    extension: string;
    has_password: boolean;
  };
  postgresql: {
    database: string;
    user: string;
    has_password: boolean;
  };
  redis: {
    has_password: boolean;
  };
  asterisk: {
    ami_user: string;
    has_ami_password: boolean;
    has_ari_password: boolean;
  };
}

export interface BackupResponse {
  message: string;
  backup_file: string;
  timestamp: string;
}

export interface BackupListItem {
  name: string;
  size: number;
  created: string;
  path: string;
}

export interface BackupsListResponse {
  backups: BackupListItem[];
}

export interface ResetSettingsResponse {
  message: string;
  success: boolean;
}

// ============================================================================
// SERVICE
// ============================================================================

export const settingsService = {
  // ==========================================================================
  // PBX SETTINGS
  // ==========================================================================
  
  /**
   * Получение настроек FreePBX
   */
  async getPBXSettings(): Promise<PBXSettings> {
    const response = await api.get('/settings/pbx');
    return response.data;
  },

  /**
   * Обновление настроек FreePBX
   */
  async updatePBXSettings(data: Partial<PBXSettings>): Promise<PBXSettings> {
    const response = await api.put('/settings/pbx', data);
    return response.data;
  },

  /**
   * Проверка статуса регистрации в FreePBX
   */
  async checkPBXStatus(): Promise<PBXStatusResponse> {
    const response = await api.get('/settings/pbx/status');
    return response.data;
  },

  /**
   * Тестирование подключения к FreePBX
   */
  async testPBXConnection(data: Partial<PBXSettings>): Promise<PBXTestResponse> {
    const response = await api.post('/settings/pbx/test', data);
    return response.data;
  },

  /**
   * Перезагрузка конфигурации PJSIP
   */
  async reloadAsteriskConfig(): Promise<PBXReloadResponse> {
    const response = await api.post('/settings/pbx/reload');
    return response.data;
  },

  /**
   * Применение настроек к Asterisk (обновление pjsip.conf + перезагрузка)
   */
  async applyPBXSettings(): Promise<PBXApplyResponse> {
    const response = await api.post('/settings/pbx/apply');
    return response.data;
  },

  // ==========================================================================
  // SYSTEM SETTINGS
  // ==========================================================================

  /**
   * Получение системных настроек
   */
  async getSystemSettings(): Promise<SystemSettings> {
    const response = await api.get('/settings/system');
    return response.data;
  },

  /**
   * Обновление системных настроек
   */
  async updateSystemSettings(data: Partial<SystemSettings>): Promise<SystemSettings> {
    const response = await api.put('/settings/system', data);
    return response.data;
  },

  // ==========================================================================
  // SECURITY SETTINGS
  // ==========================================================================

  /**
   * Получение настроек безопасности
   */
  async getSecuritySettings(): Promise<SecuritySettings> {
    const response = await api.get('/settings/security');
    return response.data;
  },

  /**
   * Обновление настроек безопасности
   */
  async updateSecuritySettings(data: Partial<SecuritySettings>): Promise<SecuritySettings> {
    const response = await api.put('/settings/security', data);
    return response.data;
  },

  // ==========================================================================
  // NOTIFICATION SETTINGS
  // ==========================================================================

  /**
   * Получение настроек уведомлений
   */
  async getNotificationSettings(): Promise<NotificationSettings> {
    const response = await api.get('/settings/notifications');
    return response.data;
  },

  /**
   * Обновление настроек уведомлений
   */
  async updateNotificationSettings(data: Partial<NotificationSettings>): Promise<NotificationSettings> {
    const response = await api.put('/settings/notifications', data);
    return response.data;
  },

  // ==========================================================================
  // ALL SETTINGS
  // ==========================================================================

  /**
   * Получение всех настроек одним запросом
   */
  async getAllSettings(): Promise<AllSettingsResponse> {
    const response = await api.get('/settings/all');
    return response.data;
  },

  // ==========================================================================
  // CREDENTIALS
  // ==========================================================================

  /**
   * Получение информации об учетных данных (без паролей)
   */
  async getCredentialsInfo(): Promise<CredentialsInfoResponse> {
    const response = await api.get('/settings/credentials');
    return response.data;
  },

  // ==========================================================================
  // BACKUP
  // ==========================================================================

  /**
   * Создание резервной копии настроек
   */
  async createBackup(): Promise<BackupResponse> {
    const response = await api.post('/settings/backup');
    return response.data;
  },

  /**
   * Получение списка резервных копий
   */
  async listBackups(): Promise<BackupsListResponse> {
    const response = await api.get('/settings/backups');
    return response.data;
  },

  /**
   * Восстановление из резервной копии
   */
  async restoreBackup(backupPath: string): Promise<{ message: string; success: boolean }> {
    const response = await api.post('/settings/restore', { backup_path: backupPath });
    return response.data;
  },

  /**
   * Удаление резервной копии
   */
  async deleteBackup(backupName: string): Promise<{ message: string; success: boolean }> {
    const response = await api.delete(`/settings/backups/${backupName}`);
    return response.data;
  },

  // ==========================================================================
  // RESET
  // ==========================================================================

  /**
   * Сброс настроек к значениям по умолчанию
   */
  async resetSettings(): Promise<ResetSettingsResponse> {
    const response = await api.post('/settings/reset');
    return response.data;
  },

  // ==========================================================================
  // IMPORT/EXPORT
  // ==========================================================================

  /**
   * Экспорт настроек в файл
   */
  async exportSettings(): Promise<Blob> {
    const response = await api.get('/settings/export', {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Импорт настроек из файла
   */
  async importSettings(file: File): Promise<{ message: string; success: boolean }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/settings/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // ==========================================================================
  // VALIDATION
  // ==========================================================================

  /**
   * Проверка корректности настроек
   */
  async validateSettings(settings: Partial<AllSettingsResponse>): Promise<{
    valid: boolean;
    errors: Array<{ field: string; message: string }>;
  }> {
    const response = await api.post('/settings/validate', settings);
    return response.data;
  },
};

// ============================================================================
// EXPORT
// ============================================================================

export default settingsService;
