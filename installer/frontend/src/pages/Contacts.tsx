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
  Tabs,
  Upload,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  ImportOutlined,
  ExportOutlined,
  DownloadOutlined,
  PhoneOutlined,
  MailOutlined,
  TeamOutlined,
  TagOutlined,
  UserOutlined,
  EyeOutlined,
  MoreOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InboxOutlined,
  FilterOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { contactService } from '@services/contactService';
import type {
  ContactListItem,
  ContactDetail,
  ContactCreateData,
  ContactUpdateData,
  ContactFilterParams,
  ContactStats,
  BulkOperationResult,
} from '@services/contactService';
import { groupService } from '@services/groupService';
import ImportModal from '@components/Common/ImportModal';
import AudioPlayer from '@components/Common/AudioPlayer';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { Dragger } = Upload;

// ============================================================================
// КОНСТАНТЫ
// ============================================================================

const PAGE_SIZE = 25;
const DEFAULT_SORT_FIELD = 'full_name';
const DEFAULT_SORT_DIRECTION = 'asc';

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

const ContactsPage: React.FC = () => {
  // =========================================================================
  // СОСТОЯНИЕ
  // =========================================================================

  // Данные
  const [contacts, setContacts] = useState<ContactListItem[]>([]);
  const [totalContacts, setTotalContacts] = useState(0);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<ContactStats | null>(null);

  // Пагинация и сортировка
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [sortField, setSortField] = useState(DEFAULT_SORT_FIELD);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(DEFAULT_SORT_DIRECTION);

  // Фильтры
  const [searchText, setSearchText] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState<string | undefined>(undefined);
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(true);
  const [groupFilter, setGroupFilter] = useState<string | undefined>(undefined);
  const [tagFilter, setTagFilter] = useState<string | undefined>(undefined);
  const [hasMobileFilter, setHasMobileFilter] = useState<boolean | undefined>(undefined);
  const [hasInternalFilter, setHasInternalFilter] = useState<boolean | undefined>(undefined);
  const [hasEmailFilter, setHasEmailFilter] = useState<boolean | undefined>(undefined);

  // Выбранные контакты
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);

  // Модальные окна
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedContact, setSelectedContact] = useState<ContactDetail | null>(null);

  // Группы и теги для фильтров
  const [groups, setGroups] = useState<Array<{ value: string; label: string }>>([]);
  const [departments, setDepartments] = useState<string[]>([]);

  // Формы
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  // =========================================================================
  // ЗАГРУЗКА ДАННЫХ
  // =========================================================================

  const loadContacts = useCallback(async () => {
    setLoading(true);
    try {
      const params: ContactFilterParams = {
        page,
        page_size: pageSize,
        sort_field: sortField,
        sort_direction: sortDirection,
      };

      if (searchText) params.search = searchText;
      if (departmentFilter) params.department = departmentFilter;
      if (activeFilter !== undefined) params.is_active = activeFilter;
      if (groupFilter) params.group_id = groupFilter;
      if (tagFilter) params.tag_id = tagFilter;
      if (hasMobileFilter !== undefined) params.has_mobile = hasMobileFilter;
      if (hasInternalFilter !== undefined) params.has_internal = hasInternalFilter;
      if (hasEmailFilter !== undefined) params.has_email = hasEmailFilter;

      const response = await contactService.getContacts(params);
      setContacts(response.items);
      setTotalContacts(response.total);

      // Сбор подразделений для фильтра
      const depts = new Set<string>();
      response.items.forEach(c => {
        if (c.department) depts.add(c.department);
      });
      setDepartments(Array.from(depts).sort());
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка загрузки контактов');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, sortField, sortDirection, searchText, departmentFilter, activeFilter, groupFilter, tagFilter, hasMobileFilter, hasInternalFilter, hasEmailFilter]);

  const loadStats = useCallback(async () => {
    try {
      const data = await contactService.getContactStats();
      setStats(data);
    } catch {
      // Не критично
    }
  }, []);

  const loadGroups = useCallback(async () => {
    try {
      const groupList = await groupService.getAllGroupsForSelect();
      setGroups(groupList.map(g => ({ value: g.value, label: g.label })));
    } catch {
      // Не критично
    }
  }, []);

  useEffect(() => {
    loadContacts();
  }, [loadContacts]);

  useEffect(() => {
    loadStats();
    loadGroups();
  }, [loadStats, loadGroups]);

  // =========================================================================
  // ОБРАБОТЧИКИ ТАБЛИЦЫ
  // =========================================================================

  const handleTableChange = (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<ContactListItem> | SorterResult<ContactListItem>[]
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
    loadContacts();
    loadStats();
  };

  const handleClearFilters = () => {
    setSearchText('');
    setDepartmentFilter(undefined);
    setActiveFilter(true);
    setGroupFilter(undefined);
    setTagFilter(undefined);
    setHasMobileFilter(undefined);
    setHasInternalFilter(undefined);
    setHasEmailFilter(undefined);
    setPage(1);
  };

  // =========================================================================
  // ДЕЙСТВИЯ С КОНТАКТАМИ
  // =========================================================================

  const handleCreateContact = async () => {
    try {
      const values = await createForm.validateFields();
      await contactService.createContact(values);
      message.success('Контакт создан');
      setCreateModalOpen(false);
      createForm.resetFields();
      loadContacts();
      loadStats();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка создания');
    }
  };

  const handleEditContact = async () => {
    if (!selectedContact) return;

    try {
      const values = await editForm.validateFields();
      await contactService.updateContact(selectedContact.id, values);
      message.success('Контакт обновлен');
      setEditModalOpen(false);
      setSelectedContact(null);
      editForm.resetFields();
      loadContacts();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Ошибка обновления');
    }
  };

  const handleDeleteContact = async (contactId: string) => {
    try {
      await contactService.deleteContact(contactId, false);
      message.success('Контакт архивирован');
      loadContacts();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleRestoreContact = async (contactId: string) => {
    try {
      await contactService.restoreContact(contactId);
      message.success('Контакт восстановлен');
      loadContacts();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка восстановления');
    }
  };

  const handleToggleActive = async (contactId: string, isActive: boolean, name: string) => {
    try {
      await contactService.updateContact(contactId, { is_active: isActive });
      message.success(`Контакт "${name}" ${isActive ? 'активирован' : 'деактивирован'}`);
      loadContacts();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  const handleViewDetails = async (contactId: string) => {
    try {
      const contact = await contactService.getContact(contactId);
      setSelectedContact(contact);
      setDetailModalOpen(true);
    } catch {
      message.error('Ошибка загрузки данных контакта');
    }
  };

  const openEditModal = async (contactId: string) => {
    try {
      const contact = await contactService.getContact(contactId);
      setSelectedContact(contact);
      editForm.setFieldsValue({
        full_name: contact.full_name,
        department: contact.department,
        position: contact.position,
        internal_number: contact.internal_number,
        mobile_number: contact.mobile_number,
        email: contact.email,
        is_active: contact.is_active,
        comment: contact.comment,
      });
      setEditModalOpen(true);
    } catch {
      message.error('Ошибка загрузки данных контакта');
    }
  };

  const handleExport = async (format: 'csv' | 'xlsx' | 'json') => {
    try {
      await contactService.exportAndDownload({
        format,
        group_id: groupFilter,
        include_archived: activeFilter === undefined ? true : activeFilter,
      });
      message.success('Экспорт завершен');
    } catch {
      message.error('Ошибка экспорта');
    }
  };

  const handleImportSuccess = (result: BulkOperationResult) => {
    setImportModalOpen(false);
    loadContacts();
    loadStats();
  };

  const handleBulkDelete = async () => {
    try {
      await contactService.bulkDelete(selectedRowKeys, false);
      message.success(`Архивировано контактов: ${selectedRowKeys.length}`);
      setSelectedRowKeys([]);
      loadContacts();
      loadStats();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка');
    }
  };

  // =========================================================================
  // КОЛОНКИ ТАБЛИЦЫ
  // =========================================================================

  const columns: ColumnsType<ContactListItem> = [
    {
      title: 'ФИО',
      dataIndex: 'full_name',
      key: 'full_name',
      sorter: true,
      width: 250,
      fixed: 'left',
      render: (text: string, record: ContactListItem) => (
        <Space>
          <UserOutlined style={{ color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{text}</div>
            {record.department && (
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>{record.department}</div>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: 'Телефоны',
      key: 'phones',
      width: 220,
      render: (_: any, record: ContactListItem) => (
        <Space direction="vertical" size={2}>
          {record.mobile_number && (
            <Text>
              <PhoneOutlined style={{ marginRight: 4, color: '#2ecc71' }} />
              {contactService.formatPhone(record.mobile_number)}
              <Tag color="green" style={{ marginLeft: 4, fontSize: 10 }}>моб.</Tag>
            </Text>
          )}
          {record.internal_number && (
            <Text>
              <PhoneOutlined style={{ marginRight: 4, color: '#3498db' }} />
              {record.internal_number}
              <Tag color="blue" style={{ marginLeft: 4, fontSize: 10 }}>вн.</Tag>
            </Text>
          )}
          {!record.mobile_number && !record.internal_number && (
            <Text type="secondary">—</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Должность',
      dataIndex: 'position',
      key: 'position',
      sorter: true,
      width: 180,
      ellipsis: true,
      render: (text: string | null) => (
        <Text>{text || '—'}</Text>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 220,
      ellipsis: true,
      render: (text: string | null) => (
        text ? (
          <a href={`mailto:${text}`}>
            <MailOutlined style={{ marginRight: 4 }} />
            {text}
          </a>
        ) : (
          <Text type="secondary">—</Text>
        )
      ),
    },
    {
      title: 'Группы',
      dataIndex: 'group_names',
      key: 'groups',
      width: 200,
      render: (names: string[]) => (
        <Space wrap size={2}>
          {names.length > 0 ? names.map(name => (
            <Tag key={name} color="blue" style={{ fontSize: 11 }}>{name}</Tag>
          )) : (
            <Text type="secondary">—</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Теги',
      dataIndex: 'tag_names',
      key: 'tags',
      width: 200,
      render: (names: string[], record: ContactListItem) => (
        <Space wrap size={2}>
          {names.length > 0 ? names.map(name => (
            <Tag
              key={name}
              color={record.tag_colors?.[name] || '#95a5a6'}
              style={{ fontSize: 11 }}
            >
              {name}
            </Tag>
          )) : (
            <Text type="secondary">—</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) => (
        <Badge
          status={isActive ? 'success' : 'error'}
          text={isActive ? 'Активен' : 'Неактивен'}
        />
      ),
    },
    {
      title: 'Создан',
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
      width: 150,
      fixed: 'right',
      render: (_: any, record: ContactListItem) => (
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
            />
          </Tooltip>

          <Dropdown
            menu={{
              items: [
                {
                  key: 'toggle',
                  icon: record.is_active ? <CloseCircleOutlined /> : <CheckCircleOutlined />,
                  label: record.is_active ? 'Деактивировать' : 'Активировать',
                  onClick: () => handleToggleActive(record.id, !record.is_active, record.full_name),
                },
                { type: 'divider' },
                {
                  key: 'delete',
                  icon: <DeleteOutlined />,
                  label: 'Архивировать',
                  danger: true,
                  onClick: () => handleDeleteContact(record.id),
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
            <TeamOutlined /> Контакты
          </Title>
          <Text type="secondary">Управление контактной базой для оповещения</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            Обновить
          </Button>
          <Dropdown
            menu={{
              items: [
                { key: 'csv', label: 'CSV', onClick: () => handleExport('csv') },
                { key: 'xlsx', label: 'XLSX (Excel)', onClick: () => handleExport('xlsx') },
                { key: 'json', label: 'JSON', onClick: () => handleExport('json') },
              ],
            }}
          >
            <Button icon={<ExportOutlined />}>
              Экспорт
            </Button>
          </Dropdown>
          <Button
            icon={<ImportOutlined />}
            onClick={() => setImportModalOpen(true)}
          >
            Импорт
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              createForm.resetFields();
              setCreateModalOpen(true);
            }}
          >
            Добавить контакт
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
              <Statistic title="С мобильными" value={stats.with_mobile} valueStyle={{ color: '#3498db' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small">
              <Statistic title="В архиве" value={stats.archived} valueStyle={{ color: '#95a5a6' }} />
            </Card>
          </Col>
          {stats.by_department && stats.by_department.length > 0 && (
            <Col span={24} style={{ marginTop: 16 }}>
              <Card size="small" title="По подразделениям">
                <Space wrap>
                  {stats.by_department.slice(0, 10).map(d => (
                    <Tag key={d.department} color="blue">
                      {d.department}: {d.count}
                    </Tag>
                  ))}
                </Space>
              </Card>
            </Col>
          )}
        </Row>
      )}

      {/* Фильтры */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input.Search
            placeholder="Поиск по ФИО, отделу, номеру..."
            allowClear
            onSearch={handleSearch}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => !e.target.value && handleSearch('')}
          />

          <Select
            placeholder="Подразделение"
            allowClear
            style={{ width: 200 }}
            value={departmentFilter}
            onChange={(v) => { setDepartmentFilter(v); setPage(1); }}
            showSearch
            optionFilterProp="label"
          >
            {departments.map(dept => (
              <Option key={dept} value={dept}>{dept}</Option>
            ))}
          </Select>

          <Select
            placeholder="Группа"
            allowClear
            style={{ width: 200 }}
            value={groupFilter}
            onChange={(v) => { setGroupFilter(v); setPage(1); }}
            options={groups}
          />

          <Select
            placeholder="Статус"
            allowClear
            style={{ width: 130 }}
            value={activeFilter}
            onChange={(v) => { setActiveFilter(v); setPage(1); }}
          >
            <Option value={true}>✅ Активен</Option>
            <Option value={false}>❌ Неактивен</Option>
          </Select>

          <Select
            placeholder="Наличие номера"
            allowClear
            style={{ width: 170 }}
            value={hasMobileFilter}
            onChange={(v) => {
              setHasMobileFilter(v);
              if (v !== undefined) setHasInternalFilter(undefined);
              setPage(1);
            }}
          >
            <Option value={true}>📱 С мобильным</Option>
            <Option value={false}>📱 Без мобильного</Option>
          </Select>

          <Select
            placeholder="Наличие email"
            allowClear
            style={{ width: 150 }}
            value={hasEmailFilter}
            onChange={(v) => { setHasEmailFilter(v); setPage(1); }}
          >
            <Option value={true}>📧 С email</Option>
            <Option value={false}>📧 Без email</Option>
          </Select>

          <Button icon={<ClearOutlined />} onClick={handleClearFilters}>
            Сбросить
          </Button>
        </Space>
      </Card>

      {/* Таблица */}
      <Card>
        {selectedRowKeys.length > 0 && (
          <div style={{ marginBottom: 16, padding: '8px 12px', background: '#fff7e6', borderRadius: 6 }}>
            <Space>
              <Text strong>Выбрано: {selectedRowKeys.length}</Text>
              <Button size="small" onClick={() => {
                // Массовая активация
                selectedRowKeys.forEach(id => handleToggleActive(id, true, ''));
                setSelectedRowKeys([]);
              }}>
                Активировать все
              </Button>
              <Button size="small" onClick={() => {
                // Массовая деактивация
                selectedRowKeys.forEach(id => handleToggleActive(id, false, ''));
                setSelectedRowKeys([]);
              }}>
                Деактивировать все
              </Button>
              <Popconfirm
                title={`Архивировать ${selectedRowKeys.length} контактов?`}
                onConfirm={handleBulkDelete}
                okText="Да"
                cancelText="Нет"
              >
                <Button size="small" danger>
                  Архивировать все
                </Button>
              </Popconfirm>
            </Space>
          </div>
        )}

        <Table
          columns={columns}
          dataSource={contacts}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: totalContacts,
            showSizeChanger: true,
            showQuickJumper: true,
            pageSizeOptions: ['10', '25', '50', '100', '200'],
            showTotal: (total, range) => `${range[0]}-${range[1]} из ${total}`,
          }}
          onChange={handleTableChange}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
          }}
          scroll={{ x: 1400 }}
          size="middle"
        />
      </Card>

      {/* =====================================================================
          МОДАЛЬНЫЕ ОКНА
      ===================================================================== */}

      {/* Создание контакта */}
      <Modal
        title="Создание контакта"
        open={createModalOpen}
        onOk={handleCreateContact}
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
            name="full_name"
            label="ФИО"
            rules={[
              { required: true, message: 'Введите ФИО' },
              { min: 2, message: 'Минимум 2 символа' },
            ]}
          >
            <Input placeholder="Иванов Иван Иванович" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="department" label="Подразделение">
                <Input placeholder="ИТ-отдел" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="position" label="Должность">
                <Input placeholder="Инженер" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="mobile_number"
                label="Мобильный номер"
                rules={[
                  {
                    validator: (_, value) => {
                      if (!value) return Promise.resolve();
                      const validation = contactService.validatePhone(value);
                      if (validation.valid) return Promise.resolve();
                      return Promise.reject(new Error(validation.error || 'Неверный формат'));
                    },
                  },
                ]}
              >
                <Input placeholder="+7 (___) ___-__-__" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="internal_number"
                label="Внутренний номер"
                rules={[
                  {
                    validator: (_, value) => {
                      if (!value) return Promise.resolve();
                      const validation = contactService.validateInternalNumber(value);
                      if (validation.valid) return Promise.resolve();
                      return Promise.reject(new Error(validation.error || 'Неверный формат'));
                    },
                  },
                ]}
              >
                <Input placeholder="123" maxLength={4} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="email"
                label="Email"
                rules={[{ type: 'email', message: 'Неверный формат email' }]}
              >
                <Input placeholder="user@example.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="group_ids" label="Добавить в группы">
                <Select
                  mode="multiple"
                  placeholder="Выберите группы"
                  options={groups}
                  allowClear
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="comment" label="Комментарий">
            <Input.TextArea rows={2} placeholder="Произвольный комментарий" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Редактирование контакта */}
      <Modal
        title="Редактирование контакта"
        open={editModalOpen}
        onOk={handleEditContact}
        onCancel={() => {
          setEditModalOpen(false);
          setSelectedContact(null);
          editForm.resetFields();
        }}
        okText="Сохранить"
        cancelText="Отмена"
        width={600}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="full_name"
            label="ФИО"
            rules={[{ required: true, message: 'Введите ФИО' }]}
          >
            <Input />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="department" label="Подразделение">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="position" label="Должность">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="mobile_number" label="Мобильный номер">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="internal_number" label="Внутренний номер">
                <Input maxLength={4} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="email" label="Email">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="is_active" label="Активен" valuePropName="checked">
                <Badge status={editForm.getFieldValue('is_active') ? 'success' : 'error'} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="comment" label="Комментарий">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Детали контакта */}
      <Modal
        title="Информация о контакте"
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedContact(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            Закрыть
          </Button>,
        ]}
        width={700}
      >
        {selectedContact && (
          <div>
            <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="ФИО" span={2}>
                <Text strong style={{ fontSize: 16 }}>{selectedContact.full_name}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Подразделение">
                {selectedContact.department || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Должность">
                {selectedContact.position || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Мобильный">
                {selectedContact.mobile_number
                  ? contactService.formatPhone(selectedContact.mobile_number)
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Внутренний">
                {selectedContact.internal_number || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Email" span={2}>
                {selectedContact.email ? (
                  <a href={`mailto:${selectedContact.email}`}>{selectedContact.email}</a>
                ) : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Статус">
                {contactService.getStatusText(selectedContact.is_active, selectedContact.is_archived)}
              </Descriptions.Item>
              <Descriptions.Item label="Основной телефон">
                {selectedContact.primary_phone
                  ? contactService.formatPhone(selectedContact.primary_phone)
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Комментарий" span={2}>
                {selectedContact.comment || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Создан">
                {selectedContact.created_at
                  ? new Date(selectedContact.created_at).toLocaleString('ru-RU')
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Обновлен">
                {selectedContact.updated_at
                  ? new Date(selectedContact.updated_at).toLocaleString('ru-RU')
                  : '—'}
              </Descriptions.Item>
            </Descriptions>

            {/* Группы */}
            {selectedContact.groups.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <Title level={5}>Группы</Title>
                <Space wrap>
                  {selectedContact.groups.map(group => (
                    <Tag key={group.id} color={group.color || '#3498db'}>
                      {group.name}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}

            {/* Теги */}
            {selectedContact.tags.length > 0 && (
              <div>
                <Title level={5}>Теги</Title>
                <Space wrap>
                  {selectedContact.tags.map(tag => (
                    <Tag key={tag.id} color={tag.color || '#95a5a6'}>
                      {tag.name}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Импорт */}
      <ImportModal
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={handleImportSuccess}
      />
    </div>
  );
};

export default ContactsPage;
