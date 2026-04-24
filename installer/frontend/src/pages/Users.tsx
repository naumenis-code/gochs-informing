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
  Switch,
  Dropdown,
  Divider,
  Descriptions,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  LockOutlined,
  UnlockOutlined,
  KeyOutlined,
  UserOutlined,
  TeamOutlined,
  SafetyOutlined,
  ExportOutlined,
  EyeOutlined,
  MoreOutlined,
  CrownOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { userService } from '@services/userService';
import type {
  UserListItem,
  UserDetail,
  UserCreateData,
  UserUpdateData,
  UserRole,
  UserFilterParams,
  UserStats,
  PasswordChangeData,
  PasswordResetData,
  BulkOperationResult,
} from '@services/userService';
import { useAuth } from '@hooks/useAuth';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ============================================================================
// КОНСТАНТЫ
// ============================================================================

const PAGE_SIZE = 20;
const DEFAULT_SORT_FIELD = 'created_at';
const DEFAULT_SORT_DIRECTION = 'desc';

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

const UsersPage: React.FC = () => {
  const { isAdmin, user: currentUser } = useAuth();

  // =========================================================================
  // СОСТОЯНИЕ
  // =========================================================================

  // Данные
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<UserStats | null>(null);

  // Пагинация и сортировка
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [sortField, setSortField] = useState(DEFAULT_SORT_FIELD);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(DEFAULT_SORT_DIRECTION);

  // Фильтры
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<UserRole | undefined>(undefined);
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);

  // Выбранные пользователи
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);

  // Модальные окна
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null);

  // Формы
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [passwordForm] = Form.useForm();

  // =========================================================================
  // ЗАГРУЗКА ДАННЫХ
  // =========================================================================

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params: UserFilterParams = {
        page,
        page_size: pageSize,
        sort_field: sortField,
        sort_direction: sortDirection,
      };

      if (searchText) params.search = searchText;
      if (roleFilter) params.role = roleFilter;
      if (activeFilter !== undefined) params.is_active = activeFilter;

      const response = await userService.getUsers(params);
      setUsers(response.items);
      setTotalUsers(response.total);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка загрузки пользователей');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, sortField, sortDirection, searchText, roleFilter, activeFilter]);

  const loadStats = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const data = await userService.getUserStats();
      setStats(data);
    } catch {
      // Статистика не критична
    }
  }, [isAdmin]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // =========================================================================
  // ОБРАБОТЧИКИ ТАБЛИЦЫ
  // =========================================================================

  const handleTableChange = (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<UserListItem> | SorterResult<UserListItem>[]
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

  const handleRoleFilter = (value: UserRole | undefined) => {
    setRoleFilter(value);
    setPage(1);
  };

  const handleActiveFilter = (value: boolean | undefined) => {
    setActiveFilter(value);
    setPage(1);
  };

  const handleRefresh = () => {
    loadUsers();
    loadStats();
  };

  // =========================================================================
  // ДЕЙСТВИЯ С ПОЛЬЗОВАТЕЛЯМИ
  // =========================================================================

  const handleCreateUser = async () => {
    try {
      const values = await createForm.validateFields();
      await userService.createUser(values);
      message.success('Пользователь создан');
      setCreateModalOpen(false);
      createForm.resetFields();
      loadUsers();
      loadStats();
    } catch (error: any) {
      if (error?.errorFields) return; // Ошибка валидации
      message.error(error?.response?.data?.detail || 'Ошибка создания');
    }
  };

  const handleEditUser = async () => {
    if (!selectedUser) return;

    try {
      const values = await editForm.validateFields();
      await userService.updateUser(selectedUser.id, values);
      message.success('Пользователь обновлен');
      setEditModalOpen(false);
      setSelectedUser(null);
      editForm.resetFields();
      loadUsers();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка обновления');
    }
  };

  const handleDeleteUser = async (userId: string) => {
    try {
      await userService.deleteUser(userId, false);
      message.success('Пользователь деактивирован');
      loadUsers();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleToggleActive = async (userId: string, isActive: boolean, username: string) => {
    try {
      if (isActive) {
        await userService.restoreUser(userId);
        message.success(`Пользователь "${username}" активирован`);
      } else {
        await userService.deleteUser(userId, false);
        message.success(`Пользователь "${username}" деактивирован`);
      }
      loadUsers();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleChangeRole = async (userId: string, newRole: UserRole, username: string) => {
    try {
      await userService.changeUserRole(userId, newRole);
      message.success(`Роль пользователя "${username}" изменена на "${newRole}"`);
      loadUsers();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка изменения роли');
    }
  };

  const handleUnlockUser = async (userId: string, username: string) => {
    try {
      await userService.unlockUser(userId);
      message.success(`Пользователь "${username}" разблокирован`);
      loadUsers();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка разблокировки');
    }
  };

  const handleResetPassword = async () => {
    if (!selectedUser) return;

    try {
      const values = await passwordForm.validateFields();
      await userService.resetUserPassword(selectedUser.id, values);
      message.success('Пароль сброшен');
      setPasswordModalOpen(false);
      setSelectedUser(null);
      passwordForm.resetFields();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка сброса пароля');
    }
  };

  const handleViewDetails = async (userId: string) => {
    try {
      const user = await userService.getUser(userId);
      setSelectedUser(user);
      setDetailModalOpen(true);
    } catch {
      message.error('Ошибка загрузки данных пользователя');
    }
  };

  const openEditModal = async (userId: string) => {
    try {
      const user = await userService.getUser(userId);
      setSelectedUser(user);
      editForm.setFieldsValue({
        email: user.email,
        username: user.username,
        full_name: user.full_name,
        role: user.role,
        is_active: user.is_active,
      });
      setEditModalOpen(true);
    } catch {
      message.error('Ошибка загрузки данных пользователя');
    }
  };

  const openPasswordResetModal = (user: UserListItem) => {
    setSelectedUser({ ...user, is_superuser: false, login_attempts: 0, force_password_change: false, created_by: null, updated_by: null, total_campaigns: 0, total_logins: 0, account_locked_until: null } as UserDetail);
    passwordForm.resetFields();
    setPasswordModalOpen(true);
  };

  // =========================================================================
  // КОЛОНКИ ТАБЛИЦЫ
  // =========================================================================

  const columns: ColumnsType<UserListItem> = [
    {
      title: 'Пользователь',
      dataIndex: 'full_name',
      key: 'full_name',
      sorter: true,
      width: 220,
      render: (text: string, record: UserListItem) => (
        <Space>
          <UserOutlined style={{ color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{text}</div>
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>{record.email}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Логин',
      dataIndex: 'username',
      key: 'username',
      sorter: true,
      width: 150,
      render: (text: string) => <Text code>{text}</Text>,
    },
    {
      title: 'Роль',
      dataIndex: 'role',
      key: 'role',
      width: 150,
      filters: [
        { text: '👑 Администратор', value: 'admin' },
        { text: '🔧 Оператор', value: 'operator' },
        { text: '👁 Наблюдатель', value: 'viewer' },
      ],
      render: (role: UserRole) => {
        const colors: Record<string, string> = {
          admin: '#e74c3c',
          operator: '#3498db',
          viewer: '#95a5a6',
        };
        const icons: Record<string, string> = {
          admin: '👑',
          operator: '🔧',
          viewer: '👁',
        };
        return (
          <Tag color={colors[role] || '#95a5a6'}>
            {icons[role]} {role === 'admin' ? 'Администратор' : role === 'operator' ? 'Оператор' : 'Наблюдатель'}
          </Tag>
        );
      },
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 120,
      filters: [
        { text: 'Активен', value: true },
        { text: 'Неактивен', value: false },
      ],
      render: (isActive: boolean) => (
        <Badge
          status={isActive ? 'success' : 'error'}
          text={isActive ? 'Активен' : 'Неактивен'}
        />
      ),
    },
    {
      title: 'Последний вход',
      dataIndex: 'last_login',
      key: 'last_login',
      sorter: true,
      width: 180,
      render: (text: string | null) => (
        <Text type="secondary">
          {text ? new Date(text).toLocaleString('ru-RU') : '—'}
        </Text>
      ),
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: true,
      width: 180,
      render: (text: string | null) => (
        <Text type="secondary">
          {text ? new Date(text).toLocaleDateString('ru-RU') : '—'}
        </Text>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_: any, record: UserListItem) => {
        const isCurrentUser = currentUser?.id === record.id;

        return (
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
                disabled={!isAdmin}
              />
            </Tooltip>

            <Dropdown
              menu={{
                items: [
                  {
                    key: 'toggle',
                    icon: record.is_active ? <CloseCircleOutlined /> : <CheckCircleOutlined />,
                    label: record.is_active ? 'Деактивировать' : 'Активировать',
                    onClick: () => handleToggleActive(record.id, !record.is_active, record.username),
                    disabled: isCurrentUser || !isAdmin,
                  },
                  {
                    key: 'role_admin',
                    icon: <CrownOutlined />,
                    label: 'Сделать администратором',
                    onClick: () => handleChangeRole(record.id, 'admin', record.username),
                    disabled: record.role === 'admin' || isCurrentUser || !isAdmin,
                  },
                  {
                    key: 'role_operator',
                    icon: <SafetyOutlined />,
                    label: 'Сделать оператором',
                    onClick: () => handleChangeRole(record.id, 'operator', record.username),
                    disabled: record.role === 'operator' || isCurrentUser || !isAdmin,
                  },
                  {
                    key: 'role_viewer',
                    icon: <EyeOutlined />,
                    label: 'Сделать наблюдателем',
                    onClick: () => handleChangeRole(record.id, 'viewer', record.username),
                    disabled: record.role === 'viewer' || isCurrentUser || !isAdmin,
                  },
                  { type: 'divider' },
                  {
                    key: 'unlock',
                    icon: <UnlockOutlined />,
                    label: 'Разблокировать',
                    onClick: () => handleUnlockUser(record.id, record.username),
                    disabled: !isAdmin,
                  },
                  {
                    key: 'reset_password',
                    icon: <KeyOutlined />,
                    label: 'Сбросить пароль',
                    onClick: () => openPasswordResetModal(record),
                    disabled: isCurrentUser || !isAdmin,
                  },
                  { type: 'divider' },
                  {
                    key: 'delete',
                    icon: <DeleteOutlined />,
                    label: 'Удалить',
                    danger: true,
                    onClick: () => handleDeleteUser(record.id),
                    disabled: isCurrentUser || !isAdmin,
                  },
                ],
              }}
              trigger={['click']}
            >
              <Button type="text" size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  // =========================================================================
  // РЕНДЕР
  // =========================================================================

  if (!isAdmin) {
    return (
      <Card>
        <Title level={4}>Доступ запрещен</Title>
        <Paragraph>Для просмотра этой страницы требуются права администратора.</Paragraph>
      </Card>
    );
  }

  return (
    <div>
      {/* Заголовок */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            <TeamOutlined /> Пользователи
          </Title>
          <Text type="secondary">Управление пользователями системы</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            Обновить
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              createForm.resetFields();
              setCreateModalOpen(true);
            }}
          >
            Добавить пользователя
          </Button>
        </Space>
      </div>

      {/* Статистика */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="Всего" value={stats.total} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="Активных" value={stats.active} valueStyle={{ color: '#2ecc71' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="Неактивных" value={stats.inactive} valueStyle={{ color: '#95a5a6' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="Заблокированных" value={stats.locked} valueStyle={{ color: '#e74c3c' }} />
            </Card>
          </Col>
          <Col xs={24} md={12} style={{ marginTop: 16 }}>
            <Card size="small" title="По ролям">
              <Space wrap>
                {Object.entries(stats.by_role).map(([role, count]) => (
                  <Tag key={role} color={userService.getRoleColor(role as UserRole)}>
                    {role}: {count}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>
      )}

      {/* Фильтры */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input.Search
            placeholder="Поиск по имени, email или логину..."
            allowClear
            onSearch={handleSearch}
            style={{ width: 350 }}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="Роль"
            allowClear
            style={{ width: 180 }}
            value={roleFilter}
            onChange={handleRoleFilter}
          >
            <Option value="admin">👑 Администратор</Option>
            <Option value="operator">🔧 Оператор</Option>
            <Option value="viewer">👁 Наблюдатель</Option>
          </Select>
          <Select
            placeholder="Статус"
            allowClear
            style={{ width: 150 }}
            value={activeFilter}
            onChange={handleActiveFilter}
          >
            <Option value={true}>✅ Активен</Option>
            <Option value={false}>❌ Неактивен</Option>
          </Select>
        </Space>
      </Card>

      {/* Таблица */}
      <Card>
        {selectedRowKeys.length > 0 && (
          <div style={{ marginBottom: 16, padding: '8px 12px', background: '#e6f7ff', borderRadius: 6 }}>
            <Space>
              <Text>Выбрано: {selectedRowKeys.length}</Text>
              <Button
                size="small"
                onClick={() => {
                  // Массовая активация
                  selectedRowKeys.forEach(id => handleToggleActive(id, true, ''));
                  setSelectedRowKeys([]);
                }}
              >
                Активировать
              </Button>
              <Button
                size="small"
                onClick={() => {
                  // Массовая деактивация
                  selectedRowKeys.forEach(id => handleToggleActive(id, false, ''));
                  setSelectedRowKeys([]);
                }}
              >
                Деактивировать
              </Button>
            </Space>
          </div>
        )}

        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: totalUsers,
            showSizeChanger: true,
            showQuickJumper: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (total, range) => `${range[0]}-${range[1]} из ${total}`,
          }}
          onChange={handleTableChange}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
            getCheckboxProps: (record) => ({
              disabled: record.id === currentUser?.id,
            }),
          }}
          scroll={{ x: 1200 }}
          size="middle"
        />
      </Card>

      {/* =====================================================================
          МОДАЛЬНЫЕ ОКНА
      ===================================================================== */}

      {/* Создание пользователя */}
      <Modal
        title="Создание пользователя"
        open={createModalOpen}
        onOk={handleCreateUser}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        okText="Создать"
        cancelText="Отмена"
        width={600}
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Введите email' },
              { type: 'email', message: 'Неверный формат email' },
            ]}
          >
            <Input placeholder="user@example.com" />
          </Form.Item>

          <Form.Item
            name="username"
            label="Логин"
            rules={[
              { required: true, message: 'Введите логин' },
              { min: 3, message: 'Минимум 3 символа' },
              { max: 100, message: 'Максимум 100 символов' },
              { pattern: /^[a-zA-Z0-9_\-\.]+$/, message: 'Только латиница, цифры, _ - .' },
            ]}
          >
            <Input placeholder="username" />
          </Form.Item>

          <Form.Item
            name="full_name"
            label="Полное имя"
            rules={[
              { required: true, message: 'Введите полное имя' },
              { min: 2, message: 'Минимум 2 символа' },
            ]}
          >
            <Input placeholder="Иванов Иван Иванович" />
          </Form.Item>

          <Form.Item
            name="role"
            label="Роль"
            initialValue="operator"
            rules={[{ required: true, message: 'Выберите роль' }]}
          >
            <Select>
              <Option value="admin">👑 Администратор</Option>
              <Option value="operator">🔧 Оператор</Option>
              <Option value="viewer">👁 Наблюдатель</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="password"
            label="Пароль"
            rules={[
              { required: true, message: 'Введите пароль' },
              { min: 8, message: 'Минимум 8 символов' },
            ]}
          >
            <Input.Password placeholder="Не менее 8 символов" />
          </Form.Item>

          <Form.Item
            name="password_confirm"
            label="Подтверждение пароля"
            dependencies={['password']}
            rules={[
              { required: true, message: 'Подтвердите пароль' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Пароли не совпадают'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="Повторите пароль" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Редактирование пользователя */}
      <Modal
        title="Редактирование пользователя"
        open={editModalOpen}
        onOk={handleEditUser}
        onCancel={() => {
          setEditModalOpen(false);
          setSelectedUser(null);
          editForm.resetFields();
        }}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Введите email' },
              { type: 'email', message: 'Неверный формат email' },
            ]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="username"
            label="Логин"
            rules={[
              { required: true, message: 'Введите логин' },
              { min: 3, message: 'Минимум 3 символа' },
            ]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="full_name"
            label="Полное имя"
            rules={[{ required: true, message: 'Введите полное имя' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item name="role" label="Роль">
            <Select>
              <Option value="admin">👑 Администратор</Option>
              <Option value="operator">🔧 Оператор</Option>
              <Option value="viewer">👁 Наблюдатель</Option>
            </Select>
          </Form.Item>

          <Form.Item name="is_active" label="Активен" valuePropName="checked">
            <Switch checkedChildren="Да" unCheckedChildren="Нет" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Сброс пароля */}
      <Modal
        title="Сброс пароля"
        open={passwordModalOpen}
        onOk={handleResetPassword}
        onCancel={() => {
          setPasswordModalOpen(false);
          setSelectedUser(null);
          passwordForm.resetFields();
        }}
        okText="Сбросить"
        cancelText="Отмена"
      >
        <div style={{ marginBottom: 16 }}>
          <Text>
            Пользователь: <Text strong>{selectedUser?.full_name}</Text>
          </Text>
        </div>
        <Form form={passwordForm} layout="vertical">
          <Form.Item
            name="new_password"
            label="Новый пароль"
            rules={[
              { required: true, message: 'Введите пароль' },
              { min: 8, message: 'Минимум 8 символов' },
            ]}
          >
            <Input.Password placeholder="Новый пароль" />
          </Form.Item>
          <Form.Item
            name="force_change"
            label="Требовать смену при входе"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="Да" unCheckedChildren="Нет" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Детали пользователя */}
      <Modal
        title="Информация о пользователе"
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedUser(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            Закрыть
          </Button>,
        ]}
        width={650}
      >
        {selectedUser && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="ID">{selectedUser.id}</Descriptions.Item>
            <Descriptions.Item label="Логин">
              <Text code>{selectedUser.username}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Email">{selectedUser.email}</Descriptions.Item>
            <Descriptions.Item label="Полное имя">{selectedUser.full_name}</Descriptions.Item>
            <Descriptions.Item label="Роль">
              <Tag color={userService.getRoleColor(selectedUser.role)}>
                {selectedUser.role === 'admin' ? '👑 Администратор' : 
                 selectedUser.role === 'operator' ? '🔧 Оператор' : '👁 Наблюдатель'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Статус">
              {userService.getStatusText(selectedUser.is_active, selectedUser.login_attempts, selectedUser.account_locked_until)}
            </Descriptions.Item>
            <Descriptions.Item label="Последний вход">
              {selectedUser.last_login ? new Date(selectedUser.last_login).toLocaleString('ru-RU') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Всего входов">{selectedUser.total_logins}</Descriptions.Item>
            <Descriptions.Item label="Неудачных попыток">{selectedUser.login_attempts}</Descriptions.Item>
            <Descriptions.Item label="Требуется смена пароля">
              {selectedUser.force_password_change ? '✅ Да' : '❌ Нет'}
            </Descriptions.Item>
            <Descriptions.Item label="Создан">
              {selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleString('ru-RU') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Обновлен">
              {selectedUser.updated_at ? new Date(selectedUser.updated_at).toLocaleString('ru-RU') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Кампаний">{selectedUser.total_campaigns}</Descriptions.Item>
            <Descriptions.Item label="Заблокирован до">
              {selectedUser.account_locked_until
                ? new Date(selectedUser.account_locked_until).toLocaleString('ru-RU')
                : '—'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default UsersPage;
