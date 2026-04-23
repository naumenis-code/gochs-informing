import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  DatePicker,
  Select,
  Input,
  Row,
  Col,
  Typography,
  Drawer,
  Descriptions,
  Badge,
  Statistic,
  Tooltip,
  Popconfirm,
  message,
  Form,
} from 'antd';
import {
  AuditOutlined,
  SearchOutlined,
  ReloadOutlined,
  ExportOutlined,
  DeleteOutlined,
  UserOutlined,
  SettingOutlined,
  PhoneOutlined,
  SafetyOutlined,
  FileTextOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DownloadOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { auditService } from '@services/auditService';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface AuditLog {
  id: string;
  user_id: string;
  user_name: string;
  user_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  entity_name: string;
  details: any;
  ip_address: string;
  user_agent: string;
  request_method: string;
  request_path: string;
  status: 'success' | 'warning' | 'error';
  error_message: string;
  execution_time_ms: number;
  created_at: string;
}

interface AuditStats {
  total_events: number;
  today_events: number;
  week_events: number;
  month_events: number;
  unique_users: number;
  error_events: number;
  warning_events: number;
  success_events: number;
  top_actions: Array<{ action: string; count: number }>;
  top_entities: Array<{ entity_type: string; count: number }>;
  top_users: Array<{ user_name: string; user_role: string; count: number }>;
  recent_activity: Array<{
    time: string;
    user: string;
    action: string;
    entity_type: string;
    entity_name: string;
    status: string;
    ip_address: string;
    description: string;
  }>;
}

const Audit: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  
  // Filters
  const [filters, setFilters] = useState({
    action: '',
    entity_type: '',
    user_name: '',
    status: '',
    dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
  });

  const [form] = Form.useForm();

  useEffect(() => {
    loadAuditLogs();
    loadAuditStats();
  }, [pagination.current, pagination.pageSize]);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const params: any = {
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        action: filters.action || undefined,
        entity_type: filters.entity_type || undefined,
        user_name: filters.user_name || undefined,
        status: filters.status || undefined,
        start_date: filters.dateRange?.[0]?.format('YYYY-MM-DD'),
        end_date: filters.dateRange?.[1]?.format('YYYY-MM-DD'),
      };
      
      const response = await auditService.getAuditLogs(params);
      setLogs(response.items);
      setPagination(prev => ({ ...prev, total: response.total }));
    } catch (error) {
      message.error('Не удалось загрузить журнал аудита');
    } finally {
      setLoading(false);
    }
  };

  const loadAuditStats = async () => {
    try {
      const stats = await auditService.getAuditStats();
      setStats(stats);
    } catch (error) {
      console.error('Failed to load audit stats:', error);
    }
  };

  const handleSearch = () => {
    setPagination(prev => ({ ...prev, current: 1 }));
    loadAuditLogs();
  };

  const handleReset = () => {
    setFilters({
      action: '',
      entity_type: '',
      user_name: '',
      status: '',
      dateRange: null,
    });
    form.resetFields();
    setPagination({ current: 1, pageSize: 20, total: 0 });
    setTimeout(loadAuditLogs, 100);
  };

  const handleExport = async () => {
    try {
      const params: any = {};
      if (filters.action) params.action = filters.action;
      if (filters.entity_type) params.entity_type = filters.entity_type;
      if (filters.user_name) params.user_name = filters.user_name;
      if (filters.dateRange?.[0]) params.start_date = filters.dateRange[0].format('YYYY-MM-DD');
      if (filters.dateRange?.[1]) params.end_date = filters.dateRange[1].format('YYYY-MM-DD');
      
      const blob = await auditService.exportAuditLogs(params);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_export_${dayjs().format('YYYYMMDD_HHmmss')}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('Экспорт выполнен успешно');
    } catch (error) {
      message.error('Ошибка экспорта');
    }
  };

  const handleClearOldLogs = async () => {
    try {
      await auditService.clearOldLogs(90);
      message.success('Старые записи аудита удалены');
      loadAuditLogs();
      loadAuditStats();
    } catch (error) {
      message.error('Ошибка очистки');
    }
  };

  const showLogDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setDrawerVisible(true);
  };

  const getActionColor = (action: string): string => {
    const colors: Record<string, string> = {
      'create': 'green',
      'update': 'blue',
      'delete': 'red',
      'login': 'cyan',
      'logout': 'default',
      'export': 'purple',
      'import': 'orange',
      'start': 'success',
      'stop': 'error',
      'pause': 'warning',
      'view': 'geekblue',
      'test': 'lime',
    };
    
    const matchedKey = Object.keys(colors).find(key => action.toLowerCase().includes(key));
    return matchedKey ? colors[matchedKey] : 'default';
  };

  const getEntityIcon = (entityType: string) => {
    const icons: Record<string, React.ReactNode> = {
      'user': <UserOutlined />,
      'campaign': <PhoneOutlined />,
      'contact': <UserOutlined />,
      'scenario': <FileTextOutlined />,
      'playbook': <FileTextOutlined />,
      'settings': <SettingOutlined />,
      'security': <SafetyOutlined />,
      'audit': <AuditOutlined />,
    };
    return icons[entityType] || <FileTextOutlined />;
  };

  const getStatusBadge = (status: string) => {
    const config = {
      success: { status: 'success' as const, text: 'Успешно', icon: <CheckCircleOutlined /> },
      warning: { status: 'warning' as const, text: 'Предупреждение', icon: <SyncOutlined /> },
      error: { status: 'error' as const, text: 'Ошибка', icon: <CloseCircleOutlined /> },
    };
    const cfg = config[status as keyof typeof config] || config.success;
    return (
      <Space>
        {cfg.icon}
        <span>{cfg.text}</span>
      </Space>
    );
  };

  const columns = [
    {
      title: 'Время',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (text: string) => (
        <Tooltip title={dayjs(text).format('DD.MM.YYYY HH:mm:ss')}>
          <Space direction="vertical" size={0}>
            <Text>{dayjs(text).format('DD.MM.YYYY')}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {dayjs(text).format('HH:mm:ss')}
            </Text>
          </Space>
        </Tooltip>
      ),
      sorter: (a: AuditLog, b: AuditLog) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
    },
    {
      title: 'Пользователь',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 160,
      render: (text: string, record: AuditLog) => (
        <Space>
          <UserOutlined />
          <Space direction="vertical" size={0}>
            <Text strong>{text || 'Система'}</Text>
            {record.user_role && (
              <Tag color={record.user_role === 'admin' ? 'red' : 'blue'} style={{ fontSize: 11 }}>
                {record.user_role}
              </Tag>
            )}
          </Space>
        </Space>
      ),
    },
    {
      title: 'Действие',
      dataIndex: 'action',
      key: 'action',
      width: 130,
      render: (text: string) => (
        <Tag color={getActionColor(text)}>{text.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Тип объекта',
      dataIndex: 'entity_type',
      key: 'entity_type',
      width: 130,
      render: (text: string) => (
        <Space>
          {getEntityIcon(text)}
          <Text>{text || '—'}</Text>
        </Space>
      ),
    },
    {
      title: 'Объект',
      dataIndex: 'entity_name',
      key: 'entity_name',
      width: 150,
      render: (text: string, record: AuditLog) => (
        <Text ellipsis={{ tooltip: text }}>
          {text || (record.entity_id ? record.entity_id.substring(0, 8) + '...' : '—')}
        </Text>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: 'IP адрес',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
      render: (text: string) => (
        <Text copyable={{ text }}>{text || '—'}</Text>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 80,
      fixed: 'right' as const,
      render: (_: any, record: AuditLog) => (
        <Tooltip title="Подробнее">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => showLogDetails(record)}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          <AuditOutlined style={{ marginRight: 12 }} />
          Журнал аудита
        </Title>
        <Space>
          <Button icon={<ExportOutlined />} onClick={handleExport}>
            Экспорт
          </Button>
          <Popconfirm
            title="Удалить записи старше 90 дней?"
            onConfirm={handleClearOldLogs}
            okText="Да"
            cancelText="Нет"
          >
            <Button icon={<DeleteOutlined />} danger>
              Очистить старые
            </Button>
          </Popconfirm>
        </Space>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6} lg={4} xl={3}>
            <Card>
              <Statistic
                title="Всего событий"
                value={stats.total_events}
                prefix={<AuditOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4} xl={3}>
            <Card>
              <Statistic
                title="За сегодня"
                value={stats.today_events}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4} xl={3}>
            <Card>
              <Statistic
                title="За неделю"
                value={stats.week_events}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4} xl={3}>
            <Card>
              <Statistic
                title="Пользователей"
                value={stats.unique_users}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4} xl={3}>
            <Card>
              <Statistic
                title="Успешно"
                value={stats.success_events}
                valueStyle={{ color: '#3f8600' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4} xl={3}>
            <Card>
              <Statistic
                title="Предупреждений"
                value={stats.warning_events}
                valueStyle={{ color: '#faad14' }}
                prefix={<SyncOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6} lg={4} xl={3}>
            <Card>
              <Statistic
                title="Ошибок"
                value={stats.error_events}
                valueStyle={{ color: '#cf1322' }}
                prefix={<CloseCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Form form={form} layout="horizontal">
          <Row gutter={16}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Действие" style={{ marginBottom: 0 }}>
                <Select
                  placeholder="Все действия"
                  allowClear
                  value={filters.action || undefined}
                  onChange={(value) => setFilters(prev => ({ ...prev, action: value || '' }))}
                >
                  <Option value="login">Вход в систему</Option>
                  <Option value="logout">Выход из системы</Option>
                  <Option value="create">Создание</Option>
                  <Option value="update">Обновление</Option>
                  <Option value="delete">Удаление</Option>
                  <Option value="view">Просмотр</Option>
                  <Option value="export">Экспорт</Option>
                  <Option value="import">Импорт</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Тип объекта" style={{ marginBottom: 0 }}>
                <Select
                  placeholder="Все типы"
                  allowClear
                  value={filters.entity_type || undefined}
                  onChange={(value) => setFilters(prev => ({ ...prev, entity_type: value || '' }))}
                >
                  <Option value="user">Пользователи</Option>
                  <Option value="campaign">Кампании</Option>
                  <Option value="contact">Контакты</Option>
                  <Option value="group">Группы</Option>
                  <Option value="scenario">Сценарии</Option>
                  <Option value="playbook">Плейбуки</Option>
                  <Option value="settings">Настройки</Option>
                  <Option value="audit">Аудит</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Статус" style={{ marginBottom: 0 }}>
                <Select
                  placeholder="Все статусы"
                  allowClear
                  value={filters.status || undefined}
                  onChange={(value) => setFilters(prev => ({ ...prev, status: value || '' }))}
                >
                  <Option value="success">Успешно</Option>
                  <Option value="warning">Предупреждение</Option>
                  <Option value="error">Ошибка</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Пользователь" style={{ marginBottom: 0 }}>
                <Input
                  placeholder="Имя пользователя"
                  allowClear
                  value={filters.user_name}
                  onChange={(e) => setFilters(prev => ({ ...prev, user_name: e.target.value }))}
                  prefix={<UserOutlined />}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="Период" style={{ marginBottom: 0 }}>
                <RangePicker
                  style={{ width: '100%' }}
                  value={filters.dateRange}
                  onChange={(dates) => setFilters(prev => ({ ...prev, dateRange: dates as [dayjs.Dayjs, dayjs.Dayjs] }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8} style={{ display: 'flex', alignItems: 'center' }}>
              <Space>
                <Button onClick={handleReset}>
                  Сбросить
                </Button>
                <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                  Поиск
                </Button>
                <Button icon={<ReloadOutlined />} onClick={() => { loadAuditLogs(); loadAuditStats(); }}>
                  Обновить
                </Button>
              </Space>
            </Col>
          </Row>
        </Form>
      </Card>

      {/* Top Stats Row */}
      {stats && (stats.top_actions.length > 0 || stats.top_entities.length > 0) && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="Топ действий" size="small">
              {stats.top_actions.map((item, index) => (
                <div key={index} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <Tag color={getActionColor(item.action)}>{item.action}</Tag>
                  <Badge count={item.count} showZero style={{ backgroundColor: '#1890ff' }} />
                </div>
              ))}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Топ сущностей" size="small">
              {stats.top_entities.map((item, index) => (
                <div key={index} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <Space>
                    {getEntityIcon(item.entity_type)}
                    <Text>{item.entity_type}</Text>
                  </Space>
                  <Badge count={item.count} showZero style={{ backgroundColor: '#52c41a' }} />
                </div>
              ))}
            </Card>
          </Col>
        </Row>
      )}

      {/* Recent Activity */}
      {stats && stats.recent_activity.length > 0 && (
        <Card title="Последняя активность" size="small" style={{ marginBottom: 16 }}>
          {stats.recent_activity.slice(0, 5).map((item, index) => (
            <div key={index} style={{ padding: '8px 0', borderBottom: index < 4 ? '1px solid #f0f0f0' : 'none' }}>
              <Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {dayjs(item.time).format('HH:mm:ss')}
                </Text>
                <Text strong>{item.user}</Text>
                <Tag color={getActionColor(item.action)}>{item.action}</Tag>
                <Text type="secondary">{item.description}</Text>
              </Space>
            </div>
          ))}
        </Card>
      )}

      {/* Audit Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `Всего ${total} записей`,
            onChange: (page, pageSize) => {
              setPagination({ current: page, pageSize: pageSize || 20, total: pagination.total });
            },
          }}
          scroll={{ x: 1300 }}
          size="middle"
        />
      </Card>

      {/* Details Drawer */}
      <Drawer
        title="Детали события аудита"
        placement="right"
        width={650}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedLog && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="ID события">
                <Text code copyable>{selectedLog.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Время">
                {dayjs(selectedLog.created_at).format('DD.MM.YYYY HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Пользователь">
                <Space>
                  <UserOutlined />
                  <Text strong>{selectedLog.user_name || 'Система'}</Text>
                  {selectedLog.user_role && (
                    <Tag color={selectedLog.user_role === 'admin' ? 'red' : 'blue'}>
                      {selectedLog.user_role}
                    </Tag>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Действие">
                <Tag color={getActionColor(selectedLog.action)}>
                  {selectedLog.action.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Тип объекта">
                <Space>
                  {getEntityIcon(selectedLog.entity_type)}
                  <Text>{selectedLog.entity_type || '—'}</Text>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="ID объекта">
                {selectedLog.entity_id ? (
                  <Text code copyable>{selectedLog.entity_id}</Text>
                ) : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Имя объекта">
                {selectedLog.entity_name || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Статус">
                {getStatusBadge(selectedLog.status)}
              </Descriptions.Item>
              {selectedLog.error_message && (
                <Descriptions.Item label="Ошибка">
                  <Text type="danger">{selectedLog.error_message}</Text>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="IP адрес">
                {selectedLog.ip_address || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="HTTP метод">
                {selectedLog.request_method || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Путь запроса">
                <Text code>{selectedLog.request_path || '—'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="User Agent">
                <Text style={{ fontSize: 11 }}>{selectedLog.user_agent || '—'}</Text>
              </Descriptions.Item>
              {selectedLog.execution_time_ms && (
                <Descriptions.Item label="Время выполнения">
                  {selectedLog.execution_time_ms} мс
                </Descriptions.Item>
              )}
            </Descriptions>

            {selectedLog.details && (
              <>
                <Divider orientation="left">Детали</Divider>
                <pre style={{
                  background: '#f5f5f5',
                  padding: 16,
                  borderRadius: 8,
                  maxHeight: 300,
                  overflow: 'auto',
                  fontSize: 12,
                }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default Audit;
