import React, { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Typography,
  Tag,
  Input,
  Select,
  Card,
  Modal,
  Form,
  message,
  Popconfirm,
  Tooltip,
  Row,
  Col,
  Statistic,
  Badge,
  Dropdown,
  Divider,
  Descriptions,
  Tabs,
  Upload,
  Slider,
  InputNumber,
  Switch,
  Progress,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import type { UploadFile, UploadProps } from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SoundOutlined,
  EyeOutlined,
  MoreOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  CopyOutlined,
  ExperimentOutlined,
  PhoneOutlined,
  AudioOutlined,
  RobotOutlined,
  UploadOutlined,
  FileAddOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import { playbookService, PLAYBOOK_CATEGORIES, TTS_VOICES } from '@services/playbookService';
import AudioPlayer from '@components/Common/AudioPlayer';
import type {
  PlaybookListItem,
  PlaybookDetail,
  PlaybookCreateData,
  PlaybookUpdateData,
  PlaybookFilterParams,
  PlaybookStats,
  TTSGenerateResult,
  AudioUploadResult,
  GreetingSource,
} from '@services/playbookService';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { Dragger } = Upload;
const { TabPane } = Tabs;

// ============================================================================
// КОНСТАНТЫ
// ============================================================================

const PAGE_SIZE = 15;
const DEFAULT_SORT_FIELD = 'created_at';
const DEFAULT_SORT_DIRECTION = 'desc';

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

const PlaybooksPage: React.FC = () => {
  // =========================================================================
  // СОСТОЯНИЕ
  // =========================================================================

  // Данные
  const [playbooks, setPlaybooks] = useState<PlaybookListItem[]>([]);
  const [totalPlaybooks, setTotalPlaybooks] = useState(0);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<PlaybookStats | null>(null);
  const [activePlaybook, setActivePlaybook] = useState<PlaybookDetail | null>(null);

  // Пагинация и сортировка
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [sortField, setSortField] = useState(DEFAULT_SORT_FIELD);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(DEFAULT_SORT_DIRECTION);

  // Фильтры
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);
  const [templateFilter, setTemplateFilter] = useState<boolean | undefined>(undefined);
  const [sourceFilter, setSourceFilter] = useState<GreetingSource | undefined>(undefined);

  // Модальные окна
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [ttsModalOpen, setTtsModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [selectedPlaybook, setSelectedPlaybook] = useState<PlaybookDetail | null>(null);

  // TTS
  const [ttsGenerating, setTtsGenerating] = useState(false);
  const [ttsResult, setTtsResult] = useState<TTSGenerateResult | null>(null);

  // Загрузка аудио
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [audioType, setAudioType] = useState<'greeting' | 'post_beep' | 'closing'>('greeting');

  // Формы
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [ttsForm] = Form.useForm();
  const [testForm] = Form.useForm();

  // =========================================================================
  // ЗАГРУЗКА ДАННЫХ
  // =========================================================================

  const loadPlaybooks = useCallback(async () => {
    setLoading(true);
    try {
      const params: PlaybookFilterParams = {
        page,
        page_size: pageSize,
        sort_field: sortField,
        sort_direction: sortDirection,
      };

      if (searchText) params.search = searchText;
      if (categoryFilter) params.category = categoryFilter as any;
      if (activeFilter !== undefined) params.is_active = activeFilter;
      if (templateFilter !== undefined) params.is_template = templateFilter;
      if (sourceFilter) params.greeting_source = sourceFilter;

      const response = await playbookService.getPlaybooks(params);
      setPlaybooks(response.items);
      setTotalPlaybooks(response.total);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка загрузки плейбуков');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, sortField, sortDirection, searchText, categoryFilter, activeFilter, templateFilter, sourceFilter]);

  const loadStats = useCallback(async () => {
    try {
      const data = await playbookService.getPlaybookStats();
      setStats(data);
      if (data.active_playbook) {
        try {
          const active = await playbookService.getActivePlaybook();
          setActivePlaybook(active);
        } catch {}
      } else {
        setActivePlaybook(null);
      }
    } catch {}
  }, []);

  useEffect(() => {
    loadPlaybooks();
  }, [loadPlaybooks]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // =========================================================================
  // ОБРАБОТЧИКИ ТАБЛИЦЫ
  // =========================================================================

  const handleTableChange = (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<PlaybookListItem> | SorterResult<PlaybookListItem>[]
  ) => {
    setPage(pagination.current || 1);
    setPageSize(pagination.pageSize || PAGE_SIZE);

    if (!Array.isArray(sorter) && sorter.field) {
      setSortField(sorter.field as string);
      setSortDirection(sorter.order === 'ascend' ? 'asc' : 'desc');
    }
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
    setPage(1);
  };

  const handleRefresh = () => {
    loadPlaybooks();
    loadStats();
  };

  // =========================================================================
  // ДЕЙСТВИЯ С ПЛЕЙБУКАМИ
  // =========================================================================

  const handleCreatePlaybook = async () => {
    try {
      const values = await createForm.validateFields();
      await playbookService.createPlaybook(values);
      message.success('Плейбук создан');
      setCreateModalOpen(false);
      createForm.resetFields();
      loadPlaybooks();
      loadStats();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка создания');
    }
  };

  const handleCreateFromTemplate = async (templateName: string) => {
    try {
      await playbookService.createFromTemplate(templateName);
      message.success('Плейбук создан из шаблона');
      loadPlaybooks();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleEditPlaybook = async () => {
    if (!selectedPlaybook) return;

    try {
      const values = await editForm.validateFields();
      await playbookService.updatePlaybook(selectedPlaybook.id, values);
      message.success('Плейбук обновлен');
      setEditModalOpen(false);
      setSelectedPlaybook(null);
      editForm.resetFields();
      loadPlaybooks();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка обновления');
    }
  };

  const handleChangeStatus = async (
    playbookId: string,
    action: 'activate' | 'deactivate' | 'archive' | 'restore' | 'make_template',
    name: string
  ) => {
    try {
      const reason = action === 'archive' ? 'Архивирование через веб-интерфейс' : undefined;
      await playbookService.changeStatus(playbookId, { action, reason });

      const messages: Record<string, string> = {
        activate: `Плейбук "${name}" активирован`,
        deactivate: `Плейбук "${name}" деактивирован`,
        archive: `Плейбук "${name}" архивирован`,
        restore: `Плейбук "${name}" восстановлен`,
        make_template: `Плейбук "${name}" преобразован в шаблон`,
      };
      message.success(messages[action] || 'Статус изменен');
      
      loadPlaybooks();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка изменения статуса');
    }
  };

  const handleDeletePlaybook = async (playbookId: string) => {
    try {
      await playbookService.deletePlaybook(playbookId, false);
      message.success('Плейбук архивирован');
      loadPlaybooks();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleClonePlaybook = async () => {
    if (!selectedPlaybook) return;

    Modal.confirm({
      title: 'Клонирование плейбука',
      content: (
        <Form layout="vertical">
          <Form.Item
            label="Название нового плейбука"
            required
          >
            <Input
              id="clone-name"
              defaultValue={`${selectedPlaybook.name} (копия)`}
              placeholder="Введите название"
            />
          </Form.Item>
        </Form>
      ),
      onOk: async () => {
        const input = document.getElementById('clone-name') as HTMLInputElement;
        const newName = input?.value || `${selectedPlaybook.name} (копия)`;

        try {
          await playbookService.clonePlaybook(selectedPlaybook.id, {
            new_name: newName,
            copy_audio_files: true,
            make_active: false,
          });
          message.success('Плейбук клонирован');
          loadPlaybooks();
          loadStats();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || 'Ошибка клонирования');
        }
      },
    });
  };

  const handleViewDetails = async (playbookId: string) => {
    try {
      const playbook = await playbookService.getPlaybook(playbookId);
      setSelectedPlaybook(playbook);
      setDetailModalOpen(true);
    } catch {
      message.error('Ошибка загрузки плейбука');
    }
  };

  const openEditModal = async (playbookId: string) => {
    try {
      const playbook = await playbookService.getPlaybook(playbookId);
      setSelectedPlaybook(playbook);
      editForm.setFieldsValue({
        name: playbook.name,
        description: playbook.description,
        category: playbook.category,
        greeting_text: playbook.greeting_text,
        greeting_source: playbook.greeting_source,
        post_beep_text: playbook.post_beep_text,
        closing_text: playbook.closing_text,
        beep_duration: playbook.beep_duration,
        pause_before_beep: playbook.pause_before_beep,
        max_recording_duration: playbook.max_recording_duration,
        min_recording_duration: playbook.min_recording_duration,
        greeting_repeat: playbook.greeting_repeat,
        repeat_interval: playbook.repeat_interval,
        language: playbook.language,
        tts_voice: playbook.tts_voice,
        tts_speed: playbook.tts_speed,
      });
      setEditModalOpen(true);
    } catch {
      message.error('Ошибка загрузки плейбука');
    }
  };

  const openTtsModal = async (playbookId: string) => {
    try {
      const playbook = await playbookService.getPlaybook(playbookId);
      setSelectedPlaybook(playbook);
      ttsForm.setFieldsValue({
        text: playbook.greeting_text || '',
        voice: playbook.tts_voice || 'ru_male',
        speed: playbook.tts_speed || 1.0,
      });
      setTtsResult(null);
      setTtsModalOpen(true);
    } catch {
      message.error('Ошибка загрузки плейбука');
    }
  };

  const handleGenerateTTS = async () => {
    if (!selectedPlaybook) return;

    try {
      const values = await ttsForm.validateFields();
      setTtsGenerating(true);

      const result = await playbookService.generateTTS(selectedPlaybook.id, {
        text: values.text,
        voice: values.voice,
        speed: values.speed,
      });

      setTtsResult(result);
      message.success('Аудио сгенерировано (8000 Гц, mono, 16-bit PCM)');
      loadPlaybooks();
      loadStats();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка генерации TTS');
    } finally {
      setTtsGenerating(false);
    }
  };

  const openUploadModal = (playbookId: string, type: 'greeting' | 'post_beep' | 'closing') => {
    setSelectedPlaybook(playbookId as any);
    setAudioType(type);
    setUploadFile(null);
    setUploadProgress(0);
    setUploading(false);
    setUploadModalOpen(true);
  };

  const handleUploadAudio = async () => {
    if (!selectedPlaybook || !uploadFile) return;

    setUploading(true);
    setUploadProgress(0);

    try {
      const result = await playbookService.uploadAudio(
        selectedPlaybook.id,
        uploadFile,
        audioType,
        true,
        (progress) => setUploadProgress(progress)
      );

      message.success(
        `Аудио загружено${result.converted ? ' и сконвертировано в формат Asterisk' : ''}`
      );
      setUploadModalOpen(false);
      loadPlaybooks();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setUploading(false);
    }
  };

  const handleTestPlaybook = async () => {
    if (!selectedPlaybook) return;

    try {
      const values = await testForm.validateFields();
      const result = await playbookService.testPlaybook(selectedPlaybook.id, {
        test_number: values.test_number,
        test_type: values.test_type || 'full',
      });

      if (result.success) {
        message.success(`Тестовый звонок на ${values.test_number} инициирован`);
        setTestModalOpen(false);
        testForm.resetFields();
      } else {
        message.error(result.message || 'Ошибка тестирования');
      }
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleDownloadAudio = async (playbookId: string, audioType: 'greeting' | 'post_beep' | 'closing', name: string) => {
    try {
      await playbookService.downloadAndSaveAudio(playbookId, audioType, name);
      message.success('Аудио скачано');
    } catch {
      message.error('Ошибка скачивания');
    }
  };

  // =========================================================================
  // КОЛОНКИ ТАБЛИЦЫ
  // =========================================================================

  const columns: ColumnsType<PlaybookListItem> = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      sorter: true,
      width: 280,
      render: (text: string, record: PlaybookListItem) => (
        <Space>
          {record.is_active ? (
            <PlayCircleOutlined style={{ color: '#2ecc71', fontSize: 18 }} />
          ) : record.is_template ? (
            <FileAddOutlined style={{ color: '#3498db', fontSize: 18 }} />
          ) : (
            <PauseCircleOutlined style={{ color: '#95a5a6', fontSize: 18 }} />
          )}
          <div>
            <div style={{ fontWeight: 500 }}>{text}</div>
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>
              v{record.version} | {playbookService.formatDuration(record.total_duration)}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'category',
      key: 'category',
      width: 140,
      filters: PLAYBOOK_CATEGORIES.map(c => ({ text: c.label, value: c.value })),
      render: (cat: string | null) => {
        const category = PLAYBOOK_CATEGORIES.find(c => c.value === cat);
        return category ? (
          <Tag color={category.color}>
            {category.icon} {category.label}
          </Tag>
        ) : (
          <Text type="secondary">—</Text>
        );
      },
    },
    {
      title: 'Источник',
      dataIndex: 'greeting_source',
      key: 'greeting_source',
      width: 130,
      filters: [
        { text: 'TTS (синтез)', value: 'tts' },
        { text: 'Загруженный файл', value: 'uploaded' },
        { text: 'Без приветствия', value: 'none' },
      ],
      render: (source: GreetingSource) => {
        const colors: Record<string, string> = { tts: '#9b59b6', uploaded: '#3498db', none: '#95a5a6' };
        const labels: Record<string, string> = { tts: '🎤 TTS', uploaded: '📁 Файл', none: '⊘ Нет' };
        return (
          <Tag color={colors[source] || '#95a5a6'}>
            {labels[source] || source}
          </Tag>
        );
      },
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean, record: PlaybookListItem) => (
        <Badge
          status={isActive ? 'success' : record.is_template ? 'processing' : 'default'}
          text={
            isActive ? 'Активен' :
            record.is_template ? 'Шаблон' : 'Неактивен'
          }
        />
      ),
    },
    {
      title: 'Использований',
      dataIndex: 'usage_count',
      key: 'usage_count',
      sorter: true,
      width: 120,
      align: 'center',
      render: (count: number) => (
        <Tag color={count > 0 ? 'blue' : 'default'}>
          {count || 0}
        </Tag>
      ),
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: true,
      width: 130,
      render: (text: string | null) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {text ? new Date(text).toLocaleDateString('ru-RU') : '—'}
        </Text>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 240,
      fixed: 'right',
      render: (_: any, record: PlaybookListItem) => (
        <Space size="small">
          <Tooltip title="Просмотр">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record.id)}
            />
          </Tooltip>

          <Tooltip title="Редактировать">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEditModal(record.id)}
            />
          </Tooltip>

          <Tooltip title="TTS генерация">
            <Button
              type="text"
              size="small"
              icon={<RobotOutlined />}
              onClick={() => openTtsModal(record.id)}
            />
          </Tooltip>

          <Dropdown
            menu={{
              items: [
                {
                  key: 'activate',
                  icon: <PlayCircleOutlined />,
                  label: 'Активировать',
                  onClick: () => handleChangeStatus(record.id, 'activate', record.name),
                  disabled: record.is_active,
                },
                {
                  key: 'deactivate',
                  icon: <PauseCircleOutlined />,
                  label: 'Деактивировать',
                  onClick: () => handleChangeStatus(record.id, 'deactivate', record.name),
                  disabled: !record.is_active,
                },
                { type: 'divider' },
                {
                  key: 'clone',
                  icon: <CopyOutlined />,
                  label: 'Клонировать',
                  onClick: () => {
                    setSelectedPlaybook(record as any);
                    setTimeout(() => handleClonePlaybook(), 100);
                  },
                },
                {
                  key: 'make_template',
                  icon: <FileAddOutlined />,
                  label: 'Сделать шаблоном',
                  onClick: () => handleChangeStatus(record.id, 'make_template', record.name),
                  disabled: record.is_template,
                },
                { type: 'divider' },
                {
                  key: 'upload_greeting',
                  icon: <UploadOutlined />,
                  label: 'Загрузить аудио',
                  onClick: () => openUploadModal(record.id, 'greeting'),
                },
                {
                  key: 'download_greeting',
                  icon: <DownloadOutlined />,
                  label: 'Скачать аудио',
                  onClick: () => handleDownloadAudio(record.id, 'greeting', record.name),
                },
                { type: 'divider' },
                {
                  key: 'archive',
                  icon: <DeleteOutlined />,
                  label: 'Архивировать',
                  danger: true,
                  onClick: () => handleChangeStatus(record.id, 'archive', record.name),
                  disabled: record.is_active,
                },
              ],
            }}
            trigger={['click']}
          >
            <Button type="text" size="small" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // =========================================================================
  // РЕНДЕР
  // =========================================================================

  return (
    <div>
      {/* Заголовок */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            <SoundOutlined /> Плейбуки
          </Title>
          <Text type="secondary">Сценарии обработки входящих звонков</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            Обновить
          </Button>
          <Dropdown
            menu={{
              items: [
                { key: 'default', label: '📞 Стандартное приветствие', onClick: () => handleCreateFromTemplate('default') },
                { key: 'emergency', label: '🚨 Экстренное оповещение', onClick: () => handleCreateFromTemplate('emergency') },
                { key: 'short', label: '⚡ Короткое приветствие', onClick: () => handleCreateFromTemplate('short') },
              ],
            }}
          >
            <Button icon={<FileAddOutlined />}>
              Из шаблона
            </Button>
          </Dropdown>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              createForm.resetFields();
              setCreateModalOpen(true);
            }}
          >
            Создать плейбук
          </Button>
        </Space>
      </div>

      {/* Активный плейбук */}
      {activePlaybook && (
        <Card style={{ marginBottom: 16, borderLeft: '4px solid #2ecc71' }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Space>
                <PlayCircleOutlined style={{ fontSize: 24, color: '#2ecc71' }} />
                <div>
                  <Text strong>Активный плейбук:</Text>
                  <Text style={{ marginLeft: 8 }}>{activePlaybook.name}</Text>
                  <Tag color="green" style={{ marginLeft: 8 }}>v{activePlaybook.version}</Tag>
                </div>
              </Space>
            </Col>
            <Col>
              <Space>
                <Text type="secondary">
                  Использован: {activePlaybook.usage_count} раз
                </Text>
                <Button
                  size="small"
                  danger
                  onClick={() => handleChangeStatus(activePlaybook.id, 'deactivate', activePlaybook.name)}
                >
                  Деактивировать
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* Статистика */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="Всего" value={stats.total} prefix={<SoundOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="Активных" value={stats.active} valueStyle={{ color: '#2ecc71' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="Шаблонов" value={stats.templates} valueStyle={{ color: '#3498db' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic
                title="Архив"
                value={stats.total - stats.active - stats.templates}
                valueStyle={{ color: '#95a5a6' }}
              />
            </Card>
          </Col>
          {stats.most_used && stats.most_used.name && (
            <Col span={24} style={{ marginTop: 16 }}>
              <Card size="small">
                <Text type="secondary">
                  Самый используемый: <Text strong>{stats.most_used.name}</Text> ({stats.most_used.usage_count} раз)
                </Text>
              </Card>
            </Col>
          )}
        </Row>
      )}

      {/* Фильтры */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input.Search
            placeholder="Поиск по названию или описанию..."
            allowClear
            onSearch={handleSearch}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => !e.target.value && handleSearch('')}
          />

          <Select
            placeholder="Категория"
            allowClear
            style={{ width: 180 }}
            value={categoryFilter}
            onChange={(v) => { setCategoryFilter(v); setPage(1); }}
          >
            {PLAYBOOK_CATEGORIES.map(cat => (
              <Option key={cat.value} value={cat.value}>
                {cat.icon} {cat.label}
              </Option>
            ))}
          </Select>

          <Select
            placeholder="Источник"
            allowClear
            style={{ width: 160 }}
            value={sourceFilter}
            onChange={(v) => { setSourceFilter(v); setPage(1); }}
          >
            <Option value="tts">🎤 TTS</Option>
            <Option value="uploaded">📁 Файл</Option>
            <Option value="none">⊘ Без приветствия</Option>
          </Select>

          <Select
            placeholder="Статус"
            allowClear
            style={{ width: 150 }}
            value={activeFilter !== undefined ? String(activeFilter) : undefined}
            onChange={(v) => {
              if (v === undefined) setActiveFilter(undefined);
              else if (v === 'active') setActiveFilter(true);
              else if (v === 'inactive') setActiveFilter(false);
              else if (v === 'template') { setActiveFilter(false); setTemplateFilter(true); }
              setPage(1);
            }}
          >
            <Option value="active">✅ Активен</Option>
            <Option value="inactive">❌ Неактивен</Option>
            <Option value="template">📋 Шаблон</Option>
          </Select>

          <Button onClick={handleRefresh} icon={<ReloadOutlined />}>
            Сбросить
          </Button>
        </Space>
      </Card>

      {/* Таблица */}
      <Card>
        <Table
          columns={columns}
          dataSource={playbooks}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: totalPlaybooks,
            showSizeChanger: true,
            showQuickJumper: true,
            pageSizeOptions: ['10', '15', '30', '50'],
            showTotal: (total, range) => `${range[0]}-${range[1]} из ${total}`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 1100 }}
          size="middle"
        />
      </Card>

      {/* =====================================================================
          МОДАЛЬНЫЕ ОКНА
      ===================================================================== */}

      {/* Создание плейбука */}
      <Modal
        title="Создание плейбука"
        open={createModalOpen}
        onOk={handleCreatePlaybook}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        okText="Создать"
        cancelText="Отмена"
        width={700}
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Введите название' }, { min: 2 }]}
          >
            <Input placeholder="Например: Стандартное приветствие" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="Категория" initialValue="общий">
                <Select>
                  {PLAYBOOK_CATEGORIES.map(cat => (
                    <Option key={cat.value} value={cat.value}>
                      {cat.icon} {cat.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="greeting_source" label="Источник приветствия" initialValue="tts">
                <Select>
                  <Option value="tts">🎤 TTS (синтез речи)</Option>
                  <Option value="uploaded">📁 Загруженный файл</Option>
                  <Option value="none">⊘ Без приветствия</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="greeting_text"
            label="Текст приветствия"
            tooltip="Текст, который будет озвучен при входящем звонке"
          >
            <Input.TextArea
              rows={3}
              placeholder="Здравствуйте. Вы позвонили в систему ГО и ЧС информирования..."
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="beep_duration" label="Сигнал (сек)" initialValue={1.0}>
                <InputNumber min={0.1} max={10} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_recording_duration" label="Макс. запись (сек)" initialValue={300}>
                <InputNumber min={10} max={3600} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="greeting_repeat" label="Повторов" initialValue={1}>
                <InputNumber min={0} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="tts_voice" label="Голос TTS" initialValue="ru_male">
                <Select>
                  {TTS_VOICES.map(v => (
                    <Option key={v.value} value={v.value}>{v.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="tts_speed" label="Скорость TTS" initialValue={1.0}>
                <Slider min={0.5} max={2.0} step={0.1} marks={{ 0.5: '0.5', 1.0: '1.0', 1.5: '1.5', 2.0: '2.0' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Редактирование плейбука */}
      <Modal
        title="Редактирование плейбука"
        open={editModalOpen}
        onOk={handleEditPlaybook}
        onCancel={() => {
          setEditModalOpen(false);
          setSelectedPlaybook(null);
          editForm.resetFields();
        }}
        okText="Сохранить"
        cancelText="Отмена"
        width={700}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="Категория">
                <Select>
                  {PLAYBOOK_CATEGORIES.map(cat => (
                    <Option key={cat.value} value={cat.value}>{cat.icon} {cat.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="greeting_source" label="Источник">
                <Select>
                  <Option value="tts">🎤 TTS</Option>
                  <Option value="uploaded">📁 Файл</Option>
                  <Option value="none">⊘ Нет</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="greeting_text" label="Текст приветствия">
            <Input.TextArea rows={3} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="beep_duration" label="Сигнал (сек)">
                <InputNumber min={0.1} max={10} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_recording_duration" label="Макс. запись">
                <InputNumber min={10} max={3600} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="greeting_repeat" label="Повторов">
                <InputNumber min={0} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="tts_voice" label="Голос TTS">
                <Select>
                  {TTS_VOICES.map(v => (
                    <Option key={v.value} value={v.value}>{v.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="tts_speed" label="Скорость TTS">
                <Slider min={0.5} max={2.0} step={0.1} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Детали плейбука */}
      <Modal
        title={selectedPlaybook?.name || 'Информация о плейбуке'}
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedPlaybook(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            Закрыть
          </Button>,
        ]}
        width={750}
      >
        {selectedPlaybook && (
          <Tabs defaultActiveKey="info">
            <TabPane tab="Информация" key="info">
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Название" span={2}>
                  <Text strong style={{ fontSize: 16 }}>{selectedPlaybook.name}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Категория">
                  <Tag color={PLAYBOOK_CATEGORIES.find(c => c.value === selectedPlaybook.category)?.color}>
                    {selectedPlaybook.category || '—'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Версия">v{selectedPlaybook.version}</Descriptions.Item>
                <Descriptions.Item label="Статус">
                  {playbookService.getStatusText(
                    selectedPlaybook.is_active,
                    selectedPlaybook.is_archived,
                    selectedPlaybook.is_template
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="Источник приветствия">
                  <Tag color={playbookService.getSourceColor(selectedPlaybook.greeting_source)}>
                    {playbookService.getSourceIcon(selectedPlaybook.greeting_source)}{' '}
                    {selectedPlaybook.greeting_source === 'tts' ? 'TTS (синтез)' :
                     selectedPlaybook.greeting_source === 'uploaded' ? 'Загруженный файл' : 'Без приветствия'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Использован">{selectedPlaybook.usage_count} раз</Descriptions.Item>
                <Descriptions.Item label="Последнее использование">
                  {selectedPlaybook.last_used_at
                    ? new Date(selectedPlaybook.last_used_at).toLocaleString('ru-RU')
                    : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="Общая длительность">
                  {playbookService.formatDuration(selectedPlaybook.total_duration)}
                </Descriptions.Item>
                <Descriptions.Item label="Сигнал">{selectedPlaybook.beep_duration} сек</Descriptions.Item>
                <Descriptions.Item label="Макс. запись">{selectedPlaybook.max_recording_duration} сек</Descriptions.Item>
                <Descriptions.Item label="Мин. запись">{selectedPlaybook.min_recording_duration} сек</Descriptions.Item>
                <Descriptions.Item label="Повторов">{selectedPlaybook.greeting_repeat}</Descriptions.Item>
                <Descriptions.Item label="Голос TTS">{selectedPlaybook.tts_voice || '—'}</Descriptions.Item>
                <Descriptions.Item label="Скорость TTS">{selectedPlaybook.tts_speed}x</Descriptions.Item>
                <Descriptions.Item label="Создан" span={2}>
                  {selectedPlaybook.created_at
                    ? new Date(selectedPlaybook.created_at).toLocaleString('ru-RU')
                    : '—'}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>

            <TabPane tab="Аудиофайлы" key="audio">
              {selectedPlaybook.audio_files.length > 0 ? (
                <div>
                  {selectedPlaybook.audio_files.map(file => (
                    <Card key={file.type} size="small" style={{ marginBottom: 12 }}>
                      <Text strong>{file.label}</Text>
                      <div style={{ marginTop: 8 }}>
                        <AudioPlayer
                          source={{
                            type: 'url',
                            url: `/api/v1/playbooks/${selectedPlaybook.id}/audio/${file.type}`,
                            filename: `playbook_${selectedPlaybook.name}_${file.type}.wav`,
                          }}
                          showDownload
                          showVolume
                          compact={false}
                          size="small"
                        />
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <SoundOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                  <Paragraph type="secondary" style={{ marginTop: 16 }}>
                    Нет аудиофайлов. Сгенерируйте через TTS или загрузите готовый файл.
                  </Paragraph>
                </div>
              )}
            </TabPane>

            <TabPane tab="Текст" key="text">
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="Приветствие">
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                    {selectedPlaybook.greeting_text || '—'}
                  </pre>
                </Descriptions.Item>
                <Descriptions.Item label="После сигнала">
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                    {selectedPlaybook.post_beep_text || '—'}
                  </pre>
                </Descriptions.Item>
                <Descriptions.Item label="Завершение">
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                    {selectedPlaybook.closing_text || '—'}
                  </pre>
                </Descriptions.Item>
              </Descriptions>
            </TabPane>
          </Tabs>
        )}
      </Modal>

      {/* TTS генерация */}
      <Modal
        title="Генерация аудио через TTS"
        open={ttsModalOpen}
        onOk={handleGenerateTTS}
        onCancel={() => {
          setTtsModalOpen(false);
          setTtsResult(null);
          ttsForm.resetFields();
        }}
        okText="Сгенерировать"
        cancelText="Отмена"
        confirmLoading={ttsGenerating}
        width={650}
      >
        <Form form={ttsForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="text"
            label="Текст для озвучивания"
            rules={[{ required: true, message: 'Введите текст' }]}
          >
            <Input.TextArea rows={4} placeholder="Введите текст сообщения..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="voice" label="Голос">
                <Select>
                  {TTS_VOICES.map(v => (
                    <Option key={v.value} value={v.value}>{v.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="speed" label="Скорость">
                <Slider min={0.5} max={2.0} step={0.1} marks={{ 0.5: '0.5', 1.0: '1.0', 1.5: '1.5', 2.0: '2.0' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {ttsGenerating && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Progress type="circle" percent={99} status="active" />
            <Paragraph type="secondary" style={{ marginTop: 12 }}>
              Генерация и конвертация в формат Asterisk (8000 Гц, mono, 16-bit)...
            </Paragraph>
          </div>
        )}

        {ttsResult && ttsResult.success && (
          <Alert
            type="success"
            message="Аудио сгенерировано"
            description={
              <div>
                <p>Длительность: {ttsResult.duration_seconds?.toFixed(1)} сек</p>
                <p>Частота: {ttsResult.sample_rate} Гц</p>
                <p>Размер: {((ttsResult.file_size_bytes || 0) / 1024).toFixed(1)} КБ</p>
                {ttsResult.audio_path && (
                  <AudioPlayer
                    source={{ type: 'url', url: ttsResult.audio_path }}
                    compact
                    size="small"
                  />
                )}
              </div>
            }
            style={{ marginTop: 16 }}
          />
        )}
      </Modal>

      {/* Загрузка аудио */}
      <Modal
        title={`Загрузка аудио: ${audioType === 'greeting' ? 'Приветствие' : audioType === 'post_beep' ? 'После сигнала' : 'Завершение'}`}
        open={uploadModalOpen}
        onOk={handleUploadAudio}
        onCancel={() => {
          setUploadModalOpen(false);
          setUploadFile(null);
          setUploadProgress(0);
        }}
        okText="Загрузить"
        cancelText="Отмена"
        confirmLoading={uploading}
        okButtonProps={{ disabled: !uploadFile }}
      >
        <div style={{ marginBottom: 16 }}>
          <Alert
            message="Формат Asterisk"
            description="Файл будет автоматически сконвертирован в WAV 8000 Гц, mono, 16-bit PCM."
            type="info"
            showIcon
          />
        </div>

        <Dragger
          name="audio"
          multiple={false}
          accept=".wav,.mp3,.ogg,.flac"
          beforeUpload={(file) => {
            const validation = playbookService.validateAudioFile(file);
            if (!validation.valid) {
              message.error(validation.error);
              return false;
            }
            setUploadFile(file);
            return false;
          }}
          onRemove={() => {
            setUploadFile(null);
            setUploadProgress(0);
          }}
          fileList={uploadFile ? [{ uid: '-1', name: uploadFile.name, status: 'done' } as UploadFile] : []}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Нажмите или перетащите аудиофайл</p>
          <p className="ant-upload-hint">Поддерживаются WAV, MP3, OGG, FLAC (до 50 МБ)</p>
        </Dragger>

        {uploading && (
          <Progress percent={uploadProgress} style={{ marginTop: 16 }} />
        )}
      </Modal>

      {/* Тестирование плейбука */}
      <Modal
        title="Тестирование плейбука"
        open={testModalOpen}
        onOk={handleTestPlaybook}
        onCancel={() => {
          setTestModalOpen(false);
          testForm.resetFields();
        }}
        okText="Позвонить"
        cancelText="Отмена"
      >
        <Alert
          message="Тестовый звонок"
          description="Система позвонит на указанный номер и воспроизведет плейбук."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form form={testForm} layout="vertical">
          <Form.Item
            name="test_number"
            label="Номер телефона"
            rules={[
              { required: true, message: 'Введите номер' },
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve();
                  const validation = playbookService.validateTestPhone(value);
                  if (validation.valid) return Promise.resolve();
                  return Promise.reject(new Error(validation.error));
                },
              },
            ]}
          >
            <Input placeholder="+7XXXXXXXXXX" />
          </Form.Item>

          <Form.Item name="test_type" label="Тип теста" initialValue="full">
            <Select>
              <Option value="full">Полный (приветствие + сигнал + запись)</Option>
              <Option value="greeting_only">Только приветствие</Option>
              <Option value="beep_only">Только сигнал</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PlaybooksPage;
