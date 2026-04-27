import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Form, Input, Card, Typography, message, Space, Avatar, Dropdown, Modal, Select, Table } from 'antd';
import { SafetyOutlined, DashboardOutlined, UserOutlined, TeamOutlined, PhoneOutlined, SoundOutlined, InboxOutlined, PlayCircleOutlined, NotificationOutlined, SettingOutlined, AuditOutlined, MenuFoldOutlined, MenuUnfoldOutlined, LogoutOutlined, LockOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;
const api = axios.create({ baseURL: '/api/v1' });
api.interceptors.request.use(c => { const t = localStorage.getItem('token'); if(t) c.headers.Authorization = `Bearer ${t}`; return c; });

const LoginPage = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const onFinish = async (v: any) => {
    setLoading(true);
    try { const fd = new FormData(); fd.append('username',v.username); fd.append('password',v.password);
          await axios.post('/api/v1/auth/login', fd); localStorage.setItem('token','ok'); message.success('Вход выполнен'); navigate('/'); }
    catch { message.error('Неверный логин или пароль'); }
    finally { setLoading(false); }
  };
  return (
    <div style={{display:'flex',justifyContent:'center',alignItems:'center',minHeight:'100vh',background:'linear-gradient(135deg,#667eea,#764ba2)'}}>
      <Card style={{width:400,borderRadius:12}}>
        <div style={{textAlign:'center',marginBottom:24}}>
          <SafetyOutlined style={{fontSize:48,color:'#1890ff'}}/>
          <Title level={3}>ГО-ЧС Информирование</Title>
        </div>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{required:true}]}><Input prefix={<UserOutlined/>} placeholder="Логин (admin)"/></Form.Item>
          <Form.Item name="password" rules={[{required:true}]}><Input.Password prefix={<LockOutlined/>} placeholder="Пароль (Admin123!)"/></Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>Войти</Button>
        </Form>
      </Card>
    </div>
  );
};

const DashboardPage = () => (<div><Title level={2}><DashboardOutlined/> Панель управления</Title><Card><Text>Система ГО-ЧС готова к работе.</Text></Card></div>);

const ListPage = ({ title, icon, endpoint, columns, formFields }: any) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const load = async () => { setLoading(true); try { const r = await api.get(endpoint); setData(r.data.items||[]); } catch {} finally { setLoading(false); } };
  useEffect(() => { load(); }, []);
  const onCreate = async () => { try { const v = await form.validateFields(); await api.post(endpoint, v); message.success('Создано'); setOpen(false); form.resetFields(); load(); } catch {} };
  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',marginBottom:16}}>
        <Title level={2}>{icon} {title}</Title>
        <Space><Button icon={<ReloadOutlined/>} onClick={load}>Обновить</Button><Button type="primary" icon={<PlusOutlined/>} onClick={()=>setOpen(true)}>Добавить</Button></Space>
      </div>
      <Card><Table dataSource={data} columns={columns} rowKey="id" loading={loading}/></Card>
      <Modal title={`Новый ${title.toLowerCase()}`} open={open} onOk={onCreate} onCancel={()=>setOpen(false)}>
        <Form form={form} layout="vertical">{formFields.map((f:any)=><Form.Item key={f.name} name={f.name} label={f.label} rules={f.required?[{required:true}]:[]}>{f.type==='select'?<Select>{f.options?.map((o:any)=><Option key={o.value} value={o.value}>{o.label}</Option>)}</Select>:f.type==='textarea'?<Input.TextArea rows={2}/>:<Input/>}</Form.Item>)}</Form>
      </Modal>
    </div>
  );
};

const ContactsPage = () => <ListPage title="Контакты" icon={<TeamOutlined/>} endpoint="/contacts/" columns={[{title:'ФИО',dataIndex:'full_name'},{title:'Отдел',dataIndex:'department'},{title:'Телефон',dataIndex:'mobile_number'}]} formFields={[{name:'full_name',label:'ФИО',required:true},{name:'department',label:'Отдел'},{name:'mobile_number',label:'Мобильный'},{name:'internal_number',label:'Внутренний'},{name:'email',label:'Email'}]}/>;
const GroupsPage = () => <ListPage title="Группы" icon={<TeamOutlined/>} endpoint="/groups/" columns={[{title:'Название',dataIndex:'name'},{title:'Описание',dataIndex:'description'},{title:'Участников',dataIndex:'member_count'}]} formFields={[{name:'name',label:'Название',required:true},{name:'description',label:'Описание',type:'textarea'},{name:'color',label:'Цвет',type:'select',options:[{value:'#3498db',label:'Синий'},{value:'#2ecc71',label:'Зеленый'},{value:'#e74c3c',label:'Красный'}]}]}/>;

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
  return (
    <Layout style={{minHeight:'100vh'}}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="light" width={250}>
        <div style={{height:64,display:'flex',alignItems:'center',justifyContent:'center',borderBottom:'1px solid #f0f0f0'}}>
          <SafetyOutlined style={{fontSize:24,color:'#1890ff'}}/>{!collapsed && <span style={{marginLeft:12,fontWeight:'bold',color:'#1890ff'}}>ГО-ЧС</span>}
        </div>
        <Menu mode="inline" selectedKeys={[location.pathname]} items={menuItems} onClick={({key})=>navigate(key)}/>
      </Sider>
      <Layout>
        <Header style={{background:'#fff',padding:'0 24px',display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #f0f0f0'}}>
          <Button type="text" icon={collapsed?<MenuUnfoldOutlined/>:<MenuFoldOutlined/>} onClick={()=>setCollapsed(!collapsed)}/>
          <Dropdown menu={{items:[{key:'logout',icon:<LogoutOutlined/>,label:'Выход',onClick:()=>{localStorage.removeItem('token');navigate('/login');}}]}}>
            <Space style={{cursor:'pointer'}}><Avatar icon={<UserOutlined/>}/><span>Администратор</span></Space>
          </Dropdown>
        </Header>
        <Content style={{margin:24,padding:24,background:'#fff',borderRadius:8,minHeight:280}}>
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

const App = () => {
  const isAuth = !!localStorage.getItem('token');
  return (
    <Routes>
      <Route path="/login" element={isAuth?<Navigate to="/"/>:<LoginPage/>}/>
      <Route path="/*" element={isAuth?<MainLayout/>:<Navigate to="/login"/>}/>
    </Routes>
  );
};
