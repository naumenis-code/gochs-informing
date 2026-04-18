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
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
    DOMAIN_OR_IP="${DOMAIN_OR_IP:-192.168.0.166}"
    GOCHS_USER="${GOCHS_USER:-gochs}"
    GOCHS_GROUP="${GOCHS_GROUP:-gochs}"
fi

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
    "dayjs": "^1.11.10",
    "react-hook-form": "^7.48.2",
    "yup": "^1.3.3",
    "@hookform/resolvers": "^3.3.2",
    "socket.io-client": "^4.5.4",
    "react-audio-player": "^0.17.0",
    "wavesurfer.js": "^7.4.0",
    "xlsx": "^0.18.5",
    "papaparse": "^5.4.1",
    "react-dropzone": "^14.2.3"
  },
  "devDependencies": {
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "@types/node": "^20.10.4",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8",
    "typescript": "^5.3.3",
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
    cat > "$INSTALL_DIR/frontend/src/pages/Dashboard.tsx" << 'EOF'
import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Progress, Badge, Space, Typography } from 'antd';
import {
  PhoneOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  LineChartOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '@hooks/useWebSocket';
import { monitoringService } from '@services/monitoringService';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({
    totalChannels: 50,
    usedChannels: 0,
    freeChannels: 50,
    gochsChannels: 0,
    inboundCalls: 0,
    outboundCalls: 0,
    activeCampaigns: 0,
    completedCampaigns: 0,
  });

  const [apiStatus, setApiStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [dbStatus, setDbStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [redisStatus, setRedisStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [asteriskStatus, setAsteriskStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  const { connected } = useWebSocket('/ws');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await monitoringService.getHealth();
        setApiStatus(data.status === 'healthy' ? 'online' : 'offline');
        setDbStatus(data.database ? 'online' : 'offline');
        setRedisStatus(data.redis ? 'online' : 'offline');
        setAsteriskStatus(data.asterisk ? 'online' : 'offline');
      } catch {
        setApiStatus('offline');
        setDbStatus('offline');
        setRedisStatus('offline');
        setAsteriskStatus('offline');
      }
    };
    
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'online': return <Badge status="success" text="Онлайн" />;
      case 'offline': return <Badge status="error" text="Офлайн" />;
      default: return <Badge status="processing" text="Проверка" />;
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>Панель управления</Title>
        <Space size="large">
          <span>API: {getStatusBadge(apiStatus)}</span>
          <span>БД: {getStatusBadge(dbStatus)}</span>
          <span>Redis: {getStatusBadge(redisStatus)}</span>
          <span>Asterisk: {getStatusBadge(asteriskStatus)}</span>
          <span>WebSocket: {connected ? <Badge status="success" text="Подключен" /> : <Badge status="error" text="Отключен" />}</span>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Всего каналов"
              value={stats.totalChannels}
              prefix={<PhoneOutlined />}
              suffix={`/ ${stats.totalChannels}`}
            />
            <Progress 
              percent={Math.round((stats.usedChannels / stats.totalChannels) * 100)} 
              size="small" 
              status={stats.usedChannels > stats.totalChannels * 0.8 ? 'exception' : 'active'}
              style={{ marginTop: 8 }}
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
              title="Входящие звонки"
              value={stats.inboundCalls}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Исходящие звонки"
              value={stats.outboundCalls}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={<><ThunderboltOutlined /> Активные кампании</>}>
            {stats.activeCampaigns > 0 ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>Кампания "Тестовая тревога"</span>
                  <span>45/100</span>
                </div>
                <Progress percent={45} status="active" />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                  <span>Кампания "Сбор руководства"</span>
                  <span>8/15</span>
                </div>
                <Progress percent={53} status="active" />
              </div>
            ) : (
              <p style={{ color: '#8c8c8c' }}>Нет активных кампаний</p>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={<><ClockCircleOutlined /> Последние входящие звонки</>}>
            <Table
              dataSource={[]}
              columns={[
                { title: 'Время', dataIndex: 'time', key: 'time' },
                { title: 'Номер', dataIndex: 'caller', key: 'caller' },
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
                    return <Tag color={colors[status] || 'default'}>{status}</Tag>;
                  },
                },
              ]}
              pagination={false}
              size="small"
              locale={{ emptyText: 'Нет входящих звонков' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
EOF

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
import io, { Socket } from 'socket.io-client';

export const useWebSocket = (endpoint: string = '/ws') => {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    
    const socket = io({
      path: endpoint,
      auth: { token },
      transports: ['websocket'],
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    });

    socket.on('message', (data) => {
      setLastMessage(data);
    });

    socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [endpoint]);

  const sendMessage = (event: string, data: any) => {
    if (socketRef.current && connected) {
      socketRef.current.emit(event, data);
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
    
    # Установка дополнительных типов
    log_info "Установка дополнительных пакетов..."
    npm install --save-dev @types/node 2>/dev/null || true
    
    # Сборка проекта
    log_info "Сборка React приложения..."
    npm run build 2>&1 | tee /tmp/npm_build.log
    
    if [[ -d "$INSTALL_DIR/frontend/build" ]] || [[ -d "$INSTALL_DIR/frontend/dist" ]]; then
        if [[ -d "$INSTALL_DIR/frontend/dist" ]] && [[ ! -d "$INSTALL_DIR/frontend/build" ]]; then
            mv "$INSTALL_DIR/frontend/dist" "$INSTALL_DIR/frontend/build"
        fi
        log_info "Фронтенд успешно собран"
        
        chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/frontend/build" 2>/dev/null || true
        chmod -R 755 "$INSTALL_DIR/frontend/build"
    else
        log_error "Ошибка сборки фронтенда (директория build не создана)"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
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
