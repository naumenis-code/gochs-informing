/**
 * API Сервис для управления плейбуками ГО-ЧС Информирование
 * Соответствует ТЗ, раздел 19: Playbook входящих звонков
 * 
 * Базовый URL: /api/v1/playbooks
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

/** Источник приветствия */
export type GreetingSource = 'tts' | 'uploaded' | 'none';

/** Категория плейбука */
export type PlaybookCategory = 'общий' | 'экстренный' | 'тестовый' | 'короткий' | 'информационный' | 'ночной';

/** Статус плейбука */
export type PlaybookStatus = 'active' | 'inactive' | 'template' | 'archived';

/** Действие со статусом */
export type StatusAction = 'activate' | 'deactivate' | 'archive' | 'restore' | 'make_template';

/** Аудиофайл плейбука */
export interface AudioFileInfo {
  type: 'greeting' | 'post_beep' | 'closing';
  path: string;
  label: string;
}

/** Полная информация о плейбуке */
export interface PlaybookDetail {
  id: string;
  name: string;
  description: string | null;
  category: PlaybookCategory | null;
  
  // Содержимое
  greeting_text: string | null;
  greeting_audio_path: string | null;
  greeting_source: GreetingSource;
  post_beep_text: string | null;
  post_beep_audio_path: string | null;
  closing_text: string | null;
  closing_audio_path: string | null;
  
  // Настройки
  beep_duration: number;
  pause_before_beep: number;
  max_recording_duration: number;
  min_recording_duration: number;
  greeting_repeat: number;
  repeat_interval: number;
  total_duration: number;
  
  // Язык
  language: string;
  tts_voice: string | null;
  tts_speed: number;
  
  // Статус
  is_active: boolean;
  is_archived: boolean;
  is_template: boolean;
  version: number;
  
  // Статистика
  usage_count: number;
  last_used_at: string | null;
  
  // Аудит
  created_by: string | null;
  updated_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  
  // Аудиофайлы
  audio_files: AudioFileInfo[];
}

/** Краткая информация о плейбуке (для списков) */
export interface PlaybookListItem {
  id: string;
  name: string;
  category: string | null;
  greeting_source: GreetingSource;
  is_active: boolean;
  is_template: boolean;
  version: number;
  usage_count: number;
  total_duration: number;
  created_at: string | null;
}

/** Данные для создания плейбука */
export interface PlaybookCreateData {
  name: string;
  description?: string;
  category?: PlaybookCategory;
  greeting_text?: string;
  greeting_source?: GreetingSource;
  post_beep_text?: string;
  closing_text?: string;
  beep_duration?: number;
  pause_before_beep?: number;
  max_recording_duration?: number;
  min_recording_duration?: number;
  greeting_repeat?: number;
  repeat_interval?: number;
  language?: string;
  tts_voice?: string;
  tts_speed?: number;
  is_template?: boolean;
  is_active?: boolean;
}

/** Данные для обновления плейбука */
export interface PlaybookUpdateData {
  name?: string;
  description?: string;
  category?: PlaybookCategory;
  greeting_text?: string;
  greeting_source?: GreetingSource;
  post_beep_text?: string;
  closing_text?: string;
  beep_duration?: number;
  pause_before_beep?: number;
  max_recording_duration?: number;
  min_recording_duration?: number;
  greeting_repeat?: number;
  repeat_interval?: number;
  language?: string;
  tts_voice?: string;
  tts_speed?: number;
  is_template?: boolean;
}

/** Данные для изменения статуса */
export interface PlaybookStatusUpdate {
  action: StatusAction;
  reason?: string;
}

/** Данные для TTS генерации */
export interface TTSGenerateData {
  text: string;
  voice?: string;
  speed?: number;
  output_filename?: string;
  overwrite?: boolean;
}

/** Результат TTS генерации */
export interface TTSGenerateResult {
  success: boolean;
  audio_path: string | null;
  duration_seconds: number | null;
  sample_rate: number | null;
  channels: number | null;
  bit_depth: number | null;
  file_size_bytes: number | null;
  text_length: number;
  voice: string;
  speed: number;
  message: string | null;
  generated_at: string;
}

/** Результат загрузки аудио */
export interface AudioUploadResult {
  audio_path: string;
  original_filename: string;
  file_size_bytes: number;
  format: string;
  duration_seconds: number | null;
  sample_rate: number | null;
  channels: number | null;
  bit_depth: number | null;
  uploaded_at: string;
  converted: boolean;
}

/** Данные для клонирования */
export interface PlaybookCloneData {
  new_name: string;
  copy_audio_files?: boolean;
  make_active?: boolean;
}

/** Данные для тестирования */
export interface PlaybookTestData {
  test_number: string;
  test_type?: 'full' | 'greeting_only' | 'beep_only';
}

/** Результат тестирования */
export interface PlaybookTestResult {
  success: boolean;
  call_sid: string | null;
  test_number: string;
  playbook_name: string;
  test_type: string;
  greeting_source: string;
  greeting_audio_path: string | null;
  greeting_duration: number;
  duration_seconds: number | null;
  recording_path: string | null;
  message: string | null;
  tested_at: string;
}

/** Параметры фильтрации плейбуков */
export interface PlaybookFilterParams extends PaginationParams {
  search?: string;
  category?: PlaybookCategory;
  is_active?: boolean;
  is_template?: boolean;
  greeting_source?: GreetingSource;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
}

/** Статистика по плейбукам */
export interface PlaybookStats {
  total: number;
  active: number;
  inactive: number;
  templates: number;
  by_category: Record<string, number>;
  by_source: Record<string, number>;
  most_used: {
    id: string | null;
    name: string | null;
    usage_count: number;
  } | null;
  active_playbook: {
    id: string;
    name: string;
    greeting_source: string;
    version: number;
    usage_count: number;
    has_audio: boolean;
  } | null;
}

// ============================================================================
// КОНСТАНТЫ
// ============================================================================

/** Категории плейбуков с иконками и цветами */
export const PLAYBOOK_CATEGORIES: Array<{
  value: PlaybookCategory;
  label: string;
  color: string;
  icon: string;
}> = [
  { value: 'общий', label: 'Общий', color: '#3498db', icon: '📞' },
  { value: 'экстренный', label: 'Экстренный', color: '#e74c3c', icon: '🚨' },
  { value: 'тестовый', label: 'Тестовый', color: '#f1c40f', icon: '🧪' },
  { value: 'короткий', label: 'Короткий', color: '#2ecc71', icon: '⚡' },
  { value: 'информационный', label: 'Информационный', color: '#9b59b6', icon: 'ℹ️' },
  { value: 'ночной', label: 'Ночной режим', color: '#34495e', icon: '🌙' },
];

/** Доступные голоса TTS */
export const TTS_VOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: 'ru_male', label: '👨 Мужской (русский)' },
  { value: 'ru_female', label: '👩 Женский (русский)' },
  { value: 'ru_male_deep', label: '👨 Мужской низкий (русский)' },
  { value: 'ru_female_soft', label: '👩 Женский мягкий (русский)' },
];

/** Шаблоны плейбуков */
export const PLAYBOOK_TEMPLATES: Record<string, { name: string; category: string; description: string }> = {
  default: {
    name: 'Стандартное приветствие',
    category: 'общий',
    description: 'Полное приветствие с инструкцией для звонящего',
  },
  emergency: {
    name: 'Экстренное оповещение',
    category: 'экстренный',
    description: 'Короткое экстренное сообщение с повтором',
  },
  short: {
    name: 'Короткое приветствие',
    category: 'короткий',
    description: 'Минимальное приветствие для быстрой записи',
  },
};

// ============================================================================
// API СЕРВИС
// ============================================================================

export const playbookService = {
  // =========================================================================
  // ПОЛУЧЕНИЕ СПИСКА
  // =========================================================================

  /**
   * Получить список плейбуков с фильтрацией
   */
  async getPlaybooks(params: PlaybookFilterParams = {}): Promise<PaginatedResponse<PlaybookListItem>> {
    const response: AxiosResponse<PaginatedResponse<PlaybookListItem>> = await api.get('/playbooks/', { params });
    return response.data;
  },

  /**
   * Получить активный плейбук
   */
  async getActivePlaybook(): Promise<PlaybookDetail> {
    const response: AxiosResponse<PlaybookDetail> = await api.get('/playbooks/active');
    return response.data;
  },

  /**
   * Получить плейбук по ID
   */
  async getPlaybook(playbookId: string): Promise<PlaybookDetail> {
    const response: AxiosResponse<PlaybookDetail> = await api.get(`/playbooks/${playbookId}`);
    return response.data;
  },

  /**
   * Скачать аудиофайл плейбука
   */
  async downloadAudio(playbookId: string, audioType: 'greeting' | 'post_beep' | 'closing'): Promise<Blob> {
    const response = await api.get(`/playbooks/${playbookId}/audio/${audioType}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // =========================================================================
  // СОЗДАНИЕ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ
  // =========================================================================

  /**
   * Создать новый плейбук
   * Требует роль: admin
   */
  async createPlaybook(data: PlaybookCreateData): Promise<PlaybookDetail> {
    const response: AxiosResponse<PlaybookDetail> = await api.post('/playbooks/', data);
    return response.data;
  },

  /**
   * Создать плейбук из шаблона
   * Требует роль: admin
   */
  async createFromTemplate(templateName: string): Promise<PlaybookDetail> {
    const response: AxiosResponse<PlaybookDetail> = await api.post(`/playbooks/from-template/${templateName}`);
    return response.data;
  },

  /**
   * Обновить плейбук
   * Требует роль: admin
   */
  async updatePlaybook(playbookId: string, data: PlaybookUpdateData): Promise<PlaybookDetail> {
    const response: AxiosResponse<PlaybookDetail> = await api.patch(`/playbooks/${playbookId}`, data);
    return response.data;
  },

  /**
   * Изменить статус плейбука
   * Требует роль: admin
   */
  async changeStatus(playbookId: string, data: PlaybookStatusUpdate): Promise<PlaybookDetail> {
    const response: AxiosResponse<PlaybookDetail> = await api.post(`/playbooks/${playbookId}/status`, data);
    return response.data;
  },

  /**
   * Удалить/архивировать плейбук
   * Требует роль: admin
   */
  async deletePlaybook(playbookId: string, hardDelete: boolean = false): Promise<{ message: string; success: boolean }> {
    const response = await api.delete(`/playbooks/${playbookId}`, {
      params: { hard_delete: hardDelete }
    });
    return response.data;
  },

  // =========================================================================
  // TTS ГЕНЕРАЦИЯ
  // =========================================================================

  /**
   * Сгенерировать аудио через TTS
   * Требует роль: admin
   */
  async generateTTS(playbookId: string, data: TTSGenerateData): Promise<TTSGenerateResult> {
    const response: AxiosResponse<TTSGenerateResult> = await api.post(
      `/playbooks/${playbookId}/generate-tts`,
      data
    );
    return response.data;
  },

  // =========================================================================
  // ЗАГРУЗКА АУДИО
  // =========================================================================

  /**
   * Загрузить аудиофайл для плейбука
   * Требует роль: admin
   */
  async uploadAudio(
    playbookId: string,
    file: File,
    audioType: 'greeting' | 'post_beep' | 'closing' = 'greeting',
    autoConvert: boolean = true,
    onProgress?: (progress: number) => void
  ): Promise<AudioUploadResult> {
    const formData = new FormData();
    formData.append('file', file);

    const params: Record<string, any> = {
      audio_type: audioType,
      auto_convert: autoConvert,
    };

    const response: AxiosResponse<AudioUploadResult> = await api.post(
      `/playbooks/${playbookId}/upload-audio`,
      formData,
      {
        params,
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent: AxiosProgressEvent) => {
          if (onProgress && progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(percent);
          }
        },
      }
    );

    return response.data;
  },

  // =========================================================================
  // КЛОНИРОВАНИЕ
  // =========================================================================

  /**
   * Клонировать плейбук
   * Требует роль: admin
   */
  async clonePlaybook(playbookId: string, data: PlaybookCloneData): Promise<PlaybookDetail> {
    const response: AxiosResponse<PlaybookDetail> = await api.post(`/playbooks/${playbookId}/clone`, data);
    return response.data;
  },

  // =========================================================================
  // ТЕСТИРОВАНИЕ
  // =========================================================================

  /**
   * Тестировать плейбук (тестовый звонок)
   * Требует роль: admin
   */
  async testPlaybook(playbookId: string, data: PlaybookTestData): Promise<PlaybookTestResult> {
    const response: AxiosResponse<PlaybookTestResult> = await api.post(`/playbooks/${playbookId}/test`, data);
    return response.data;
  },

  // =========================================================================
  // СТАТИСТИКА
  // =========================================================================

  /**
   * Получить статистику по плейбукам
   */
  async getPlaybookStats(): Promise<PlaybookStats> {
    const response: AxiosResponse<PlaybookStats> = await api.get('/playbooks/stats/summary');
    return response.data;
  },

  // =========================================================================
  // ВСПОМОГАТЕЛЬНЫЕ
  // =========================================================================

  /**
   * Получить список категорий
   */
  getCategories(): Array<{ value: string; label: string; color: string; icon: string }> {
    return PLAYBOOK_CATEGORIES;
  },

  /**
   * Получить список голосов TTS
   */
  getTTSVoices(): Array<{ value: string; label: string }> {
    return TTS_VOICES;
  },

  /**
   * Получить список шаблонов
   */
  getTemplates(): Record<string, { name: string; category: string; description: string }> {
    return PLAYBOOK_TEMPLATES;
  },

  /**
   * Скачать аудиофайл и сохранить
   */
  async downloadAndSaveAudio(
    playbookId: string,
    audioType: 'greeting' | 'post_beep' | 'closing',
    playbookName: string
  ): Promise<void> {
    const blob = await this.downloadAudio(playbookId, audioType);
    
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    const safeName = playbookName.replace(/[^a-zA-Z0-9а-яА-Я]/g, '_').slice(0, 50);
    link.download = `playbook_${safeName}_${audioType}.wav`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Воспроизвести аудиофайл (создает временный URL)
   */
  async playAudio(playbookId: string, audioType: 'greeting' | 'post_beep' | 'closing'): Promise<string> {
    const blob = await this.downloadAudio(playbookId, audioType);
    return window.URL.createObjectURL(blob);
  },

  /**
   * Проверить допустимый формат аудиофайла
   */
  validateAudioFile(file: File): { valid: boolean; error?: string } {
    const allowedExtensions = ['.wav', '.mp3', '.ogg', '.flac'];
    const allowedMimeTypes = [
      'audio/wav', 'audio/wave', 'audio/x-wav',
      'audio/mpeg', 'audio/mp3',
      'audio/ogg', 'audio/vorbis',
      'audio/flac', 'audio/x-flac',
    ];
    
    const fileName = file.name.toLowerCase();
    const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
    const hasValidMime = allowedMimeTypes.some(mime => file.type === mime);
    
    if (!hasValidExtension && !hasValidMime) {
      return {
        valid: false,
        error: `Неподдерживаемый формат. Допустимые: WAV, MP3, OGG, FLAC`
      };
    }

    const maxSize = 50 * 1024 * 1024; // 50 МБ
    if (file.size > maxSize) {
      return {
        valid: false,
        error: `Размер файла (${(file.size / (1024 * 1024)).toFixed(1)} МБ) превышает максимальный (50 МБ)`
      };
    }

    return { valid: true };
  },

  /**
   * Получить цвет для источника приветствия
   */
  getSourceColor(source: GreetingSource): string {
    const colors: Record<GreetingSource, string> = {
      tts: '#9b59b6',
      uploaded: '#3498db',
      none: '#95a5a6',
    };
    return colors[source] || '#95a5a6';
  },

  /**
   * Получить иконку для источника приветствия
   */
  getSourceIcon(source: GreetingSource): string {
    const icons: Record<GreetingSource, string> = {
      tts: '🎤',
      uploaded: '📁',
      none: '⊘',
    };
    return icons[source] || '❓';
  },

  /**
   * Получить текст статуса
   */
  getStatusText(isActive: boolean, isArchived: boolean, isTemplate: boolean): string {
    if (isArchived) return '📦 Архив';
    if (isActive) return '✅ Активен';
    if (isTemplate) return '📋 Шаблон';
    return '❌ Неактивен';
  },

  /**
   * Получить цвет статуса
   */
  getStatusColor(isActive: boolean, isArchived: boolean, isTemplate: boolean): string {
    if (isArchived) return '#e74c3c';
    if (isActive) return '#2ecc71';
    if (isTemplate) return '#3498db';
    return '#95a5a6';
  },

  /**
   * Форматировать длительность (секунды → MM:SS)
   */
  formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  },

  /**
   * Проверка номера телефона для тестового звонка
   */
  validateTestPhone(phone: string): { valid: boolean; error?: string } {
    const cleaned = phone.replace(/[\s\-\(\)]/g, '');
    
    if (!cleaned) {
      return { valid: false, error: 'Номер не может быть пустым' };
    }

    if (/^(\+7|8|7)?\d{10}$/.test(cleaned)) {
      return { valid: true };
    }

    return {
      valid: false,
      error: 'Неверный формат. Ожидается: +7XXXXXXXXXX или 8XXXXXXXXXX'
    };
  },
};

export default playbookService;
