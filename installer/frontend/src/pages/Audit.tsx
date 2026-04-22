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
  Timeline,
  Statistic,
  Tooltip,
  Popconfirm,
  message,
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
  MailOutlined,
  SafetyOutlined,
  FileTextOutlined,
  EyeOutlined,
  FilterOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
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
  details: any;
  ip_address: string;
  user_agent: string;
  created_at: string;
  status: 'success' | 'warning' | 'error';
}

interface AuditStats {
  total_events: number;
  today_events: number;
  unique_users: number;
  error_events: number;
  top_actions: Array<{ action: string; count: number }>;
  recent_activity: Array<{ time: string; description: string }>;
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
    dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
  });

  useEffect(() => {
    loadAuditLogs();
    loadAuditStats();
  }, [pagination.current, pagination.pageSize]);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const params = {
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        action: filters.action || undefined,
        entity_type: filters.entity_type || undefined,
        user_name: filters.user_name || undefined,
        start_date: filters.dateRange?.[0]?.toISOString(),
        end_date: filters.dateRange?.[1]?.toISOString(),
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
      dateRange: null,
    });
    setPagination({ current: 1, pageSize: 20, total: 0 });
    setTimeout(loadAuditLogs, 100);
  };

  const handleExport = async () => {
    try {
      const blob = await auditService.exportAuditLogs(filters);
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
    };
    return icons[entityType] || <FileTextOutlined />;
  };

  const getStatusBadge = (status: string) => {
    const config = {
      success: { status: 'success' as const, text: 'Успешно' },
      warning: { status: 'warning' as const, text: 'Предупреждение' },
      error: { status: 'error' as const, text: 'Ошибка' },
    };
    const cfg = config[status as keyof typeof config] || config.success;
    return <Badge status={cfg.status} text={cfg.text} />;
  };

  const columns = [
    {
      title: 'Время',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => (
        <Space direction="vertical" size={0}>
          <Text>{dayjs(text).format('DD.MM.YYYY')}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {dayjs(text).format('HH:mm:ss')}
          </Text>
        </Space>
      ),
      sorter: (a: AuditLog, b: AuditLog) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
    },
    {
      title: 'Пользователь',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 180,
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
      width: 150,
      render: (text: string) => (
        <Tag color={getActionColor(text)}>{text.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Тип объекта',
      dataIndex: 'entity_type',
      key: 'entity_type',
      width: 150,
      render: (text: string) => (
        <Space>
          {getEntityIcon(text)}
          <Text>{text || '—'}</Text>
        </Space>
      ),
    },
    {
      title: 'Объект',
      dataIndex: 'entity_id',
      key: 'entity_id',
      width: 200,
      render: (text: string) => (
        <Text code copyable={{ text }}>
          {text ? text.substring(0, 8) + '...' : '—'}
        </Text>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: 'IP адрес',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (text: string) => (
        <Text copyable={{ text }}>{text || '—'}</Text>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
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
          <Col span={6}>
            <Card>
              <Statistic
                title="Всего событий"
                value={stats.total_events}
                prefix={<AuditOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="За сегодня"
                value={stats.today_events}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Активных пользователей"
                value={stats.unique_users}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Ошибок"
                value={stats.error_events}
                valueStyle={{ color: stats.error_events > 0 ? '#cf1322' : '#3f8600' }}
                prefix={<SafetyOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Select
              placeholder="Тип действия"
              allowClear
              style={{ width: '100%' }}
              value={filters.action || undefined}
              onChange={(value) => setFilters(prev => ({ ...prev, action: value || '' }))}
            >
              <Option value="login">Вход в систему</Option>
              <Option value="logout">Выход из системы</Option>
              <Option value="create">Создание</Option>
              <Option value="update">Обновление</Option>
              <Option value="delete">Удаление</Option>
              <Option value="export">Экспорт</Option>
              <Option value="import">Импорт</Option>
            </Select>
          </Col>
          <Col span={6}>
            <Select
              placeholder="Тип объекта"
              allowClear
              style={{ width: '100%' }}
              value={filters.entity_type || undefined}
              onChange={(value) => setFilters(prev => ({ ...prev, entity_type: value || '' }))}
            >
              <Option value="user">Пользователи</Option>
              <Option value="campaign">Кампании</Option>
              <Option value="contact">Контакты</Option>
              <Option value="scenario">Сценарии</Option>
              <Option value="playbook">Плейбуки</Option>
              <Option value="settings">Настройки</Option>
            </Select>
          </Col>
          <Col span={6}>
            <Input
              placeholder="Пользователь"
              allowClear
              value={filters.user_name}
              onChange={(e) => setFilters(prev => ({ ...prev, user_name: e.target.value }))}
              prefix={<UserOutlined />}
            />
          </Col>
          <Col span={6}>
            <RangePicker
              style={{ width: '100%' }}
              value={filters.dateRange}
              onChange={(dates) => setFilters(prev => ({ ...prev, dateRange: dates as [dayjs.Dayjs, dayjs.Dayjs] }))}
            />
          </Col>
        </Row>
        <Row style={{ marginTop: 16 }}>
          <Col span={24} style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={handleReset}>
                Сбросить
              </Button>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                Поиск
              </Button>
              <Button icon={<ReloadOutlined />} onClick={loadAuditLogs}>
                Обновить
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

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
            showTotal: (total) => `Всего ${total} записей`,
            onChange: (page, pageSize) => {
              setPagination({ current: page, pageSize: pageSize || 20, total: pagination.total });
            },
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* Details Drawer */}
      <Drawer
        title="Детали события аудита"
        placement="right"
        width={600}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedLog && (
          <>
            <Descriptions column={1} bordered>
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
                {selectedLog.entity_type || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="ID объекта">
                {selectedLog.entity_id ? (
                  <Text code copyable>{selectedLog.entity_id}</Text>
                ) : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Статус">
                {getStatusBadge(selectedLog.status)}
              </Descriptions.Item>
              <Descriptions.Item label="IP адрес">
                {selectedLog.ip_address || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="User Agent">
                <Text style={{ fontSize: 12 }}>{selectedLog.user_agent || '—'}</Text>
              </Descriptions.Item>
            </Descriptions>

            {selectedLog.details && (
              <>
                <Divider>Детали изменений</Divider>
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
