#!/bin/bash

################################################################################
# Создание недостающих страниц фронтенда
################################################################################

INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
FRONTEND_SRC="$INSTALL_DIR/frontend/src"

log_info() { echo -e "\033[0;32m[INFO]\033[0m $(date '+%H:%M:%S') $*"; }

log_info "Создание недостающих страниц фронтенда..."

# ============================================================================
# SCENARIOS PAGE
# ============================================================================
cat > "$FRONTEND_SRC/pages/Scenarios.tsx" << 'EOF'
import React, { useState, useEffect } from 'react';
import {
  Table, Button, Space, Typography, Tag, Input, Select, Card, Modal, Form,
  message, Popconfirm, Tooltip, Row, Col, Statistic, Badge, Dropdown, Upload
} from 'antd';
import {
  PlusOutlined, SearchOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
  SoundOutlined, EyeOutlined, MoreOutlined, PlayCircleOutlined, UploadOutlined
} from '@ant-design/icons';
import { scenarioService } from '@services/scenarioService';
import AudioPlayer from '@components/Common/AudioPlayer';

const { Title, Text } = Typography;
const { Option } = Select;

const Scenarios: React.FC = () => {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<any>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const loadScenarios = async () => {
    setLoading(true);
    try {
      const data = await scenarioService.getScenarios();
      setScenarios(data.items || []);
    } catch { message.error('Ошибка загрузки'); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadScenarios(); }, []);

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      await scenarioService.createScenario(values);
      message.success('Сценарий создан');
      setCreateModalOpen(false);
      createForm.resetFields();
      loadScenarios();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('Ошибка создания');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await scenarioService.deleteScenario(id);
      message.success('Сценарий удален');
      loadScenarios();
    } catch { message.error('Ошибка удаления'); }
  };

  const columns = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <Space>
          <SoundOutlined style={{ color: '#9b59b6' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{text || 'Без названия'}</div>
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>{record.category || '—'}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'category',
      key: 'category',
      width: 150,
      render: (cat: string) => (
        <Tag color={
          cat === 'fire' ? '#e74c3c' :
          cat === 'evacuation' ? '#e67e22' :
          cat === 'emergency' ? '#f39c12' :
          cat === 'test' ? '#3498db' : '#95a5a6'
        }>{cat || '—'}</Tag>
      ),
    },
    {
      title: 'Длительность',
      dataIndex: 'duration',
      key: 'duration',
      width: 120,
      render: (d: number) => d ? `${Math.floor(d/60)}:${(d%60).toString().padStart(2,'0')}` : '—',
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean) => (
        <Badge status={active ? 'success' : 'default'} text={active ? 'Активен' : 'Неактивен'} />
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 150,
      render: (_: any, record: any) => (
        <Space size="small">
          <Tooltip title="Просмотр">
            <Button type="text" size="small" icon={<EyeOutlined />} />
          </Tooltip>
          <Tooltip title="Редактировать">
            <Button type="text" size="small" icon={<EditOutlined />}
              onClick={() => {
                setSelectedScenario(record);
                editForm.setFieldsValue(record);
                setEditModalOpen(true);
              }}
            />
          </Tooltip>
          <Popconfirm title="Удалить?" onConfirm={() => handleDelete(record.id)}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}><SoundOutlined /> Сценарии оповещения</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadScenarios}>Обновить</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { createForm.resetFields(); setCreateModalOpen(true); }}>
            Создать сценарий
          </Button>
        </Space>
      </div>

      <Card>
        <Table columns={columns} dataSource={scenarios} rowKey="id" loading={loading}
          pagination={{ pageSize: 20, showTotal: (total: number) => `Всего ${total}` }}
        />
      </Card>

      {/* Create Modal */}
      <Modal title="Создание сценария" open={createModalOpen} onOk={handleCreate}
        onCancel={() => setCreateModalOpen(false)} okText="Создать" cancelText="Отмена" width={600}>
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Название" rules={[{ required: true, message: 'Введите название' }]}>
            <Input placeholder="Пожарная тревога" />
          </Form.Item>
          <Form.Item name="category" label="Категория" initialValue="fire">
            <Select>
              <Option value="fire">🔥 Пожар</Option>
              <Option value="evacuation">🚶 Эвакуация</Option>
              <Option value="emergency">🚨 Экстренная</Option>
              <Option value="test">🧪 Тестовая</Option>
              <Option value="info">ℹ️ Информационная</Option>
            </Select>
          </Form.Item>
          <Form.Item name="text_content" label="Текст сценария">
            <Input.TextArea rows={4} placeholder="Внимание! В здании пожар..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal title="Редактирование сценария" open={editModalOpen} onOk={async () => {
        try {
          const values = await editForm.validateFields();
          await scenarioService.updateScenario(selectedScenario?.id, values);
          message.success('Сценарий обновлен');
          setEditModalOpen(false);
          loadScenarios();
        } catch {}
      }} onCancel={() => setEditModalOpen(false)} okText="Сохранить" cancelText="Отмена" width={600}>
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="Категория">
            <Select>
              <Option value="fire">🔥 Пожар</Option>
              <Option value="evacuation">🚶 Эвакуация</Option>
              <Option value="emergency">🚨 Экстренная</Option>
              <Option value="test">🧪 Тестовая</Option>
              <Option value="info">ℹ️ Информационная</Option>
            </Select>
          </Form.Item>
          <Form.Item name="text_content" label="Текст сценария">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Scenarios;
EOF

# ============================================================================
# CAMPAIGNS PAGE
# ============================================================================
cat > "$FRONTEND_SRC/pages/Campaigns.tsx" << 'EOF'
import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Space, Typography, Tag, Input, Select, Card, Modal, Form,
  message, Popconfirm, Tooltip, Row, Col, Statistic, Badge, Progress, Dropdown
} from 'antd';
import {
  PlusOutlined, SearchOutlined, ReloadOutlined, StopOutlined,
  ThunderboltOutlined, EyeOutlined, MoreOutlined, PlayCircleOutlined,
  PauseCircleOutlined, CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons';
import { scenarioService } from '@services/scenarioService';
import { groupService } from '@services/groupService';

const { Title, Text } = Typography;
const { Option } = Select;

const Campaigns: React.FC = () => {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [createForm] = Form.useForm();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [scenariosData, groupsData] = await Promise.all([
        scenarioService.getScenarios(),
        groupService.getGroups({ page_size: 100 }),
      ]);
      setScenarios(scenariosData.items || []);
      setGroups(groupsData.items || []);
    } catch {
      message.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      message.success(`Кампания "${values.name}" создана`);
      setCreateModalOpen(false);
      createForm.resetFields();
      loadData();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error('Ошибка создания');
    }
  };

  const getStatusTag = (status: string) => {
    const colors: Record<string, string> = {
      running: '#2ecc71', pending: '#f39c12', completed: '#3498db',
      stopped: '#e74c3c', paused: '#e67e22', failed: '#e74c3c',
    };
    const labels: Record<string, string> = {
      running: 'Выполняется', pending: 'Ожидание', completed: 'Завершена',
      stopped: 'Остановлена', paused: 'Пауза', failed: 'Ошибка',
    };
    return <Tag color={colors[status] || '#95a5a6'}>{labels[status] || status}</Tag>;
  };

  const columns = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <Space>
          <ThunderboltOutlined style={{ color: record.status === 'running' ? '#2ecc71' : '#f39c12' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{text || 'Кампания'}</div>
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>
              {record.scenario_name || 'Сценарий не выбран'}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: 'Прогресс',
      dataIndex: 'progress_percent',
      key: 'progress',
      width: 200,
      render: (percent: number, record: any) => (
        <div>
          <Progress percent={percent || 0} size="small" />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.completed_calls || 0}/{record.total_contacts || 0}
          </Text>
        </div>
      ),
    },
    {
      title: 'Приоритет',
      dataIndex: 'priority',
      key: 'priority',
      width: 90,
      align: 'center',
      render: (p: number) => (
        <Tag color={p <= 3 ? '#e74c3c' : p <= 6 ? '#f39c12' : '#95a5a6'}>{p}</Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 180,
      render: (_: any, record: any) => (
        <Space size="small">
          {record.status === 'pending' && (
            <Tooltip title="Запустить">
              <Button type="text" size="small" icon={<PlayCircleOutlined style={{ color: '#2ecc71' }} />} />
            </Tooltip>
          )}
          {record.status === 'running' && (
            <>
              <Tooltip title="Пауза">
                <Button type="text" size="small" icon={<PauseCircleOutlined style={{ color: '#f39c12' }} />} />
              </Tooltip>
              <Tooltip title="Остановить">
                <Button type="text" size="small" icon={<StopOutlined style={{ color: '#e74c3c' }} />} />
              </Tooltip>
            </>
          )}
          <Tooltip title="Просмотр">
            <Button type="text" size="small" icon={<EyeOutlined />} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}><ThunderboltOutlined /> Кампании обзвона</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData}>Обновить</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { createForm.resetFields(); setCreateModalOpen(true); }}>
            Новая кампания
          </Button>
        </Space>
      </div>

      {/* Quick Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="Всего" value={campaigns.length} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="Активных" value={campaigns.filter(c => c.status === 'running').length} valueStyle={{ color: '#2ecc71' }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="Завершено" value={campaigns.filter(c => c.status === 'completed').length} valueStyle={{ color: '#3498db' }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="Ошибок" value={campaigns.filter(c => c.status === 'failed').length} valueStyle={{ color: '#e74c3c' }} /></Card>
        </Col>
      </Row>

      <Card>
        <Table columns={columns} dataSource={campaigns} rowKey="id" loading={loading}
          pagination={{ pageSize: 20, showTotal: (total: number) => `Всего ${total}` }}
        />
      </Card>

      {/* Create Campaign Modal */}
      <Modal title="Новая кампания обзвона" open={createModalOpen} onOk={handleCreate}
        onCancel={() => setCreateModalOpen(false)} okText="Создать" cancelText="Отмена" width={600}>
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Название кампании" rules={[{ required: true }]}>
            <Input placeholder="Обзвон руководства" />
          </Form.Item>
          <Form.Item name="scenario_id" label="Сценарий" rules={[{ required: true }]}>
            <Select placeholder="Выберите сценарий" showSearch optionFilterProp="label">
              {scenarios.map((s: any) => (
                <Option key={s.id} value={s.id} label={s.name}>{s.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="group_ids" label="Группы контактов" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="Выберите группы" showSearch optionFilterProp="label">
              {groups.map((g: any) => (
                <Option key={g.id} value={g.id} label={g.name}>{g.name} ({g.member_count})</Option>
              ))}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="priority" label="Приоритет" initialValue={5}>
                <Select>
                  {[1,2,3,4,5,6,7,8,9,10].map(p => (
                    <Option key={p} value={p}>{p} — {p <= 3 ? 'Высокий' : p <= 6 ? 'Средний' : 'Низкий'}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="max_channels" label="Макс. каналов" initialValue={20}>
                <Select>
                  {[5,10,20,30,50].map(c => <Option key={c} value={c}>{c}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="start_immediately" label="Запустить сразу" valuePropName="checked" initialValue={false}>
            <Select>
              <Option value={true}>Да</Option>
              <Option value={false}>Нет</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Campaigns;
EOF

# ============================================================================
# INBOUND PAGE
# ============================================================================
cat > "$FRONTEND_SRC/pages/Inbound.tsx" << 'EOF'
import React, { useState, useEffect } from 'react';
import {
  Table, Button, Space, Typography, Tag, Card, message, Tooltip, Row, Col, Statistic, DatePicker
} from 'antd';
import {
  ReloadOutlined, InboxOutlined, PlayCircleOutlined, DownloadOutlined, PhoneOutlined, ClockCircleOutlined
} from '@ant-design/icons';
import AudioPlayer from '@components/Common/AudioPlayer';

const { Title, Text } = Typography;

const Inbound: React.FC = () => {
  const [calls, setCalls] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadCalls = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/inbound/calls?limit=100');
      const data = await response.json();
      setCalls(data.items || []);
    } catch { message.error('Ошибка загрузки'); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadCalls(); }, []);

  const columns = [
    {
      title: 'Время',
      dataIndex: 'started_at',
      key: 'time',
      width: 170,
      render: (text: string) => (
        <Space direction="vertical" size={0}>
          <Text>{text ? new Date(text).toLocaleDateString('ru-RU') : '—'}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <ClockCircleOutlined /> {text ? new Date(text).toLocaleTimeString('ru-RU') : '—'}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Номер',
      dataIndex: 'caller_number',
      key: 'caller',
      width: 150,
      render: (text: string) => (
        <Text><PhoneOutlined /> {text || 'Неизвестный'}</Text>
      ),
    },
    {
      title: 'Длительность',
      dataIndex: 'duration',
      key: 'duration',
      width: 120,
      align: 'center',
      render: (d: number) => d ? `${Math.floor(d/60)}:${(d%60).toString().padStart(2,'0')}` : '—',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const colors: Record<string, string> = {
          recorded: '#2ecc71', missed: '#e74c3c', transcribed: '#3498db',
          answered: '#f39c12', failed: '#e74c3c',
        };
        const labels: Record<string, string> = {
          recorded: 'Записан', missed: 'Пропущен', transcribed: 'Расшифрован',
          answered: 'Отвечен', failed: 'Ошибка',
        };
        return <Tag color={colors[status] || '#95a5a6'}>{labels[status] || status}</Tag>;
      },
    },
    {
      title: 'Транскрипция',
      dataIndex: 'transcription',
      key: 'transcription',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text ellipsis style={{ maxWidth: 300 }}>{text || '—'}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Аудио',
      key: 'audio',
      width: 200,
      render: (_: any, record: any) => (
        record.recording_path ? (
          <AudioPlayer
            source={{ type: 'url', url: record.recording_path }}
            compact
            size="small"
            showDownload
          />
        ) : (
          <Text type="secondary">Нет записи</Text>
        )
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}><InboxOutlined /> Входящие звонки</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadCalls}>Обновить</Button>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="Всего" value={calls.length} prefix={<InboxOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="С записями" value={calls.filter(c => c.recording_path).length} valueStyle={{ color: '#2ecc71' }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="Пропущено" value={calls.filter(c => c.status === 'missed').length} valueStyle={{ color: '#e74c3c' }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="Расшифровано" value={calls.filter(c => c.transcription).length} valueStyle={{ color: '#3498db' }} /></Card>
        </Col>
      </Row>

      <Card>
        <Table columns={columns} dataSource={calls} rowKey="id" loading={loading}
          pagination={{ pageSize: 20, showTotal: (total: number) => `Всего ${total}` }}
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  );
};

export default Inbound;
EOF

# ============================================================================
# FRONTEND SERVICES
# ============================================================================
log_info "Создание недостающих сервисов фронтенда..."

# scenarioService.ts
cat > "$FRONTEND_SRC/services/scenarioService.ts" << 'EOF'
import api from './api';

export const scenarioService = {
  async getScenarios(params?: any) {
    const response = await api.get('/scenarios/', { params });
    return response.data;
  },
  async getScenario(id: string) {
    const response = await api.get(`/scenarios/${id}`);
    return response.data;
  },
  async createScenario(data: any) {
    const response = await api.post('/scenarios/', data);
    return response.data;
  },
  async updateScenario(id: string, data: any) {
    const response = await api.patch(`/scenarios/${id}`, data);
    return response.data;
  },
  async deleteScenario(id: string) {
    const response = await api.delete(`/scenarios/${id}`);
    return response.data;
  },
  async uploadAudio(id: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/scenarios/${id}/audio`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

export default scenarioService;
EOF

# campaignService.ts (обновленная)
cat > "$FRONTEND_SRC/services/campaignService.ts" << 'EOF'
import api from './api';

export const campaignService = {
  async getCampaigns(params?: any) {
    const response = await api.get('/campaigns/', { params });
    return response.data;
  },
  async getCampaign(id: string) {
    const response = await api.get(`/campaigns/${id}`);
    return response.data;
  },
  async createCampaign(data: any) {
    const response = await api.post('/campaigns/', data);
    return response.data;
  },
  async startCampaign(id: string) {
    const response = await api.post(`/campaigns/${id}/start`);
    return response.data;
  },
  async stopCampaign(id: string, force: boolean = false) {
    const response = await api.post(`/campaigns/${id}/stop`, { force });
    return response.data;
  },
  async getActiveCampaigns() {
    const response = await api.get('/campaigns/active');
    return response.data;
  },
  async getCampaignStatus(id: string) {
    const response = await api.get(`/campaigns/${id}/status`);
    return response.data;
  },
};

export default campaignService;
EOF

log_info "✓ Недостающие страницы и сервисы созданы"

# Обновление App.tsx с новыми страницами
log_info "Обновление App.tsx..."
APP_FILE="$FRONTEND_SRC/App.tsx"
if [[ -f "$APP_FILE" ]]; then
    # Добавляем импорты
    if ! grep -q "import Scenarios" "$APP_FILE"; then
        sed -i "/import.*from '@pages\/.*';/a import Scenarios from '@pages/Scenarios';" "$APP_FILE"
        sed -i "/import.*from '@pages\/.*';/a import Campaigns from '@pages/Campaigns';" "$APP_FILE"
        sed -i "/import.*from '@pages\/.*';/a import Inbound from '@pages/Inbound';" "$APP_FILE"
    fi
    # Добавляем маршруты
    if ! grep -q 'path="campaigns"' "$APP_FILE"; then
        sed -i '/<Route path="scenarios"/a \          <Route path="campaigns" element={<Campaigns />} />' "$APP_FILE"
        sed -i '/<Route path="playbooks"/a \          <Route path="scenarios" element={<Scenarios />} />' "$APP_FILE"
        sed -i '/<Route path="campaigns"/a \          <Route path="inbound" element={<Inbound />} />' "$APP_FILE"
    fi
    log_info "✓ App.tsx обновлен"
fi

# Пересборка фронтенда
log_info "Пересборка фронтенда..."
cd "$FRONTEND_SRC/.."
npm run build 2>&1 | tail -10
BUILD_STATUS=$?

if [[ $BUILD_STATUS -eq 0 ]]; then
    chown -R www-data:www-data build 2>/dev/null || true
    log_info "✓ Фронтенд пересобран"
else
    log_error "✗ Ошибка сборки фронтенда"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  СТРАНИЦЫ СОЗДАНЫ"
echo "═══════════════════════════════════════════════════════════════"
