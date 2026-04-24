#!/bin/bash

################################################################################
# Модуль: 10-users-contacts-groups-playbooks.sh
# Назначение: Установка страниц Пользователей, Контактов, Групп и Плейбуков
# Версия: 1.0.0
################################################################################

# Определение путей
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Загрузка общих функций
if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

# Если common.sh не найден - определяем функции локально
if ! type log_info &>/dev/null; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    NC='\033[0m'
    
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { 
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}  $*${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() {
        local module="$1"
        local state_file="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"
        mkdir -p "$(dirname "$state_file")"
        echo "$module:$(date +%s)" >> "$state_file"
    }
    backup_file() {
        local file="$1"
        if [[ -f "$file" ]]; then
            cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
            log_info "Создана резервная копия: $file"
        fi
    }
    wait_for_service() {
        local service="$1"
        local max_wait="${2:-30}"
        local count=0
        while ! systemctl is-active --quiet "$service" 2>/dev/null; do
            sleep 1
            ((count++))
            [[ $count -ge $max_wait ]] && return 1
        done
        return 0
    }
fi

MODULE_NAME="10-users-contacts-groups-playbooks"
MODULE_DESCRIPTION="Пользователи, Контакты, Группы и Плейбуки"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Fallback: загрузка из .env
if [[ -z "$POSTGRES_PASSWORD" ]] && [[ -f "$INSTALL_DIR/.env" ]]; then
    source "$INSTALL_DIR/.env"
fi

# Fallback: парсинг из credentials
if [[ -z "$POSTGRES_PASSWORD" ]] && [[ -f "/root/.gochs_credentials" ]]; then
    POSTGRES_PASSWORD=$(grep -A 2 "БАЗА ДАННЫХ POSTGRESQL:" /root/.gochs_credentials | grep -oP 'Пароль: \K.*')
    REDIS_PASSWORD=$(grep -A 2 "REDIS:" /root/.gochs_credentials | grep -oP 'Пароль: \K.*')
fi

INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
POSTGRES_DB="${POSTGRES_DB:-gochs}"
POSTGRES_USER="${POSTGRES_USER:-gochs_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
GOCHS_USER="${GOCHS_USER:-gochs}"
GOCHS_GROUP="${GOCHS_GROUP:-gochs}"

# Пути к исходным файлам в installer
INSTALLER_DIR="${SCRIPT_DIR}"
INSTALLER_APP_SRC="${INSTALLER_DIR}/app"
INSTALLER_FRONTEND_SRC="${INSTALLER_DIR}/frontend/src"

# Пути к целевым файлам в /opt/gochs-informing
TARGET_APP="${INSTALL_DIR}/app"
TARGET_FRONTEND="${INSTALL_DIR}/frontend/src"

install() {
    log_step "Установка модуля ${MODULE_NAME}"
    
    # Проверка наличия исходных файлов
    check_source_files
    
    # 1. Копирование файлов бэкенда (модели, схемы, сервисы, эндпоинты)
    install_backend_files
    
    # 2. Копирование файлов фронтенда (страницы, сервисы, компоненты)
    install_frontend_files
    
    # 3. Обновление __init__.py файлов
    update_init_files
    
    # 4. Создание таблиц в базе данных
    create_database_tables
    
    # 5. Установка прав
    fix_permissions
    
    # 6. Пересборка фронтенда
    rebuild_frontend
    
    # 7. Перезапуск сервисов
    restart_services
    
    # 8. Отмечаем модуль как установленный
    mark_module_installed "$MODULE_NAME"
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Доступны новые разделы в веб-интерфейсе:"
    log_info "  - Пользователи: /users"
    log_info "  - Контакты: /contacts"
    log_info "  - Группы: /groups"
    log_info "  - Плейбуки: /playbooks"
    
    return 0
}

check_source_files() {
    log_info "Проверка наличия исходных файлов в installer..."
    
    local missing_files=()
    local optional_files=()
    
    # Бэкенд файлы (обязательные)
    declare -a backend_files=(
        "app/models/contact.py"
        "app/models/tag.py"
        "app/models/contact_tag.py"
        "app/models/contact_group.py"
        "app/models/contact_group_member.py"
        "app/models/playbook.py"
        "app/schemas/common.py"
        "app/schemas/user.py"
        "app/schemas/contact.py"
        "app/schemas/group.py"
        "app/schemas/playbook.py"
        "app/services/user_service.py"
        "app/services/contact_service.py"
        "app/services/group_service.py"
        "app/services/playbook_service.py"
        "app/api/v1/endpoints/users.py"
        "app/api/v1/endpoints/contacts.py"
        "app/api/v1/endpoints/groups.py"
        "app/api/v1/endpoints/playbooks.py"
    )
    
    # Фронтенд файлы (обязательные)
    declare -a frontend_files=(
        "frontend/src/pages/Users.tsx"
        "frontend/src/pages/Contacts.tsx"
        "frontend/src/pages/Groups.tsx"
        "frontend/src/pages/Playbooks.tsx"
        "frontend/src/services/userService.ts"
        "frontend/src/services/contactService.ts"
        "frontend/src/services/groupService.ts"
        "frontend/src/services/playbookService.ts"
        "frontend/src/components/Common/AudioPlayer.tsx"
        "frontend/src/components/Common/ImportModal.tsx"
    )
    
    for file in "${backend_files[@]}"; do
        if [[ ! -f "${INSTALLER_DIR}/${file}" ]]; then
            missing_files+=("${file}")
        fi
    done
    
    for file in "${frontend_files[@]}"; do
        if [[ ! -f "${INSTALLER_DIR}/${file}" ]]; then
            missing_files+=("${file}")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "Отсутствуют следующие обязательные файлы:"
        for file in "${missing_files[@]}"; do
            log_error "  ✗ $file"
        done
        log_error "Установка прервана. Убедитесь, что все файлы модуля находятся в installer/"
        exit 1
    fi
    
    log_info "✓ Все обязательные файлы найдены (${#backend_files[@]} backend + ${#frontend_files[@]} frontend)"
}

install_backend_files() {
    log_step "Установка файлов бэкенда"
    
    # Создание целевых директорий
    ensure_dir "$TARGET_APP/models"
    ensure_dir "$TARGET_APP/schemas"
    ensure_dir "$TARGET_APP/services"
    ensure_dir "$TARGET_APP/services/asterisk"
    ensure_dir "$TARGET_APP/services/dialer"
    ensure_dir "$TARGET_APP/services/inbound"
    ensure_dir "$TARGET_APP/services/tts"
    ensure_dir "$TARGET_APP/services/stt"
    ensure_dir "$TARGET_APP/services/reports"
    ensure_dir "$TARGET_APP/services/security"
    ensure_dir "$TARGET_APP/api/v1/endpoints"
    
    # Список файлов для копирования
    declare -A files_to_copy=(
        # Модели
        ["app/models/contact.py"]="$TARGET_APP/models/contact.py"
        ["app/models/tag.py"]="$TARGET_APP/models/tag.py"
        ["app/models/contact_tag.py"]="$TARGET_APP/models/contact_tag.py"
        ["app/models/contact_group.py"]="$TARGET_APP/models/contact_group.py"
        ["app/models/contact_group_member.py"]="$TARGET_APP/models/contact_group_member.py"
        ["app/models/playbook.py"]="$TARGET_APP/models/playbook.py"
        # Схемы
        ["app/schemas/common.py"]="$TARGET_APP/schemas/common.py"
        ["app/schemas/user.py"]="$TARGET_APP/schemas/user.py"
        ["app/schemas/contact.py"]="$TARGET_APP/schemas/contact.py"
        ["app/schemas/group.py"]="$TARGET_APP/schemas/group.py"
        ["app/schemas/playbook.py"]="$TARGET_APP/schemas/playbook.py"
        # Сервисы
        ["app/services/user_service.py"]="$TARGET_APP/services/user_service.py"
        ["app/services/contact_service.py"]="$TARGET_APP/services/contact_service.py"
        ["app/services/group_service.py"]="$TARGET_APP/services/group_service.py"
        ["app/services/playbook_service.py"]="$TARGET_APP/services/playbook_service.py"
        # Эндпоинты
        ["app/api/v1/endpoints/users.py"]="$TARGET_APP/api/v1/endpoints/users.py"
        ["app/api/v1/endpoints/contacts.py"]="$TARGET_APP/api/v1/endpoints/contacts.py"
        ["app/api/v1/endpoints/groups.py"]="$TARGET_APP/api/v1/endpoints/groups.py"
        ["app/api/v1/endpoints/playbooks.py"]="$TARGET_APP/api/v1/endpoints/playbooks.py"
    )
    
    local copied=0
    local skipped=0
    
    for src_rel in "${!files_to_copy[@]}"; do
        local src="${INSTALLER_DIR}/${src_rel}"
        local dst="${files_to_copy[$src_rel]}"
        
        if [[ -f "$src" ]]; then
            backup_file "$dst"
            cp "$src" "$dst"
            log_info "  ✓ $(basename "$dst")"
            ((copied++))
        else
            log_warn "  ✗ Исходный файл не найден: $src_rel"
            ((skipped++))
        fi
    done
    
    # Создание __init__.py файлов где нужно
    touch "$TARGET_APP/api/v1/endpoints/__init__.py"
    touch "$TARGET_APP/services/__init__.py"
    
    log_info "Скопировано файлов бэкенда: $copied (пропущено: $skipped)"
}

install_frontend_files() {
    log_step "Установка файлов фронтенда"
    
    # Создание целевых директорий
    ensure_dir "$TARGET_FRONTEND/pages"
    ensure_dir "$TARGET_FRONTEND/services"
    ensure_dir "$TARGET_FRONTEND/components/Common"
    
    # Список файлов для копирования
    declare -A files_to_copy=(
        # Страницы
        ["frontend/src/pages/Users.tsx"]="$TARGET_FRONTEND/pages/Users.tsx"
        ["frontend/src/pages/Contacts.tsx"]="$TARGET_FRONTEND/pages/Contacts.tsx"
        ["frontend/src/pages/Groups.tsx"]="$TARGET_FRONTEND/pages/Groups.tsx"
        ["frontend/src/pages/Playbooks.tsx"]="$TARGET_FRONTEND/pages/Playbooks.tsx"
        # Сервисы
        ["frontend/src/services/userService.ts"]="$TARGET_FRONTEND/services/userService.ts"
        ["frontend/src/services/contactService.ts"]="$TARGET_FRONTEND/services/contactService.ts"
        ["frontend/src/services/groupService.ts"]="$TARGET_FRONTEND/services/groupService.ts"
        ["frontend/src/services/playbookService.ts"]="$TARGET_FRONTEND/services/playbookService.ts"
        # Компоненты
        ["frontend/src/components/Common/AudioPlayer.tsx"]="$TARGET_FRONTEND/components/Common/AudioPlayer.tsx"
        ["frontend/src/components/Common/ImportModal.tsx"]="$TARGET_FRONTEND/components/Common/ImportModal.tsx"
    )
    
    local copied=0
    local skipped=0
    
    for src_rel in "${!files_to_copy[@]}"; do
        local src="${INSTALLER_DIR}/${src_rel}"
        local dst="${files_to_copy[$src_rel]}"
        
        if [[ -f "$src" ]]; then
            backup_file "$dst"
            cp "$src" "$dst"
            log_info "  ✓ $(basename "$dst")"
            ((copied++))
        else
            log_warn "  ✗ Исходный файл не найден: $src_rel"
            ((skipped++))
        fi
    done
    
    log_info "Скопировано файлов фронтенда: $copied (пропущено: $skipped)"
}

update_init_files() {
    log_step "Обновление __init__.py файлов"
    
    # Обновление models/__init__.py
    local models_init="$TARGET_APP/models/__init__.py"
    if [[ -f "$models_init" ]]; then
        backup_file "$models_init"
        
        # Добавляем новые модели если их еще нет
        if ! grep -q "from app.models.contact import Contact" "$models_init" 2>/dev/null; then
            log_info "Обновление models/__init__.py..."
            
            # Создаем новый файл с импортами
            cat > "$models_init" << 'PYEOF'
#!/usr/bin/env python3
"""Models module - импорт всех моделей"""

# Пользователи
try:
    from app.models.user import User
except ImportError:
    User = None

# Контакты
try:
    from app.models.contact import Contact
except ImportError:
    Contact = None

# Теги
try:
    from app.models.tag import Tag
except ImportError:
    Tag = None

# Связка контакт-тег
try:
    from app.models.contact_tag import ContactTag
except ImportError:
    ContactTag = None

# Группы контактов
try:
    from app.models.contact_group import ContactGroup
except ImportError:
    ContactGroup = None

# Связка контакт-группа
try:
    from app.models.contact_group_member import ContactGroupMember
except ImportError:
    ContactGroupMember = None

# Кампании
try:
    from app.models.campaign import Campaign
except ImportError:
    Campaign = None

# Плейбуки
try:
    from app.models.playbook import Playbook
except ImportError:
    Playbook = None

# Аудит
try:
    from app.models.audit_log import AuditLog
except ImportError:
    AuditLog = None

__all__ = [
    "User", "Contact", "Tag", "ContactTag",
    "ContactGroup", "ContactGroupMember",
    "Campaign", "Playbook", "AuditLog"
]

__all__ = [name for name in __all__ if globals().get(name) is not None]
PYEOF
        fi
    fi
    
    # Обновление api/v1/__init__.py (роутер)
    local api_init="$TARGET_APP/api/v1/__init__.py"
    if [[ -f "$api_init" ]]; then
        backup_file "$api_init"
        
        # Проверяем наличие новых модулей
        if ! grep -q "from app.api.v1.endpoints import users" "$api_init" 2>/dev/null; then
            log_info "Обновление api/v1/__init__.py (добавление новых роутеров)..."
            
            # Копируем обновленный роутер из installer
            if [[ -f "${INSTALLER_DIR}/app/api/v1/__init__.py" ]]; then
                cp "${INSTALLER_DIR}/app/api/v1/__init__.py" "$api_init"
                log_info "  ✓ Роутер v1 обновлен из installer"
            else
                log_warn "  ✗ Обновленный роутер не найден в installer, пропускаем"
            fi
        fi
    fi
    
    log_info "✓ __init__.py файлы обновлены"
}

create_database_tables() {
    log_step "Создание таблиц в базе данных"
    
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        log_warn "Пароль PostgreSQL не найден, пробуем получить..."
        POSTGRES_PASSWORD=$(grep -oP 'POSTGRES_PASSWORD=\K.*' "$INSTALL_DIR/.env" 2>/dev/null || echo "")
        
        if [[ -z "$POSTGRES_PASSWORD" ]]; then
            POSTGRES_PASSWORD=$(grep -A 2 "БАЗА ДАННЫХ POSTGRESQL:" /root/.gochs_credentials 2>/dev/null | grep -oP 'Пароль: \K.*')
        fi
    fi
    
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        log_error "Не удалось получить пароль PostgreSQL"
        log_warn "Пропуск создания таблиц. Таблицы будут созданы при запуске API."
        return 0
    fi
    
    log_info "Создание таблиц для новых моделей..."
    
    # SQL для создания таблиц
    cat > /tmp/create_module_tables.sql << 'SQLEOF'
-- Таблица тегов
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7) DEFAULT '#95a5a6',
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для тегов
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_is_active ON tags(is_active);

-- Системные теги
INSERT INTO tags (name, color, description, is_system) VALUES
    ('VIP', '#e74c3c', 'Руководители и ключевые сотрудники', TRUE),
    ('Дежурный', '#e67e22', 'Дежурная смена', TRUE),
    ('Оповещение', '#f1c40f', 'Обязательные для оповещения', TRUE),
    ('Удаленный', '#3498db', 'Работает удаленно', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Таблица связи контакт-тег
CREATE TABLE IF NOT EXISTS contact_tags (
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    added_by UUID REFERENCES users(id) ON DELETE SET NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason VARCHAR(255),
    PRIMARY KEY (contact_id, tag_id)
);

-- Индексы для contact_tags
CREATE INDEX IF NOT EXISTS idx_contact_tags_contact_id ON contact_tags(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_tags_tag_id ON contact_tags(tag_id);

-- Таблица групп контактов
CREATE TABLE IF NOT EXISTS contact_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3498db',
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    member_count INTEGER DEFAULT 0,
    total_member_count INTEGER DEFAULT 0,
    default_priority INTEGER DEFAULT 5,
    max_retries INTEGER DEFAULT 3,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для групп
CREATE INDEX IF NOT EXISTS idx_contact_groups_name ON contact_groups(name);
CREATE INDEX IF NOT EXISTS idx_contact_groups_is_active ON contact_groups(is_active);

-- Системные группы
INSERT INTO contact_groups (name, description, color, is_system, default_priority) VALUES
    ('Все сотрудники', 'Все активные сотрудники предприятия', '#3498db', TRUE, 5),
    ('Руководство', 'Руководители и топ-менеджмент', '#e74c3c', TRUE, 1),
    ('Дежурная смена', 'Текущая дежурная смена', '#e67e22', TRUE, 2)
ON CONFLICT (name) DO NOTHING;

-- Таблица связи контакт-группа
CREATE TABLE IF NOT EXISTS contact_group_members (
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    group_id UUID REFERENCES contact_groups(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR(50),
    priority INTEGER DEFAULT 5,
    added_by UUID REFERENCES users(id) ON DELETE SET NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    removed_at TIMESTAMP WITH TIME ZONE,
    removed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reason TEXT,
    note TEXT,
    PRIMARY KEY (contact_id, group_id)
);

-- Индексы для contact_group_members
CREATE INDEX IF NOT EXISTS idx_cgm_contact_id ON contact_group_members(contact_id);
CREATE INDEX IF NOT EXISTS idx_cgm_group_id ON contact_group_members(group_id);

-- Таблица плейбуков
CREATE TABLE IF NOT EXISTS playbooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    greeting_text TEXT,
    greeting_audio_path VARCHAR(500),
    greeting_source VARCHAR(20) DEFAULT 'tts',
    post_beep_text TEXT,
    post_beep_audio_path VARCHAR(500),
    closing_text TEXT,
    closing_audio_path VARCHAR(500),
    beep_duration FLOAT DEFAULT 1.0,
    pause_before_beep FLOAT DEFAULT 0.5,
    max_recording_duration INTEGER DEFAULT 300,
    min_recording_duration INTEGER DEFAULT 3,
    greeting_repeat INTEGER DEFAULT 1,
    repeat_interval FLOAT DEFAULT 0.0,
    language VARCHAR(10) DEFAULT 'ru',
    tts_voice VARCHAR(50),
    tts_speed FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    is_template BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для плейбуков
CREATE INDEX IF NOT EXISTS idx_playbooks_name ON playbooks(name);
CREATE INDEX IF NOT EXISTS idx_playbooks_is_active ON playbooks(is_active);
CREATE INDEX IF NOT EXISTS idx_playbooks_category ON playbooks(category);
SQLEOF

    # Выполнение SQL
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/create_module_tables.sql 2>/dev/null; then
        log_info "✓ Таблицы созданы успешно"
    else
        log_warn "⚠ Ошибка создания таблиц. Возможно, они уже существуют."
    fi
    
    # Настройка прав
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;" 2>/dev/null; then
        log_info "✓ Права на таблицы настроены"
    fi
    
    rm -f /tmp/create_module_tables.sql
}

fix_permissions() {
    log_step "Настройка прав доступа"
    
    # Права на директории бэкенда
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$TARGET_APP" 2>/dev/null || true
    chmod -R 755 "$TARGET_APP" 2>/dev/null || true
    
    # Права на директории фронтенда
    if [[ -d "$INSTALL_DIR/frontend" ]]; then
        chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/frontend/src" 2>/dev/null || true
    fi
    
    # Права на директории для аудиофайлов
    ensure_dir "$INSTALL_DIR/playbooks"
    ensure_dir "$INSTALL_DIR/generated_voice"
    ensure_dir "$INSTALL_DIR/recordings"
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/playbooks" 2>/dev/null || true
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/generated_voice" 2>/dev/null || true
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/recordings" 2>/dev/null || true
    
    log_info "✓ Права доступа настроены"
}

rebuild_frontend() {
    log_step "Пересборка фронтенда"
    
    if [[ ! -d "$INSTALL_DIR/frontend" ]]; then
        log_warn "Директория фронтенда не найдена, пропуск сборки"
        return 0
    fi
    
    cd "$INSTALL_DIR/frontend"
    
    # Проверка наличия node_modules
    if [[ ! -d "node_modules" ]]; then
        log_info "Установка зависимостей npm..."
        npm install --legacy-peer-deps 2>&1 | tail -5 || {
            log_warn "⚠ Ошибка установки зависимостей"
        }
    fi
    
    # Сборка
    log_info "Запуск сборки React..."
    if npm run build 2>&1 | tail -10; then
        log_info "✓ Фронтенд успешно пересобран"
        
        # Права для nginx
        if [[ -d "build" ]]; then
            chown -R www-data:www-data "$INSTALL_DIR/frontend/build" 2>/dev/null || true
        elif [[ -d "dist" ]]; then
            chown -R www-data:www-data "$INSTALL_DIR/frontend/dist" 2>/dev/null || true
        fi
    else
        log_warn "⚠ Сборка фронтенда завершилась с ошибками"
        log_info "Попробуйте пересобрать вручную:"
        log_info "  cd $INSTALL_DIR/frontend && npm run build"
    fi
    
    cd "$SCRIPT_DIR"
}

restart_services() {
    log_step "Перезапуск сервисов"
    
    # Перезапуск API
    if systemctl is-active --quiet gochs-api.service 2>/dev/null; then
        systemctl restart gochs-api.service
        log_info "✓ gochs-api перезапущен"
    fi
    
    # Перезапуск Worker
    if systemctl is-active --quiet gochs-worker.service 2>/dev/null; then
        systemctl restart gochs-worker.service
        log_info "✓ gochs-worker перезапущен"
    fi
    
    # Перезагрузка Nginx
    if systemctl is-active --quiet nginx 2>/dev/null; then
        systemctl reload nginx 2>/dev/null || systemctl restart nginx
        log_info "✓ nginx перезагружен"
    fi
    
    # Даем время на запуск
    sleep 3
    
    # Проверка статуса
    log_info "Статус сервисов:"
    for service in gochs-api gochs-worker nginx; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            log_info "  ✓ $service"
        else
            log_warn "  ✗ $service"
        fi
    done
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    log_warn "Удаление страниц Пользователей, Контактов, Групп и Плейбуков..."
    
    # Удаление файлов фронтенда
    rm -f "$TARGET_FRONTEND/pages/Users.tsx" 2>/dev/null
    rm -f "$TARGET_FRONTEND/pages/Contacts.tsx" 2>/dev/null
    rm -f "$TARGET_FRONTEND/pages/Groups.tsx" 2>/dev/null
    rm -f "$TARGET_FRONTEND/pages/Playbooks.tsx" 2>/dev/null
    rm -f "$TARGET_FRONTEND/services/userService.ts" 2>/dev/null
    rm -f "$TARGET_FRONTEND/services/contactService.ts" 2>/dev/null
    rm -f "$TARGET_FRONTEND/services/groupService.ts" 2>/dev/null
    rm -f "$TARGET_FRONTEND/services/playbookService.ts" 2>/dev/null
    rm -f "$TARGET_FRONTEND/components/Common/AudioPlayer.tsx" 2>/dev/null
    rm -f "$TARGET_FRONTEND/components/Common/ImportModal.tsx" 2>/dev/null
    
    # Удаление файлов бэкенда
    rm -f "$TARGET_APP/models/contact.py" 2>/dev/null
    rm -f "$TARGET_APP/models/tag.py" 2>/dev/null
    rm -f "$TARGET_APP/models/contact_tag.py" 2>/dev/null
    rm -f "$TARGET_APP/models/contact_group.py" 2>/dev/null
    rm -f "$TARGET_APP/models/contact_group_member.py" 2>/dev/null
    rm -f "$TARGET_APP/models/playbook.py" 2>/dev/null
    rm -f "$TARGET_APP/schemas/common.py" 2>/dev/null
    rm -f "$TARGET_APP/schemas/user.py" 2>/dev/null
    rm -f "$TARGET_APP/schemas/contact.py" 2>/dev/null
    rm -f "$TARGET_APP/schemas/group.py" 2>/dev/null
    rm -f "$TARGET_APP/schemas/playbook.py" 2>/dev/null
    rm -f "$TARGET_APP/services/user_service.py" 2>/dev/null
    rm -f "$TARGET_APP/services/contact_service.py" 2>/dev/null
    rm -f "$TARGET_APP/services/group_service.py" 2>/dev/null
    rm -f "$TARGET_APP/services/playbook_service.py" 2>/dev/null
    rm -f "$TARGET_APP/api/v1/endpoints/users.py" 2>/dev/null
    rm -f "$TARGET_APP/api/v1/endpoints/contacts.py" 2>/dev/null
    rm -f "$TARGET_APP/api/v1/endpoints/groups.py" 2>/dev/null
    rm -f "$TARGET_APP/api/v1/endpoints/playbooks.py" 2>/dev/null
    
    log_info "Файлы модуля удалены"
    
    # Восстановление роутеров из бэкапа
    local api_init="$TARGET_APP/api/v1/__init__.py"
    local latest_backup=$(ls -t "${api_init}.backup."* 2>/dev/null | head -1)
    if [[ -n "$latest_backup" ]]; then
        cp "$latest_backup" "$api_init"
        log_info "Восстановлен оригинальный api/v1/__init__.py"
    fi
    
    local models_init="$TARGET_APP/models/__init__.py"
    local models_backup=$(ls -t "${models_init}.backup."* 2>/dev/null | head -1)
    if [[ -n "$models_backup" ]]; then
        cp "$models_backup" "$models_init"
        log_info "Восстановлен оригинальный models/__init__.py"
    fi
    
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка файлов фронтенда
    local frontend_files=(
        "$TARGET_FRONTEND/pages/Users.tsx"
        "$TARGET_FRONTEND/pages/Contacts.tsx"
        "$TARGET_FRONTEND/pages/Groups.tsx"
        "$TARGET_FRONTEND/pages/Playbooks.tsx"
        "$TARGET_FRONTEND/services/userService.ts"
        "$TARGET_FRONTEND/services/contactService.ts"
        "$TARGET_FRONTEND/services/groupService.ts"
        "$TARGET_FRONTEND/services/playbookService.ts"
        "$TARGET_FRONTEND/components/Common/AudioPlayer.tsx"
        "$TARGET_FRONTEND/components/Common/ImportModal.tsx"
    )
    
    log_info "Файлы фронтенда:"
    for file in "${frontend_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_info "  ✓ $(basename "$file")"
        else
            log_warn "  ✗ $(basename "$file")"
            status=1
        fi
    done
    
    # Проверка файлов бэкенда
    local backend_files=(
        "$TARGET_APP/models/contact.py"
        "$TARGET_APP/models/tag.py"
        "$TARGET_APP/models/contact_tag.py"
        "$TARGET_APP/models/contact_group.py"
        "$TARGET_APP/models/contact_group_member.py"
        "$TARGET_APP/models/playbook.py"
        "$TARGET_APP/schemas/common.py"
        "$TARGET_APP/schemas/user.py"
        "$TARGET_APP/schemas/contact.py"
        "$TARGET_APP/schemas/group.py"
        "$TARGET_APP/schemas/playbook.py"
        "$TARGET_APP/services/user_service.py"
        "$TARGET_APP/services/contact_service.py"
        "$TARGET_APP/services/group_service.py"
        "$TARGET_APP/services/playbook_service.py"
        "$TARGET_APP/api/v1/endpoints/users.py"
        "$TARGET_APP/api/v1/endpoints/contacts.py"
        "$TARGET_APP/api/v1/endpoints/groups.py"
        "$TARGET_APP/api/v1/endpoints/playbooks.py"
    )
    
    log_info "Файлы бэкенда:"
    for file in "${backend_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_info "  ✓ $(basename "$file")"
        else
            log_warn "  ✗ $(basename "$file")"
            status=1
        fi
    done
    
    # Проверка API эндпоинтов
    log_info "Проверка API эндпоинтов..."
    if systemctl is-active --quiet gochs-api.service 2>/dev/null; then
        if curl -s http://localhost:8000/docs 2>/dev/null | grep -q "users\|contacts\|groups\|playbooks"; then
            log_info "  ✓ Эндпоинты users, contacts, groups, playbooks доступны"
        else
            log_warn "  (проверьте после перезапуска API)"
        fi
    else
        log_warn "  ✗ API сервис не запущен"
        status=1
    fi
    
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
    rebuild)
        rebuild_frontend
        ;;
    fix-permissions)
        fix_permissions
        ;;
    restart)
        restart_services
        ;;
    create-tables)
        create_database_tables
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|rebuild|fix-permissions|restart|create-tables}"
        echo ""
        echo "  install          - Полная установка модуля"
        echo "  uninstall        - Удаление модуля"
        echo "  status           - Проверка статуса установки"
        echo "  rebuild          - Пересборка фронтенда"
        echo "  fix-permissions  - Исправление прав доступа"
        echo "  restart          - Перезапуск сервисов"
        echo "  create-tables    - Создание таблиц в БД"
        exit 1
        ;;
esac
