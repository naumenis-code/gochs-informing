/**
 * API Сервис для управления контактами ГО-ЧС Информирование
 * Соответствует ТЗ, раздел 10: Контактная база
 * 
 * Базовый URL: /api/v1/contacts
 */

import api from './api';
import type { AxiosResponse, AxiosProgressEvent } from 'axios';

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

/** Информация о группе контакта */
export interface ContactGroupInfo {
  id: string;
  name: string;
  color: string;
  added_at: string | null;
  role: string | null;
  priority: number;
}

/** Информация о теге контакта */
export interface ContactTagInfo {
  id: string;
  name: string;
  color: string;
  added_at: string | null;
}

/** Полная информация о контакте */
export interface ContactDetail {
  id: string;
  full_name: string;
  department: string | null;
  position: string | null;
  internal_number: string | null;
  mobile_number: string | null;
  email: string | null;
  is_active: boolean;
  is_archived: boolean;
  comment: string | null;
  groups: ContactGroupInfo[];
  tags: ContactTagInfo[];
  primary_phone: string | null;
  has_mobile: boolean;
  has_internal: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** Краткая информация о контакте (для списков) */
export interface ContactListItem {
  id: string;
  full_name: string;
  department: string | null;
  position: string | null;
  mobile_number: string | null;
  internal_number: string | null;
  email: string | null;
  is_active: boolean;
  group_names: string[];
  tag_names: string[];
  tag_colors: Record<string, string>;
  created_at: string | null;
}

/** Данные для создания контакта */
export interface ContactCreateData {
  full_name: string;
  department?: string;
  position?: string;
  internal_number?: string;
  mobile_number?: string;
  email?: string;
  is_active?: boolean;
  comment?: string;
  group_ids?: string[];
  tag_ids?: string[];
}

/** Данные для обновления контакта */
export interface ContactUpdateData {
  full_name?: string;
  department?: string;
  position?: string;
  internal_number?: string;
  mobile_number?: string;
  email?: string;
  is_active?: boolean;
  comment?: string;
}

/** Параметры фильтрации контактов */
export interface ContactFilterParams extends PaginationParams {
  search?: string;
  department?: string;
  is_active?: boolean;
  group_id?: string;
  tag_id?: string;
  has_mobile?: boolean;
  has_internal?: boolean;
  has_email?: boolean;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
}

/** Параметры импорта */
export interface ImportOptions {
  update_existing?: boolean;
  skip_duplicates?: boolean;
  default_group_id?: string;
  encoding?: string;
}

/** Результат массовой операции */
export interface BulkOperationResult {
  total_processed: number;
  success_count: number;
  error_count: number;
  skipped_count?: number;
  errors: Array<{
    row?: number;
    name?: string;
    contact_id?: string;
    error: string;
  }>;
  message: string;
}

/** Массовое действие */
export interface BulkActionData {
  contact_ids: string[];
  action: 'activate' | 'deactivate' | 'archive' | 'delete' | 'add_to_group' | 'remove_from_group' | 'add_tag' | 'remove_tag';
  group_id?: string;
  tag_id?: string;
  reason?: string;
}

/** Статистика по контактам */
export interface ContactStats {
  total: number;
  active: number;
  inactive: number;
  archived: number;
  with_mobile: number;
  with_internal: number;
  with_both: number;
  with_email: number;
  without_phone: number;
  by_department: Array<{ department: string; count: number }>;
  by_group: Array<{ group_name: string; count: number }>;
}

/** Параметры экспорта */
export interface ExportOptions {
  format?: 'csv' | 'xlsx' | 'json';
  fields?: string[];
  group_id?: string;
  include_archived?: boolean;
  encoding?: string;
}

// ============================================================================
// API СЕРВИС
// ============================================================================

export const contactService = {
  // =========================================================================
  // ПОЛУЧЕНИЕ СПИСКА
  // =========================================================================

  /**
   * Получить список контактов с фильтрацией
   */
  async getContacts(params: ContactFilterParams = {}): Promise<PaginatedResponse<ContactListItem>> {
    const response: AxiosResponse<PaginatedResponse<ContactListItem>> = await api.get('/contacts/', { params });
    return response.data;
  },

  /**
   * Получить контакт по ID
   */
  async getContact(contactId: string): Promise<ContactDetail> {
    const response: AxiosResponse<ContactDetail> = await api.get(`/contacts/${contactId}`);
    return response.data;
  },

  /**
   * Найти контакт по номеру телефона
   */
  async getContactByPhone(phone: string): Promise<ContactDetail> {
    const response: AxiosResponse<ContactDetail> = await api.get(`/contacts/by-phone/${encodeURIComponent(phone)}`);
    return response.data;
  },

  // =========================================================================
  // СОЗДАНИЕ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ
  // =========================================================================

  /**
   * Создать новый контакт
   */
  async createContact(data: ContactCreateData): Promise<ContactDetail> {
    const response: AxiosResponse<ContactDetail> = await api.post('/contacts/', data);
    return response.data;
  },

  /**
   * Обновить контакт
   */
  async updateContact(contactId: string, data: ContactUpdateData): Promise<ContactDetail> {
    const response: AxiosResponse<ContactDetail> = await api.patch(`/contacts/${contactId}`, data);
    return response.data;
  },

  /**
   * Удалить/архивировать контакт
   * Требует роль: admin
   */
  async deleteContact(contactId: string, hardDelete: boolean = false): Promise<{ message: string; success: boolean }> {
    const response = await api.delete(`/contacts/${contactId}`, {
      params: { hard_delete: hardDelete }
    });
    return response.data;
  },

  /**
   * Восстановить контакт из архива
   * Требует роль: admin
   */
  async restoreContact(contactId: string): Promise<{ message: string; success: boolean }> {
    const response = await api.post(`/contacts/${contactId}/restore`);
    return response.data;
  },

  // =========================================================================
  // ИМПОРТ / ЭКСПОРТ
  // =========================================================================

  /**
   * Импортировать контакты из файла (CSV/XLSX)
   * Требует роль: admin
   */
  async importContacts(
    file: File,
    options: ImportOptions = {},
    onProgress?: (progress: number) => void
  ): Promise<BulkOperationResult> {
    const formData = new FormData();
    formData.append('file', file);

    const params: Record<string, any> = {};
    if (options.update_existing !== undefined) params.update_existing = options.update_existing;
    if (options.skip_duplicates !== undefined) params.skip_duplicates = options.skip_duplicates;
    if (options.default_group_id) params.default_group_id = options.default_group_id;
    if (options.encoding) params.encoding = options.encoding;

    const response: AxiosResponse<BulkOperationResult> = await api.post('/contacts/import', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });

    return response.data;
  },

  /**
   * Экспортировать контакты
   */
  async exportContacts(options: ExportOptions = {}): Promise<Blob> {
    const params: Record<string, any> = {
      format: options.format || 'csv',
      encoding: options.encoding || 'utf-8',
    };

    if (options.fields && options.fields.length > 0) {
      params.fields = options.fields.join(',');
    }
    if (options.group_id) {
      params.group_id = options.group_id;
    }
    if (options.include_archived !== undefined) {
      params.include_archived = options.include_archived;
    }

    const response = await api.get('/contacts/export', {
      params,
      responseType: 'blob',
    });

    return response.data;
  },

  /**
   * Скачать шаблон для импорта
   */
  async downloadImportTemplate(format: 'csv' | 'xlsx' = 'csv'): Promise<Blob> {
    const response = await api.get('/contacts/import-template', {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },

  // =========================================================================
  // МАССОВЫЕ ОПЕРАЦИИ
  // =========================================================================

  /**
   * Массовое действие с контактами
   */
  async bulkAction(data: BulkActionData): Promise<BulkOperationResult> {
    const response: AxiosResponse<BulkOperationResult> = await api.post('/contacts/bulk-action', data);
    return response.data;
  },

  /**
   * Массовое удаление контактов
   * Требует роль: admin
   */
  async bulkDelete(
    contactIds: string[],
    hardDelete: boolean = false,
    reason?: string
  ): Promise<BulkOperationResult> {
    const response: AxiosResponse<BulkOperationResult> = await api.post('/contacts/bulk-delete', {
      contact_ids: contactIds,
      hard_delete: hardDelete,
      reason: reason,
    });
    return response.data;
  },

  // =========================================================================
  // СТАТИСТИКА
  // =========================================================================

  /**
   * Получить статистику по контактам
   */
  async getContactStats(): Promise<ContactStats> {
    const response: AxiosResponse<ContactStats> = await api.get('/contacts/stats/summary');
    return response.data;
  },

  // =========================================================================
  // ВСПОМОГАТЕЛЬНЫЕ
  // =========================================================================

  /**
   * Экспортировать и скачать файл
   */
  async exportAndDownload(options: ExportOptions = {}): Promise<void> {
    const format = options.format || 'csv';
    const blob = await this.exportContacts(options);
    
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const extensions: Record<string, string> = {
      csv: 'csv',
      xlsx: 'xlsx',
      json: 'json',
    };
    link.download = `contacts_export_${timestamp}.${extensions[format] || 'csv'}`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Скачать шаблон и сохранить
   */
  async downloadTemplate(format: 'csv' | 'xlsx' = 'csv'): Promise<void> {
    const blob = await this.downloadImportTemplate(format);
    
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `contacts_import_template.${format}`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Валидация номера телефона
   */
  validatePhone(phone: string): { valid: boolean; cleaned: string; error?: string } {
    // Удаляем пробелы, дефисы, скобки
    const cleaned = phone.replace(/[\s\-\(\)]/g, '');
    
    if (!cleaned) {
      return { valid: false, cleaned: '', error: 'Номер не может быть пустым' };
    }

    // Проверка форматов
    if (/^\+7\d{10}$/.test(cleaned)) {
      return { valid: true, cleaned };
    }
    if (/^8\d{10}$/.test(cleaned)) {
      return { valid: true, cleaned: '+7' + cleaned.slice(1) };
    }
    if (/^7\d{10}$/.test(cleaned)) {
      return { valid: true, cleaned: '+' + cleaned };
    }
    if (/^\d{10}$/.test(cleaned)) {
      return { valid: true, cleaned: '+7' + cleaned };
    }

    return {
      valid: false,
      cleaned,
      error: 'Неверный формат. Ожидается: +7XXXXXXXXXX или 8XXXXXXXXXX'
    };
  },

  /**
   * Валидация внутреннего номера
   */
  validateInternalNumber(number: string): { valid: boolean; cleaned: string; error?: string } {
    const cleaned = number.replace(/[\s\-]/g, '');
    
    if (!cleaned) {
      return { valid: true, cleaned: '' }; // Внутренний номер опционален
    }

    if (/^\d{3,4}$/.test(cleaned)) {
      return { valid: true, cleaned };
    }

    return {
      valid: false,
      cleaned,
      error: 'Внутренний номер должен содержать 3-4 цифры'
    };
  },

  /**
   * Форматирование номера телефона для отображения
   */
  formatPhone(phone: string | null): string {
    if (!phone) return '—';
    
    const cleaned = phone.replace(/[^\d+]/g, '');
    
    if (cleaned.startsWith('+7') && cleaned.length === 12) {
      return `+7 (${cleaned.slice(2, 5)}) ${cleaned.slice(5, 8)}-${cleaned.slice(8, 10)}-${cleaned.slice(10, 12)}`;
    }
    
    return phone;
  },

  /**
   * Получить цвет для статуса контакта
   */
  getStatusColor(isActive: boolean, isArchived: boolean): string {
    if (isArchived) return '#95a5a6';
    if (isActive) return '#2ecc71';
    return '#e74c3c';
  },

  /**
   * Получить текст статуса
   */
  getStatusText(isActive: boolean, isArchived: boolean): string {
    if (isArchived) return '📦 В архиве';
    if (isActive) return '✅ Активен';
    return '❌ Неактивен';
  },

  /**
   * Проверка допустимого формата файла для импорта
   */
  validateImportFile(file: File): { valid: boolean; error?: string } {
    const allowedExtensions = ['.csv', '.xlsx', '.xls'];
    const fileName = file.name.toLowerCase();
    
    const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
    if (!hasValidExtension) {
      return {
        valid: false,
        error: `Неподдерживаемый формат. Допустимые: ${allowedExtensions.join(', ')}`
      };
    }

    const maxSize = 10 * 1024 * 1024; // 10 МБ
    if (file.size > maxSize) {
      return {
        valid: false,
        error: `Размер файла (${(file.size / (1024 * 1024)).toFixed(1)} МБ) превышает максимальный (10 МБ)`
      };
    }

    return { valid: true };
  },
};

export default contactService;
