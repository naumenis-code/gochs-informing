#!/bin/bash

################################################################################
# Модуль: 03-db.sh
# Назначение: Установка и настройка PostgreSQL
################################################################################

source "${UTILS_DIR}/utils/common.sh"

MODULE_NAME="03-db"
MODULE_DESCRIPTION="PostgreSQL база данных"

# Версия PostgreSQL
POSTGRESQL_VERSION="15"

install() {
    log_step "Установка и настройка PostgreSQL"
    
    # Проверка наличия PostgreSQL
    if command -v psql &> /dev/null; then
        PG_VERSION=$(psql --version | awk '{print $3}' | cut -d'.' -f1)
        log_info "PostgreSQL уже установлен (версия $PG_VERSION)"
    else
        log_info "Установка PostgreSQL $POSTGRESQL_VERSION..."
        
        # Добавление официального репозитория PostgreSQL
        sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
        wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
        
        apt-get update
        apt-get install -y \
            postgresql-$POSTGRESQL_VERSION \
            postgresql-contrib-$POSTGRESQL_VERSION \
            postgresql-client-$POSTGRESQL_VERSION \
            libpq-dev
        
        log_info "PostgreSQL $POSTGRESQL_VERSION установлен"
    fi
    
    # Остановка PostgreSQL для настройки
    systemctl stop postgresql
    
    # Оптимизация конфигурации PostgreSQL
    log_info "Оптимизация конфигурации PostgreSQL..."
    configure_postgresql
    
    # Запуск PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Ожидание запуска
    wait_for_service "postgresql" 30
    
    # Создание базы данных и пользователя
    log_info "Создание базы данных и пользователя..."
    create_database_and_user
    
    # Создание структуры базы данных
    log_info "Создание структуры базы данных..."
    create_tables
    
    # Создание скриптов обслуживания
    create_maintenance_scripts
    
    # Настройка резервного копирования
    setup_backup
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "База данных: $POSTGRES_DB"
    log_info "Пользователь: $POSTGRES_USER"
    log_info "Пароль сохранен в /root/.gochs_credentials"
    
    return 0
}

configure_postgresql() {
    local pg_conf="/etc/postgresql/$POSTGRESQL_VERSION/main/postgresql.conf"
    
    # Резервное копирование оригинальной конфигурации
    backup_file "$pg_conf"
    
    # Расчет оптимальных параметров
    local total_ram=$(free -m | awk '/^Mem:/{print $2}')
    local shared_buffers=$((total_ram / 4))
    local effective_cache_size=$((total_ram * 3 / 4))
    local maintenance_work_mem=$((total_ram / 16))
    local work_mem=$((total_ram / 50))
    
    # Применение оптимизированных настроек
    cat >> "$pg_conf" << EOF

# ================================================
# ГО-ЧС Информирование - Оптимизированные настройки
# ================================================

# Connection Settings
max_connections = 200
superuser_reserved_connections = 10

# Memory Settings
shared_buffers = ${shared_buffers}MB
effective_cache_size = ${effective_cache_size}MB
maintenance_work_mem = ${maintenance_work_mem}MB
work_mem = ${work_mem}MB

# Write Ahead Log
wal_level = replica
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 4GB
min_wal_size = 1GB

# Query Tuning
random_page_cost = 1.1
effective_io_concurrency = 200

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0

# Autovacuum
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
autovacuum_vacuum_scale_factor = 0.05
autovacuum_analyze_scale_factor = 0.02

# Locale
lc_messages = 'ru_RU.UTF-8'
lc_monetary = 'ru_RU.UTF-8'
lc_numeric = 'ru_RU.UTF-8'
lc_time = 'ru_RU.UTF-8'
timezone = 'Europe/Moscow'

EOF
    
    log_info "Конфигурация PostgreSQL оптимизирована"
}

create_database_and_user() {
    # Создание пользователя и базы данных
    sudo -u postgres psql << EOF
-- Удаление существующих объектов (если есть)
DROP DATABASE IF EXISTS $POSTGRES_DB;
DROP USER IF EXISTS $POSTGRES_USER;

-- Создание пользователя
CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';

-- Создание базы данных
CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER ENCODING 'UTF8' LC_COLLATE 'ru_RU.UTF-8' LC_CTYPE 'ru_RU.UTF-8' TEMPLATE template0;

-- Подключение к базе данных
\c $POSTGRES_DB

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Настройка прав
GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO $POSTGRES_USER;

-- Настройка схемы по умолчанию
ALTER DATABASE $POSTGRES_DB SET search_path TO public;
ALTER USER $POSTGRES_USER SET search_path TO public;

EOF

    log_info "База данных и пользователь созданы"
}

create_tables() {
    # Создание SQL скрипта для инициализации таблиц
    cat > /tmp/init_gochs_db.sql << 'EOF'
-- =====================================================
-- ГО-ЧС Информирование - Схема базы данных
-- Версия: 1.0.0
-- =====================================================

-- Таблица пользователей системы
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица сессий пользователей
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Таблица контактов
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    position VARCHAR(100),
    internal_number VARCHAR(10),
    mobile_number VARCHAR(20),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    comment TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица групп контактов
CREATE TABLE IF NOT EXISTS contact_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3498db',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Связка контактов и групп (многие ко многим)
CREATE TABLE IF NOT EXISTS contact_group_members (
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    group_id UUID REFERENCES contact_groups(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, group_id)
);

-- Таблица тегов
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7) DEFAULT '#95a5a6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Связка контактов и тегов
CREATE TABLE IF NOT EXISTS contact_tags (
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, tag_id)
);

-- Таблица сценариев оповещения
CREATE TABLE IF NOT EXISTS notification_scenarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    text_content TEXT,
    audio_file_path VARCHAR(500),
    duration INTEGER, -- в секундах
    is_active BOOLEAN DEFAULT true,
    is_archived BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица Playbook для входящих звонков
CREATE TABLE IF NOT EXISTS playbooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    text_content TEXT,
    audio_file_path VARCHAR(500),
    is_active BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица кампаний обзвона
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    scenario_id UUID REFERENCES notification_scenarios(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, paused, completed, stopped
    priority INTEGER DEFAULT 5, -- 1-10, где 1 - наивысший
    max_retries INTEGER DEFAULT 3,
    retry_interval INTEGER DEFAULT 300, -- секунды
    max_channels INTEGER DEFAULT 20,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица групп для кампании
CREATE TABLE IF NOT EXISTS campaign_groups (
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    group_id UUID REFERENCES contact_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (campaign_id, group_id)
);

-- Таблица попыток звонков
CREATE TABLE IF NOT EXISTS call_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    attempt_number INTEGER DEFAULT 1,
    status VARCHAR(50), -- queued, dialing, answered, completed, busy, no_answer, failed, cancelled
    duration INTEGER, -- секунды
    call_sid VARCHAR(100), -- ID звонка в Asterisk
    started_at TIMESTAMP,
    answered_at TIMESTAMP,
    ended_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица входящих звонков
CREATE TABLE IF NOT EXISTS inbound_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    caller_number VARCHAR(20) NOT NULL,
    caller_name VARCHAR(255),
    playbook_id UUID REFERENCES playbooks(id),
    recording_path VARCHAR(500),
    transcription TEXT,
    duration INTEGER,
    status VARCHAR(50), -- answered, recorded, transcribed, processed
    call_sid VARCHAR(100),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица аудита действий
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек системы
CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    category VARCHAR(50),
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица интеграции с Asterisk
CREATE TABLE IF NOT EXISTS asterisk_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pbx_host VARCHAR(255) NOT NULL,
    pbx_port INTEGER DEFAULT 5060,
    extension VARCHAR(20) NOT NULL,
    username VARCHAR(100),
    password VARCHAR(100),
    transport VARCHAR(10) DEFAULT 'udp',
    max_channels INTEGER DEFAULT 50,
    codecs TEXT DEFAULT 'ulaw,alaw',
    is_registered BOOLEAN DEFAULT false,
    last_check TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица статистики звонков
CREATE TABLE IF NOT EXISTS call_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    total_calls INTEGER DEFAULT 0,
    answered_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    total_duration INTEGER DEFAULT 0,
    avg_duration INTEGER DEFAULT 0,
    campaign_id UUID REFERENCES campaigns(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для оптимизации
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

CREATE INDEX idx_contacts_full_name ON contacts(full_name);
CREATE INDEX idx_contacts_department ON contacts(department);
CREATE INDEX idx_contacts_mobile_number ON contacts(mobile_number);
CREATE INDEX idx_contacts_internal_number ON contacts(internal_number);
CREATE INDEX idx_contacts_is_active ON contacts(is_active);

CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_created_at ON campaigns(created_at);

CREATE INDEX idx_call_attempts_campaign_id ON call_attempts(campaign_id);
CREATE INDEX idx_call_attempts_contact_id ON call_attempts(contact_id);
CREATE INDEX idx_call_attempts_status ON call_attempts(status);
CREATE INDEX idx_call_attempts_started_at ON call_attempts(started_at);

CREATE INDEX idx_inbound_calls_caller_number ON inbound_calls(caller_number);
CREATE INDEX idx_inbound_calls_started_at ON inbound_calls(started_at);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

CREATE INDEX idx_settings_key ON settings(key);

-- Создание представлений
CREATE OR REPLACE VIEW v_active_contacts AS
SELECT * FROM contacts WHERE is_active = true;

CREATE OR REPLACE VIEW v_campaign_summary AS
SELECT 
    c.id,
    c.name,
    c.status,
    c.priority,
    COUNT(ca.id) as total_attempts,
    SUM(CASE WHEN ca.status = 'completed' THEN 1 ELSE 0 END) as successful_calls,
    SUM(CASE WHEN ca.status IN ('busy', 'no_answer', 'failed') THEN 1 ELSE 0 END) as failed_calls,
    c.created_at,
    c.started_at,
    c.completed_at
FROM campaigns c
LEFT JOIN call_attempts ca ON c.id = ca.campaign_id
GROUP BY c.id;

-- Создание триггеров для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scenarios_updated_at BEFORE UPDATE ON notification_scenarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Вставка начальных данных
INSERT INTO settings (key, value, category, description) VALUES
('system.name', 'ГО-ЧС Информирование', 'general', 'Название системы'),
('system.version', '1.0.0', 'general', 'Версия системы'),
('notification.max_channels', '20', 'notification', 'Максимальное количество одновременных звонков'),
('notification.default_retries', '3', 'notification', 'Количество повторных попыток по умолчанию'),
('notification.retry_interval', '300', 'notification', 'Интервал между повторами (сек)'),
('recording.format', 'wav', 'recording', 'Формат записи звонков'),
('recording.max_duration', '300', 'recording', 'Максимальная длительность записи (сек)')
ON CONFLICT (key) DO NOTHING;

-- Создание пользователя-администратора по умолчанию
INSERT INTO users (email, username, full_name, hashed_password, role, is_superuser)
VALUES (
    'admin@gochs.local',
    'admin',
    'Администратор системы',
    -- Пароль: Admin123! (изменить при первом входе)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYjKMdCpTpRi',
    'admin',
    true
) ON CONFLICT (email) DO NOTHING;

-- Создание тестовых тегов
INSERT INTO tags (name, color) VALUES
('Руководство', '#e74c3c'),
('ИТ-отдел', '#3498db'),
('Безопасность', '#f39c12'),
('Производство', '#2ecc71')
ON CONFLICT (name) DO NOTHING;

EOF

    # Выполнение SQL скрипта
    sudo -u postgres psql -d "$POSTGRES_DB" -f /tmp/init_gochs_db.sql
    
    rm /tmp/init_gochs_db.sql
    
    log_info "Структура базы данных создана"
}

create_maintenance_scripts() {
    # Скрипт для вакуума
    cat > "$INSTALL_DIR/scripts/vacuum_db.sh" << 'EOF'
#!/bin/bash
source /opt/gochs-informing/.env
PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -U $POSTGRES_USER -d $POSTGRES_DB -c "VACUUM ANALYZE;"
EOF

    # Скрипт для проверки состояния БД
    cat > "$INSTALL_DIR/scripts/check_db.sh" << 'EOF'
#!/bin/bash
source /opt/gochs-informing/.env
echo "=== Статистика базы данных ==="
PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -U $POSTGRES_USER -d $POSTGRES_DB << SQL
SELECT 
    (SELECT COUNT(*) FROM contacts) as total_contacts,
    (SELECT COUNT(*) FROM campaigns) as total_campaigns,
    (SELECT COUNT(*) FROM call_attempts) as total_calls,
    (SELECT COUNT(*) FROM inbound_calls) as total_inbound,
    pg_size_pretty(pg_database_size('$POSTGRES_DB')) as db_size;
SQL
EOF

    mkdir -p "$INSTALL_DIR/scripts"
    chmod +x "$INSTALL_DIR"/scripts/*.sh
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts"
    
    log_info "Скрипты обслуживания созданы в $INSTALL_DIR/scripts"
}

setup_backup() {
    log_info "Настройка автоматического резервного копирования"
    
    # Создание скрипта резервного копирования
    cat > "$INSTALL_DIR/scripts/backup_db.sh" << EOF
#!/bin/bash
BACKUP_DIR="$INSTALL_DIR/backups/db"
mkdir -p "\$BACKUP_DIR"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/gochs_backup_\$DATE.sql.gz"

PGPASSWORD='$POSTGRES_PASSWORD' pg_dump -h localhost -U $POSTGRES_USER $POSTGRES_DB | gzip > "\$BACKUP_FILE"

# Удаление старых бэкапов (старше 30 дней)
find "\$BACKUP_DIR" -name "gochs_backup_*.sql.gz" -mtime +30 -delete

echo "Backup created: \$BACKUP_FILE"
EOF

    chmod +x "$INSTALL_DIR/scripts/backup_db.sh"
    chown "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts/backup_db.sh"
    
    # Добавление в crontab
    (crontab -l 2>/dev/null; echo "0 2 * * * $INSTALL_DIR/scripts/backup_db.sh >> $INSTALL_DIR/logs/backup.log 2>&1") | crontab -
    
    log_info "Резервное копирование настроено (ежедневно в 2:00)"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    read -p "Удалить базу данных $POSTGRES_DB? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Удаление базы данных
        sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS $POSTGRES_DB;
DROP USER IF EXISTS $POSTGRES_USER;
EOF
        log_info "База данных удалена"
    fi
    
    # Удаление crontab задачи
    crontab -l | grep -v "backup_db.sh" | crontab -
    
    # Удаление скриптов
    rm -rf "$INSTALL_DIR/scripts"/*db*.sh
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка сервиса PostgreSQL
    if systemctl is-active --quiet postgresql; then
        log_info "Сервис PostgreSQL: активен"
    else
        log_error "Сервис PostgreSQL: не активен"
        status=1
    fi
    
    # Проверка подключения к базе данных
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" &>/dev/null; then
        log_info "Подключение к БД: успешно"
        
        # Проверка наличия таблиц
        TABLE_COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        log_info "Количество таблиц: $TABLE_COUNT"
        
        if [[ $TABLE_COUNT -lt 10 ]]; then
            log_warn "Недостаточно таблиц (возможно, структура БД не создана)"
            status=1
        fi
    else
        log_error "Подключение к БД: ошибка"
        status=1
    fi
    
    # Проверка размера БД
    DB_SIZE=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));" | xargs)
    log_info "Размер БД: $DB_SIZE"
    
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
    backup)
        if [[ -f "$INSTALL_DIR/scripts/backup_db.sh" ]]; then
            bash "$INSTALL_DIR/scripts/backup_db.sh"
        else
            log_error "Скрипт резервного копирования не найден"
            exit 1
        fi
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|backup}"
        exit 1
        ;;
esac
