#!/bin/bash
################################################################################
# Модуль: 06-backend.sh (ИСПРАВЛЕННЫЙ - копирует готовые файлы)
################################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${SCRIPT_DIR}/utils/common.sh" 2>/dev/null || {
    log_info() { echo -e "\033[0;32m[INFO]\033[0m $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }
    log_step() { echo -e "\n\033[0;34m═══ $* ═══\033[0m"; }
}

MODULE_NAME="06-backend"
INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
INSTALLER_APP="${SCRIPT_DIR}/app"
TARGET_APP="$INSTALL_DIR/app"

install() {
    log_step "Установка FastAPI бэкенда"
    
    # Проверка
    [ -d "$INSTALL_DIR/venv" ] || { log_error "Python venv не найден"; return 1; }
    
    # Установка пакетов
    log_info "Установка Python пакетов..."
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --quiet fastapi uvicorn sqlalchemy asyncpg psycopg2-binary \
        redis celery pydantic python-dotenv python-multipart aiofiles \
        python-jose passlib bcrypt jinja2 aiohttp httpx 2>&1 | tail -1
    
    # Создание структуры
    log_info "Создание структуры директорий..."
    for dir in core api/v1/endpoints models schemas services tasks utils; do
        mkdir -p "$TARGET_APP/$dir"
    done
    
    # КОПИРОВАНИЕ ГОТОВЫХ ФАЙЛОВ
    log_info "Копирование готовых файлов из installer/app/..."
    
    copy_file() {
        local src="$INSTALLER_APP/$1"
        local dst="$TARGET_APP/$1"
        if [ -f "$src" ]; then
            mkdir -p "$(dirname "$dst")"
            cp "$src" "$dst"
            log_info "  ✓ $1"
        else
            log_info "  ○ $1 (пропущен - нет в installer)"
        fi
    }
    
    # Core
    copy_file "main.py"
    copy_file "core/config.py"
    copy_file "core/database.py"
    copy_file "core/redis_client.py"
    copy_file "core/security.py"
    copy_file "core/logging_config.py"
    copy_file "api/deps.py"
    copy_file "api/v1/__init__.py"
    
    # Endpoints
    for ep in auth users contacts groups campaigns scenarios inbound playbooks settings monitoring audit reports; do
        copy_file "api/v1/endpoints/${ep}.py"
    done
    
    # Models
    for model in user contact contact_group contact_group_member contact_tag tag playbook audit_log; do
        copy_file "models/${model}.py"
    done
    copy_file "models/__init__.py"
    
    # Schemas
    for schema in common contact group playbook settings audit user; do
        copy_file "schemas/${schema}.py"
    done
    copy_file "schemas/__init__.py"
    
    # Services
    for svc in contact_service group_service playbook_service user_service; do
        copy_file "services/${svc}.py"
    done
    
    # Utils
    copy_file "utils/audit_helper.py"
    
    # Права
    chown -R gochs:gochs "$TARGET_APP" 2>/dev/null || true
    
    # Systemd сервис
    log_info "Создание systemd сервиса..."
    cat > /etc/systemd/system/gochs-api.service << SERVICEEOF
[Unit]
Description=ГО-ЧС API Service
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=gochs
Group=gochs
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
Environment="HOME=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
SERVICEEOF

    systemctl daemon-reload
    systemctl enable gochs-api
    systemctl restart gochs-api
    sleep 3
    
    # Проверка
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        log_info "✓ API запущен и отвечает"
    else
        log_error "✗ API не отвечает. Проверьте: journalctl -u gochs-api -n 20"
    fi
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль $MODULE_NAME установлен"
}

uninstall() {
    systemctl stop gochs-api 2>/dev/null
    systemctl disable gochs-api 2>/dev/null
    rm -f /etc/systemd/system/gochs-api.service
    systemctl daemon-reload
    log_info "Модуль $MODULE_NAME удален"
}

case "${1:-}" in
    install) install ;;
    uninstall) uninstall ;;
    *) echo "Использование: $0 {install|uninstall}" ;;
esac
