import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Slider, Space, Typography, Tooltip, Spin, message } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  DownloadOutlined,
  SoundOutlined,
  LoadingOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { playbookService } from '@services/playbookService';

const { Text } = Typography;

// ============================================================================
// ТИПЫ
// ============================================================================

export type AudioSourceType = 'url' | 'blob' | 'playbook' | 'file';

export interface AudioSource {
  type: AudioSourceType;
  /** URL для воспроизведения */
  url?: string;
  /** Blob с аудио */
  blob?: Blob;
  /** ID плейбука и тип аудио */
  playbookId?: string;
  playbookAudioType?: 'greeting' | 'post_beep' | 'closing';
  /** File объект */
  file?: File;
  /** Название файла для скачивания */
  filename?: string;
}

export interface AudioPlayerProps {
  /** Источник аудио */
  source?: AudioSource;
  /** Автоматически начинать воспроизведение */
  autoPlay?: boolean;
  /** Показывать кнопку скачивания */
  showDownload?: boolean;
  /** Показывать регулятор громкости */
  showVolume?: boolean;
  /** Показывать длительность */
  showDuration?: boolean;
  /** Компактный режим (только кнопка play/pause) */
  compact?: boolean;
  /** Размер кнопок */
  size?: 'small' | 'middle' | 'large';
  /** Callback при начале воспроизведения */
  onPlay?: () => void;
  /** Callback при паузе */
  onPause?: () => void;
  /** Callback при завершении */
  onEnded?: () => void;
  /** Callback при ошибке */
  onError?: (error: Error) => void;
  /** Дополнительный className */
  className?: string;
  /** Дополнительные стили */
  style?: React.CSSProperties;
}

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

const AudioPlayer: React.FC<AudioPlayerProps> = ({
  source,
  autoPlay = false,
  showDownload = true,
  showVolume = true,
  showDuration = true,
  compact = false,
  size = 'middle',
  onPlay,
  onPause,
  onEnded,
  onError,
  className,
  style,
}) => {
  // =========================================================================
  // СОСТОЯНИЕ
  // =========================================================================
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // =========================================================================
  // ЗАГРУЗКА АУДИО
  // =========================================================================

  const loadAudio = useCallback(async () => {
    if (!source) return;

    setIsLoading(true);
    setError(null);

    try {
      let url: string | null = null;

      switch (source.type) {
        case 'url':
          url = source.url || null;
          break;

        case 'blob':
          if (source.blob) {
            url = URL.createObjectURL(source.blob);
          }
          break;

        case 'playbook':
          if (source.playbookId && source.playbookAudioType) {
            const blob = await playbookService.downloadAudio(
              source.playbookId,
              source.playbookAudioType
            );
            url = URL.createObjectURL(blob);
          }
          break;

        case 'file':
          if (source.file) {
            url = URL.createObjectURL(source.file);
          }
          break;

        default:
          throw new Error('Неизвестный тип источника аудио');
      }

      if (url) {
        // Очищаем предыдущий URL
        if (audioUrl) {
          URL.revokeObjectURL(audioUrl);
        }
        setAudioUrl(url);
      } else {
        throw new Error('Не удалось получить URL аудио');
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Ошибка загрузки аудио';
      setError(errorMsg);
      message.error(errorMsg);
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  }, [source, audioUrl, onError]);

  // Загрузка при изменении источника
  useEffect(() => {
    loadAudio();

    return () => {
      // Очистка URL при размонтировании
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [source?.url, source?.blob, source?.playbookId, source?.file]);

  // =========================================================================
  // УПРАВЛЕНИЕ ВОСПРОИЗВЕДЕНИЕМ
  // =========================================================================

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch((err) => {
        message.error('Ошибка воспроизведения');
        onError?.(err);
      });
    }
  }, [isPlaying, audioUrl, onError]);

  const handlePlay = () => {
    setIsPlaying(true);
    onPlay?.();
  };

  const handlePause = () => {
    setIsPlaying(false);
    onPause?.();
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
    onEnded?.();
  };

  const handleTimeUpdate = () => {
    const audio = audioRef.current;
    if (audio) {
      setCurrentTime(audio.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    const audio = audioRef.current;
    if (audio) {
      setDuration(audio.duration);
    }
  };

  const handleError = (e: React.SyntheticEvent<HTMLAudioElement>) => {
    const errorMsg = 'Ошибка загрузки аудиофайла';
    setError(errorMsg);
    message.error(errorMsg);
    onError?.(new Error(errorMsg));
  };

  // =========================================================================
  // УПРАВЛЕНИЕ ГРОМКОСТЬЮ
  // =========================================================================

  const handleVolumeChange = (value: number) => {
    const audio = audioRef.current;
    if (audio) {
      audio.volume = value;
      setVolume(value);
    }
  };

  // =========================================================================
  // ПЕРЕМОТКА
  // =========================================================================

  const handleSeek = (value: number) => {
    const audio = audioRef.current;
    if (audio) {
      audio.currentTime = value;
      setCurrentTime(value);
    }
  };

  // =========================================================================
  // СКАЧИВАНИЕ
  // =========================================================================

  const handleDownload = () => {
    if (!audioUrl) return;

    const link = document.createElement('a');
    link.href = audioUrl;
    link.download = source?.filename || 'audio.wav';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // =========================================================================
  // ФОРМАТИРОВАНИЕ ВРЕМЕНИ
  // =========================================================================

  const formatTime = (seconds: number): string => {
    if (isNaN(seconds)) return '0:00';

    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // =========================================================================
  // РЕНДЕР
  // =========================================================================

  // Компактный режим
  if (compact) {
    return (
      <Space size="small" className={className} style={style}>
        {audioUrl && (
          <audio
            ref={audioRef}
            src={audioUrl}
            onPlay={handlePlay}
            onPause={handlePause}
            onEnded={handleEnded}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onError={handleError}
            autoPlay={autoPlay}
            preload="metadata"
          />
        )}

        {isLoading ? (
          <Spin indicator={<LoadingOutlined />} size="small" />
        ) : error ? (
          <Tooltip title={error}>
            <CloseOutlined style={{ color: '#e74c3c' }} />
          </Tooltip>
        ) : (
          <Button
            type={isPlaying ? 'primary' : 'default'}
            shape="circle"
            size="small"
            icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={togglePlay}
            disabled={!audioUrl}
          />
        )}
      </Space>
    );
  }

  // Полный режим
  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 12px',
        background: '#f8f9fa',
        borderRadius: 8,
        border: '1px solid #e9ecef',
        ...style,
      }}
    >
      {/* Скрытый audio элемент */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onPlay={handlePlay}
          onPause={handlePause}
          onEnded={handleEnded}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onError={handleError}
          autoPlay={autoPlay}
          preload="metadata"
        />
      )}

      {/* Кнопка Play/Pause */}
      {isLoading ? (
        <Spin indicator={<LoadingOutlined />} size={size} />
      ) : (
        <Button
          type={isPlaying ? 'primary' : 'default'}
          shape="circle"
          size={size}
          icon={
            isPlaying ? (
              <PauseCircleOutlined style={{ fontSize: size === 'large' ? 24 : 18 }} />
            ) : (
              <PlayCircleOutlined style={{ fontSize: size === 'large' ? 24 : 18 }} />
            )
          }
          onClick={togglePlay}
          disabled={!audioUrl || !!error}
        />
      )}

      {/* Ползунок перемотки */}
      <div style={{ flex: 1, minWidth: 100 }}>
        <Slider
          min={0}
          max={duration || 100}
          value={currentTime}
          onChange={handleSeek}
          tooltip={{ formatter: (value) => formatTime(value || 0) }}
          disabled={!audioUrl || duration === 0}
          size={size}
        />
      </div>

      {/* Длительность */}
      {showDuration && (
        <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap', minWidth: 70, textAlign: 'center' }}>
          {formatTime(currentTime)} / {formatTime(duration)}
        </Text>
      )}

      {/* Регулятор громкости */}
      {showVolume && (
        <div style={{ width: 80, display: 'flex', alignItems: 'center', gap: 4 }}>
          <SoundOutlined style={{ fontSize: 14, color: '#8c8c8c' }} />
          <Slider
            min={0}
            max={1}
            step={0.1}
            value={volume}
            onChange={handleVolumeChange}
            size="small"
            style={{ margin: 0 }}
          />
        </div>
      )}

      {/* Кнопка скачивания */}
      {showDownload && (
        <Tooltip title="Скачать аудио">
          <Button
            type="text"
            size="small"
            icon={<DownloadOutlined />}
            onClick={handleDownload}
            disabled={!audioUrl}
          />
        </Tooltip>
      )}

      {/* Ошибка */}
      {error && (
        <Tooltip title={error}>
          <CloseOutlined style={{ color: '#e74c3c', fontSize: 16 }} />
        </Tooltip>
      )}
    </div>
  );
};

// ============================================================================
// ХУК ДЛЯ ПРОСТОГО ИСПОЛЬЗОВАНИЯ
// ============================================================================

export const useAudioPlayer = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const play = useCallback((url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    const audio = new Audio(url);
    audioRef.current = audio;

    audio.onplay = () => setIsPlaying(true);
    audio.onpause = () => setIsPlaying(false);
    audio.onended = () => {
      setIsPlaying(false);
      audioRef.current = null;
    };

    audio.play().catch(console.error);
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
      setIsPlaying(false);
    }
  }, []);

  return { isPlaying, play, stop };
};

export default AudioPlayer;
