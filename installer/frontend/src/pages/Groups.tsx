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
  Dropdown,
  Divider,
  Transfer,
  Descriptions,
  List,
  Avatar,
  Slider,
  InputNumber,
  ColorPicker,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  TeamOutlined,
  EyeOutlined,
  MoreOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserAddOutlined,
  UserDeleteOutlined,
  PhoneOutlined,
  MergeCellsOutlined,
  DashboardOutlined,
  SettingOutlined,
  FilterOutlined,
  ClearOutlined,
  CrownOutlined,
} from '@ant-design/icons';
import { groupService, GROUP_COLORS } from '@services/groupService';
import { contactService } from '@services/contactService';
import type {
  GroupListItem,
  GroupDetail,
  GroupCreateData,
  GroupUpdateData,
  GroupMember,
  GroupFilterParams,
  GroupStats,
  AddMembersData,
  RemoveMembersData,
  DialerListResponse,
} from '@services/groupService';
import type { ContactListItem } from '@services/contactService';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ============================================================================
// КОНСТАНТЫ
// ============================================================================

const PAGE_SIZE = 20;
const DEFAULT_SORT_FIELD = 'name';
const DEFAULT_SORT_DIRECTION = 'asc';

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

const GroupsPage: React.FC = () => {
  // =========================================================================
  // СОСТОЯНИЕ
  // =========================================================================

  // Данные
  const [groups, setGroups] = useState<GroupListItem[]>([]);
  const [totalGroups, setTotalGroups] = useState(0);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<GroupStats | null>(null);

  // Пагинация и сортировка
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [sortField, setSortField] = useState(DEFAULT_SORT_FIELD);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(DEFAULT_SORT_DIRECTION);

  // Фильтры
  const [searchText, setSearchText] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(true);
  const [systemFilter, setSystemFilter] = useState<boolean | undefined>(undefined);
  const [hasMembersFilter, setHasMembersFilter] = useState<boolean | undefined>(undefined);

  // Выбранные группы
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);

  // Модальные окна
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [membersModalOpen, setMembersModalOpen] = useState(false);
  const [addMembersModalOpen, setAddMembersModalOpen] = useState(false);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<GroupDetail | null>(null);

  // Участники
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [availableContacts, setAvailableContacts] = useState<ContactListItem[]>([]);
  const [selectedContactIds, setSelectedContactIds] = useState<string[]>([]);

  // Формы
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [mergeForm] = Form.useForm();

  // =========================================================================
  // ЗАГРУЗКА ДАННЫХ
  // =========================================================================

  const loadGroups = useCallback(async () => {
    setLoading(true);
    try {
      const params: GroupFilterParams = {
        page,
        page_size: pageSize,
        sort_field: sortField,
        sort_direction: sortDirection,
      };

      if (searchText) params.search = searchText;
      if (activeFilter !== undefined) params.is_active = activeFilter;
      if (systemFilter !== undefined) params.is_system = systemFilter;
      if (hasMembersFilter !== undefined) params.has_members = hasMembersFilter;

      const response = await groupService.getGroups(params);
      setGroups(response.items);
      setTotalGroups(response.total);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка загрузки групп');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, sortField, sortDirection, searchText, activeFilter, systemFilter, hasMembersFilter]);

  const loadStats = useCallback(async () => {
    try {
      const data = await groupService.getGroupStats();
      setStats(data);
    } catch {
      // Не критично
    }
  }, []);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // =========================================================================
  // ОБРАБОТЧИКИ ТАБЛИЦЫ
  // =========================================================================

  const handleTableChange = (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<GroupListItem> | SorterResult<GroupListItem>[]
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

  const handleRefresh = () => {
    loadGroups();
    loadStats();
  };

  const handleClearFilters = () => {
    setSearchText('');
    setActiveFilter(true);
    setSystemFilter(undefined);
    setHasMembersFilter(undefined);
    setPage(1);
  };

  // =========================================================================
  // ДЕЙСТВИЯ С ГРУППАМИ
  // =========================================================================

  const handleCreateGroup = async () => {
    try {
      const values = await createForm.validateFields();
      await groupService.createGroup(values);
      message.success('Группа создана');
      setCreateModalOpen(false);
      createForm.resetFields();
      loadGroups();
      loadStats();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка создания');
    }
  };

  const handleEditGroup = async () => {
    if (!selectedGroup) return;

    try {
      const values = await editForm.validateFields();
      await groupService.updateGroup(selectedGroup.id, values);
      message.success('Группа обновлена');
      setEditModalOpen(false);
      setSelectedGroup(null);
      editForm.resetFields();
      loadGroups();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка обновления');
    }
  };

  const handleDeleteGroup = async (groupId: string) => {
    try {
      await groupService.deleteGroup(groupId, false);
      message.success('Группа архивирована');
      loadGroups();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleRestoreGroup = async (groupId: string) => {
    try {
      await groupService.restoreGroup(groupId);
      message.success('Группа восстановлена');
      loadGroups();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка восстановления');
    }
  };

  const handleToggleActive = async (groupId: string, isActive: boolean, name: string) => {
    try {
      await groupService.updateGroup(groupId, { is_active: isActive });
      message.success(`Группа "${name}" ${isActive ? 'активирована' : 'деактивирована'}`);
      loadGroups();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleViewDetails = async (groupId: string) => {
    try {
      const group = await groupService.getGroup(groupId, true);
      setSelectedGroup(group);
      setDetailModalOpen(true);
    } catch {
      message.error('Ошибка загрузки данных группы');
    }
  };

  const handleViewMembers = async (groupId: string) => {
    try {
      const group = await groupService.getGroup(groupId, true);
      setSelectedGroup(group);
      setMembers(group.members);
      setMembersModalOpen(true);
    } catch {
      message.error('Ошибка загрузки участников');
    }
  };

  const openEditModal = async (groupId: string) => {
    try {
      const group = await groupService.getGroup(groupId, false);
      setSelectedGroup(group);
      editForm.setFieldsValue({
        name: group.name,
        description: group.description,
        color: group.color,
        is_active: group.is_active,
        default_priority: group.default_priority,
        max_retries: group.max_retries,
      });
      setEditModalOpen(true);
    } catch {
      message.error('Ошибка загрузки данных группы');
    }
  };

  const openAddMembersModal = async (groupId: string) => {
    try {
      // Загрузка всех контактов для выбора
      const contactsData = await contactService.getContacts({ page_size: 500, is_active: true });
      setAvailableContacts(contactsData.items);
      
      // Загрузка текущих участников
      const group = await groupService.getGroup(groupId, true);
      setSelectedGroup(group);
      setSelectedContactIds(group.members.map(m => m.contact_id));
      setAddMembersModalOpen(true);
    } catch {
      message.error('Ошибка загрузки данных');
    }
  };

  const handleAddMembers = async () => {
    if (!selectedGroup) return;

    // Определяем новых участников
    const currentMemberIds = new Set(selectedGroup.members?.map(m => m.contact_id) || []);
    const newMemberIds = selectedContactIds.filter(id => !currentMemberIds.has(id));
    const removedMemberIds = Array.from(currentMemberIds).filter(id => !selectedContactIds.includes(id));

    try {
      if (newMemberIds.length > 0) {
        await groupService.addMembers(selectedGroup.id, {
          contact_ids: newMemberIds,
        });
      }
      
      if (removedMemberIds.length > 0) {
        await groupService.removeMembers(selectedGroup.id, {
          contact_ids: removedMemberIds,
        });
      }

      message.success('Участники обновлены');
      setAddMembersModalOpen(false);
      loadGroups();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка обновления участников');
    }
  };

  const handleRemoveMember = async (groupId: string, contactId: string, contactName: string) => {
    try {
      await groupService.removeMembers(groupId, {
        contact_ids: [contactId],
      });
      message.success(`Контакт "${contactName}" удален из группы`);
      
      // Обновляем список участников
      const group = await groupService.getGroup(groupId, true);
      setSelectedGroup(group);
      setMembers(group.members);
      loadGroups();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleGetDialerList = async (groupId: string) => {
    try {
      const data = await groupService.getDialerList(groupId);
      Modal.info({
        title: `Список для обзвона: ${data.group_name}`,
        width: 600,
        content: (
          <div>
            <Paragraph>Всего номеров: {data.total_contacts}</Paragraph>
            <Table
              dataSource={data.contacts}
              columns={[
                { title: 'Имя', dataIndex: 'name', key: 'name' },
                { title: 'Телефон', dataIndex: 'phone', key: 'phone' },
                {
                  title: 'Приоритет',
                  dataIndex: 'priority',
                  key: 'priority',
                  width: 100,
                  render: (p: number) => (
                    <Tag color={groupService.getPriorityColor(p)}>
                      {groupService.getPriorityLabel(p)}
                    </Tag>
                  ),
                },
              ]}
              size="small"
              pagination={{ pageSize: 10 }}
              rowKey="contact_id"
            />
          </div>
        ),
      });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleBulkAction = async (action: 'activate' | 'deactivate' | 'archive') => {
    try {
      await groupService.bulkAction({
        group_ids: selectedRowKeys,
        action,
      });
      message.success(`Группы обработаны: ${selectedRowKeys.length}`);
      setSelectedRowKeys([]);
      loadGroups();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  // =========================================================================
  // КОЛОНКИ ТАБЛИЦЫ
  // =========================================================================

  const columns: ColumnsType<GroupListItem> = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      sorter: true,
      width: 280,
      render: (text: string, record: GroupListItem) => (
        <Space>
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: 3,
              backgroundColor: record.color || '#3498db',
              flexShrink: 0,
            }}
          />
          <div>
            <div style={{ fontWeight: 500 }}>
              {text}
              {record.is_system && (
                <CrownOutlined style={{ color: '#f39c12', marginLeft: 6 }} />
              )}
            </div>
            {record.description && (
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>{record.description}</div>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: 'Участники',
      dataIndex: 'member_count',
      key: 'member_count',
      sorter: true,
      width: 130,
      align: 'center',
      render: (count: number) => (
        <Tooltip title={groupService.formatMemberCount(count)}>
          <Tag color={count > 0 ? 'blue' : 'default'} style={{ fontSize: 14, padding: '4px 12px' }}>
            <TeamOutlined style={{ marginRight: 4 }} />
            {count}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: 'Приоритет',
      dataIndex: 'default_priority',
      key: 'default_priority',
      sorter: true,
      width: 130,
      align: 'center',
      render: (priority: number) => (
        <Tag color={groupService.getPriorityColor(priority)}>
          {priority}
        </Tag>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 110,
      render: (isActive: boolean, record: GroupListItem) => (
        <Badge
          status={isActive ? 'success' : 'error'}
          text={groupService.getStatusText(isActive, false, record.is_system)}
        />
      ),
    },
    {
      title: 'Создана',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: true,
      width: 130,
      render: (text: string | null) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {text ? new Date(text).toLocaleDateString('ru-RU') : '—'}
        </Text>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render: (_: any, record: GroupListItem) => (
        <Space size="small">
          <Tooltip title="Просмотр">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record.id)}
            />
          </Tooltip>

          <Tooltip title="Участники">
            <Button
              type="text"
              size="small"
              icon={<TeamOutlined />}
              onClick={() => handleViewMembers(record.id)}
            />
          </Tooltip>

          <Tooltip title="Список обзвона">
            <Button
              type="text"
              size="small"
              icon={<PhoneOutlined />}
              onClick={() => handleGetDialerList(record.id)}
            />
          </Tooltip>

          <Dropdown
            menu={{
              items: [
                {
                  key: 'edit',
                  icon: <EditOutlined />,
                  label: 'Редактировать',
                  onClick: () => openEditModal(record.id),
                },
                {
                  key: 'add_members',
                  icon: <UserAddOutlined />,
                  label: 'Управление участниками',
                  onClick: () => openAddMembersModal(record.id),
                },
                { type: 'divider' },
                {
                  key: 'toggle',
                  icon: record.is_active ? <CloseCircleOutlined /> : <CheckCircleOutlined />,
                  label: record.is_active ? 'Деактивировать' : 'Активировать',
                  onClick: () => handleToggleActive(record.id, !record.is_active, record.name),
                  disabled: record.is_system && record.is_active,
                },
                {
                  key: 'delete',
                  icon: <DeleteOutlined />,
                  label: 'Архивировать',
                  danger: true,
                  onClick: () => handleDeleteGroup(record.id),
                  disabled: record.is_system,
                },
              ],
            }}
            trigger={['click']}
          >
            <Button type="text" size="small" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // =========================================================================
  // РЕНДЕР
  // =========================================================================

  return (
    <div>
      {/* Заголовок */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            <TeamOutlined /> Группы контактов
          </Title>
          <Text type="secondary">Управление группами для массового обзвона</Text>
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
            Создать группу
          </Button>
        </Space>
      </div>

      {/* Статистика */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="Всего групп" value={stats.total_groups} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="Активных" value={stats.active_groups} valueStyle={{ color: '#2ecc71' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="Системных" value={stats.system_groups} valueStyle={{ color: '#9b59b6' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic
                title="Среднее участников"
                value={stats.avg_members_per_group}
                precision={1}
                valueStyle={{ color: '#3498db' }}
              />
            </Card>
          </Col>
          {stats.largest_group && (
            <Col span={24} style={{ marginTop: 16 }}>
              <Card size="small">
                <Text type="secondary">
                  Самая большая группа: <Text strong>{stats.largest_group.name}</Text> ({stats.largest_group.count} чел.)
                </Text>
              </Card>
            </Col>
          )}
        </Row>
      )}

      {/* Фильтры */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input.Search
            placeholder="Поиск по названию или описанию..."
            allowClear
            onSearch={handleSearch}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => !e.target.value && handleSearch('')}
          />

          <Select
            placeholder="Статус"
            allowClear
            style={{ width: 130 }}
            value={activeFilter}
            onChange={(v) => { setActiveFilter(v); setPage(1); }}
          >
            <Option value={true}>✅ Активна</Option>
            <Option value={false}>❌ Неактивна</Option>
          </Select>

          <Select
            placeholder="Тип"
            allowClear
            style={{ width: 160 }}
            value={systemFilter}
            onChange={(v) => { setSystemFilter(v); setPage(1); }}
          >
            <Option value={true}>🔒 Системные</Option>
            <Option value={false}>👤 Пользовательские</Option>
          </Select>

          <Select
            placeholder="Наличие участников"
            allowClear
            style={{ width: 180 }}
            value={hasMembersFilter}
            onChange={(v) => { setHasMembersFilter(v); setPage(1); }}
          >
            <Option value={true}>👥 С участниками</Option>
            <Option value={false}>👤 Без участников</Option>
          </Select>

          <Button icon={<ClearOutlined />} onClick={handleClearFilters}>
            Сбросить
          </Button>
        </Space>
      </Card>

      {/* Таблица */}
      <Card>
        {selectedRowKeys.length > 0 && (
          <div style={{ marginBottom: 16, padding: '8px 12px', background: '#e6f7ff', borderRadius: 6 }}>
            <Space>
              <Text strong>Выбрано групп: {selectedRowKeys.length}</Text>
              <Button size="small" onClick={() => handleBulkAction('activate')}>
                Активировать
              </Button>
              <Button size="small" onClick={() => handleBulkAction('deactivate')}>
                Деактивировать
              </Button>
              <Popconfirm
                title={`Архивировать ${selectedRowKeys.length} групп?`}
                onConfirm={() => handleBulkAction('archive')}
                okText="Да"
                cancelText="Нет"
              >
                <Button size="small" danger>
                  Архивировать
                </Button>
              </Popconfirm>
            </Space>
          </div>
        )}

        <Table
          columns={columns}
          dataSource={groups}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: totalGroups,
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
              disabled: record.is_system,
            }),
          }}
          scroll={{ x: 1000 }}
          size="middle"
        />
      </Card>

      {/* =====================================================================
          МОДАЛЬНЫЕ ОКНА
      ===================================================================== */}

      {/* Создание группы */}
      <Modal
        title="Создание группы"
        open={createModalOpen}
        onOk={handleCreateGroup}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        okText="Создать"
        cancelText="Отмена"
        width={550}
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="Название группы"
            rules={[
              { required: true, message: 'Введите название' },
              { min: 2, message: 'Минимум 2 символа' },
              { max: 100, message: 'Максимум 100 символов' },
            ]}
          >
            <Input placeholder="Например: ИТ-отдел, Руководство, Корпус А" />
          </Form.Item>

          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={2} placeholder="Для чего используется эта группа" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="color" label="Цвет" initialValue="#3498db">
                <Select>
                  {Object.entries(GROUP_COLORS).map(([name, hex]) => (
                    <Option key={name} value={hex}>
                      <Space>
                        <div
                          style={{
                            width: 16,
                            height: 16,
                            borderRadius: 3,
                            backgroundColor: hex,
                          }}
                        />
                        {name}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="default_priority"
                label="Приоритет обзвона"
                initialValue={5}
                tooltip="1 = высший приоритет, 10 = низший"
              >
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="max_retries"
            label="Максимум повторов"
            initialValue={3}
            tooltip="Количество повторных попыток при недоступности"
          >
            <Slider min={0} max={10} marks={{ 0: '0', 3: '3', 5: '5', 10: '10' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Редактирование группы */}
      <Modal
        title="Редактирование группы"
        open={editModalOpen}
        onOk={handleEditGroup}
        onCancel={() => {
          setEditModalOpen(false);
          setSelectedGroup(null);
          editForm.resetFields();
        }}
        okText="Сохранить"
        cancelText="Отмена"
        width={550}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="color" label="Цвет">
                <Select>
                  {Object.entries(GROUP_COLORS).map(([name, hex]) => (
                    <Option key={name} value={hex}>
                      <Space>
                        <div style={{ width: 16, height: 16, borderRadius: 3, backgroundColor: hex }} />
                        {name}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="default_priority" label="Приоритет">
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="max_retries" label="Максимум повторов">
            <Slider min={0} max={10} />
          </Form.Item>

          <Form.Item name="is_active" label="Активна" valuePropName="checked">
            <Badge status={editForm.getFieldValue('is_active') ? 'success' : 'error'} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Детали группы */}
      <Modal
        title={selectedGroup?.name || 'Информация о группе'}
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedGroup(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            Закрыть
          </Button>,
        ]}
        width={700}
      >
        {selectedGroup && (
          <div>
            <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Название" span={2}>
                <Space>
                  <div
                    style={{
                      width: 14,
                      height: 14,
                      borderRadius: 3,
                      backgroundColor: selectedGroup.color || '#3498db',
                    }}
                  />
                  <Text strong style={{ fontSize: 16 }}>{selectedGroup.name}</Text>
                  {selectedGroup.is_system && <Tag color="gold">Системная</Tag>}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Описание" span={2}>
                {selectedGroup.description || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Участников">
                {selectedGroup.member_count}
              </Descriptions.Item>
              <Descriptions.Item label="Всего (вкл. неактивных)">
                {selectedGroup.total_member_count}
              </Descriptions.Item>
              <Descriptions.Item label="С мобильными">
                {selectedGroup.mobile_members_count}
              </Descriptions.Item>
              <Descriptions.Item label="С внутренними">
                {selectedGroup.internal_members_count}
              </Descriptions.Item>
              <Descriptions.Item label="Приоритет">
                <Tag color={groupService.getPriorityColor(selectedGroup.default_priority)}>
                  {groupService.getPriorityLabel(selectedGroup.default_priority)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Макс. повторов">
                {selectedGroup.max_retries}
              </Descriptions.Item>
              <Descriptions.Item label="Статус">
                {groupService.getStatusText(
                  selectedGroup.is_active,
                  selectedGroup.is_archived,
                  selectedGroup.is_system
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Создана">
                {selectedGroup.created_at
                  ? new Date(selectedGroup.created_at).toLocaleString('ru-RU')
                  : '—'}
              </Descriptions.Item>
            </Descriptions>

            {/* Участники */}
            {selectedGroup.members && selectedGroup.members.length > 0 && (
              <div>
                <Divider orientation="left">Участники ({selectedGroup.members.length})</Divider>
                <Table
                  dataSource={selectedGroup.members.slice(0, 10)}
                  columns={[
                    { title: 'Имя', dataIndex: 'contact_name', key: 'name' },
                    { title: 'Отдел', dataIndex: 'department', key: 'dept', ellipsis: true },
                    {
                      title: 'Приоритет',
                      dataIndex: 'priority',
                      key: 'priority',
                      width: 100,
                      render: (p: number) => (
                        <Tag color={groupService.getPriorityColor(p)}>{p}</Tag>
                      ),
                    },
                  ]}
                  size="small"
                  pagination={false}
                  rowKey="contact_id"
                />
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Просмотр участников */}
      <Modal
        title={`Участники группы: ${selectedGroup?.name || ''}`}
        open={membersModalOpen}
        onCancel={() => {
          setMembersModalOpen(false);
          setMembers([]);
        }}
        footer={[
          <Button key="close" onClick={() => setMembersModalOpen(false)}>
            Закрыть
          </Button>,
        ]}
        width={800}
      >
        <Table
          dataSource={members}
          columns={[
            { title: 'Имя', dataIndex: 'contact_name', key: 'name', width: 200 },
            { title: 'Отдел', dataIndex: 'department', key: 'dept', width: 150, ellipsis: true },
            { title: 'Должность', dataIndex: 'position', key: 'pos', width: 150, ellipsis: true },
            {
              title: 'Тел. моб.',
              dataIndex: 'mobile_number',
              key: 'mobile',
              width: 150,
              render: (v: string | null) => v ? contactService.formatPhone(v) : '—',
            },
            {
              title: 'Приоритет',
              dataIndex: 'priority',
              key: 'priority',
              width: 100,
              render: (p: number) => (
                <Tag color={groupService.getPriorityColor(p)}>{p}</Tag>
              ),
            },
            {
              title: '',
              key: 'actions',
              width: 50,
              render: (_: any, record: GroupMember) => (
                selectedGroup && !selectedGroup.is_system && (
                  <Popconfirm
                    title={`Удалить "${record.contact_name}" из группы?`}
                    onConfirm={() => handleRemoveMember(selectedGroup.id, record.contact_id, record.contact_name)}
                    okText="Да"
                    cancelText="Нет"
                  >
                    <Button type="text" size="small" danger icon={<UserDeleteOutlined />} />
                  </Popconfirm>
                )
              ),
            },
          ]}
          size="small"
          pagination={{ pageSize: 25 }}
          rowKey="contact_id"
          scroll={{ y: 400 }}
        />
      </Modal>

      {/* Управление участниками (Transfer) */}
      <Modal
        title={`Управление участниками: ${selectedGroup?.name || ''}`}
        open={addMembersModalOpen}
        onOk={handleAddMembers}
        onCancel={() => {
          setAddMembersModalOpen(false);
          setSelectedContactIds([]);
        }}
        okText="Сохранить"
        cancelText="Отмена"
        width={750}
      >
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">
            Выберите контакты для добавления в группу. Невыбранные будут удалены.
          </Text>
        </div>
        <Transfer
          dataSource={availableContacts.map(c => ({
            key: c.id,
            title: c.full_name,
            description: `${c.department || '—'} | ${contactService.formatPhone(c.mobile_number) || c.internal_number || '—'}`,
          }))}
          targetKeys={selectedContactIds}
          onChange={(targetKeys) => setSelectedContactIds(targetKeys as string[])}
          render={(item) => item.title}
          listStyle={{
            width: 340,
            height: 400,
          }}
          showSearch
          filterOption={(inputValue, item) =>
            item.title.toLowerCase().includes(inputValue.toLowerCase()) ||
            (item.description || '').toLowerCase().includes(inputValue.toLowerCase())
          }
          titles={['Доступные контакты', 'В группе']}
        />
      </Modal>
    </div>
  );
};

export default GroupsPage;
