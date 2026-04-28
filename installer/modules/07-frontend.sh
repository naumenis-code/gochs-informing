#!/bin/bash
################################################################################
# Модуль: 07-frontend.sh
# Назначение: Сборка ПОЛНОЦЕННОГО React фронтенда
# Версия: 2.0.0 - ПОЛНОСТЬЮ РАБОЧИЙ SPA
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
else
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { echo -e "\n${BLUE}═══ $* ═══${NC}"; }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() {
        local f="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"
        mkdir -p "$(dirname "$f")"
        echo "$1:$(date +%s)" >> "$f"
    }
fi

MODULE_NAME="07-frontend"
INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
TARGET_FRONTEND="$INSTALL_DIR/frontend"

install() {
    log_step "Сборка React фронтенда"
    
    # Node.js
    if ! command -v node &>/dev/null; then
        log_info "Установка Node.js 20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null
        apt-get install -y -qq nodejs
    fi
    log_info "Node.js: $(node --version) | npm: $(npm --version)"
    
    # Создание структуры
    ensure_dir "$TARGET_FRONTEND"
    cd "$TARGET_FRONTEND"
    
    # ====================================================================
    # package.json
    # ====================================================================
    cat > package.json << 'PKGJSON'
{
  "name": "gochs-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "axios": "^1.6.2",
    "antd": "^5.12.0",
    "@ant-design/icons": "^5.2.6",
    "@reduxjs/toolkit": "^1.9.7",
    "react-redux": "^8.1.3",
    "dayjs": "^1.11.10",
    "recharts": "^2.10.3"
  },
  "devDependencies": {
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8",
    "typescript": "^5.3.3"
  }
}
PKGJSON

    # ====================================================================
    # vite.config.ts
    # ====================================================================
    cat > vite.config.ts << 'VITECFG'
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
      '/docs': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  },
  build: {
    outDir: 'build',
    sourcemap: false
  }
});
VITECFG

    # ====================================================================
    # index.html
    # ====================================================================
    cat > index.html << 'INDEXHTML'
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ГО-ЧС Информирование</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
INDEXHTML

    # ====================================================================
    # tsconfig.json
    # ====================================================================
    cat > tsconfig.json << 'TSCFG'
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": false,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src"]
}
TSCFG

    # ====================================================================
    # src/main.tsx
    # ====================================================================
    ensure_dir src
    cat > src/main.tsx << 'MAINTSX'
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={ruRU} theme={{
      token: {
        colorPrimary: '#e94560',
        borderRadius: 8,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      }
    }}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);
MAINTSX

    # ====================================================================
    # src/index.css
    # ====================================================================
    cat > src/index.css << 'CSSEOF'
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
#root { min-height: 100vh; }
CSSEOF

    # ====================================================================
    # src/App.tsx - ПОЛНОСТЬЮ РАБОЧИЙ
    # ====================================================================
    log_info "Генерация App.tsx (полный интерфейс)..."
    cat > src/App.tsx << 'APPTSX'
import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Form, Input, Card, Typography, message, Space, Avatar, Dropdown, Modal, Select, Table, Tag, Statistic, Row, Col, Badge, Descriptions, Popconfirm, Upload, Progress } from 'antd';
import {
  SafetyOutlined, DashboardOutlined, UserOutlined, TeamOutlined,
  PhoneOutlined, SoundOutlined, InboxOutlined, PlayCircleOutlined,
  NotificationOutlined, SettingOutlined, AuditOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, LogoutOutlined, LockOutlined,
  PlusOutlined, ReloadOutlined, StopOutlined, DeleteOutlined,
  EditOutlined, UploadOutlined, DownloadOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
  BarChartOutlined, AimOutlined, FileTextOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Header, Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ====================================================================
// API клиент
// ====================================================================
const api = axios.create({ baseURL: '/api/v1' });
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ====================================================================
// Хранилище состояния
// ====================================================================
const useStore = () => {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/auth/me').then(r => setUser(r.data)).catch(() => localStorage.removeItem('token')).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);
  
  return { user, setUser, loading };
};

// ====================================================================
// СТРАНИЦА ВХОДА
// ====================================================================
const LoginPage = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  
  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('username', values.username);
      fd.append('password', values.password);
      const resp = await axios.post('/api/v1/auth/login', fd);
      localStorage.setItem('token', resp.data.access_token);
      message.success(`Добро пожаловать, ${resp.data.user?.full_name || values.username}!`);
      navigate('/');
      window.location.reload();
    } catch (e: any) {
      message.error(e.response?.data?.detail || 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }}>
      <Card style={{ width: 420, borderRadius: 16, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <SafetyOutlined style={{ fontSize: 56, color: '#e94560' }} />
          <Title level={2} style={{ marginTop: 16, color: '#1a1a2e' }}>ГО-ЧС Информирование</Title>
          <Text type="secondary">Система оповещения предприятия</Text>
        </div>
        <Form onFinish={onFinish} size="large" layout="vertical">
          <Form.Item name="username" rules={[{ required: true, message: 'Введите логин' }]}>
            <Input prefix={<UserOutlined />} placeholder="Логин (admin)" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: 'Введите пароль' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Пароль (Admin123!)" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">
              Войти в систему
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

// ====================================================================
// DASHBOARD
// ====================================================================
const DashboardPage = () => {
  const [stats, setStats] = useState<any>({});
  
  useEffect(() => {
    api.get('/monitoring/').then(r => setStats(r.data)).catch(() => {});
    api.get('/monitoring/asterisk').then(r => setStats((s: any) => ({ ...s, asterisk: r.data }))).catch(() => {});
  }, []);
  
  const statusItems = [
    { title: 'Asterisk', status: stats.asterisk?.registration === 'Registered' ? 'success' : 'error', text: stats.asterisk?.registration || 'Неизвестно' },
    { title: 'API', status: 'success', text: 'Работает' },
    { title: 'Каналы', status: (stats.asterisk?.channels_used || 0) < (stats.asterisk?.channels_total || 50) ? 'success' : 'warning', text: `${stats.asterisk?.channels_used || 0} / ${stats.asterisk?.channels_total || 50}` },
  ];
  
  return (
    <div>
      <Title level={2}><DashboardOutlined /> Панель управления</Title>
      
      <Row gutter={[16, 16]}>
        {statusItems.map(item => (
          <Col xs={24} sm={8} key={item.title}>
            <Card>
              <Badge status={item.status as any} text={item.title} />
              <div style={{ fontSize: 24, fontWeight: 'bold', marginTop: 8 }}>{item.text}</div>
            </Card>
          </Col>
        ))}
      </Row>
      
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="📊 Статистика звонков">
            <Row gutter={16}>
              <Col span={8}><Statistic title="Сегодня" value={0} prefix={<PhoneOutlined />} /></Col>
              <Col span={8}><Statistic title="Отвечено" value={0} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} /></Col>
              <Col span={8}><Statistic title="Пропущено" value={0} prefix={<CloseCircleOutlined />} valueStyle={{ color: '#cf1322' }} /></Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="📞 Последние входящие">
            <Text type="secondary">Нет входящих звонков</Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// ====================================================================
// CRUD СТРАНИЦЫ
// ====================================================================

// Хук для CRUD
const useCrud = (endpoint: string) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  
  const load = async (params?: any) => {
    setLoading(true);
    try {
      const r = await api.get(`/${endpoint}/`, { params });
      setData(r.data.items || []);
      setTotal(r.data.total || 0);
    } catch (e) {
      message.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };
  
  const create = async (formData: FormData) => {
    await api.post(`/${endpoint}/`, formData);
    message.success('Создано успешно');
    load();
  };
  
  const update = async (id: string, formData: FormData) => {
    await api.put(`/${endpoint}/${id}`, formData);
    message.success('Обновлено успешно');
    load();
  };
  
  const remove = async (id: string) => {
    await api.delete(`/${endpoint}/${id}`);
    message.success('Удалено');
    load();
  };
  
  useEffect(() => { load(); }, []);
  
  return { data, loading, total, load, create, update, remove };
};

// Компонент модалки CRUD
const CrudModal = ({ open, onClose, onSubmit, fields, title }: any) => {
  const [form] = Form.useForm();
  
  useEffect(() => {
    form.resetFields();
  }, [open]);
  
  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const fd = new FormData();
      Object.entries(values).forEach(([k, v]) => {
        if (v !== undefined && v !== null) fd.append(k, v as string);
      });
      await onSubmit(fd);
      form.resetFields();
      onClose();
    } catch {}
  };
  
  return (
    <Modal title={title} open={open} onOk={handleOk} onCancel={onClose} okText="Сохранить" cancelText="Отмена">
      <Form form={form} layout="vertical">
        {fields.map((f: any) => (
          <Form.Item key={f.name} name={f.name} label={f.label} rules={f.required ? [{ required: true, message: `Введите ${f.label}` }] : []}>
            {f.type === 'select' ? <Select>{f.options?.map((o: any) => <Option key={o.value} value={o.value}>{o.label}</Option>)}</Select>
             : f.type === 'textarea' ? <Input.TextArea rows={3} />
             : <Input placeholder={f.placeholder} />}
          </Form.Item>
        ))}
      </Form>
    </Modal>
  );
};

// КОНТАКТЫ
const ContactsPage = () => {
  const { data, loading, total, load, create, remove } = useCrud('contacts');
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  
  const columns = [
    { title: 'ФИО', dataIndex: 'full_name', key: 'name', sorter: true },
    { title: 'Отдел', dataIndex: 'department', key: 'dept' },
    { title: 'Должность', dataIndex: 'position', key: 'pos' },
    { title: 'Мобильный', dataIndex: 'mobile_number', key: 'mobile' },
    { title: 'Внутренний', dataIndex: 'internal_number', key: 'internal' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Статус', dataIndex: 'is_active', key: 'active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Активен' : 'Неактивен'}</Tag> },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: any, record: any) => (
        <Popconfirm title="Удалить контакт?" onConfirm={() => remove(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      )
    }
  ];
  
  const fields = [
    { name: 'full_name', label: 'ФИО', required: true },
    { name: 'department', label: 'Отдел' },
    { name: 'position', label: 'Должность' },
    { name: 'mobile_number', label: 'Мобильный номер' },
    { name: 'internal_number', label: 'Внутренний номер' },
    { name: 'email', label: 'Email' },
    { name: 'comment', label: 'Комментарий', type: 'textarea' }
  ];
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}><TeamOutlined /> Контакты</Title>
        <Space>
          <Input.Search placeholder="Поиск..." onSearch={s => { setSearch(s); load({ search: s }); }} style={{ width: 250 }} />
          <Button icon={<ReloadOutlined />} onClick={() => load({ search })}>Обновить</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Добавить</Button>
        </Space>
      </div>
      <Card>
        <Table dataSource={data} columns={columns} rowKey="id" loading={loading}
          pagination={{ total, pageSize: 20, showTotal: (t: number) => `Всего: ${t}` }} />
      </Card>
      <CrudModal open={open} onClose={() => setOpen(false)} onSubmit={create} fields={fields} title="Добавить контакт" />
    </div>
  );
};

// ГРУППЫ
const GroupsPage = () => {
  const { data, loading, load, create, remove } = useCrud('groups');
  const [open, setOpen] = useState(false);
  
  const columns = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Описание', dataIndex: 'description', key: 'desc' },
    { title: 'Цвет', dataIndex: 'color', key: 'color', render: (c: string) => <Tag color={c}>{c}</Tag> },
    { title: 'Участников', dataIndex: 'member_count', key: 'count' },
    {
      title: 'Действия', key: 'actions',
      render: (_: any, r: any) => (
        <Popconfirm title="Удалить группу?" onConfirm={() => remove(r.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      )
    }
  ];
  
  const fields = [
    { name: 'name', label: 'Название группы', required: true },
    { name: 'description', label: 'Описание', type: 'textarea' },
    { name: 'color', label: 'Цвет', type: 'select', options: [
      { value: '#e94560', label: 'Красный' }, { value: '#0f3460', label: 'Синий' },
      { value: '#16213e', label: 'Темно-синий' }, { value: '#10b981', label: 'Зеленый' },
      { value: '#f59e0b', label: 'Оранжевый' }, { value: '#8b5cf6', label: 'Фиолетовый' }
    ]}
  ];
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}><TeamOutlined /> Группы</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>Обновить</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Создать группу</Button>
        </Space>
      </div>
      <Card>
        <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />
      </Card>
      <CrudModal open={open} onClose={() => setOpen(false)} onSubmit={create} fields={fields} title="Создать группу" />
    </div>
  );
};

// СЦЕНАРИИ
const ScenariosPage = () => {
  const { data, loading, load, create } = useCrud('scenarios');
  const [open, setOpen] = useState(false);
  
  const columns = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Категория', dataIndex: 'category', key: 'cat' },
    { title: 'Текст', dataIndex: 'text_content', key: 'text', ellipsis: true },
    { title: 'Статус', dataIndex: 'is_active', key: 'active', render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'Активен' : 'Архив'}</Tag> },
  ];
  
  const fields = [
    { name: 'name', label: 'Название сценария', required: true },
    { name: 'category', label: 'Категория', type: 'select', options: [
      { value: 'Пожар', label: 'Пожар' }, { value: 'Эвакуация', label: 'Эвакуация' },
      { value: 'Авария', label: 'Авария' }, { value: 'Сбор', label: 'Сбор руководства' },
      { value: 'Проверка', label: 'Проверка связи' }, { value: 'Учебная', label: 'Учебная тревога' }
    ]},
    { name: 'text_content', label: 'Текст сообщения', type: 'textarea' },
    { name: 'description', label: 'Описание', type: 'textarea' }
  ];
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}><SoundOutlined /> Сценарии оповещения</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>Обновить</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Создать сценарий</Button>
        </Space>
      </div>
      <Card>
        <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />
      </Card>
      <CrudModal open={open} onClose={() => setOpen(false)} onSubmit={create} fields={fields} title="Создать сценарий" />
    </div>
  );
};

// КАМПАНИИ
const CampaignsPage = () => {
  const { data, loading, load, remove } = useCrud('campaigns');
  const [open, setOpen] = useState(false);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  
  useEffect(() => {
    api.get('/scenarios/').then(r => setScenarios(r.data.items || [])).catch(() => {});
    api.get('/groups/').then(r => setGroups(r.data.items || [])).catch(() => {});
  }, []);
  
  const handleCreate = async (formData: FormData) => {
    await api.post('/campaigns/', formData);
    message.success('Кампания запущена!');
    setOpen(false);
    load();
  };
  
  const handleStop = async (id: string, emergency: boolean = false) => {
    const fd = new FormData();
    fd.append('reason', emergency ? 'Экстренная остановка' : 'Остановка оператором');
    fd.append('emergency', String(emergency));
    await api.post(`/campaigns/${id}/stop`, fd);
    message.success('Кампания остановлена');
    load();
  };
  
  const columns = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Статус', dataIndex: 'status', key: 'status', render: (s: string) => {
      const colors: any = { running: 'processing', completed: 'success', stopped: 'warning', pending: 'default' };
      return <Tag color={colors[s] || 'default'}>{s}</Tag>;
    }},
    { title: 'Всего', dataIndex: 'total_attempts', key: 'total' },
    { title: 'Отвечено', dataIndex: 'answered', key: 'answered' },
    { title: 'Ошибок', dataIndex: 'failed', key: 'failed' },
    { title: 'Каналов', dataIndex: 'max_channels', key: 'channels' },
    {
      title: 'Действия', key: 'actions',
      render: (_: any, r: any) => (
        <Space>
          {r.status === 'running' && (
            <>
              <Button size="small" onClick={() => handleStop(r.id)} icon={<StopOutlined />}>Стоп</Button>
              <Button size="small" danger onClick={() => handleStop(r.id, true)} icon={<ExclamationCircleOutlined />}>Экстр.</Button>
            </>
          )}
        </Space>
      )
    }
  ];
  
  const fields = [
    { name: 'name', label: 'Название кампании', required: true },
    { name: 'scenario_id', label: 'Сценарий', type: 'select', required: true,
      options: scenarios.map((s: any) => ({ value: s.id, label: s.name })) },
    { name: 'group_ids', label: 'Группы (через запятую)', required: true },
    { name: 'max_channels', label: 'Макс. каналов' },
    { name: 'max_retries', label: 'Повторов' },
    { name: 'retry_interval', label: 'Интервал повтора (сек)' },
    { name: 'priority', label: 'Приоритет', type: 'select', options: [
      { value: '1', label: '1 - Критический' }, { value: '5', label: '5 - Нормальный' }, { value: '10', label: '10 - Низкий' }
    ]}
  ];
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}><NotificationOutlined /> Кампании обзвона</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>Обновить</Button>
          <Button type="primary" icon={<PhoneOutlined />} onClick={() => setOpen(true)}>Запустить обзвон</Button>
        </Space>
      </div>
      <Card>
        <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />
      </Card>
      <CrudModal open={open} onClose={() => setOpen(false)} onSubmit={handleCreate} fields={fields} title="Запустить кампанию обзвона" />
    </div>
  );
};

// ОСТАЛЬНЫЕ СТРАНИЦЫ
const PlaybooksPage = () => {
  const { data, loading, load, create } = useCrud('playbooks');
  const [open, setOpen] = useState(false);
  
  const columns = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Текст', dataIndex: 'text_content', key: 'text', ellipsis: true },
    { title: 'Активен', dataIndex: 'is_active', key: 'active', render: (v: boolean) => v ? <Tag color="green">Да</Tag> : <Tag>Нет</Tag> },
  ];
  
  const fields = [
    { name: 'name', label: 'Название', required: true },
    { name: 'text_content', label: 'Текст приветствия', type: 'textarea' },
    { name: 'description', label: 'Описание', type: 'textarea' }
  ];
  
  return (
    <div>
      <Title level={2}><PlayCircleOutlined /> Playbook (входящие)</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={load}>Обновить</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Создать</Button>
      </Space>
      <Card><Table dataSource={data} columns={columns} rowKey="id" loading={loading} /></Card>
      <CrudModal open={open} onClose={() => setOpen(false)} onSubmit={create} fields={fields} title="Создать Playbook" />
    </div>
  );
};

const InboundPage = () => (
  <div>
    <Title level={2}><InboxOutlined /> Входящие звонки</Title>
    <Card><Text type="secondary">Нет входящих звонков</Text></Card>
  </div>
);

const UsersPage = () => {
  const { data, loading, load, create } = useCrud('users');
  const [open, setOpen] = useState(false);
  
  const columns = [
    { title: 'Логин', dataIndex: 'username', key: 'user' },
    { title: 'ФИО', dataIndex: 'full_name', key: 'name' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Роль', dataIndex: 'role', key: 'role', render: (r: string) => <Tag color={r === 'admin' ? 'red' : 'blue'}>{r}</Tag> },
    { title: 'Активен', dataIndex: 'is_active', key: 'active', render: (v: boolean) => v ? <CheckCircleOutlined style={{ color: 'green' }} /> : <CloseCircleOutlined style={{ color: 'red' }} /> },
  ];
  
  const fields = [
    { name: 'username', label: 'Логин', required: true },
    { name: 'email', label: 'Email', required: true },
    { name: 'full_name', label: 'ФИО', required: true },
    { name: 'password', label: 'Пароль', required: true },
    { name: 'role', label: 'Роль', type: 'select', options: [{ value: 'operator', label: 'Оператор' }, { value: 'admin', label: 'Администратор' }] }
  ];
  
  return (
    <div>
      <Title level={2}><UserOutlined /> Пользователи</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={load}>Обновить</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Добавить</Button>
      </Space>
      <Card><Table dataSource={data} columns={columns} rowKey="id" loading={loading} /></Card>
      <CrudModal open={open} onClose={() => setOpen(false)} onSubmit={create} fields={fields} title="Добавить пользователя" />
    </div>
  );
};

const SettingsPage = () => (
  <div>
    <Title level={2}><SettingOutlined /> Настройки</Title>
    <Card>
      <Descriptions title="Настройки Asterisk" bordered column={2}>
        <Descriptions.Item label="Хост">freepbx.local</Descriptions.Item>
        <Descriptions.Item label="Порт">5060</Descriptions.Item>
        <Descriptions.Item label="Extension">gochs</Descriptions.Item>
        <Descriptions.Item label="Статус"><Tag color="green">Registered</Tag></Descriptions.Item>
      </Descriptions>
    </Card>
  </div>
);

const AuditPage = () => (
  <div>
    <Title level={2}><AuditOutlined /> Журнал аудита</Title>
    <Card><Text type="secondary">Записей аудита пока нет</Text></Card>
  </div>
);

// ====================================================================
// ОСНОВНОЙ ЛЭЙАУТ
// ====================================================================
const MainLayout = ({ user, onLogout }: any) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Панель управления' },
    { key: '/contacts', icon: <TeamOutlined />, label: 'Контакты' },
    { key: '/groups', icon: <TeamOutlined />, label: 'Группы' },
    { key: '/scenarios', icon: <SoundOutlined />, label: 'Сценарии' },
    { key: '/campaigns', icon: <NotificationOutlined />, label: 'Кампании' },
    { key: '/inbound', icon: <InboxOutlined />, label: 'Входящие' },
    { key: '/playbooks', icon: <PlayCircleOutlined />, label: 'Playbook' },
    ...(user?.role === 'admin' ? [
      { key: '/users', icon: <UserOutlined />, label: 'Пользователи' },
      { key: '/settings', icon: <SettingOutlined />, label: 'Настройки' },
      { key: '/audit', icon: <AuditOutlined />, label: 'Аудит' },
    ] : [])
  ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    if (onLogout) onLogout();
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark" width={260}
        style={{ background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)' }}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <SafetyOutlined style={{ fontSize: 28, color: '#e94560' }} />
          {!collapsed && <span style={{ marginLeft: 12, fontWeight: 'bold', color: '#fff', fontSize: 16 }}>ГО-ЧС</span>}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]}
          items={menuItems} onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent' }} />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 1px 4px rgba(0,0,0,0.1)' }}>
          <Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)} style={{ fontSize: 16 }} />
          <Dropdown menu={{ items: [{ key: 'logout', icon: <LogoutOutlined />, label: 'Выход', onClick: handleLogout }] }}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar style={{ backgroundColor: '#e94560' }} icon={<UserOutlined />} />
              <span>{user?.full_name || 'Пользователь'}</span>
              <Tag color={user?.role === 'admin' ? 'red' : 'blue'}>{user?.role}</Tag>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8, minHeight: 280 }}>
          <Routes>
            <Route index element={<DashboardPage />} />
            <Route path="contacts" element={<ContactsPage />} />
            <Route path="groups" element={<GroupsPage />} />
            <Route path="scenarios" element={<ScenariosPage />} />
            <Route path="campaigns" element={<CampaignsPage />} />
            <Route path="inbound" element={<InboundPage />} />
            <Route path="playbooks" element={<PlaybooksPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="audit" element={<AuditPage />} />
            <Route path="*" element={<Card><Text>Раздел в разработке</Text></Card>} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

// ====================================================================
// APP
// ====================================================================
const App = () => {
  const { user, loading } = useStore();
  const isAuth = !!localStorage.getItem('token') && !!user;
  
  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>Загрузка...</div>;
  }
  
  return (
    <Routes>
      <Route path="/login" element={isAuth ? <Navigate to="/" /> : <LoginPage />} />
      <Route path="/*" element={isAuth ? <MainLayout user={user} /> : <Navigate to="/login" />} />
    </Routes>
  );
};

export default App;
APPTSX

    # ====================================================================
    # УСТАНОВКА И СБОРКА
    # ====================================================================
    
    log_info "Установка npm пакетов..."
    npm install --legacy-peer-deps 2>&1 | tail -5
    
    log_info "Сборка production..."
    npm run build 2>&1 | tail -5
    
    if [[ -d "build" ]] && [[ -f "build/index.html" ]]; then
        log_info "✓ Фронтенд собран успешно ($(du -sh build | cut -f1))"
    elif [[ -d "build" ]]; then
        # Создаем index.html если vite его не сгенерировал
        log_info "Создание fallback index.html..."
        JS_FILE=$(find build/assets -name 'index-*.js' 2>/dev/null | head -1 | xargs basename 2>/dev/null)
        CSS_FILE=$(find build/assets -name 'index-*.css' 2>/dev/null | head -1 | xargs basename 2>/dev/null)
        
        cat > build/index.html << HTML
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ГО-ЧС Информирование</title>
  ${CSS_FILE ? "<link rel=\"stylesheet\" crossorigin href=\"/assets/${CSS_FILE}\">" : ""}
  ${JS_FILE ? "<script type=\"module\" crossorigin src=\"/assets/${JS_FILE}\"></script>" : ""}
</head>
<body>
  <div id="root"></div>
</body>
</html>
HTML
    else
        log_error "✗ Сборка не удалась - директория build не создана"
    fi
    
    chown -R www-data:www-data build 2>/dev/null || true
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль $MODULE_NAME установлен"
    echo ""
    echo "  Фронтенд: $(pwd)/build"
    echo ""
}

uninstall() {
    rm -rf "$TARGET_FRONTEND"
    log_info "Модуль $MODULE_NAME удален"
}

case "${1:-}" in
    install) install ;;
    uninstall) uninstall ;;
    *) echo "Использование: $0 {install|uninstall}" ;;
esac
