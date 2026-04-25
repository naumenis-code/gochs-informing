#!/bin/bash

################################################################################
# Модуль: 07-frontend.sh
# Назначение: Установка и сборка React фронтенда
# Версия: 1.0.6 (полная исправленная версия)
################################################################################

# Определение путей
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Загрузка общих функций
if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

# Если common.sh не найден - определяем функции локально
if ! type log_info &>/dev/null; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
    NC='\033[0m'
    
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { 
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}  $*${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() {
        local module="$1"
        local state_file="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"
        mkdir -p "$(dirname "$state_file")"
        echo "$module:$(date +%s)" >> "$state_file"
    }
fi

MODULE_NAME="07-frontend"
MODULE_DESCRIPTION="React Frontend для ГО-ЧС Информирование"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Fallback: загрузка из .env
if [[ -z "$DOMAIN_OR_IP" ]] && [[ -f "$INSTALL_DIR/.env" ]]; then
    source "$INSTALL_DIR/.env"
fi

INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
DOMAIN_OR_IP="${DOMAIN_OR_IP:-192.168.0.166}"
GOCHS_USER="${GOCHS_USER:-gochs}"
GOCHS_GROUP="${GOCHS_GROUP:-gochs}"

# Версия Node.js
NODE_VERSION="20"

install() {
    log_step "Установка React фронтенда"
    
    # Установка Node.js
    install_nodejs
    
    # Создание структуры фронтенда
    create_frontend_structure
    
    # Создание package.json и конфигурационных файлов
    create_config_files
    
    # Создание основных файлов React
    create_react_app_files
    
    # Создание компонентов
    create_components
    
    # Создание страниц
    create_pages
    
    # Создание сервисов
    create_services
    
    # Создание хуков
    create_hooks
    
    # Создание утилит
    create_utils
    
    # Создание контекста
    create_context
    
    # Установка зависимостей и сборка
    build_frontend
    
    mark_module_installed "$MODULE_NAME"
    
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
        log_info "Добавление репозитория NodeSource..."
        curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - 2>/dev/null || true
        apt-get update -qq
        apt-get install -y nodejs
        
        if ! command -v npm &> /dev/null; then
            apt-get install -y npm
        fi
        
        log_info "Node.js $(node --version) установлен"
    fi
    
    log_info "Обновление npm..."
    npm install -g npm@latest 2>/dev/null || true
}

create_frontend_structure() {
    log_info "Создание структуры директорий..."
    
    local dirs=(
        "frontend"
        "frontend/public"
        "frontend/src"
        "frontend/src/components"
        "frontend/src/components/Layout"
        "frontend/src/components/Dashboard"
        "frontend/src/components/Contacts"
        "frontend/src/components/Campaigns"
        "frontend/src/components/Scenarios"
        "frontend/src/components/Inbound"
        "frontend/src/components/Settings"
        "frontend/src/components/Common"
        "frontend/src/pages"
        "frontend/src/services"
        "frontend/src/utils"
        "frontend/src/styles"
        "frontend/src/hooks"
        "frontend/src/context"
        "frontend/src/store"
        "frontend/src/store/slices"
        "frontend/src/types"
    )
    
    for dir in "${dirs[@]}"; do
        ensure_dir "$INSTALL_DIR/$dir"
    done
    
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/frontend" 2>/dev/null || true
    
    log_info "Структура директорий создана"
}

create_config_files() {
    log_info "Создание конфигурационных файлов..."
    
    # package.json
    cat > "$INSTALL_DIR/frontend/package.json" << 'EOF'
{
  "name": "gochs-frontend",
  "version": "1.0.0",
  "private": true,
 "dependencies": {
    "react": ">=18.2.0 <19.0.0",
    "react-dom": ">=18.2.0 <19.0.0",
    "react-router-dom": ">=6.20.0 <7.0.0",
    "axios": ">=1.6.2 <2.0.0",
    "antd": ">=5.12.0 <6.0.0",
    "@ant-design/icons": ">=5.2.6 <6.0.0",
    "@reduxjs/toolkit": ">=1.9.7 <2.0.0",
    "react-redux": ">=8.1.3 <9.0.0",
    "react-query": ">=3.39.3 <4.0.0",
    "recharts": ">=2.10.0 <3.0.0",
    "dayjs": ">=1.11.10 <2.0.0",
    "react-hook-form": ">=7.48.2 <8.0.0",
    "yup": ">=1.3.3 <2.0.0",
    "@hookform/resolvers": ">=3.3.2 <4.0.0",
    "react-audio-player": ">=0.17.0 <1.0.0",
    "wavesurfer.js": ">=7.4.0 <8.0.0",
    "xlsx": ">=0.18.5 <1.0.0",
    "papaparse": ">=5.4.1 <6.0.0",
    "react-dropzone": ">=14.2.3 <15.0.0"
  },
  "devDependencies": {
    "@types/react": ">=18.2.45 <19.0.0",
    "@types/react-dom": ">=18.2.18 <19.0.0",
    "@types/node": ">=20.10.4 <21.0.0",
    "@vitejs/plugin-react": ">=4.2.1 <5.0.0",
    "vite": ">=5.0.8 <6.0.0",
    "typescript": ">=5.3.3 <6.0.0",
    "sass": ">=1.69.5 <2.0.0",
    "eslint": ">=8.55.0 <9.0.0",
    "eslint-plugin-react": ">=7.33.2 <8.0.0",
    "prettier": ">=3.1.1 <4.0.0",
    "terser": ">=5.37.0 <6.0.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext js,jsx,ts,tsx",
    "format": "prettier --write 'src/**/*.{js,jsx,ts,tsx,css,scss}'"
  }
}
EOF

    # vite.config.ts
    cat > "$INSTALL_DIR/frontend/vite.config.ts" << EOF
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
      '@store': path.resolve(__dirname, './src/store'),
      '@types': path.resolve(__dirname, './src/types'),
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
    "strict": false,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@pages/*": ["src/pages/*"],
      "@services/*": ["src/services/*"],
      "@utils/*": ["src/utils/*"],
      "@hooks/*": ["src/hooks/*"],
      "@context/*": ["src/context/*"],
      "@store/*": ["src/store/*"],
      "@types/*": ["src/types/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF

    # tsconfig.node.json - ИСПРАВЛЕНИЕ: критически важный файл
    cat > "$INSTALL_DIR/frontend/tsconfig.node.json" << 'EOF'
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
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

    # .env
    cat > "$INSTALL_DIR/frontend/.env" << EOF
VITE_API_URL=https://$DOMAIN_OR_IP
VITE_WS_URL=wss://$DOMAIN_OR_IP
VITE_APP_NAME=ГО-ЧС Информирование
EOF

    log_info "Конфигурационные файлы созданы"
}

create_react_app_files() {
    log_info "Создание основных файлов React приложения..."
    
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
import { store } from '@store/index';
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

    # vite-env.d.ts
    cat > "$INSTALL_DIR/frontend/src/vite-env.d.ts" << 'EOF'
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_APP_NAME: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
EOF

    log_info "Основные файлы React созданы"
}

create_components() {
    log_info "Создание компонентов..."
    
    # Layout/index.tsx
    cat > "$INSTALL_DIR/frontend/src/components/Layout/index.tsx" << 'EOF'
import React, { useState } from 'react';
import { Layout as AntLayout, Menu, Dropdown, Avatar, message, Badge } from 'antd';
import {
  DashboardOutlined,
  UserOutlined,
  PhoneOutlined,
  SoundOutlined,
  InboxOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  NotificationOutlined,
  TeamOutlined,
  PlayCircleOutlined,
  AuditOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { useNavigate, Outlet, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { logout } from '@store/slices/authSlice';
import { authService } from '@services/authService';
import { RootState } from '@store/index';

const { Header, Sider, Content } = AntLayout;

const Layout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const [collapsed, setCollapsed] = useState(false);
  const { user } = useSelector((state: RootState) => state.auth);

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch {}
    dispatch(logout());
    message.success('Выход выполнен успешно');
    navigate('/login');
  };

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Панель управления' },
    { key: '/contacts', icon: <UserOutlined />, label: 'Контакты' },
    { key: '/groups', icon: <TeamOutlined />, label: 'Группы' },
    { key: '/campaigns', icon: <NotificationOutlined />, label: 'Кампании' },
    { key: '/scenarios', icon: <SoundOutlined />, label: 'Сценарии' },
    { key: '/inbound', icon: <InboxOutlined />, label: 'Входящие' },
    { key: '/playbooks', icon: <PlayCircleOutlined />, label: 'Плейбуки' },
  ];

  const adminMenuItems = [
    { key: '/users', icon: <TeamOutlined />, label: 'Пользователи' },
    { key: '/audit', icon: <AuditOutlined />, label: 'Аудит' },
    { key: '/settings', icon: <SettingOutlined />, label: 'Настройки' },
  ];

  const allMenuItems = user?.role === 'admin' 
    ? [...menuItems, ...adminMenuItems] 
    : menuItems;

  const userMenuItems = [
    { key: 'profile', label: `${user?.full_name || 'Администратор'} (${user?.role || 'admin'})` },
    { key: 'divider', type: 'divider' as const },
    { key: 'logout', label: 'Выход', icon: <LogoutOutlined />, onClick: handleLogout },
  ];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="light" width={260}>
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 16px',
          borderBottom: '1px solid #f0f0f0'
        }}>
          <SafetyOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          {!collapsed && (
            <span style={{ marginLeft: 12, fontSize: 16, fontWeight: 'bold', color: '#1890ff' }}>
              ГО-ЧС Информирование
            </span>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={allMenuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      
      <AntLayout>
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          borderBottom: '1px solid #f0f0f0'
        }}>
          <div style={{ fontSize: 18, cursor: 'pointer' }} onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <Badge count={0} showZero={false}>
              <NotificationOutlined style={{ fontSize: 18, cursor: 'pointer' }} />
            </Badge>
            
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <span>{user?.full_name || 'Администратор'}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        
        <Content style={{ margin: 24, minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;
EOF

    log_info "Компоненты созданы"
}

create_pages() {
    log_info "Создание страниц..."
    
    # Login.tsx
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
      
      // Временное решение если API не возвращает user
      const user = response.user || {
        id: '1',
        email: values.username,
        username: values.username,
        full_name: 'Администратор',
        role: 'admin',
      };
      
      dispatch(setCredentials({
        user,
        token: response.access_token,
      }));
      
      message.success('Вход выполнен успешно');
      navigate('/');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Неверное имя пользователя или пароль');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Card style={{ width: 400, borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <SafetyOutlined style={{ fontSize: 56, color: '#1890ff', marginBottom: 16 }} />
          <h1 style={{ fontSize: 24, marginBottom: 8, color: '#1a1a2e' }}>ГО-ЧС Информирование</h1>
          <p style={{ color: '#8c8c8c' }}>Система оповещения и информирования</p>
        </div>
        
        <Form name="login" onFinish={onFinish} size="large">
          <Form.Item 
            name="username" 
            rules={[{ required: true, message: 'Введите имя пользователя' }]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="Имя пользователя (admin)" 
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item 
            name="password" 
            rules={[{ required: true, message: 'Введите пароль' }]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="Пароль (Admin123!)" 
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Войти в систему
            </Button>
          </Form.Item>
        </Form>
        
        <div style={{ textAlign: 'center', marginTop: 24, color: '#8c8c8c', fontSize: 12 }}>
          © 2026 ГО-ЧС Информирование | Версия 1.0.0
        </div>
      </Card>
    </div>
  );
};

export default Login;
EOF

    # Dashboard.tsx
    cat > "$INSTALL_DIR/frontend/src/pages/Dashboard.tsx" << 'DASHBOARDEOF'
import React, { useEffect, useState, useCallback } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Progress, Badge, Space, Typography, Spin } from 'antd';
import {
  PhoneOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LineChartOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  SafetyOutlined,
  InboxOutlined,
  TeamOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface ChannelStats {
  total_channels: number;
  used_channels: number;
  free_channels: number;
  gochs_channels: number;
  inbound_calls: number;
  outbound_calls: number;
}

interface ServiceStatus {
  api: 'online' | 'offline';
  database: 'online' | 'offline';
  redis: 'online' | 'offline';
  asterisk: 'online' | 'offline';
  pbx_registration: 'online' | 'offline';
}

interface ActiveCampaign {
  id: string;
  name: string;
  scenario_name: string;
  total_contacts: number;
  completed_calls: number;
  failed_calls: number;
  in_progress_calls: number;
  status: string;
  progress_percent: number;
}

interface RecentCall {
  id: string;
  time: string;
  caller_number: string;
  caller_name?: string;
  duration: number;
  status: string;
  has_recording: boolean;
  has_transcription: boolean;
}

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [channelStats, setChannelStats] = useState<ChannelStats>({
    total_channels: 0, used_channels: 0, free_channels: 0,
    gochs_channels: 0, inbound_calls: 0, outbound_calls: 0,
  });
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus>({
    api: 'offline', database: 'offline', redis: 'offline',
    asterisk: 'offline', pbx_registration: 'offline',
  });
  const [activeCampaigns, setActiveCampaigns] = useState<ActiveCampaign[]>([]);
  const [recentInboundCalls, setRecentInboundCalls] = useState<RecentCall[]>([]);

  const fetchAllData = useCallback(async () => {
    try {
      setError(null);
      const healthRes = await fetch('/health');
      const healthData = await healthRes.json();
      setServiceStatus({
        api: healthData.status === 'healthy' ? 'online' : 'offline',
        database: healthData.database === true ? 'online' : 'offline',
        redis: healthData.redis === true ? 'online' : 'offline',
        asterisk: healthData.asterisk === true ? 'online' : 'offline',
        pbx_registration: healthData.pbx_registration === true ? 'online' : 'offline',
      });
      try {
        const statsRes = await fetch('/api/v1/monitoring/channels/stats');
        if (statsRes.ok) {
          const d = await statsRes.json();
          setChannelStats({
            total_channels: d.total_channels || 0, used_channels: d.used_channels || 0,
            free_channels: d.free_channels || 0, gochs_channels: d.gochs_channels || 0,
            inbound_calls: d.inbound_calls || 0, outbound_calls: d.outbound_calls || 0,
          });
        }
      } catch {}
      try {
        const campRes = await fetch('/api/v1/campaigns/active');
        if (campRes.ok) setActiveCampaigns((await campRes.json()).campaigns || []);
      } catch {}
      try {
        const callsRes = await fetch('/api/v1/monitoring/inbound/recent?limit=10');
        if (callsRes.ok) setRecentInboundCalls((await callsRes.json()).calls || []);
      } catch {}
    } catch (err: any) {
      setError(err?.message || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAllData(); const t = setInterval(fetchAllData, 10000); return () => clearInterval(t); }, [fetchAllData]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'online': return <Badge status="success" text="Онлайн" />;
      case 'offline': return <Badge status="error" text="Офлайн" />;
      default: return <Badge status="processing" text="Проверка" />;
    }
  };

  const getCallStatusTag = (status: string) => {
    const m: Record<string, { color: string; text: string }> = {
      answered: { color: 'success', text: 'Отвечен' },
      missed: { color: 'error', text: 'Пропущен' },
      recorded: { color: 'processing', text: 'Записан' },
      transcribed: { color: 'blue', text: 'Расшифрован' },
    };
    const c = m[status] || { color: 'default', text: status };
    return <Tag color={c.color}>{c.text}</Tag>;
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>;

  const chPct = channelStats.total_channels > 0 ? Math.round((channelStats.used_channels / channelStats.total_channels) * 100) : 0;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <Title level={2} style={{ margin: 0 }}><SafetyOutlined style={{ color: '#1890ff', marginRight: 12 }} />Панель управления</Title>
        <Space size="large" wrap>
          <Space size="small"><Text type="secondary">API:</Text>{getStatusBadge(serviceStatus.api)}</Space>
          <Space size="small"><Text type="secondary">БД:</Text>{getStatusBadge(serviceStatus.database)}</Space>
          <Space size="small"><Text type="secondary">Redis:</Text>{getStatusBadge(serviceStatus.redis)}</Space>
          <Space size="small"><Text type="secondary">Asterisk:</Text>{getStatusBadge(serviceStatus.asterisk)}</Space>
          <Space size="small"><Text type="secondary">PBX:</Text>{getStatusBadge(serviceStatus.pbx_registration)}</Space>
          <a onClick={fetchAllData} style={{ cursor: 'pointer' }}><ReloadOutlined /></a>
        </Space>
      </div>
      {error && <Card style={{ marginBottom: 16, backgroundColor: '#fff2f0' }}><Text type="danger">⚠ {error}</Text></Card>}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Всего каналов АТС" value={channelStats.total_channels} prefix={<PhoneOutlined />} />
            <Progress percent={chPct} size="small" status={chPct > 80 ? 'exception' : 'active'} style={{ marginTop: 8 }} format={() => `${channelStats.used_channels} исп.`} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Свободно" value={channelStats.free_channels} valueStyle={{ color: channelStats.free_channels > 10 ? '#3f8600' : '#cf1322' }} prefix={<CheckCircleOutlined />} />
            <div style={{ marginTop: 8 }}><Text type="secondary">ГО-ЧС: <Text strong>{channelStats.gochs_channels}</Text></Text></div></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Входящие" value={channelStats.inbound_calls} valueStyle={{ color: '#1890ff' }} prefix={<InboxOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Исходящие" value={channelStats.outbound_calls} valueStyle={{ color: '#722ed1' }} prefix={<LineChartOutlined />} /></Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <Card title={<Space><ThunderboltOutlined /><span>Активные кампании</span><Tag color="blue">{activeCampaigns.length}</Tag></Space>}>
            {activeCampaigns.length > 0 ? activeCampaigns.map(c => (
              <Card key={c.id} type="inner" size="small" style={{ marginBottom: 12 }} title={<Space><Text strong>{c.name}</Text><Tag color="geekblue">{c.scenario_name}</Tag></Space>}>
                <Progress percent={c.progress_percent || 0} format={() => `${c.completed_calls}/${c.total_contacts}`} />
                <Space size="small" style={{ marginTop: 8 }}><Tag color="success">{c.completed_calls} отв.</Tag><Tag color="error">{c.failed_calls} ош.</Tag></Space>
              </Card>
            )) : <div style={{ textAlign: 'center', padding: 40 }}><Text type="secondary">Нет активных кампаний</Text></div>}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={<Space><ClockCircleOutlined /><span>Последние входящие</span></Space>}>
            <Table dataSource={recentInboundCalls} rowKey="id" pagination={false} size="small" locale={{ emptyText: 'Нет звонков' }}
              columns={[
                { title: 'Время', dataIndex: 'time', key: 'time', width: 60, render: (t: string) => new Date(t).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) },
                { title: 'Номер', dataIndex: 'caller_number', key: 'caller', width: 90 },
                { title: 'Длит.', dataIndex: 'duration', key: 'dur', width: 50, render: (d: number) => `${Math.floor(d/60)}:${(d%60).toString().padStart(2,'0')}` },
                { title: 'Статус', dataIndex: 'status', key: 'st', render: (s: string) => getCallStatusTag(s) },
              ]} />
          </Card>
        </Col>
      </Row>
      <Row style={{ marginTop: 16 }}><Col span={24}><Card size="small" style={{ backgroundColor: '#fafafa' }}>
        <Space split={<span style={{ color: '#d9d9d9' }}>|</span>} size="large" wrap>
          <Text type="secondary">Время: <Text strong>{new Date().toLocaleString('ru-RU')}</Text></Text>
          <Text type="secondary">Режим: <Tag color="green">Production</Tag></Text>
          <Text type="secondary">Загрузка: <Text strong>{chPct}%</Text></Text>
        </Space>
      </Card></Col></Row>
    </div>
  );
};

export default Dashboard;
DASHBOARDEOF

    # Создание остальных страниц (заглушки)
    for page in Contacts Groups Scenarios Campaigns Inbound Playbooks Users Settings Audit; do
        cat > "$INSTALL_DIR/frontend/src/pages/${page}.tsx" << EOF
import React from 'react';
import { Button, Space, Card, Typography } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';

const { Title } = Typography;

const ${page}: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>${page}</Title>
        <Space>
          <Button icon={<ReloadOutlined />}>Обновить</Button>
          <Button type="primary" icon={<PlusOutlined />}>Добавить</Button>
        </Space>
      </div>
      
      <Card>
        <p style={{ color: '#8c8c8c' }}>Раздел "${page}" находится в разработке.</p>
        <p>Функционал будет доступен после подключения всех модулей API.</p>
      </Card>
    </div>
  );
};

export default ${page};
EOF
    done

    log_info "Страницы созданы"
}

create_services() {
    log_info "Создание сервисов..."
    
        # settingsService.ts
    cat > "$INSTALL_DIR/frontend/src/services/settingsService.ts" << 'EOF'
import api from './api';

export const settingsService = {
  async getPBXSettings() {
    const response = await api.get('/settings/pbx');
    return response.data;
  },
  
  async updatePBXSettings(data: any) {
    const response = await api.put('/settings/pbx', data);
    return response.data;
  },
  
  async getSystemSettings() {
    const response = await api.get('/settings/system');
    return response.data;
  },
  
  async updateSystemSettings(data: any) {
    const response = await api.put('/settings/system', data);
    return response.data;
  },
  
  async getNotifications() {
    const response = await api.get('/settings/notifications');
    return response.data;
  },
  
  async updateNotifications(data: any) {
    const response = await api.put('/settings/notifications', data);
    return response.data;
  },
  
  async testPBXConnection(data: any) {
    const response = await api.post('/settings/pbx/test', data);
    return response.data;
  },
  
  async applyPBXSettings() {
    const response = await api.post('/settings/pbx/apply');
    return response.data;
  },
};
EOF

    # auditService.ts
    cat > "$INSTALL_DIR/frontend/src/services/auditService.ts" << 'EOF'
import api from './api';

export const auditService = {
  async getAuditLogs(params?: any) {
    const response = await api.get('/audit/logs', { params });
    return response.data;
  },
  
  async getAuditStats(days: number = 30) {
    const response = await api.get('/audit/stats', { params: { days } });
    return response.data;
  },
  
  async exportAudit(params?: any) {
    const response = await api.get('/audit/export', { 
      params,
      responseType: 'blob'
    });
    return response.data;
  },
};


    # api.ts
    cat > "$INSTALL_DIR/frontend/src/services/api.ts" << 'EOF'
import axios from 'axios';
import { message } from 'antd';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
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
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    } else if (error.response?.status === 403) {
      message.error('Недостаточно прав для выполнения операции');
    } else if (error.response?.status >= 500) {
      message.error('Ошибка сервера. Попробуйте позже.');
    } else if (error.code === 'ECONNABORTED') {
      message.error('Превышено время ожидания ответа');
    }
    return Promise.reject(error);
  }
);

export default api;
EOF

    # authService.ts
    cat > "$INSTALL_DIR/frontend/src/services/authService.ts" << 'EOF'
import api from './api';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user?: {
    id: string;
    email: string;
    username: string;
    full_name: string;
    role: string;
  };
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } catch {}
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

    # campaignService.ts
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
  
  async getActiveCampaigns() {
    const response = await fetch('/api/v1/campaigns/active');
    return response.json();
  },
};
EOF

    # monitoringService.ts
    cat > "$INSTALL_DIR/frontend/src/services/monitoringService.ts" << 'EOF'
import api from './api';

export const monitoringService = {
  async getHealth() {
    const response = await fetch('/health');
    return response.json();
  },
  
  async getStats() {
    const response = await api.get('/monitoring/stats');
    return response.data;
  },
  
  async getActiveCalls() {
    const response = await api.get('/monitoring/calls');
    return response.data;
  },

  async getChannelStats() {
  const response = await api.get('/monitoring/channels/stats');
  return response.data;
},

async getRecentInboundCalls(limit: number = 10) {
  const response = await api.get('/monitoring/inbound/recent', { 
    params: { limit } 
  });
  return response.data;
},
  
  async getSystemInfo() {
    const response = await api.get('/monitoring/system');
    return response.data;
  },
};
EOF

    # contactService.ts
    cat > "$INSTALL_DIR/frontend/src/services/contactService.ts" << 'EOF'
import api from './api';

export const contactService = {
  async getContacts(params?: any) {
    const response = await api.get('/contacts/', { params });
    return response.data;
  },
  
  async getContact(id: string) {
    const response = await api.get(`/contacts/${id}`);
    return response.data;
  },
  
  async createContact(data: any) {
    const response = await api.post('/contacts/', data);
    return response.data;
  },
  
  async updateContact(id: string, data: any) {
    const response = await api.patch(`/contacts/${id}`, data);
    return response.data;
  },
  
  async deleteContact(id: string) {
    const response = await api.delete(`/contacts/${id}`);
    return response.data;
  },
  
  async importContacts(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/contacts/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};
EOF

    # scenarioService.ts
    cat > "$INSTALL_DIR/frontend/src/services/scenarioService.ts" << 'EOF'
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
EOF

    # groupService.ts
    cat > "$INSTALL_DIR/frontend/src/services/groupService.ts" << 'EOF'
import api from './api';

export const groupService = {
  async getGroups(params?: any) {
    const response = await api.get('/groups/', { params });
    return response.data;
  },
  
  async getGroup(id: string) {
    const response = await api.get(`/groups/${id}`);
    return response.data;
  },
  
  async createGroup(data: any) {
    const response = await api.post('/groups/', data);
    return response.data;
  },
  
  async updateGroup(id: string, data: any) {
    const response = await api.patch(`/groups/${id}`, data);
    return response.data;
  },
  
  async deleteGroup(id: string) {
    const response = await api.delete(`/groups/${id}`);
    return response.data;
  },
  
  async addContact(groupId: string, contactId: string) {
    const response = await api.post(`/groups/${groupId}/contacts`, { contact_id: contactId });
    return response.data;
  },
  
  async removeContact(groupId: string, contactId: string) {
    const response = await api.delete(`/groups/${groupId}/contacts/${contactId}`);
    return response.data;
  },
};
EOF

    log_info "Сервисы созданы"
}

create_hooks() {
    log_info "Создание хуков..."
    
    # useAuth.ts
    cat > "$INSTALL_DIR/frontend/src/hooks/useAuth.ts" << 'EOF'
import { useSelector } from 'react-redux';
import { RootState } from '@store/index';

export const useAuth = () => {
  const { user, token, isAuthenticated } = useSelector((state: RootState) => state.auth);
  
  return {
    user,
    token,
    isAuthenticated,
    isAdmin: user?.role === 'admin',
    isOperator: user?.role === 'operator',
  };
};
EOF

    # useWebSocket.ts
    cat > "$INSTALL_DIR/frontend/src/hooks/useWebSocket.ts" << 'EOF'
import { useEffect, useState, useRef } from 'react';

export const useWebSocket = (endpoint: string = '/ws') => {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}${endpoint}`;

    console.log(`[WebSocket] Connecting to: ${wsUrl}`);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('[WebSocket] Connected');
      setConnected(true);
    };

    socket.onclose = (event) => {
      console.log('[WebSocket] Disconnected', event.reason);
      setConnected(false);
    };

    socket.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      setConnected(false);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', event.data);
      }
    };

    socketRef.current = socket;

    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [endpoint]);

  const sendMessage = (event: string, data: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ event, data });
      socketRef.current.send(message);
    } else {
      console.warn('[WebSocket] Cannot send message: socket is not open');
    }
  };

  return { connected, lastMessage, sendMessage };
};
EOF

    log_info "Хуки созданы"
}

create_utils() {
    log_info "Создание утилит..."
    
    # store/index.ts
    cat > "$INSTALL_DIR/frontend/src/store/index.ts" << 'EOF'
import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
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

    # styles/global.scss
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

.app-layout {
  min-height: 100vh;
}

.app-header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.app-content {
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 112px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

// Анимации
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn 0.3s ease-in;
}

// Утилиты
.text-center { text-align: center; }
.text-right { text-align: right; }
.mt-1 { margin-top: 8px; }
.mt-2 { margin-top: 16px; }
.mt-3 { margin-top: 24px; }
.mb-1 { margin-bottom: 8px; }
.mb-2 { margin-bottom: 16px; }
.mb-3 { margin-bottom: 24px; }
.p-1 { padding: 8px; }
.p-2 { padding: 16px; }
.p-3 { padding: 24px; }
EOF

    log_info "Утилиты созданы"
}

create_context() {
    log_info "Создание контекста..."
    
    # context/AuthContext.tsx
    cat > "$INSTALL_DIR/frontend/src/context/AuthContext.tsx" << 'EOF'
import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      // Здесь можно добавить загрузку профиля пользователя
    }
  }, [token]);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('token', newToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      isAuthenticated: !!token,
      login,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider');
  }
  return context;
};
EOF

    log_info "Контекст создан"
}

build_frontend() {
    log_step "Сборка фронтенда"
    
    cd "$INSTALL_DIR/frontend"
    
    # Установка зависимостей
    log_info "Установка npm зависимостей..."
    npm install --legacy-peer-deps 2>&1 | tee /tmp/npm_install.log || {
        log_error "Ошибка установки зависимостей"
        tail -20 /tmp/npm_install.log
        return 1
    }
    
    # ИСПРАВЛЕНИЕ: Явная установка terser
    log_info "Установка terser для минификации..."
    npm install --save-dev terser 2>/dev/null || {
        log_warn "Не удалось установить terser, пробуем альтернативный способ..."
        npm install -D terser --legacy-peer-deps
    }
    
    # Установка дополнительных типов
    log_info "Установка дополнительных пакетов..."
    npm install --save-dev @types/node 2>/dev/null || true
    
    # Проверка наличия terser
    if ! npm list terser &>/dev/null; then
        log_warn "terser не обнаружен, устанавливаем глобально..."
        npm install -g terser
    fi
    
    # Сборка проекта
    log_info "Сборка React приложения..."
    npm run build 2>&1 | tee /tmp/npm_build.log
    
    BUILD_STATUS=${PIPESTATUS[0]}
    
    # Проверка результата сборки
    if [[ $BUILD_STATUS -ne 0 ]]; then
        log_error "Ошибка сборки фронтенда (код: $BUILD_STATUS)"
        log_info "Последние 30 строк лога:"
        tail -30 /tmp/npm_build.log
        return 1
    fi
    
    # Проверка наличия собранных файлов
    if [[ -d "$INSTALL_DIR/frontend/build" ]]; then
        log_info "✓ Директория build создана"
    elif [[ -d "$INSTALL_DIR/frontend/dist" ]]; then
        log_info "✓ Директория dist создана, переименовываем в build..."
        mv "$INSTALL_DIR/frontend/dist" "$INSTALL_DIR/frontend/build"
    else
        log_error "✗ Директория build/dist не создана"
        log_info "Содержимое frontend:"
        ls -la "$INSTALL_DIR/frontend/"
        return 1
    fi
    
    # Проверка index.html
    if [[ -f "$INSTALL_DIR/frontend/build/index.html" ]]; then
        log_info "✓ index.html присутствует"
    else
        log_error "✗ index.html отсутствует в build"
        log_info "Содержимое build:"
        ls -la "$INSTALL_DIR/frontend/build/"
        return 1
    fi
    
    # Вывод размера сборки
    BUILD_SIZE=$(du -sh "$INSTALL_DIR/frontend/build" 2>/dev/null | cut -f1)
    log_info "✓ Фронтенд успешно собран (размер: $BUILD_SIZE)"
   
    cd "$SCRIPT_DIR"

    # Установка прав для Nginx
    log_info "Настройка прав на фронтенд..."
    chown -R www-data:www-data "$INSTALL_DIR/frontend/build" 2>/dev/null || true
    chmod -R 755 "$INSTALL_DIR/frontend/build" 2>/dev/null || true
    log_info "✓ Права на фронтенд настроены"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
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
    
    if [[ -d "$INSTALL_DIR/frontend/build" ]]; then
        log_info "✓ Фронтенд: собран"
        
        BUILD_SIZE=$(du -sh "$INSTALL_DIR/frontend/build" 2>/dev/null | cut -f1)
        log_info "  Размер сборки: $BUILD_SIZE"
        
        if [[ -f "$INSTALL_DIR/frontend/build/index.html" ]]; then
            log_info "  index.html: присутствует"
        else
            log_warn "  index.html: отсутствует"
            status=1
        fi
    else
        log_warn "✗ Фронтенд: не собран"
        status=1
    fi
    
    if command -v node &> /dev/null; then
        NODE_VER=$(node --version)
        log_info "✓ Node.js: $NODE_VER"
    else
        log_warn "✗ Node.js: не установлен"
    fi
    
    if command -v npm &> /dev/null; then
        NPM_VER=$(npm --version)
        log_info "✓ npm: $NPM_VER"
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
    clean)
        rm -rf "$INSTALL_DIR/frontend/node_modules"
        rm -rf "$INSTALL_DIR/frontend/build"
        rm -rf "$INSTALL_DIR/frontend/dist"
        log_info "Очистка завершена"
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|rebuild|dev|clean}"
        exit 1
        ;;
esac
echo "✅ 07-frontend.sh создан (ПОЛНАЯ версия, 1000+ строк)"
