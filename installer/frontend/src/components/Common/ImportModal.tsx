import React, { useState, useCallback } from 'react';
import {
  Modal,
  Upload,
  Button,
  Space,
  Typography,
  Alert,
  Steps,
  Progress,
  Checkbox,
  Select,
  Divider,
  Table,
  Tag,
  message,
  Tooltip,
  Radio,
  Card,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  InboxOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { UploadProps, UploadFile } from 'antd';
import { contactService } from '@services/contactService';
import { groupService } from '@services/groupService';
import type { BulkOperationResult } from '@services/contactService';

const { Text, Title, Paragraph } = Typography;
const { Dragger } = Upload;

// ============================================================================
// ТИПЫ
// ============================================================================

export interface ImportModalProps {
  /** Видимость модального окна */
  open: boolean;
  /** Callback закрытия */
  onClose: () => void;
  /** Callback после успешного импорта */
  onSuccess?: (result: BulkOperationResult) => void;
  /** Callback после ошибки */
  onError?: (error: Error) => void;
}

// Шаги импорта
enum ImportStep {
  UPLOAD = 0,
  SETTINGS = 1,
  IMPORTING = 2,
  RESULT = 3,
}

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

const ImportModal: React.FC<ImportModalProps> = ({
  open,
  onClose,
  onSuccess,
  onError,
}) => {
  // =========================================================================
  // СОСТОЯНИЕ
  // =========================================================================

  const [currentStep, setCurrentStep] = useState<ImportStep>(ImportStep.UPLOAD);
  const [file, setFile] = useState<File | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [importResult, setImportResult] = useState<BulkOperationResult | null>(null);
  const [isImporting, setIsImporting] = useState(false);

  // Настройки импорта
  const [updateExisting, setUpdateExisting] = useState(false);
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [defaultGroupId, setDefaultGroupId] = useState<string | undefined>(undefined);
  const [encoding, setEncoding] = useState('utf-8');
  const [groups, setGroups] = useState<Array<{ value: string; label: string; color: string; memberCount: number }>>([]);
  const [groupsLoaded, setGroupsLoaded] = useState(false);

  // =========================================================================
  // ЗАГРУЗКА ГРУПП ДЛЯ ВЫПАДАЮЩЕГО СПИСКА
  // =========================================================================

  const loadGroups = useCallback(async () => {
    if (groupsLoaded) return;
    
    try {
      const groupList = await groupService.getAllGroupsForSelect();
      setGroups(groupList);
      setGroupsLoaded(true);
    } catch {
      // Не критично, просто не показываем выбор группы
    }
  }, [groupsLoaded]);

  React.useEffect(() => {
    if (open && currentStep === ImportStep.SETTINGS) {
      loadGroups();
    }
  }, [open, currentStep, loadGroups]);

  // =========================================================================
  // ОБРАБОТЧИКИ ЗАГРУЗКИ ФАЙЛА
  // =========================================================================

  const handleBeforeUpload = useCallback((file: File): boolean | Promise<void> => {
    const validation = contactService.validateImportFile(file);
    
    if (!validation.valid) {
      message.error(validation.error || 'Неверный формат файла');
      return false;
    }

    setFile(file);
    setCurrentStep(ImportStep.SETTINGS);
    return false; // Не загружаем автоматически
  }, []);

  const handleRemoveFile = useCallback(() => {
    setFile(null);
    setFileList([]);
    setCurrentStep(ImportStep.UPLOAD);
  }, []);

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.csv,.xlsx,.xls',
    fileList: fileList,
    beforeUpload: handleBeforeUpload as any,
    onRemove: handleRemoveFile,
    onChange: (info) => {
      setFileList(info.fileList);
    },
    showUploadList: {
      showRemoveIcon: true,
      showPreviewIcon: true,
    },
  };

  // =========================================================================
  // ЗАПУСК ИМПОРТА
  // =========================================================================

  const handleStartImport = useCallback(async () => {
    if (!file) {
      message.error('Файл не выбран');
      return;
    }

    setIsImporting(true);
    setCurrentStep(ImportStep.IMPORTING);
    setUploadProgress(0);

    try {
      const result = await contactService.importContacts(
        file,
        {
          update_existing: updateExisting,
          skip_duplicates: skipDuplicates,
          default_group_id: defaultGroupId,
          encoding: encoding,
        },
        (progress) => {
          setUploadProgress(progress);
        }
      );

      setImportResult(result);
      setCurrentStep(ImportStep.RESULT);

      if (result.error_count === 0) {
        message.success(`Импорт завершен: ${result.success_count} контактов`);
      } else {
        message.warning(
          `Импорт завершен с ошибками: ${result.success_count} успешно, ${result.error_count} ошибок`
        );
      }

      onSuccess?.(result);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Ошибка импорта');
      setCurrentStep(ImportStep.SETTINGS);
      onError?.(error);
    } finally {
      setIsImporting(false);
    }
  }, [file, updateExisting, skipDuplicates, defaultGroupId, encoding, onSuccess, onError]);

  // =========================================================================
  // СБРОС
  // =========================================================================

  const handleReset = useCallback(() => {
    setCurrentStep(ImportStep.UPLOAD);
    setFile(null);
    setFileList([]);
    setUploadProgress(0);
    setImportResult(null);
    setIsImporting(false);
    setUpdateExisting(false);
    setSkipDuplicates(true);
    setDefaultGroupId(undefined);
    setEncoding('utf-8');
  }, []);

  // =========================================================================
  // ЗАКРЫТИЕ
  // =========================================================================

  const handleClose = useCallback(() => {
    handleReset();
    onClose();
  }, [handleReset, onClose]);

  // =========================================================================
  // СКАЧИВАНИЕ ШАБЛОНА
  // =========================================================================

  const handleDownloadTemplate = useCallback(async (format: 'csv' | 'xlsx') => {
    try {
      await contactService.downloadTemplate(format);
      message.success('Шаблон скачан');
    } catch {
      message.error('Ошибка скачивания шаблона');
    }
  }, []);

  // =========================================================================
  // РЕНДЕР ШАГА 1: ЗАГРУЗКА ФАЙЛА
  // =========================================================================

  const renderUploadStep = () => (
    <div>
      <Alert
        message="Поддерживаемые форматы"
        description={
          <div>
            <p>• CSV (разделитель: запятая, кодировка: UTF-8)</p>
            <p>• XLSX / XLS (Microsoft Excel)</p>
            <p>• Максимальный размер файла: 10 МБ</p>
            <p>• Максимальное количество строк: 10 000</p>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Dragger {...uploadProps}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">Нажмите или перетащите файл в эту область</p>
        <p className="ant-upload-hint">
          Поддерживаются CSV, XLSX, XLS файлы
        </p>
      </Dragger>

      <Divider />

      <div style={{ textAlign: 'center' }}>
        <Space>
          <Text>Нет файла? Скачайте шаблон:</Text>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadTemplate('csv')}
          >
            CSV
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadTemplate('xlsx')}
          >
            XLSX
          </Button>
        </Space>
      </div>
    </div>
  );

  // =========================================================================
  // РЕНДЕР ШАГА 2: НАСТРОЙКИ ИМПОРТА
  // =========================================================================

  const renderSettingsStep = () => (
    <div>
      {file && (
        <Card size="small" style={{ marginBottom: 16, background: '#f0f5ff' }}>
          <Space>
            {file.name.endsWith('.csv') ? (
              <FileTextOutlined style={{ fontSize: 24, color: '#2ecc71' }} />
            ) : (
              <FileExcelOutlined style={{ fontSize: 24, color: '#2ecc71' }} />
            )}
            <div>
              <Text strong>{file.name}</Text>
              <br />
              <Text type="secondary">
                {(file.size / 1024).toFixed(1)} КБ
              </Text>
            </div>
            <Button size="small" onClick={handleRemoveFile}>
              Изменить
            </Button>
          </Space>
        </Card>
      )}

      <Title level={5}>Параметры импорта</Title>

      <div style={{ marginBottom: 16 }}>
        <Checkbox
          checked={updateExisting}
          onChange={(e) => setUpdateExisting(e.target.checked)}
        >
          Обновлять существующие контакты
        </Checkbox>
        <Tooltip title="Если контакт с таким мобильным номером уже существует, его данные будут обновлены">
          <QuestionCircleOutlined style={{ color: '#8c8c8c', marginLeft: 8 }} />
        </Tooltip>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Checkbox
          checked={skipDuplicates}
          onChange={(e) => setSkipDuplicates(e.target.checked)}
        >
          Пропускать дубликаты
        </Checkbox>
        <Tooltip title="Контакт с таким же мобильным номером будет пропущен">
          <QuestionCircleOutlined style={{ color: '#8c8c8c', marginLeft: 8 }} />
        </Tooltip>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Text>Добавить все контакты в группу:</Text>
        <Select
          style={{ width: '100%', marginTop: 4 }}
          placeholder="Выберите группу (опционально)"
          allowClear
          showSearch
          optionFilterProp="label"
          value={defaultGroupId}
          onChange={setDefaultGroupId}
          options={groups.map(g => ({
            value: g.value,
            label: g.label,
          }))}
          loading={!groupsLoaded}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <Text>Кодировка файла:</Text>
        <Radio.Group
          value={encoding}
          onChange={(e) => setEncoding(e.target.value)}
          style={{ marginLeft: 16 }}
        >
          <Radio.Button value="utf-8">UTF-8</Radio.Button>
          <Radio.Button value="windows-1251">Windows-1251</Radio.Button>
          <Radio.Button value="cp1251">CP1251</Radio.Button>
        </Radio.Group>
      </div>

      <Divider />

      <div style={{ textAlign: 'right' }}>
        <Space>
          <Button onClick={() => setCurrentStep(ImportStep.UPLOAD)}>
            Назад
          </Button>
          <Button type="primary" onClick={handleStartImport} disabled={!file}>
            Начать импорт
          </Button>
        </Space>
      </div>
    </div>
  );

  // =========================================================================
  // РЕНДЕР ШАГА 3: ПРОГРЕСС ИМПОРТА
  // =========================================================================

  const renderImportingStep = () => (
    <div style={{ textAlign: 'center', padding: '40px 0' }}>
      <Title level={4}>Импорт выполняется...</Title>
      <Progress
        type="circle"
        percent={uploadProgress}
        status="active"
        style={{ marginBottom: 24 }}
      />
      <Paragraph type="secondary">
        Пожалуйста, не закрывайте окно до завершения импорта
      </Paragraph>
      {file && (
        <Text type="secondary">
          Файл: {file.name} ({(file.size / 1024).toFixed(1)} КБ)
        </Text>
      )}
    </div>
  );

  // =========================================================================
  // РЕНДЕР ШАГА 4: РЕЗУЛЬТАТ
  // =========================================================================

  const renderResultStep = () => {
    if (!importResult) return null;

    const { total_processed, success_count, error_count, skipped_count, errors } = importResult;
    const hasErrors = error_count > 0;
    const hasSkipped = skipped_count && skipped_count > 0;

    return (
      <div>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          {hasErrors ? (
            <ExclamationCircleOutlined style={{ fontSize: 48, color: '#f39c12' }} />
          ) : (
            <CheckCircleOutlined style={{ fontSize: 48, color: '#2ecc71' }} />
          )}
          <Title level={4} style={{ marginTop: 16 }}>
            {hasErrors ? 'Импорт завершен с предупреждениями' : 'Импорт успешно завершен!'}
          </Title>
        </div>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="Всего"
                value={total_processed}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="Успешно"
                value={success_count}
                valueStyle={{ color: '#2ecc71' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          {hasSkipped && (
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="Пропущено"
                  value={skipped_count}
                  valueStyle={{ color: '#3498db' }}
                  prefix={<QuestionCircleOutlined />}
                />
              </Card>
            </Col>
          )}
          <Col span={hasSkipped ? 6 : 6}>
            <Card size="small">
              <Statistic
                title="Ошибки"
                value={error_count}
                valueStyle={{ color: hasErrors ? '#e74c3c' : '#95a5a6' }}
                prefix={<CloseCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {hasErrors && errors.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Title level={5}>Ошибки импорта:</Title>
            <Table
              dataSource={errors.map((err, index) => ({
                key: index,
                row: err.row || '—',
                name: err.name || 'Неизвестно',
                error: err.error,
              }))}
              columns={[
                {
                  title: 'Строка',
                  dataIndex: 'row',
                  key: 'row',
                  width: 80,
                },
                {
                  title: 'Имя',
                  dataIndex: 'name',
                  key: 'name',
                  width: 200,
                },
                {
                  title: 'Ошибка',
                  dataIndex: 'error',
                  key: 'error',
                  render: (text: string) => (
                    <Tag color="error" style={{ whiteSpace: 'pre-wrap' }}>
                      {text}
                    </Tag>
                  ),
                },
              ]}
              size="small"
              pagination={{ pageSize: 5 }}
              scroll={{ y: 200 }}
            />
          </div>
        )}

        <div style={{ textAlign: 'center' }}>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              Импортировать еще
            </Button>
            <Button type="primary" onClick={handleClose}>
              Готово
            </Button>
          </Space>
        </div>
      </div>
    );
  };

  // =========================================================================
  // ШАГИ
  // =========================================================================

  const stepItems = [
    { title: 'Загрузка файла', icon: <InboxOutlined /> },
    { title: 'Настройки', icon: <FileExcelOutlined /> },
    { title: 'Импорт', icon: <ReloadOutlined spin={isImporting} /> },
    { title: 'Результат', icon: <CheckCircleOutlined /> },
  ];

  // =========================================================================
  // РЕНДЕР МОДАЛЬНОГО ОКНА
  // =========================================================================

  return (
    <Modal
      title="Импорт контактов"
      open={open}
      onCancel={handleClose}
      width={700}
      footer={currentStep === ImportStep.RESULT ? null : undefined}
      maskClosable={!isImporting}
      closable={!isImporting}
    >
      <Steps
        current={currentStep}
        items={stepItems}
        size="small"
        style={{ marginBottom: 24 }}
      />

      {currentStep === ImportStep.UPLOAD && renderUploadStep()}
      {currentStep === ImportStep.SETTINGS && renderSettingsStep()}
      {currentStep === ImportStep.IMPORTING && renderImportingStep()}
      {currentStep === ImportStep.RESULT && renderResultStep()}
    </Modal>
  );
};

export default ImportModal;
