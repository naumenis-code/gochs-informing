import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Switch,
  Select,
  Slider,
  InputNumber,
  Divider,
  message,
  Space,
  Typography,
  Alert,
  Spin,
  Row,
  Col,
  Tag,
  Badge,
  Modal,
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  PhoneOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  SafetyOutlined,
  BellOutlined,
  AudioOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  EditOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { settingsService } from '@services/settingsService';
import { monitoringService } from '@services/monitoringService';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface PBXSettings {
  host: string;
  port: number;
  extension: string;
  username: string;
  password: string;
  transport: 'udp' | 'tcp' | 'tls';
  max_channels: number;
  codecs: string[];
  register_enabled: boolean;
  status?: 'online' | 'offline' | 'checking';
}

interface SystemSettings {
  app_name: string;
  timezone: string;
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  max_concurrent_calls: number;
  recording_retention_days: number;
  backup_enabled: boolean;
  backup_time: string;
}

interface SecuritySettings {
  jwt_expire_minutes: number;
  refresh_token_expire_days: number;
  max_login_attempts: number;
  lockout_minutes: number;
  password_min_length: number;
  require_special_chars: boolean;
  session_timeout_minutes: number;
}

interface NotificationSettings {
  email_enabled: boolean;
  smtp_server: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  from_email: string;
  admin_email: string;
  notify_on_campaign_complete: boolean;
  notify_on_system_error: boolean;
}

const Settings: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [activeTab, setActiveTab] = useState('pbx');
  
  // Forms
  const [pbxForm] = Form.useForm();
  const [systemForm] = Form.useForm();
  const [securityForm] = Form.useForm();
  const [notificationForm] = Form.useForm();
  
  // PBX Status
  const [pbxStatus, setPbxStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [pbxSettings, setPbxSettings] = useState<PBXSettings | null>(null);

  // Load all settings
  useEffect(() => {
    loadAllSettings();
    checkPBXStatus();
  }, []);

  const loadAllSettings = async () => {
    setLoading(true);
    try {
      const [pbx, system, security, notifications] = await Promise.all([
        settingsService.getPBXSettings(),
        settingsService.getSystemSettings(),
        settingsService.getSecuritySettings(),
        settingsService.getNotificationSettings(),
      ]);
      
      setPbxSettings(pbx);
      pbxForm.setFieldsValue(pbx);
      systemForm.setFieldsValue(system);
      securityForm.setFieldsValue(security);
      notificationForm.setFieldsValue(notifications);
    } catch (error) {
      message.error('Не удалось загрузить настройки');
    } finally {
      setLoading(false);
    }
  };

  const checkPBXStatus = async () => {
    try {
      const status = await settingsService.checkPBXStatus();
      setPbxStatus(status.registered ? 'online' : 'offline');
    } catch {
      setPbxStatus('offline');
    }
  };

  const handleSaveSettings = async (section: string, values: any) => {
    setSaving(true);
    try {
      switch (section) {
        case 'pbx':
          await settingsService.updatePBXSettings(values);
          message.success('Настройки телефонии сохранены');
          checkPBXStatus();
          break;
        case 'system':
          await settingsService.updateSystemSettings(values);
          message.success('Системные настройки сохранены');
          break;
        case 'security':
          await settingsService.updateSecuritySettings(values);
          message.success('Настройки безопасности сохранены');
          break;
        case 'notification':
          await settingsService.updateNotificationSettings(values);
          message.success('Настройки уведомлений сохранены');
          break;
      }
    } catch (error) {
      message.error('Ошибка при сохранении настроек');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    const values = pbxForm.getFieldsValue();
    setTestingConnection(true);
    try {
      const result = await settingsService.testPBXConnection(values);
      if (result.success) {
        message.success('Подключение к FreePBX успешно');
        setPbxStatus('online');
      } else {
        message.error(`Ошибка подключения: ${result.error}`);
        setPbxStatus('offline');
      }
    } catch {
      message.error('Ошибка тестирования подключения');
      setPbxStatus('offline');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleReloadAsterisk = async () => {
    try {
      await settingsService.reloadAsteriskConfig();
      message.success('Конфигурация Asterisk перезагружена');
    } catch {
      message.error('Ошибка перезагрузки конфигурации');
    }
  };

  const handleApplySettings = async () => {
    try {
      await settingsService.applyPBXSettings();
      message.success('Настройки применены к Asterisk');
      checkPBXStatus();
    } catch {
      message.error('Ошибка применения настроек');
    }
  };

  const renderPBXStatus = () => {
    const statusConfig = {
      online: { color: 'success', icon: <CheckCircleOutlined />, text: 'Онлайн' },
      offline: { color: 'error', icon: <CloseCircleOutlined />, text: 'Офлайн' },
      checking: { color: 'processing', icon: <SyncOutlined spin />, text: 'Проверка' },
    };
    const config = statusConfig[pbxStatus];
    return <Badge status={config.color as any} text={config.text} />;
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          <SettingOutlined style={{ marginRight: 12 }} />
          Настройки системы
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadAllSettings}>
            Обновить
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Card>
          <Tabs activeKey={activeTab} onChange={setActiveTab} type="card">
            {/* ========== ТЕЛЕФОНИЯ ========== */}
            <TabPane
              tab={
                <span>
                  <PhoneOutlined />
                  Телефония (FreePBX)
                </span>
              }
              key="pbx"
            >
              <Alert
                message={
                  <Space>
                    <span>Статус регистрации:</span>
                    {renderPBXStatus()}
                  </Space>
                }
                type={pbxStatus === 'online' ? 'success' : 'warning'}
                showIcon
                style={{ marginBottom: 24 }}
                action={
                  <Space>
                    <Button size="small" onClick={checkPBXStatus}>
                      Проверить
                    </Button>
                    <Button size="small" onClick={handleReloadAsterisk}>
                      Перезагрузить PJSIP
                    </Button>
                  </Space>
                }
              />

              <Form
                form={pbxForm}
                layout="vertical"
                onFinish={(values) => handleSaveSettings('pbx', values)}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="IP адрес FreePBX"
                      name="host"
                      rules={[{ required: true, message: 'Введите IP адрес' }]}
                    >
                      <Input placeholder="192.168.1.10" prefix={<CloudServerOutlined />} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Порт SIP (PJSIP)"
                      name="port"
                      rules={[{ required: true, message: 'Введите порт' }]}
                    >
                      <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Внутренний номер (Extension)"
                      name="extension"
                      rules={[{ required: true, message: 'Введите номер' }]}
                    >
                      <Input placeholder="gochs" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Логин"
                      name="username"
                      rules={[{ required: true, message: 'Введите логин' }]}
                    >
                      <Input placeholder="gochs" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Пароль (Secret)"
                      name="password"
                      rules={[{ required: true, message: 'Введите пароль' }]}
                    >
                      <Input.Password placeholder="Секретный ключ" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Транспорт"
                      name="transport"
                      rules={[{ required: true }]}
                    >
                      <Select>
                        <Option value="udp">UDP</Option>
                        <Option value="tcp">TCP</Option>
                        <Option value="tls">TLS</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Максимум каналов"
                      name="max_channels"
                    >
                      <Slider
                        min={1}
                        max={100}
                        marks={{ 1: '1', 20: '20', 50: '50', 100: '100' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Кодеки"
                      name="codecs"
                    >
                      <Select mode="multiple" placeholder="Выберите кодеки">
                        <Option value="ulaw">ulaw (G.711)</Option>
                        <Option value="alaw">alaw (G.711)</Option>
                        <Option value="g729">G.729</Option>
                        <Option value="opus">Opus</Option>
                        <Option value="gsm">GSM</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Включить регистрацию"
                      name="register_enabled"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="Да" unCheckedChildren="Нет" />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider />

                <Form.Item>
                  <Space>
                    <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                      Сохранить настройки
                    </Button>
                    <Button icon={<ApiOutlined />} onClick={handleTestConnection} loading={testingConnection}>
                      Тестировать подключение
                    </Button>
                    <Button onClick={handleApplySettings}>
                      Применить к Asterisk
                    </Button>
                  </Space>
                </Form.Item>
              </Form>
            </TabPane>

            {/* ========== СИСТЕМНЫЕ ========== */}
            <TabPane
              tab={
                <span>
                  <CloudServerOutlined />
                  Системные
                </span>
              }
              key="system"
            >
              <Form
                form={systemForm}
                layout="vertical"
                onFinish={(values) => handleSaveSettings('system', values)}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Название системы"
                      name="app_name"
                    >
                      <Input placeholder="ГО-ЧС Информирование" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Часовой пояс"
                      name="timezone"
                    >
                      <Select showSearch>
                        <Option value="Europe/Moscow">Москва (UTC+3)</Option>
                        <Option value="Europe/London">Лондон (UTC+0)</Option>
                        <Option value="Asia/Yekaterinburg">Екатеринбург (UTC+5)</Option>
                        <Option value="Asia/Novosibirsk">Новосибирск (UTC+7)</Option>
                        <Option value="Asia/Vladivostok">Владивосток (UTC+10)</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Уровень логирования"
                      name="log_level"
                    >
                      <Select>
                        <Option value="DEBUG">DEBUG (Отладка)</Option>
                        <Option value="INFO">INFO (Информация)</Option>
                        <Option value="WARNING">WARNING (Предупреждения)</Option>
                        <Option value="ERROR">ERROR (Ошибки)</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Максимум одновременных звонков"
                      name="max_concurrent_calls"
                    >
                      <InputNumber min={1} max={100} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Хранить записи (дней)"
                      name="recording_retention_days"
                    >
                      <InputNumber min={1} max={365} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider>Резервное копирование</Divider>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Автоматическое резервное копирование"
                      name="backup_enabled"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="Включено" unCheckedChildren="Выключено" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Время запуска"
                      name="backup_time"
                    >
                      <Input placeholder="02:00" />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item>
                  <Space>
                    <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                      Сохранить настройки
                    </Button>
                    <Button onClick={() => systemForm.resetFields()}>
                      Сбросить
                    </Button>
                  </Space>
                </Form.Item>
              </Form>
            </TabPane>

            {/* ========== БЕЗОПАСНОСТЬ ========== */}
            <TabPane
              tab={
                <span>
                  <SafetyOutlined />
                  Безопасность
                </span>
              }
              key="security"
            >
              <Form
                form={securityForm}
                layout="vertical"
                onFinish={(values) => handleSaveSettings('security', values)}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Срок действия JWT токена (минут)"
                      name="jwt_expire_minutes"
                    >
                      <InputNumber min={5} max={1440} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Срок действия Refresh токена (дней)"
                      name="refresh_token_expire_days"
                    >
                      <InputNumber min={1} max={30} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Максимум попыток входа"
                      name="max_login_attempts"
                    >
                      <InputNumber min={3} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Блокировка (минут)"
                      name="lockout_minutes"
                    >
                      <InputNumber min={5} max={60} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Минимальная длина пароля"
                      name="password_min_length"
                    >
                      <InputNumber min={8} max={32} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Требовать спецсимволы"
                      name="require_special_chars"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="Да" unCheckedChildren="Нет" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Таймаут сессии (минут)"
                      name="session_timeout_minutes"
                    >
                      <InputNumber min={5} max={480} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                    Сохранить настройки безопасности
                  </Button>
                </Form.Item>
              </Form>
            </TabPane>

            {/* ========== УВЕДОМЛЕНИЯ ========== */}
            <TabPane
              tab={
                <span>
                  <BellOutlined />
                  Уведомления
                </span>
              }
              key="notification"
            >
              <Form
                form={notificationForm}
                layout="vertical"
                onFinish={(values) => handleSaveSettings('notification', values)}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Включить Email уведомления"
                      name="email_enabled"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="Включено" unCheckedChildren="Выключено" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="SMTP сервер"
                      name="smtp_server"
                    >
                      <Input placeholder="smtp.gmail.com" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="SMTP порт"
                      name="smtp_port"
                    >
                      <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="SMTP пользователь"
                      name="smtp_username"
                    >
                      <Input placeholder="user@example.com" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="SMTP пароль"
                      name="smtp_password"
                    >
                      <Input.Password placeholder="Пароль" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="От кого"
                      name="from_email"
                    >
                      <Input placeholder="gochs@company.ru" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Email администратора"
                      name="admin_email"
                    >
                      <Input placeholder="admin@company.ru" />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider />

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Уведомлять о завершении кампании"
                      name="notify_on_campaign_complete"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="Да" unCheckedChildren="Нет" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Уведомлять об ошибках системы"
                      name="notify_on_system_error"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="Да" unCheckedChildren="Нет" />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                    Сохранить настройки уведомлений
                  </Button>
                </Form.Item>
              </Form>
            </TabPane>
          </Tabs>
        </Card>
      </Spin>
    </div>
  );
};

export default Settings;
