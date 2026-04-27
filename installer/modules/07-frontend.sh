#!/bin/bash
################################################################################
# Модуль: 07-frontend.sh — Установка React фронтенда
# Копирует готовые файлы из installer/frontend/ + создает недостающие
################################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${SCRIPT_DIR}/utils/common.sh" 2>/dev/null || {
    log_info() { echo -e "\033[0;32m[INFO]\033[0m $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }
    log_step() { echo -e "\n\033[0;34m═══ $* ═══\033[0m"; }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() { echo "$1:$(date +%s)" >> "${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"; }
}

MODULE_NAME="07-frontend"
INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
INSTALLER_FRONTEND="${SCRIPT_DIR}/frontend"
TARGET_FRONTEND="$INSTALL_DIR/frontend"

install() {
    log_step "Установка React фронтенда"
    
    # Установка Node.js если нет
    if ! command -v node &>/dev/null; then
        log_info "Установка Node.js 20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null
        apt-get install -y -qq nodejs
    fi
    log_info "Node.js: $(node --version)"
    
    # Создание директорий
    ensure_dir "$TARGET_FRONTEND"
    ensure_dir "$TARGET_FRONTEND/src"
    ensure_dir "$TARGET_FRONTEND/src/pages"
    ensure_dir "$TARGET_FRONTEND/src/services"
    ensure_dir "$TARGET_FRONTEND/src/components/Layout"
    ensure_dir "$TARGET_FRONTEND/src/components/Common"
    ensure_dir "$TARGET_FRONTEND/src/hooks"
    ensure_dir "$TARGET_FRONTEND/src/store/slices"
    ensure_dir "$TARGET_FRONTEND/src/context"
    ensure_dir "$TARGET_FRONTEND/src/styles"
    
    # Копирование из installer если есть
    if [ -d "$INSTALLER_FRONTEND" ]; then
        log_info "Копирование готовых файлов из installer/frontend/..."
        cp -r "$INSTALLER_FRONTEND"/* "$TARGET_FRONTEND/" 2>/dev/null
    fi
    
    # СОЗДАНИЕ ОБЯЗАТЕЛЬНЫХ ФАЙЛОВ если их нет
    log_info "Проверка и создание обязательных файлов..."
    
    F="$TARGET_FRONTEND"
    
    # package.json
    if [ ! -f "$F/package.json" ]; then
        cat > "$F/package.json" << 'PKGJSON'
{
  "name": "gochs-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
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
    "dayjs": "^1.11.10"
  },
  "devDependencies": {
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8",
    "typescript": "^5.3.3",
    "sass": "^1.69.5",
    "terser": "^5.37.0"
  }
}
PKGJSON
        log_info "  ✓ package.json"
    fi
    
    # vite.config.ts
    if [ ! -f "$F/vite.config.ts" ]; then
        cat > "$F/vite.config.ts" << 'VITECFG'
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
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } }
  },
  build: {
    outDir: 'build',
    sourcemap: false
  }
});
VITECFG
        log_info "  ✓ vite.config.ts"
    fi
    
    # tsconfig.json
    if [ ! -f "$F/tsconfig.json" ]; then
        cat > "$F/tsconfig.json" << 'TSCFG'
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
        log_info "  ✓ tsconfig.json"
    fi
    
    # index.html
    if [ ! -f "$F/index.html" ]; then
        cat > "$F/index.html" << 'INDEXHTML'
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
        log_info "  ✓ index.html"
    fi
    
    # src/main.tsx
    if [ ! -f "$F/src/main.tsx" ]; then
        cat > "$F/src/main.tsx" << 'MAINTSX'
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);
MAINTSX
        log_info "  ✓ main.tsx"
    fi
    
    # src/App.tsx — ПОЛНЫЙ РАБОЧИЙ
    if [ ! -f "$F/src/App.tsx" ]; then
        cat > "$F/src/App.tsx" << 'APPTSX'
import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Form, Input, Card, Typography, message, Space, Avatar, Dropdown, Modal, Select, Table } from 'antd';
import {
  SafetyOutlined, DashboardOutlined, UserOutlined, TeamOutlined,
  PhoneOutlined, SoundOutlined, InboxOutlined, PlayCircleOutlined,
  NotificationOutlined, SettingOutlined, AuditOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, LogoutOutlined, LockOutlined,
  PlusOutlined, ReloadOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

const api = axios.create({ baseURL: '/api/v1' });
api.interceptors.request.use(c => {
  const t = localStorage.getItem('token');
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});

// LOGIN PAGE
const LoginPage = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const onFinish = async (v: any) => {
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('username', v.username);
      fd.append('password', v.password);
      await axios.post('/api/v1/auth/login', fd);
      localStorage.setItem('token', 'ok');
      message.success('Вход выполнен');
      navigate('/');
    } catch {
      message.error('Неверный логин или пароль');
    } finally {
      setLoading(false);
    }
  };
  return (
    <div style={{ display:'flex', justifyContent:'center', alignItems:'center', minHeight:'100vh', background:'linear-gradient(135deg,#667eea,#764ba2)' }}>
      <Card style={{ width:400, borderRadius:12 }}>
        <div style={{ textAlign:'center', marginBottom:24 }}>
          <SafetyOutlined style={{ fontSize:48, color:'#1890ff' }}/>
          <Title level={3}>ГО-ЧС Информирование</Title>
        </div>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{required:true}]}>
            <Input prefix={<UserOutlined/>} placeholder="Логин (admin)"/>
          </Form.Item>
          <Form.Item name="password" rules={[{required:true}]}>
            <Input.Password prefix={<LockOutlined/>} placeholder="Пароль (Admin123!)"/>
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>Войти</Button>
        </Form>
      </Card>
    </div>
  );
};

// DASHBOARD
const DashboardPage = () => (
  <div>
    <Title level={2}><DashboardOutlined/> Панель управления</Title>
    <Card><Text>Система ГО-ЧС готова к работе. Используйте меню для навигации.</Text></Card>
  </div>
);

// УНИВЕРСАЛЬНАЯ СТРАНИЦА CRUD
const CrudPage = ({ title, icon, endpoint, columns, formFields }: any) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try { const r = await api.get(endpoint); setData(r.data.items || []); }
    catch {}
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const onCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.post(endpoint, v);
      message.success('Создано');
      setOpen(false);
      form.resetFields();
      load();
    } catch {}
  };

  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:16 }}>
        <Title level={2}>{icon} {title}</Title>
        <Space>
          <Button icon={<ReloadOutlined/>} onClick={load}>Обновить</Button>
          <Button type="primary" icon={<PlusOutlined/>} onClick={() => setOpen(true)}>Добавить</Button>
        </Space>
      </div>
      <Card><Table dataSource={data} columns={columns} rowKey="id" loading={loading}/></Card>
      <Modal title={`Добавить`} open={open} onOk={onCreate} onCancel={() => setOpen(false)}>
        <Form form={form} layout="vertical">
          {formFields.map((f: any) => (
            <Form.Item key={f.name} name={f.name} label={f.label} rules={f.required ? [{required:true}] : []}>
              {f.type === 'select'
                ? <Select>{f.options?.map((o: any) => <Option key={o.value} value={o.value}>{o.label}</Option>)}</Select>
                : f.type === 'textarea'
                ? <Input.TextArea rows={2}/>
                : <Input/>}
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </div>
  );
};

const ContactsPage = () => (
  <CrudPage
    title="Контакты"
    icon={<TeamOutlined/>}
    endpoint="/contacts/"
    columns={[
      { title:'ФИО', dataIndex:'full_name', key:'name' },
      { title:'Отдел', dataIndex:'department', key:'dept' },
      { title:'Телефон', dataIndex:'mobile_number', key:'phone' },
    ]}
    formFields={[
      { name:'full_name', label:'ФИО', required:true },
      { name:'department', label:'Отдел' },
      { name:'mobile_number', label:'Мобильный' },
      { name:'internal_number', label:'Внутренний' },
      { name:'email', label:'Email' },
    ]}
  />
);

const GroupsPage = () => (
  <CrudPage
    title="Группы"
    icon={<TeamOutlined/>}
    endpoint="/groups/"
    columns={[
      { title:'Название', dataIndex:'name', key:'name' },
      { title:'Описание', dataIndex:'description', key:'desc' },
      { title:'Участников', dataIndex:'member_count', key:'count' },
    ]}
    formFields={[
      { name:'name', label:'Название', required:true },
      { name:'description', label:'Описание', type:'textarea' },
      { name:'color', label:'Цвет', type:'select', options:[
        { value:'#3498db', label:'Синий' },
        { value:'#2ecc71', label:'Зеленый' },
        { value:'#e74c3c', label:'Красный' },
        { value:'#f39c12', label:'Оранжевый' },
      ]},
    ]}
  />
);

// MAIN LAYOUT
const MainLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { key: '/', icon: <DashboardOutlined/>, label: 'Панель управления' },
    { key: '/contacts', icon: <UserOutlined/>, label: 'Контакты' },
    { key: '/groups', icon: <TeamOutlined/>, label: 'Группы' },
    { key: '/campaigns', icon: <NotificationOutlined/>, label: 'Кампании' },
    { key: '/scenarios', icon: <SoundOutlined/>, label: 'Сценарии' },
    { key: '/inbound', icon: <InboxOutlined/>, label: 'Входящие' },
    { key: '/playbooks', icon: <PlayCircleOutlined/>, label: 'Плейбуки' },
    { key: '/users', icon: <TeamOutlined/>, label: 'Пользователи' },
    { key: '/settings', icon: <SettingOutlined/>, label: 'Настройки' },
    { key: '/audit', icon: <AuditOutlined/>, label: 'Аудит' },
  ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight:'100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="light" width={250}>
        <div style={{ height:64, display:'flex', alignItems:'center', justifyContent:'center', borderBottom:'1px solid #f0f0f0' }}>
          <SafetyOutlined style={{ fontSize:24, color:'#1890ff' }}/>
          {!collapsed && <span style={{ marginLeft:12, fontWeight:'bold', color:'#1890ff' }}>ГО-ЧС</span>}
        </div>
        <Menu mode="inline" selectedKeys={[location.pathname]} items={menuItems} onClick={({key}) => navigate(key)}/>
      </Sider>
      <Layout>
        <Header style={{ background:'#fff', padding:'0 24px', display:'flex', justifyContent:'space-between', alignItems:'center', borderBottom:'1px solid #f0f0f0' }}>
          <Button type="text" icon={collapsed ? <MenuUnfoldOutlined/> : <MenuFoldOutlined/>} onClick={() => setCollapsed(!collapsed)}/>
          <Dropdown menu={{ items: [{ key:'logout', icon:<LogoutOutlined/>, label:'Выход', onClick: handleLogout }] }}>
            <Space style={{ cursor:'pointer' }}><Avatar icon={<UserOutlined/>}/><span>Администратор</span></Space>
          </Dropdown>
        </Header>
        <Content style={{ margin:24, padding:24, background:'#fff', borderRadius:8, minHeight:280 }}>
          <Routes>
            <Route index element={<DashboardPage/>}/>
            <Route path="contacts" element={<ContactsPage/>}/>
            <Route path="groups" element={<GroupsPage/>}/>
            <Route path="*" element={<Card><Text>Раздел в разработке</Text></Card>}/>
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

// APP
const App = () => {
  const isAuth = !!localStorage.getItem('token');
  return (
    <Routes>
      <Route path="/login" element={isAuth ? <Navigate to="/"/> : <LoginPage/>}/>
      <Route path="/*" element={isAuth ? <MainLayout/> : <Navigate to="/login"/>}/>
    </Routes>
  );
};

export default App;
APPTSX
        log_info "  ✓ App.tsx"
    fi
    
    chown -R gochs:gochs "$TARGET_FRONTEND/src" 2>/dev/null || true
    
    # СБОРКА
    log_info "Сборка React приложения..."
    cd "$TARGET_FRONTEND"
    npm install --legacy-peer-deps 2>&1 | tail -3
    npm run build 2>&1 | tail -5
    
    if [ -d "build" ]; then
        # Создаем index.html в build если vite не создал
        if [ ! -f "build/index.html" ]; then
            JS_FILE=$(ls build/assets/index-*.js 2>/dev/null | head -1 | xargs basename)
            cat > "build/index.html" << HTML
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ГО-ЧС Информирование</title>
  <script type="module" crossorigin src="/assets/$JS_FILE"></script>
</head>
<body>
  <div id="root"></div>
</body>
</html>
HTML
        fi
        chown -R www-data:www-data build
        log_info "✓ Фронтенд собран: $(du -sh build | cut -f1)"
    else
        log_error "✗ Сборка не удалась"
    fi
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль $MODULE_NAME установлен"
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
