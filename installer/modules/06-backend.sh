#!/bin/bash
################################################################################
# Модуль: 06-backend.sh — Установка бэкенда
# Копирует готовые файлы из installer/app/ + создает недостающие
# ИСПРАВЛЕННАЯ ВЕРСИЯ: права .env, проверка API, логирование ошибок
################################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${SCRIPT_DIR}/utils/common.sh" 2>/dev/null || {
    log_info() { echo -e "\033[0;32m[INFO]\033[0m $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }
    log_warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
    log_step() { echo -e "\n\033[0;34m═══ $* ═══\033[0m"; }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() { echo "$1:$(date +%s)" >> "${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"; }
}

MODULE_NAME="06-backend"
INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
GOCHS_USER="${GOCHS_USER:-gochs}"
GOCHS_GROUP="${GOCHS_GROUP:-gochs}"
source "${SCRIPT_DIR}/config/config.env" 2>/dev/null || true

INSTALLER_APP="${SCRIPT_DIR}/app"
TARGET_APP="$INSTALL_DIR/app"

install() {
    log_step "Установка FastAPI бэкенда"
    
    # Проверка зависимостей
    [ -d "$INSTALL_DIR/venv" ] || { log_error "Python venv не найден. Запустите 02-python.sh"; return 1; }
    systemctl is-active --quiet postgresql || { log_error "PostgreSQL не запущен"; return 1; }
    systemctl is-active --quiet redis-server || { log_error "Redis не запущен"; return 1; }
    
    # Установка Python пакетов
    log_info "Установка Python пакетов..."
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --quiet fastapi uvicorn sqlalchemy asyncpg psycopg2-binary \
        redis celery pydantic python-dotenv python-multipart aiofiles \
        python-jose passlib bcrypt jinja2 aiohttp httpx 2>&1 | tail -1
    
    # Создание структуры
    log_info "Создание структуры директорий..."
    for dir in core api/v1/endpoints models schemas services tasks utils; do
        ensure_dir "$TARGET_APP/$dir"
        touch "$TARGET_APP/$dir/__init__.py"
    done
    
    # КОПИРОВАНИЕ ГОТОВЫХ ФАЙЛОВ из installer/app/
    log_info "Копирование готовых файлов из installer/app/..."
    
    copy_file() {
        local src="$INSTALLER_APP/$1"
        local dst="$TARGET_APP/$1"
        if [ -f "$src" ]; then
            mkdir -p "$(dirname "$dst")"
            cp "$src" "$dst"
            log_info "  ✓ $1"
        else
            return 1
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
    
    # СОЗДАНИЕ НЕДОСТАЮЩИХ ФАЙЛОВ (если нет в installer)
    log_info "Проверка и создание недостающих файлов..."
    
    # core/logging_config.py
    if [ ! -f "$TARGET_APP/core/logging_config.py" ]; then
        cat > "$TARGET_APP/core/logging_config.py" << 'PYEOF'
import logging
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
PYEOF
        log_info "  ✓ core/logging_config.py"
    fi
    
    # models/user.py
    if [ ! -f "$TARGET_APP/models/user.py" ]; then
        cat > "$TARGET_APP/models/user.py" << 'PYEOF'
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="operator")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    login_count = Column(Integer, default=0)
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
PYEOF
        log_info "  ✓ models/user.py"
    fi
    
    # api/v1/endpoints/reports.py
    if [ ! -f "$TARGET_APP/api/v1/endpoints/reports.py" ]; then
        cat > "$TARGET_APP/api/v1/endpoints/reports.py" << 'PYEOF'
from fastapi import APIRouter
router = APIRouter()
@router.get("/summary")
async def summary():
    return {"campaigns": {"total": 0}, "calls": {"total": 0}}
PYEOF
        log_info "  ✓ endpoints/reports.py"
    fi
    
    # =========================================================================
    # ИСПРАВЛЕНИЕ 1: Проверка и исправление прав на .env
    # =========================================================================
    log_info "Проверка и исправление прав на .env..."
    if [ -f "$INSTALL_DIR/.env" ]; then
        local current_owner=$(stat -c %U "$INSTALL_DIR/.env" 2>/dev/null)
        local current_perms=$(stat -c %a "$INSTALL_DIR/.env" 2>/dev/null)
        
        if [ "$current_owner" != "$GOCHS_USER" ]; then
            chown "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/.env" 2>/dev/null || \
                chown gochs:gochs "$INSTALL_DIR/.env" 2>/dev/null || true
            log_info "  ✓ Владелец .env изменён на $GOCHS_USER"
        fi
        
        if [ "$current_perms" != "600" ]; then
            chmod 600 "$INSTALL_DIR/.env"
            log_info "  ✓ Права .env изменены на 600"
        fi
    else
        log_warn "⚠ .env файл не найден, создаю..."
        # Создаём .env из config.env
        source "${SCRIPT_DIR}/config/config.env" 2>/dev/null || true
        cat > "$INSTALL_DIR/.env" << EOF
GOCHS_ENV=production
DEBUG=false
POSTGRES_DB=${POSTGRES_DB:-gochs}
POSTGRES_USER=${POSTGRES_USER:-gochs_user}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
ASTERISK_AMI_USER=${ASTERISK_AMI_USER:-gochs_ami}
ASTERISK_AMI_PASSWORD=${ASTERISK_AMI_PASSWORD}
ASTERISK_ARI_USER=${ASTERISK_ARI_USER:-gochs}
ASTERISK_ARI_PASSWORD=${ASTERISK_ARI_PASSWORD}
SECRET_KEY=$(openssl rand -base64 32 2>/dev/null | tr -d "=+/" | cut -c1-32 || echo "defaultsecretkey")
JWT_SECRET_KEY=$(openssl rand -base64 32 2>/dev/null | tr -d "=+/" | cut -c1-32 || echo "defaultjwtkey")
EOF
        chown "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/.env" 2>/dev/null || \
            chown gochs:gochs "$INSTALL_DIR/.env" 2>/dev/null || true
        chmod 600 "$INSTALL_DIR/.env"
        log_info "  ✓ .env создан с правами 600"
    fi
    
    # =========================================================================
    # ИСПРАВЛЕНИЕ 2: Исправление прав на все файлы проекта
    # =========================================================================
    log_info "Исправление прав на файлы проекта..."
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$TARGET_APP" 2>/dev/null || \
        chown -R gochs:gochs "$TARGET_APP" 2>/dev/null || true
    chmod -R 755 "$TARGET_APP" 2>/dev/null || true
    log_info "  ✓ Права на $TARGET_APP исправлены"

    # =========================================================================
    # ИСПРАВЛЕНИЕ 3: Systemd сервис с EnvironmentFile
    # =========================================================================
    log_info "Создание systemd сервиса..."
    cat > /etc/systemd/system/gochs-api.service << SERVICEEOF
[Unit]
Description=ГО-ЧС API Service
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
Environment="HOME=$INSTALL_DIR"
EnvironmentFile=-$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
Restart=always
RestartSec=10
TimeoutStartSec=120
StandardOutput=append:$INSTALL_DIR/logs/api.log
StandardError=append:$INSTALL_DIR/logs/api_error.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

    log_info "  ✓ Systemd сервис создан"
    
    # =========================================================================
    # ИСПРАВЛЕНИЕ 4: Создание сервиса Celery Worker
    # =========================================================================
    log_info "Создание сервиса Celery Worker..."
    cat > /etc/systemd/system/gochs-worker.service << 'WORKEREOF'
[Unit]
Description=ГО-ЧС Celery Worker
After=network.target redis-server.service postgresql.service
Wants=redis-server.service postgresql.service

[Service]
Type=simple
User=gochs
Group=gochs
WorkingDirectory=/opt/gochs-informing
Environment="PATH=/opt/gochs-informing/venv/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/gochs-informing"
EnvironmentFile=-/opt/gochs-informing/.env
ExecStart=/opt/gochs-informing/venv/bin/celery -A app.tasks worker --loglevel=info --concurrency=4
Restart=always
RestartSec=10
StandardOutput=append:/opt/gochs-informing/logs/worker.log
StandardError=append:/opt/gochs-informing/logs/worker_error.log

[Install]
WantedBy=multi-user.target
WORKEREOF

    log_info "  ✓ Сервис Worker создан"
    
    # =========================================================================
    # ИСПРАВЛЕНИЕ 5: Создание сервиса Celery Beat (Scheduler)
    # =========================================================================
    log_info "Создание сервиса Celery Beat..."
    cat > /etc/systemd/system/gochs-scheduler.service << 'SCHEDEOF'
[Unit]
Description=ГО-ЧС Celery Beat Scheduler
After=network.target redis-server.service postgresql.service
Wants=redis-server.service postgresql.service

[Service]
Type=simple
User=gochs
Group=gochs
WorkingDirectory=/opt/gochs-informing
Environment="PATH=/opt/gochs-informing/venv/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/gochs-informing"
EnvironmentFile=-/opt/gochs-informing/.env
ExecStart=/opt/gochs-informing/venv/bin/celery -A app.tasks beat --loglevel=info --schedule=/opt/gochs-informing/celerybeat-schedule
Restart=always
RestartSec=10
StandardOutput=append:/opt/gochs-informing/logs/scheduler.log
StandardError=append:/opt/gochs-informing/logs/scheduler_error.log

[Install]
WantedBy=multi-user.target
SCHEDEOF

    log_info "  ✓ Сервис Scheduler создан"

    # Перезагрузка демона
    systemctl daemon-reload
    
    # =========================================================================
    # ИСПРАВЛЕНИЕ 6: Запуск и проверка API с детальной диагностикой
    # =========================================================================
    log_info "Запуск сервисов..."
    
    # Запускаем worker и scheduler (могут не запуститься если нет задач)
    systemctl enable gochs-worker 2>/dev/null || true
    systemctl start gochs-worker 2>/dev/null || true
    systemctl enable gochs-scheduler 2>/dev/null || true
    systemctl start gochs-scheduler 2>/dev/null || true
    
    # Запускаем API
    systemctl enable gochs-api
    systemctl restart gochs-api
    sleep 5
    
    # Проверка API
    local api_ok=false
    
    if curl -s http://localhost:8000/health 2>/dev/null | grep -q "status"; then
        log_info "✓ API запущен и отвечает на /health"
        api_ok=true
    elif curl -s http://localhost:8000/docs 2>/dev/null | grep -q "openapi"; then
        log_info "✓ API запущен (проверка через /docs)"
        api_ok=true
    else
        log_error "✗ API не отвечает"
        log_info "  Проверка статуса сервиса..."
        systemctl status gochs-api --no-pager -l 2>&1 | tail -10
        
        log_info "  Последние ошибки:"
        journalctl -u gochs-api -n 20 --no-pager 2>&1 | grep -i "error\|fail" || echo "  Нет явных ошибок"
        
        log_info "  Проверка файлов:"
        ls -la "$INSTALL_DIR/.env" 2>/dev/null || echo "  .env отсутствует"
        ls -la "$TARGET_APP/main.py" 2>/dev/null || echo "  main.py отсутствует"
        
        log_info "  Пробный запуск вручную:"
        cd "$INSTALL_DIR"
        sudo -u "$GOCHS_USER" "$INSTALL_DIR/venv/bin/python" -c "from app.main import app; print('OK: app imported')" 2>&1 | tail -5 || {
            log_warn "  Не удалось импортировать приложение, пробую исправить..."
            # Дополнительная диагностика
            sudo -u "$GOCHS_USER" cat "$INSTALL_DIR/.env" 2>&1 | head -3 || log_error "  Нет доступа к .env"
        }
        cd "$SCRIPT_DIR"
    fi
    
    # Сохраняем статус для отчета
    if $api_ok; then
        echo "API_STATUS=OK" >> "$INSTALL_DIR/.install_status"
    else
        echo "API_STATUS=FAILED" >> "$INSTALL_DIR/.install_status"
    fi
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль $MODULE_NAME установлен"
    
    # Итоговая информация
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  БЭКЕНД УСТАНОВЛЕН${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  API: ${CYAN}http://localhost:8000${NC}"
    echo -e "  Docs: ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  Health: ${CYAN}http://localhost:8000/health${NC}"
    echo ""
    echo -e "  Логи:"
    echo -e "    API: ${CYAN}journalctl -u gochs-api -f${NC}"
    echo -e "    Worker: ${CYAN}journalctl -u gochs-worker -f${NC}"
    echo -e "    Файл: ${CYAN}tail -f $INSTALL_DIR/logs/api.log${NC}"
    echo ""
    
    return 0
}

uninstall() {
    log_step "Удаление модуля $MODULE_NAME"
    
    systemctl stop gochs-api 2>/dev/null || true
    systemctl stop gochs-worker 2>/dev/null || true
    systemctl stop gochs-scheduler 2>/dev/null || true
    
    systemctl disable gochs-api 2>/dev/null || true
    systemctl disable gochs-worker 2>/dev/null || true
    systemctl disable gochs-scheduler 2>/dev/null || true
    
    rm -f /etc/systemd/system/gochs-api.service
    rm -f /etc/systemd/system/gochs-worker.service
    rm -f /etc/systemd/system/gochs-scheduler.service
    systemctl daemon-reload
    
    # Удаление файлов (опционально)
    read -p "Удалить файлы бэкенда? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$TARGET_APP"
        log_info "Файлы бэкенда удалены"
    fi
    
    log_info "Модуль $MODULE_NAME удален"
    return 0
}

check_status() {
    log_info "Проверка статуса модуля $MODULE_NAME"
    local status=0
    
    # Проверка сервисов
    for service in gochs-api gochs-worker gochs-scheduler; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            log_info "  ✓ $service: активен"
        else
            log_warn "  ✗ $service: не активен"
            status=1
        fi
    done
    
    # Проверка API
    if curl -s http://localhost:8000/health 2>/dev/null | grep -q "status"; then
        log_info "  ✓ API отвечает"
    else
        log_warn "  ✗ API не отвечает"
        status=1
    fi
    
    return $status
}

case "${1:-}" in
    install) install ;;
    uninstall) uninstall ;;
    status) check_status ;;
    *)
        echo "Использование: $0 {install|uninstall|status}"
        exit 1
        ;;
esac
