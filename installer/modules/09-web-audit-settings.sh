#!/bin/bash

################################################################################
# Модуль: 09-web-audit-settings.sh
# Назначение: Установка страниц Аудита и Настроек, копирование файлов в проект
# Версия: 1.0.2 (полная)
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

MODULE_NAME="09-web-audit-settings"
MODULE_DESCRIPTION="Установка страниц Аудита и Настроек в веб-интерфейс"

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
INSTALLER_DIR="${SCRIPT_DIR}"
POSTGRES_DB="${POSTGRES_DB:-gochs}"
POSTGRES_USER="${POSTGRES_USER:-gochs_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
GOCHS_USER="${GOCHS_USER:-gochs}"
GOCHS_GROUP="${GOCHS_GROUP:-gochs}"

# Пути к исходным файлам в installer
INSTALLER_FRONTEND_SRC="$INSTALLER_DIR/frontend/src"
INSTALLER_APP_SRC="$INSTALLER_DIR/app"

# Пути к целевым файлам в /opt/gochs-informing
TARGET_FRONTEND="$INSTALL_DIR/frontend/src"
TARGET_APP="$INSTALL_DIR/app"

install() {
    log_step "Установка страниц Аудита и Настроек"
    
    # Проверка наличия исходных файлов
    check_source_files
    
    # Копирование файлов фронтенда
    copy_frontend_files
    
    # Копирование файлов бэкенда
    copy_backend_files
    
    # Обновление роутеров для подключения новых эндпоинтов
    update_api_routers
    
    # Создание таблицы аудита в базе данных
    create_audit_table
    
    # Проверка и исправление прав в базе данных
    fix_database_permissions
    
    # Обновление импортов в frontend
    update_frontend_imports
    
    # Пересборка фронтенда
    rebuild_frontend
    
    # Перезапуск сервисов
    restart_services
    
    mark_module_installed "$MODULE_NAME"
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Страницы доступны в веб-интерфейсе:"
    log_info "  - Настройки: /settings"
    log_info "  - Аудит: /audit"
    
    return 0
}

check_source_files() {
    log_info "Проверка наличия исходных файлов в installer..."
    
    local missing_files=()
    
    # Проверка фронтенда
    [[ ! -f "$INSTALLER_FRONTEND_SRC/pages/Settings.tsx" ]] && missing_files+=("frontend/src/pages/Settings.tsx")
    [[ ! -f "$INSTALLER_FRONTEND_SRC/pages/Audit.tsx" ]] && missing_files+=("frontend/src/pages/Audit.tsx")
    [[ ! -f "$INSTALLER_FRONTEND_SRC/services/settingsService.ts" ]] && missing_files+=("frontend/src/services/settingsService.ts")
    [[ ! -f "$INSTALLER_FRONTEND_SRC/services/auditService.ts" ]] && missing_files+=("frontend/src/services/auditService.ts")
    
    # Проверка бэкенда
    [[ ! -f "$INSTALLER_APP_SRC/api/v1/endpoints/settings.py" ]] && missing_files+=("app/api/v1/endpoints/settings.py")
    [[ ! -f "$INSTALLER_APP_SRC/api/v1/endpoints/audit.py" ]] && missing_files+=("app/api/v1/endpoints/audit.py")
    [[ ! -f "$INSTALLER_APP_SRC/schemas/settings.py" ]] && missing_files+=("app/schemas/settings.py")
    [[ ! -f "$INSTALLER_APP_SRC/schemas/audit.py" ]] && missing_files+=("app/schemas/audit.py")
    [[ ! -f "$INSTALLER_APP_SRC/models/audit_log.py" ]] && missing_files+=("app/models/audit_log.py")
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_warn "Отсутствуют следующие файлы в installer:"
        for file in "${missing_files[@]}"; do
            log_warn "  - $file"
        done
        log_info "Будут использованы существующие файлы в системе"
    else
        log_info "✓ Все необходимые файлы найдены"
    fi
}

copy_frontend_files() {
    log_info "Копирование файлов фронтенда..."
    
    # Создание целевых директорий
    ensure_dir "$TARGET_FRONTEND/pages"
    ensure_dir "$TARGET_FRONTEND/services"
    
    # Копирование с бэкапом существующих файлов
    local files=(
        "pages/Settings.tsx"
        "pages/Audit.tsx"
        "services/settingsService.ts"
        "services/auditService.ts"
    )
    
    for file in "${files[@]}"; do
        local src="$INSTALLER_FRONTEND_SRC/$file"
        local dst="$TARGET_FRONTEND/$file"
        
        if [[ -f "$src" ]]; then
            backup_file "$dst"
            cp "$src" "$dst"
            log_info "  ✓ $file"
        else
            log_warn "  ✗ $file не найден в installer, пропускаем"
        fi
    done
    
    # Установка прав
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$TARGET_FRONTEND/pages" 2>/dev/null || true
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$TARGET_FRONTEND/services" 2>/dev/null || true
    
    log_info "Файлы фронтенда скопированы"
}

copy_backend_files() {
    log_info "Копирование файлов бэкенда..."
    
    # Создание целевых директорий
    ensure_dir "$TARGET_APP/api/v1/endpoints"
    ensure_dir "$TARGET_APP/schemas"
    ensure_dir "$TARGET_APP/models"
    
    # Копирование с бэкапом
    local files=(
        "api/v1/endpoints/settings.py"
        "api/v1/endpoints/audit.py"
        "schemas/settings.py"
        "schemas/audit.py"
        "models/audit_log.py"
    )
    
    for file in "${files[@]}"; do
        local src="$INSTALLER_APP_SRC/$file"
        local dst="$TARGET_APP/$file"
        
        if [[ -f "$src" ]]; then
            backup_file "$dst"
            cp "$src" "$dst"
            log_info "  ✓ $file"
        else
            log_warn "  ✗ $file не найден в installer, пропускаем"
        fi
    done
    
    # Создание файлов __init__.py если их нет
    touch "$TARGET_APP/api/v1/endpoints/__init__.py"
    touch "$TARGET_APP/schemas/__init__.py"
    touch "$TARGET_APP/models/__init__.py"
    
    # Установка прав
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$TARGET_APP" 2>/dev/null || true
    
    log_info "Файлы бэкенда скопированы"
}

update_api_routers() {
    log_info "Обновление API роутеров..."
    
    local api_init="$TARGET_APP/api/v1/__init__.py"
    
    if [[ ! -f "$api_init" ]]; then
        log_warn "Файл $api_init не найден, создаем новый..."
        cat > "$api_init" << 'ROUTER_EOF'
#!/usr/bin/env python3
"""API v1 роутер"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, contacts, groups, scenarios, campaigns, inbound, playbooks, settings, monitoring, audit

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(inbound.router, prefix="/inbound", tags=["inbound"])
api_router.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
ROUTER_EOF
    else
        backup_file "$api_init"
        
        # Проверяем, есть ли уже импорт settings и audit
        if ! grep -q "from app.api.v1.endpoints import.*settings" "$api_init"; then
            sed -i 's/from app.api.v1.endpoints import \([^)]*\)/from app.api.v1.endpoints import \1, settings/' "$api_init"
        fi
        
        if ! grep -q "from app.api.v1.endpoints import.*audit" "$api_init"; then
            sed -i 's/from app.api.v1.endpoints import \([^)]*\)/from app.api.v1.endpoints import \1, audit/' "$api_init"
        fi
        
        # Проверяем, есть ли уже include_router для settings
        if ! grep -q 'include_router(settings.router' "$api_init"; then
            if grep -q 'include_router(monitoring.router' "$api_init"; then
                sed -i '/include_router(monitoring.router/a\api_router.include_router(settings.router, prefix="/settings", tags=["settings"])' "$api_init"
            else
                echo 'api_router.include_router(settings.router, prefix="/settings", tags=["settings"])' >> "$api_init"
            fi
        fi
        
        # Проверяем, есть ли уже include_router для audit
        if ! grep -q 'include_router(audit.router' "$api_init"; then
            echo 'api_router.include_router(audit.router, prefix="/audit", tags=["audit"])' >> "$api_init"
        fi
    fi
    
    # Обновляем models/__init__.py
    local models_init="$TARGET_APP/models/__init__.py"
    if [[ -f "$models_init" ]]; then
        if ! grep -q "AuditLog" "$models_init"; then
            echo "from app.models.audit_log import AuditLog" >> "$models_init"
            echo "__all__ = [\"User\", \"Contact\", \"Campaign\", \"AuditLog\"]" >> "$models_init"
        fi
    fi
    
    chown "$GOCHS_USER:$GOCHS_GROUP" "$api_init"
    log_info "✓ API роутеры обновлены"
}

create_audit_table() {
    log_info "Создание таблицы аудита в базе данных..."
    
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        log_warn "Пароль PostgreSQL не найден, пробуем получить из конфигурации..."
        POSTGRES_PASSWORD=$(grep -oP 'POSTGRES_PASSWORD=\K.*' "$INSTALL_DIR/.env" 2>/dev/null || echo "")
    fi
    
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        log_error "Не удалось получить пароль PostgreSQL"
        return 1
    fi
    
    # SQL для создания таблицы аудита
    cat > /tmp/create_audit_table.sql << 'EOF'
-- Таблица аудита действий
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    user_name VARCHAR(255),
    user_role VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(20) DEFAULT 'success',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_status ON audit_logs(status);

-- Комментарии
COMMENT ON TABLE audit_logs IS 'Журнал аудита действий пользователей';
COMMENT ON COLUMN audit_logs.user_id IS 'ID пользователя (если действие от системы - NULL)';
COMMENT ON COLUMN audit_logs.user_name IS 'Имя пользователя для быстрого отображения';
COMMENT ON COLUMN audit_logs.details IS 'JSON с деталями изменений';
EOF

    # Выполнение SQL
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/create_audit_table.sql 2>/dev/null; then
        log_info "✓ Таблица audit_logs создана"
    else
        log_error "Ошибка создания таблицы audit_logs"
        # Пробуем создать через sudo если psql не сработал
        sudo -u postgres psql -d "$POSTGRES_DB" -f /tmp/create_audit_table.sql 2>/dev/null && log_info "✓ Таблица audit_logs создана (через sudo)"
    fi
    
    rm -f /tmp/create_audit_table.sql
}

fix_database_permissions() {
    log_step "Проверка и исправление прав в базе данных"
    
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        POSTGRES_PASSWORD=$(grep -oP 'POSTGRES_PASSWORD=\K.*' "$INSTALL_DIR/.env" 2>/dev/null || echo "")
    fi
    
    log_info "Проверка владельца базы данных..."
    
    # Функция выполнения SQL
    run_sql() {
        if [[ -n "$POSTGRES_PASSWORD" ]]; then
            PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1" 2>/dev/null
        else
            sudo -u postgres psql -d "$POSTGRES_DB" -c "$1" 2>/dev/null
        fi
    }
    
    # Проверка текущего владельца БД
    local current_owner=$(run_sql "SELECT datowner FROM pg_database WHERE datname = '$POSTGRES_DB';" | grep -v "datowner" | grep -v "^-" | grep -v "row" | xargs)
    
    log_info "Текущий владелец БД '$POSTGRES_DB': ${current_owner:-не определен}"
    
    if [[ "$current_owner" != "$POSTGRES_USER" ]]; then
        log_warn "Владелец БД не соответствует $POSTGRES_USER, исправляем..."
        
        if [[ -n "$POSTGRES_PASSWORD" ]]; then
            PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ALTER DATABASE $POSTGRES_DB OWNER TO $POSTGRES_USER;" 2>/dev/null
        else
            sudo -u postgres psql -c "ALTER DATABASE $POSTGRES_DB OWNER TO $POSTGRES_USER;" 2>/dev/null
        fi
        log_info "✓ Владелец БД изменен на $POSTGRES_USER"
    else
        log_info "✓ Владелец БД корректен"
    fi
    
    log_info "Проверка владельца схемы public..."
    
    local schema_owner=$(run_sql "SELECT nspowner::regrole FROM pg_namespace WHERE nspname = 'public';" | grep -v "nspowner" | grep -v "^-" | grep -v "row" | xargs)
    log_info "Текущий владелец схемы public: ${schema_owner:-не определен}"
    
    if [[ "$schema_owner" != "$POSTGRES_USER" ]]; then
        log_warn "Владелец схемы public не соответствует $POSTGRES_USER, исправляем..."
        run_sql "ALTER SCHEMA public OWNER TO $POSTGRES_USER;" 2>/dev/null
        log_info "✓ Владелец схемы public изменен на $POSTGRES_USER"
    else
        log_info "✓ Владелец схемы public корректен"
    fi
    
    log_info "Настройка прав доступа для $POSTGRES_USER..."
    
    # Гранты на все таблицы
    run_sql "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;" 2>/dev/null
    # Гранты на все последовательности
    run_sql "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;" 2>/dev/null
    # Гранты на все функции
    run_sql "GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO $POSTGRES_USER;" 2>/dev/null
    # Дефолтные привилегии
    run_sql "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $POSTGRES_USER;" 2>/dev/null
    run_sql "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $POSTGRES_USER;" 2>/dev/null
    # Права на схему
    run_sql "GRANT ALL ON SCHEMA public TO $POSTGRES_USER;" 2>/dev/null
    
    log_info "✓ Права доступа настроены"
    
    # Проверка прав на таблицу audit_logs
    log_info "Проверка прав на таблицу audit_logs..."
    local has_privileges=$(run_sql "SELECT has_table_privilege('$POSTGRES_USER', 'audit_logs', 'INSERT, SELECT, UPDATE, DELETE');" 2>/dev/null | grep -o '[tf]')
    
    if [[ "$has_privileges" == "t" ]]; then
        log_info "✓ Права на audit_logs корректны"
    else
        log_warn "Исправляем права на audit_logs..."
        run_sql "GRANT ALL PRIVILEGES ON TABLE audit_logs TO $POSTGRES_USER;" 2>/dev/null
        log_info "✓ Права на audit_logs исправлены"
    fi
    
    log_info "Проверка прав завершена"
}

update_frontend_imports() {
    log_info "Обновление импортов в App.tsx..."
    
    local app_tsx="$TARGET_FRONTEND/App.tsx"
    
    if [[ -f "$app_tsx" ]]; then
        backup_file "$app_tsx"
        
        # Проверяем, есть ли уже импорт Settings
        if ! grep -q "import Settings from '@pages/Settings';" "$app_tsx"; then
            sed -i "/import.*from '@pages\/.*';/a import Settings from '@pages/Settings';" "$app_tsx"
        fi
        
        # Проверяем, есть ли уже импорт Audit
        if ! grep -q "import Audit from '@pages/Audit';" "$app_tsx"; then
            sed -i "/import.*from '@pages\/.*';/a import Audit from '@pages/Audit';" "$app_tsx"
        fi
        
        # Проверяем, есть ли уже Route для Settings
        if ! grep -q 'path="settings"' "$app_tsx"; then
            # Находим место для добавления Route
            if grep -q 'path="audit"' "$app_tsx"; then
                sed -i '/path="audit"/i \          <Route path="settings" element={<Settings />} />' "$app_tsx"
            elif grep -q 'path="users"' "$app_tsx"; then
                sed -i '/path="users"/i \          <Route path="settings" element={<Settings />} />' "$app_tsx"
            else
                # Добавляем в конец блока Routes
                sed -i '/<\/Routes>/i \          <Route path="settings" element={<Settings />} />' "$app_tsx"
            fi
        fi
        
        # Проверяем, есть ли уже Route для Audit
        if ! grep -q 'path="audit"' "$app_tsx"; then
            sed -i '/<\/Routes>/i \          <Route path="audit" element={<Audit />} />' "$app_tsx"
        fi
        
        log_info "✓ App.tsx обновлен"
    else
        log_warn "Файл App.tsx не найден, пропускаем обновление импортов"
    fi
    
    # Обновление Layout для добавления пунктов меню
    update_layout_menu
}

update_layout_menu() {
    log_info "Обновление меню в Layout..."
    
    local layout_file="$TARGET_FRONTEND/components/Layout/index.tsx"
    
    if [[ -f "$layout_file" ]]; then
        backup_file "$layout_file"
        
        # Добавляем импорты иконок если нужно
        if ! grep -q "SettingOutlined" "$layout_file"; then
            sed -i "s/import {/import { SettingOutlined, AuditOutlined, /" "$layout_file"
        fi
        
        # Проверяем, есть ли пункт меню "Настройки"
        if ! grep -q "key: '/settings'" "$layout_file"; then
            # Добавляем в adminMenuItems
            sed -i "/const adminMenuItems = \[/a \    { key: '\/settings', icon: <SettingOutlined \/>, label: 'Настройки' }," "$layout_file"
        fi
        
        # Проверяем, есть ли пункт меню "Аудит"
        if ! grep -q "key: '/audit'" "$layout_file"; then
            # Добавляем в adminMenuItems
            sed -i "/const adminMenuItems = \[/a \    { key: '\/audit', icon: <AuditOutlined \/>, label: 'Аудит' }," "$layout_file"
        fi
        
        log_info "✓ Layout меню обновлено"
    else
        log_warn "Файл Layout/index.tsx не найден"
    fi
}

rebuild_frontend() {
    log_info "Пересборка фронтенда..."
    
    if [[ ! -d "$INSTALL_DIR/frontend" ]]; then
        log_warn "Директория фронтенда не найдена"
        return 1
    fi
    
    cd "$INSTALL_DIR/frontend"
    
    # Проверка наличия node_modules
    if [[ ! -d "node_modules" ]]; then
        log_info "Установка зависимостей npm..."
        npm install --legacy-peer-deps 2>&1 | tail -5
    fi
    
    # Сборка
    log_info "Запуск сборки React..."
    if npm run build 2>&1 | tail -10; then
        log_info "✓ Фронтенд успешно пересобран"
        
        # Копирование в nginx
        if [[ -d "build" ]]; then
            chown -R www-data:www-data "$INSTALL_DIR/frontend/build" 2>/dev/null || true
        fi
    else
        log_warn "⚠ Сборка фронтенда завершилась с ошибками"
        log_info "Попробуйте пересобрать вручную: cd $INSTALL_DIR/frontend && npm run build"
    fi
    
    cd "$SCRIPT_DIR"
}

restart_services() {
    log_info "Перезапуск сервисов..."
    
    # Перезапуск API для применения новых эндпоинтов
    if systemctl is-active --quiet gochs-api.service 2>/dev/null; then
        systemctl restart gochs-api.service
        log_info "✓ gochs-api перезапущен"
    fi
    
    # Перезапуск Nginx для применения новых статических файлов
    if systemctl is-active --quiet nginx 2>/dev/null; then
        systemctl reload nginx 2>/dev/null || systemctl restart nginx
        log_info "✓ nginx перезагружен"
    fi
    
    # Даем время на запуск
    sleep 3
    
    # Проверка статуса
    if systemctl is-active --quiet gochs-api.service; then
        log_info "✓ API сервис работает"
    else
        log_warn "✗ API сервис не запущен"
    fi
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    log_warn "Удаление страниц Настройки и Аудита..."
    
    # Удаление файлов фронтенда
    rm -f "$TARGET_FRONTEND/pages/Settings.tsx" 2>/dev/null
    rm -f "$TARGET_FRONTEND/pages/Audit.tsx" 2>/dev/null
    rm -f "$TARGET_FRONTEND/services/settingsService.ts" 2>/dev/null
    rm -f "$TARGET_FRONTEND/services/auditService.ts" 2>/dev/null
    
    # Удаление файлов бэкенда
    rm -f "$TARGET_APP/api/v1/endpoints/settings.py" 2>/dev/null
    rm -f "$TARGET_APP/api/v1/endpoints/audit.py" 2>/dev/null
    rm -f "$TARGET_APP/schemas/settings.py" 2>/dev/null
    rm -f "$TARGET_APP/schemas/audit.py" 2>/dev/null
    rm -f "$TARGET_APP/models/audit_log.py" 2>/dev/null
    
    log_info "Файлы модуля удалены"
    
    # Восстановление роутеров из бэкапа
    local api_init="$TARGET_APP/api/v1/__init__.py"
    local latest_backup=$(ls -t "${api_init}.backup."* 2>/dev/null | head -1)
    if [[ -n "$latest_backup" ]]; then
        cp "$latest_backup" "$api_init"
        log_info "Восстановлен оригинальный api/v1/__init__.py"
    fi
    
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка файлов фронтенда
    local frontend_files=(
        "$TARGET_FRONTEND/pages/Settings.tsx"
        "$TARGET_FRONTEND/pages/Audit.tsx"
        "$TARGET_FRONTEND/services/settingsService.ts"
        "$TARGET_FRONTEND/services/auditService.ts"
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
        "$TARGET_APP/api/v1/endpoints/settings.py"
        "$TARGET_APP/api/v1/endpoints/audit.py"
        "$TARGET_APP/schemas/settings.py"
        "$TARGET_APP/schemas/audit.py"
        "$TARGET_APP/models/audit_log.py"
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
    
    # Проверка таблицы в БД
    log_info "Проверка таблицы audit_logs..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt audit_logs" 2>/dev/null | grep -q "audit_logs"; then
        log_info "  ✓ Таблица audit_logs существует"
    else
        log_warn "  ✗ Таблица audit_logs не найдена"
        status=1
    fi
    
    # Проверка эндпоинтов API
    log_info "Проверка API эндпоинтов..."
    if curl -s http://localhost:8000/docs 2>/dev/null | grep -q "settings\|audit"; then
        log_info "  ✓ Эндпоинты settings/audit доступны"
    else
        log_info "  (проверьте после перезапуска API)"
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
        fix_database_permissions
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|rebuild|fix-permissions}"
        echo ""
        echo "  install         - Установка страниц Аудита и Настроек"
        echo "  uninstall       - Удаление страниц"
        echo "  status          - Проверка статуса установки"
        echo "  rebuild         - Пересборка фронтенда"
        echo "  fix-permissions - Исправление прав в базе данных"
        exit 1
        ;;
esac
