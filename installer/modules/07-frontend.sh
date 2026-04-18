#!/bin/bash

################################################################################
# Модуль: 07-frontend.sh
# Назначение: Установка и сборка React фронтенда
################################################################################

source "${UTILS_DIR}/common.sh"

MODULE_NAME="07-frontend"
MODULE_DESCRIPTION="React Frontend для ГО-ЧС Информирование"

# Версия Node.js
NODE_VERSION="20"

install() {
    log_step "Установка React фронтенда"
    
    # Установка Node.js
    install_nodejs
    
    # Создание структуры фронтенда
    log_info "Создание структуры фронтенда..."
    create_frontend_structure
    
    # Создание package.json
    create_package_json
    
    # Создание основных компонентов React
    create_react_components
    
    # Создание стилей
    create_styles
    
    # Создание утилит и сервисов
    create_utils
    
    # Сборка фронтенда
    build_frontend
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Фронтенд собран в: $INSTALL_DIR/frontend/build"
    
    return 0
}

install_nodejs() {
    log_info "Установка Node.js $NODE_VERSION..."
    
    if command -v node &> /dev/null; then
        NODE_VER=$(node --version)
        log_info "Node.js уже установлен: $NODE_VER"
    else
        # Добавление репозитория NodeSource
        curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
        apt-get install -y nodejs
        
        # Установка yarn
        npm install -g yarn
        
        log_info "Node.js $(node --version) установлен"
    fi
}

create_frontend_structure() {
    log_info "Создание структуры директорий..."
    
    mkdir -p "$INSTALL_DIR/frontend"/{public,src}
    mkdir -p "$INSTALL_DIR/frontend/src"/{components,pages,services,utils,styles,hooks,context}
    
    # Поддиректории компонентов
    mkdir -p "$INSTALL_DIR/frontend/src/components"/{Layout,Dashboard,Contacts,Campaigns,Scenarios,Inbound,Settings,Common}
    
    # Установка прав
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/frontend"
}

create_package_json() {
    log_info "Создание package.json..."
    
    cat > "$INSTALL_DIR/frontend/package.json" << 'EOF'
{
  "name": "gochs-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.2",
    "antd": "^5.12.0",
    "@ant-design/icons": "^5.2.6",
    "@reduxjs/toolkit": "^1.9.7",
    "react-redux": "^8.1.3",
    "react-query": "^3.39.3",
    "recharts": "^2.10.0",
    "socket.io-client": "^4.5.4",
    "dayjs": "^1.11.10",
    "react-hook-form": "^7.48.2",
    "yup": "^1.3.3",
    "@hookform/resolvers": "^3.3.2",
    "react-audio-player": "^0.17.0",
    "wavesurfer.js": "^7.4.0",
    "xlsx": "^0.18.5",
    "papaparse": "^5.4.1",
    "react-dropzone": "^14.2.3",
    "react-beautiful-dnd": "^13.1.1",
    "@emotion/react": "^11.11.1",
    "@emotion/styled": "^11.11.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "@types/node": "^20.10.4",
    "typescript": "^5.3.3",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8",
    "sass": "^1.69.5",
    "eslint": "^8.55.0",
    "eslint-plugin-react": "^7.33.2",
    "prettier": "^3.1.1"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext js,jsx,ts,tsx",
    "format": "prettier --write 'src/**/*.{js,jsx,ts,tsx,css,scss}'"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
EOF

    # vite.config.ts
    cat > "$INSTALL_DIR/frontend/vite.config.ts" << 'EOF'
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@services': path.resolve(__dirname, './src/services'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@context': path.resolve(__dirname, './src/context'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'build',
    sourcemap: false,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd', '@ant-design/icons'],
          charts: ['recharts'],
        },
      },
    },
  },
});
EOF

    # tsconfig.json
    cat > "$INSTALL_DIR/frontend/tsconfig.json" << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@pages/*": ["src/pages/*"],
      "@services/*": ["src/services/*"],
      "@utils/*": ["src/utils/*"],
      "@hooks/*": ["src/hooks/*"],
      "@context/*": ["src/context/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF

    # index.html
    cat > "$INSTALL_DIR/frontend/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="ГО-ЧС Информирование - Система оповещения" />
    <title>ГО-ЧС Информирование</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF
}

create_react_components() {
    log_info "Создание React компонентов..."
    
    # main.tsx
    cat > "$INSTALL_DIR/frontend/src/main.tsx" << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';

import App from './App';
import { store } from './store';
import './styles/global.scss';

dayjs.locale('ru');

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={ruRU} theme={{
          token: {
            colorPrimary: '#1890ff',
            borderRadius: 6,
          },
        }}>
          <App />
        </ConfigProvider>
      </QueryClientProvider>
    </Provider>
  </React.StrictMode>
);
EOF

    # App.tsx
    cat > "$INSTALL_DIR/frontend/src/App.tsx" << 'EOF'
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth';

import Layout from '@components/Layout';
import Login from '@pages/Login';
import Dashboard from '@pages/Dashboard';
import Contacts from '@pages/Contacts';
import Groups from '@pages/Groups';
import Scenarios from '@pages/Scenarios';
import Campaigns from '@pages/Campaigns';
import Inbound from '@pages/Inbound';
import Playbooks from '@pages/Playbooks';
import Users from '@pages/Users';
import Settings from '@pages/Settings';
import Audit from '@pages/Audit';

const App: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Router>
      <Routes>
        <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
        
        <Route path="/" element={isAuthenticated ? <Layout /> : <Navigate to="/login" />}>
          <Route index element={<Dashboard />} />
          <Route path="contacts" element={<Contacts />} />
          <Route path="groups" element={<Groups />} />
          <Route path="scenarios" element={<Scenarios />} />
          <Route path="campaigns" element={<Campaigns />} />
          <Route path="inbound" element={<Inbound />} />
          <Route path="playbooks" element={<Playbooks />} />
          <Route path="users" element={<Users />} />
          <Route path="settings" element={<Settings />} />
          <Route path="audit" element={<Audit />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
};

export default App;
EOF

    # store/index.ts
    cat > "$INSTALL_DIR/frontend/src/store/index.ts" << 'EOF'
import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import contactsReducer from './slices/contactsSlice';
import campaignsReducer from './slices/campaignsSlice';
import monitoringReducer from './slices/monitoringSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    contacts: contactsReducer,
    campaigns: campaignsReducer,
    monitoring: monitoringReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
EOF

    # store/slices/authSlice.ts
    cat > "$INSTALL_DIR/frontend/src/store/slices/authSlice.ts" << 'EOF'
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<{ user: User; token: string }>) => {
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.isAuthenticated = true;
      localStorage.setItem('token', action.payload.token);
    },
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      localStorage.removeItem('token');
    },
  },
});

export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;
EOF

    # pages/Dashboard.tsx
    cat > "$INSTALL_DIR/frontend/src/pages/Dashboard.tsx" << 'EOF'
import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Progress, Badge } from 'antd';
import {
  PhoneOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { Line, Pie } from '@ant-design/charts';
import { useWebSocket } from '@hooks/useWebSocket';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({
    totalChannels: 50,
    usedChannels: 12,
    freeChannels: 38,
    gochsChannels: 8,
    inboundCalls: 3,
    outboundCalls: 5,
  });

  const [activeCampaigns, setActiveCampaigns] = useState([]);
  const [recentInbound, setRecentInbound] = useState([]);

  const { connected, lastMessage } = useWebSocket('/ws/monitoring');

  useEffect(() => {
    if (lastMessage) {
      const data = JSON.parse(lastMessage.data);
      setStats(data.stats);
      setActiveCampaigns(data.activeCampaigns);
    }
  }, [lastMessage]);

  const columns = [
    {
      title: 'Время',
      dataIndex: 'time',
      key: 'time',
    },
    {
      title: 'Номер',
      dataIndex: 'caller',
      key: 'caller',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          answered: 'success',
          missed: 'error',
          recorded: 'processing',
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      },
    },
  ];

  const channelData = [
    { type: 'Используется', value: stats.usedChannels },
    { type: 'Свободно', value: stats.freeChannels },
  ];

  const config = {
    data: channelData,
    angleField: 'value',
    colorField: 'type',
    radius: 0.8,
    label: {
      type: 'outer',
      content: '{name} {percentage}',
    },
    interactions: [{ type: 'pie-legend-active' }, { type: 'element-active' }],
  };

  return (
    <div className="dashboard">
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="Состояние системы" bordered={false}>
            <Badge status={connected ? 'success' : 'error'} text={connected ? 'Online' : 'Offline'} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Всего каналов"
              value={stats.totalChannels}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Используется"
              value={stats.usedChannels}
              valueStyle={{ color: '#3f8600' }}
              prefix={<LineChartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Входящие"
              value={stats.inboundCalls}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Исходящие"
              value={stats.outboundCalls}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="Использование каналов">
            <Pie {...config} height={300} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Активные кампании">
            {activeCampaigns.map((campaign: any) => (
              <div key={campaign.id} style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>{campaign.name}</span>
                  <span>{campaign.completed}/{campaign.total}</span>
                </div>
                <Progress
                  percent={campaign.progress}
                  status={campaign.status === 'running' ? 'active' : 'success'}
                />
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="Последние входящие звонки">
            <Table
              dataSource={recentInbound}
              columns={columns}
              pagination={{ pageSize: 5 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
EOF

    # pages/Login.tsx
    cat > "$INSTALL_DIR/frontend/src/pages/Login.tsx" << 'EOF'
import React from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined, SafetyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { setCredentials } from '@store/slices/authSlice';
import { authService } from '@services/authService';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [loading, setLoading] = React.useState(false);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      const response = await authService.login(values.username, values.password);
      dispatch(setCredentials({
        user: response.user,
        token: response.access_token,
      }));
      message.success('Вход выполнен успешно');
      navigate('/');
    } catch (error) {
      message.error('Неверное имя пользователя или пароль');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <SafetyOutlined className="login-icon" />
          <h1>ГО-ЧС Информирование</h1>
          <p>Система оповещения и информирования</p>
        </div>
        
        <Form
          name="login"
          onFinish={onFinish}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Введите имя пользователя' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Имя пользователя"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Введите пароль' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Пароль"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              Войти
            </Button>
          </Form.Item>
        </Form>
        
        <div className="login-footer">
          <p>© 2024 ГО-ЧС Информирование. Все права защищены.</p>
        </div>
      </Card>
    </div>
  );
};

export default Login;
EOF

    # pages/Campaigns.tsx
    cat > "$INSTALL_DIR/frontend/src/pages/Campaigns.tsx" << 'EOF'
import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Popconfirm,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { campaignService } from '@services/campaignService';
import { scenarioService } from '@services/scenarioService';
import { groupService } from '@services/groupService';

const Campaigns: React.FC = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [scenarios, setScenarios] = useState([]);
  const [groups, setGroups] = useState([]);
  const [form] = Form.useForm();

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const data = await campaignService.getCampaigns();
      setCampaigns(data);
    } catch (error) {
      message.error('Ошибка загрузки кампаний');
    } finally {
      setLoading(false);
    }
  };

  const loadScenarios = async () => {
    try {
      const data = await scenarioService.getScenarios();
      setScenarios(data);
    } catch (error) {
      message.error('Ошибка загрузки сценариев');
    }
  };

  const loadGroups = async () => {
    try {
      const data = await groupService.getGroups();
      setGroups(data);
    } catch (error) {
      message.error('Ошибка загрузки групп');
    }
  };

  useEffect(() => {
    loadCampaigns();
    loadScenarios();
    loadGroups();
    
    const interval = setInterval(loadCampaigns, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await campaignService.createCampaign(values);
      message.success('Кампания создана');
      setModalVisible(false);
      form.resetFields();
      loadCampaigns();
    } catch (error) {
      message.error('Ошибка создания кампании');
    }
  };

  const handleStart = async (id: string) => {
    try {
      await campaignService.startCampaign(id);
      message.success('Кампания запущена');
      loadCampaigns();
    } catch (error) {
      message.error('Ошибка запуска кампании');
    }
  };

  const handleStop = async (id: string) => {
    try {
      await campaignService.stopCampaign(id);
      message.success('Кампания остановлена');
      loadCampaigns();
    } catch (error) {
      message.error('Ошибка остановки кампании');
    }
  };

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: 'Ожидает' },
      running: { color: 'processing', text: 'Выполняется' },
      paused: { color: 'warning', text: 'Приостановлена' },
      completed: { color: 'success', text: 'Завершена' },
      stopped: { color: 'error', text: 'Остановлена' },
    };
    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Сценарий',
      dataIndex: ['scenario', 'name'],
      key: 'scenario',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag,
    },
    {
      title: 'Прогресс',
      key: 'progress',
      render: (record: any) => {
        const percent = record.total_contacts > 0
          ? Math.round((record.completed_calls / record.total_contacts) * 100)
          : 0;
        return <Progress percent={percent} size="small" />;
      },
    },
    {
      title: 'Приоритет',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: number) => {
        const colors = ['', 'red', 'orange', 'gold', 'blue', 'default'];
        return <Tag color={colors[priority]}>{priority}</Tag>;
      },
    },
    {
      title: 'Создана',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString('ru-RU'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (record: any) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record.id)}
            >
              Запустить
            </Button>
          )}
          {record.status === 'running' && (
            <Popconfirm
              title="Остановить кампанию?"
              onConfirm={() => handleStop(record.id)}
            >
              <Button type="link" danger icon={<StopOutlined />}>
                Остановить
              </Button>
            </Popconfirm>
          )}
          <Button type="link" icon={<EyeOutlined />}>
            Детали
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="campaigns-page">
      <div className="page-header">
        <h2>Кампании оповещения</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadCampaigns}>
            Обновить
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalVisible(true)}
          >
            Создать кампанию
          </Button>
        </Space>
      </div>

      <Table
        dataSource={campaigns}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title="Создание кампании"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
        >
          <Form.Item
            name="name"
            label="Название кампании"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input placeholder="Например: Пожарная тревога" />
          </Form.Item>

          <Form.Item
            name="scenario_id"
            label="Сценарий оповещения"
            rules={[{ required: true, message: 'Выберите сценарий' }]}
          >
            <Select placeholder="Выберите сценарий">
              {scenarios.map((s: any) => (
                <Select.Option key={s.id} value={s.id}>
                  {s.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="group_ids"
            label="Группы контактов"
            rules={[{ required: true, message: 'Выберите группы' }]}
          >
            <Select mode="multiple" placeholder="Выберите группы">
              {groups.map((g: any) => (
                <Select.Option key={g.id} value={g.id}>
                  {g.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="priority"
            label="Приоритет (1-10)"
            initialValue={5}
          >
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="max_retries"
            label="Количество повторов"
            initialValue={3}
          >
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="max_channels"
            label="Максимум каналов"
            initialValue={20}
          >
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="start_immediately"
            valuePropName="checked"
          >
            <Button type="primary" htmlType="submit" block>
              Создать и запустить
            </Button>
          </Form.Item>

          <Form.Item>
            <Button htmlType="submit" block>
              Создать
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Campaigns;
EOF

    log_info "React компоненты созданы"
}

create_styles() {
    log_info "Создание стилей..."
    
    mkdir -p "$INSTALL_DIR/frontend/src/styles"
    
    # global.scss
    cat > "$INSTALL_DIR/frontend/src/styles/global.scss" << 'EOF'
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f0f2f5;
}

#root {
  min-height: 100vh;
}

// Login page
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  
  .login-card {
    width: 400px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    
    .login-header {
      text-align: center;
      margin-bottom: 32px;
      
      .login-icon {
        font-size: 48px;
        color: #1890ff;
        margin-bottom: 16px;
      }
      
      h1 {
        font-size: 24px;
        margin-bottom: 8px;
      }
      
      p {
        color: #8c8c8c;
      }
    }
    
    .login-footer {
      text-align: center;
      margin-top: 24px;
      color: #8c8c8c;
      font-size: 12px;
    }
  }
}

// Layout
.app-layout {
  min-height: 100vh;
  
  .app-header {
    background: #fff;
    padding: 0 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    
    .header-left {
      display: flex;
      align-items: center;
      
      .logo {
        font-size: 20px;
        font-weight: bold;
        color: #1890ff;
        margin-right: 24px;
      }
      
      .trigger {
        font-size: 18px;
        cursor: pointer;
      }
    }
    
    .header-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }
  }
  
  .app-sider {
    background: #fff;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.06);
  }
  
  .app-content {
    margin: 24px;
    padding: 24px;
    background: #fff;
    border-radius: 8px;
    min-height: calc(100vh - 112px);
  }
}

// Pages
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  h2 {
    margin: 0;
  }
}

// Dashboard
.dashboard {
  .stat-card {
    height: 100%;
  }
}

// Responsive
@media (max-width: 768px) {
  .app-content {
    margin: 16px;
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
}
EOF

    log_info "Стили созданы"
}

create_utils() {
    log_info "Создание утилит и сервисов..."
    
    mkdir -p "$INSTALL_DIR/frontend/src/services"
    
    # services/api.ts
    cat > "$INSTALL_DIR/frontend/src/services/api.ts" << 'EOF'
import axios from 'axios';
import { message } from 'antd';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    } else if (error.response?.status === 403) {
      message.error('Недостаточно прав для выполнения операции');
    } else if (error.response?.status >= 500) {
      message.error('Ошибка сервера. Попробуйте позже.');
    }
    return Promise.reject(error);
  }
);

export default api;
EOF

    # services/authService.ts
    cat > "$INSTALL_DIR/frontend/src/services/authService.ts" << 'EOF'
import api from './api';

export const authService = {
  async login(username: string, password: string) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData);
    return response.data;
  },
  
  async logout() {
    const response = await api.post('/auth/logout');
    return response.data;
  },
  
  async getCurrentUser() {
    const response = await api.get('/auth/me');
    return response.data;
  },
  
  async refreshToken(refreshToken: string) {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },
};
EOF

    # services/campaignService.ts
    cat > "$INSTALL_DIR/frontend/src/services/campaignService.ts" << 'EOF'
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
  
  async updateCampaign(id: string, data: any) {
    const response = await api.patch(`/campaigns/${id}`, data);
    return response.data;
  },
  
  async deleteCampaign(id: string) {
    const response = await api.delete(`/campaigns/${id}`);
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
  
  async getCampaignStatus(id: string) {
    const response = await api.get(`/campaigns/${id}/status`);
    return response.data;
  },
};
EOF

    log_info "Утилиты и сервисы созданы"
}

build_frontend() {
    log_step "Сборка фронтенда"
    
    cd "$INSTALL_DIR/frontend"
    
    # Установка зависимостей
    log_info "Установка npm зависимостей..."
    npm install --legacy-peer-deps
    
    # Сборка проекта
    log_info "Сборка React приложения..."
    npm run build
    
    if [[ -d "$INSTALL_DIR/frontend/build" ]]; then
        log_info "Фронтенд успешно собран"
        
        # Установка прав
        chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/frontend/build"
        
        # Создание символической ссылки
        ln -sf "$INSTALL_DIR/frontend/build" "$INSTALL_DIR/frontend/static"
    else
        log_error "Ошибка сборки фронтенда"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Удаление файлов фронтенда
    read -p "Удалить файлы фронтенда? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR/frontend"
        log_info "Файлы фронтенда удалены"
    fi
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка наличия собранного фронтенда
    if [[ -d "$INSTALL_DIR/frontend/build" ]]; then
        log_info "Фронтенд: собран"
        
        BUILD_SIZE=$(du -sh "$INSTALL_DIR/frontend/build" | cut -f1)
        log_info "  Размер сборки: $BUILD_SIZE"
        
        # Проверка index.html
        if [[ -f "$INSTALL_DIR/frontend/build/index.html" ]]; then
            log_info "  index.html: присутствует"
        else
            log_warn "  index.html: отсутствует"
            status=1
        fi
    else
        log_warn "Фронтенд: не собран"
        status=1
    fi
    
    # Проверка Node.js
    if command -v node &> /dev/null; then
        NODE_VER=$(node --version)
        log_info "Node.js: $NODE_VER"
    else
        log_warn "Node.js: не установлен"
    fi
    
    return $status
}

# Обработка аргументов
case "${1:-}" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    status)
        check_status
        ;;
    rebuild)
        cd "$INSTALL_DIR/frontend"
        npm run build
        ;;
    dev)
        cd "$INSTALL_DIR/frontend"
        npm run dev
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|rebuild|dev}"
        exit 1
        ;;
esac
