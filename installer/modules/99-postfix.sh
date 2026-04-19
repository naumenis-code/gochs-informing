#!/bin/bash

################################################################################
# Модуль: 99-postfix.sh
# Назначение: Автоматическое исправление типовых ошибок после установки
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
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}\n${BLUE}  $*${NC}\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"; }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() {
        local m="$1"
        local f="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"
        mkdir -p "$(dirname "$f")"
        echo "$m:$(date +%s)" >> "$f"
    }
fi

MODULE_NAME="99-postfix"
MODULE_DESCRIPTION="Автоматическое исправление типовых ошибок после установки"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
    POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-gochs_password}"
    POSTGRES_USER="${POSTGRES_USER:-gochs_user}"
    POSTGRES_DB="${POSTGRES_DB:-gochs}"
    GOCHS_USER="${GOCHS_USER:-gochs}"
    GOCHS_GROUP="${GOCHS_GROUP:-gochs}"
fi

install() {
    log_step "Применение финальных патчей и исправлений"
    
    # 1. Создание директории логов
    log_info "Проверка директории логов..."
    mkdir -p "$INSTALL_DIR/logs"
    if id -u "$GOCHS_USER" &>/dev/null; then
        chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/logs" 2>/dev/null || true
    fi
    chmod 755 "$INSTALL_DIR/logs"
    log_info "✓ Директория логов готова"
    
    # 2. Исправление прав на фронтенд для Nginx
    if [[ -d "$INSTALL_DIR/frontend/build" ]]; then
        log_info "Исправление прав на фронтенд..."
        chown -R www-data:www-data "$INSTALL_DIR/frontend/build" 2>/dev/null || true
        chmod -R 755 "$INSTALL_DIR/frontend/build" 2>/dev/null || true
        log_info "✓ Права на фронтенд исправлены"
    else
        log_warn "Директория фронтенда не найдена, пропускаем"
    fi
    
    # 3. Установка email-validator если не установлен
    if [[ -d "$INSTALL_DIR/venv" ]]; then
        log_info "Проверка email-validator..."
        source "$INSTALL_DIR/venv/bin/activate" 2>/dev/null
        if ! python3 -c "import email_validator" 2>/dev/null; then
            log_info "Установка email-validator..."
            pip install email-validator --quiet 2>/dev/null || true
            log_info "✓ email-validator установлен"
        else
            log_info "✓ email-validator уже установлен"
        fi
        deactivate 2>/dev/null || true
    fi
    
    # 4. Установка bcrypt правильной версии
    if [[ -d "$INSTALL_DIR/venv" ]]; then
        log_info "Проверка bcrypt..."
        source "$INSTALL_DIR/venv/bin/activate" 2>/dev/null
        BC_VERSION=$(pip show bcrypt 2>/dev/null | grep Version | awk '{print $2}')
        if [[ "$BC_VERSION" != "4.0.1" ]]; then
            log_info "Установка bcrypt==4.0.1..."
            pip uninstall bcrypt -y 2>/dev/null || true
            pip install bcrypt==4.0.1 --quiet 2>/dev/null || true
            log_info "✓ bcrypt обновлён до 4.0.1"
        else
            log_info "✓ bcrypt версии 4.0.1"
        fi
        deactivate 2>/dev/null || true
    fi
    
    # 5. Включение pgcrypto в PostgreSQL
    if [[ -n "$POSTGRES_PASSWORD" ]]; then
        log_info "Включение pgcrypto в PostgreSQL..."
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            log_info "✓ pgcrypto включён"
        else
            log_warn "Не удалось включить pgcrypto"
        fi
    fi
    
    # 6. Создание пользователя admin
    if [[ -n "$POSTGRES_PASSWORD" ]]; then
        log_info "Проверка пользователя admin..."
        
        ADMIN_EXISTS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM users WHERE username='admin';" 2>/dev/null | xargs)
        
        if [[ "$ADMIN_EXISTS" == "0" ]] || [[ -z "$ADMIN_EXISTS" ]]; then
            log_info "Создание пользователя admin..."
            PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" << EOF 2>/dev/null
INSERT INTO users (email, username, full_name, hashed_password, role, is_superuser, is_active) 
VALUES ('admin@gochs.local', 'admin', 'Администратор', crypt('Admin123!', gen_salt('bf')), 'admin', TRUE, TRUE);
EOF
            if [[ $? -eq 0 ]]; then
                log_info "✓ Пользователь admin создан (пароль: Admin123!)"
            else
                log_warn "Не удалось создать пользователя admin"
            fi
        else
            log_info "✓ Пользователь admin уже существует"
        fi
    fi
    
    # 7. Исправление gochs-worker.service
    log_info "Проверка gochs-worker.service..."
    if ! systemctl is-active --quiet gochs-worker 2>/dev/null; then
        log_info "Исправление конфигурации gochs-worker.service..."
        cat > /etc/systemd/system/gochs-worker.service << EOF
[Unit]
Description=ГО-ЧС Celery Worker
After=network.target redis-server.service postgresql.service
Wants=redis-server.service postgresql.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload
        log_info "✓ gochs-worker.service исправлен"
    else
        log_info "✓ gochs-worker.service работает"
    fi
    
    # 8. Исправление gochs-api.service (таймаут)
    log_info "Проверка gochs-api.service..."
    if [[ -f /etc/systemd/system/gochs-api.service ]]; then
        if ! grep -q "TimeoutStartSec" /etc/systemd/system/gochs-api.service; then
            sed -i '/\[Service\]/a TimeoutStartSec=60' /etc/systemd/system/gochs-api.service
            systemctl daemon-reload
            log_info "✓ Таймаут gochs-api.service увеличен"
        fi
    fi
    
    # 9. Исправление package.json если есть ошибка JSON
    if [[ -f "$INSTALL_DIR/frontend/package.json" ]]; then
        if grep -q '"prettier": "\^3.1.1"' "$INSTALL_DIR/frontend/package.json" && \
           ! grep -q '"prettier": "\^3.1.1",' "$INSTALL_DIR/frontend/package.json"; then
            log_info "Исправление package.json..."
            sed -i 's/"prettier": "\^3.1.1"/"prettier": "\^3.1.1",/' "$INSTALL_DIR/frontend/package.json"
            log_info "✓ package.json исправлен"
        fi
    fi
    
    # 10. Перезапуск сервисов
    log_info "Перезапуск сервисов..."
    systemctl restart gochs-api 2>/dev/null || true
    systemctl restart gochs-worker 2>/dev/null || true
    systemctl restart gochs-scheduler 2>/dev/null || true
    systemctl restart nginx 2>/dev/null || true
    systemctl restart asterisk 2>/dev/null || true
    
    # 11. Финальная проверка
    log_info "Финальная проверка..."
    sleep 5
    
    local errors=0
    
    echo ""
    log_info "Статус сервисов:"
    for service in postgresql redis-server asterisk gochs-api gochs-worker gochs-scheduler nginx; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            log_info "  ✓ $service"
        else
            log_error "  ✗ $service"
            ((errors++))
        fi
    done
    
    echo ""
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_info "✓ API отвечает: $(curl -s http://localhost:8000/health | head -c 50)"
    else
        log_warn "✗ API не отвечает"
        ((errors++))
    fi
    
    echo ""
    if [[ $errors -eq 0 ]]; then
        log_info "✅ Все системы работают корректно!"
    else
        log_warn "⚠ Обнаружено $errors проблем(ы)"
        log_info "Рекомендуется выполнить: journalctl -u gochs-api -n 20"
    fi
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль $MODULE_NAME успешно установлен"
    
    return 0
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    log_info "Этот модуль не содержит данных для удаления"
    return 0
}

check_status() {
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    local all_ok=true
    
    # Проверка API
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_info "✓ API работает"
    else
        log_warn "✗ API не работает"
        all_ok=false
    fi
    
    # Проверка admin
    if [[ -n "$POSTGRES_PASSWORD" ]]; then
        ADMIN_EXISTS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM users WHERE username='admin';" 2>/dev/null | xargs)
        if [[ "$ADMIN_EXISTS" -gt 0 ]]; then
            log_info "✓ Пользователь admin существует"
        else
            log_warn "✗ Пользователь admin не найден"
            all_ok=false
        fi
    fi
    
    # Проверка прав на фронтенд
    if [[ -d "$INSTALL_DIR/frontend/build" ]]; then
        OWNER=$(stat -c '%U' "$INSTALL_DIR/frontend/build" 2>/dev/null)
        if [[ "$OWNER" == "www-data" ]]; then
            log_info "✓ Права на фронтенд корректны"
        else
            log_warn "✗ Права на фронтенд: $OWNER (ожидается www-data)"
            all_ok=false
        fi
    fi
    
    if $all_ok; then
        return 0
    else
        return 1
    fi
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
    fix)
        # Принудительное исправление (аналог install без отметки об установке)
        install
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|fix}"
        exit 1
        ;;
esac
