#!/bin/bash

################################################################################
# Общие функции для модулей установки
################################################################################

# Цвета для вывода
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export NC='\033[0m'

# Глобальные переменные
export INSTALL_DIR="/opt/gochs-informing"
export GOCHS_USER="gochs"
export GOCHS_GROUP="gochs"
export LOG_FILE="${INSTALL_DIR}/install.log"
export MODULES_STATE_FILE="${INSTALL_DIR}/.modules_state"

# Инициализация логирования
init_logging() {
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    exec 2> >(tee -a "$LOG_FILE" >&2)
}

# Функции логирования
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $@" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $@" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $@" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}  $@${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
}

# Загрузка конфигурации
load_config() {
    local config_file="${SCRIPT_DIR}/../config/config.env"
    
    if [[ -f "$config_file" ]]; then
        source "$config_file"
        log_info "Конфигурация загружена из $config_file"
    else
        log_warn "Файл конфигурации не найден, используются значения по умолчанию"
        generate_default_config
    fi
}

# Генерация конфигурации по умолчанию
generate_default_config() {
    local config_file="${SCRIPT_DIR}/../config/config.env"
    
    cat > "$config_file" << EOF
# Конфигурация ГО-ЧС Информирование
# Сгенерировано: $(date)

# Сетевые настройки
DOMAIN_OR_IP="${DOMAIN_OR_IP:-localhost}"
HTTP_PORT=80
HTTPS_PORT=443

# База данных
POSTGRES_DB="gochs"
POSTGRES_USER="gochs_user"
POSTGRES_PASSWORD="$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)"

# Redis
REDIS_PASSWORD="$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)"
REDIS_PORT=6379

# Asterisk
ASTERISK_SIP_PORT=5060
ASTERISK_RTP_START=10000
ASTERISK_RTP_END=20000
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USER="gochs_ami"
ASTERISK_AMI_PASSWORD="$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)"

# Email администратора
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@localhost}"

# Пути
INSTALL_DIR="/opt/gochs-informing"
LOG_LEVEL="INFO"
EOF

    source "$config_file"
}

# Управление состоянием модулей
mark_module_installed() {
    local module=$1
    echo "$module:$(date +%s)" >> "$MODULES_STATE_FILE"
}

unmark_module_installed() {
    local module=$1
    sed -i "/^$module:/d" "$MODULES_STATE_FILE"
}

check_module_installed() {
    local module=$1
    grep -q "^$module:" "$MODULES_STATE_FILE" 2>/dev/null
}

# Проверка и ожидание сервиса
wait_for_service() {
    local service=$1
    local max_wait=${2:-30}
    local count=0
    
    while ! systemctl is-active --quiet "$service"; do
        sleep 1
        count=$((count + 1))
        if [[ $count -ge $max_wait ]]; then
            log_error "Сервис $service не запустился за ${max_wait} секунд"
            return 1
        fi
    done
    
    log_info "Сервис $service запущен"
    return 0
}

# Проверка порта
check_port() {
    local port=$1
    if netstat -tuln | grep -q ":$port "; then
        log_warn "Порт $port уже используется"
        return 1
    fi
    return 0
}

# Создание systemd службы
create_systemd_service() {
    local service_name=$1
    local description=$2
    local exec_start=$3
    local user=${4:-$GOCHS_USER}
    local group=${5:-$GOCHS_GROUP}
    
    cat > "/etc/systemd/system/${service_name}.service" << EOF
[Unit]
Description=$description
After=network.target

[Service]
Type=simple
User=$user
Group=$group
WorkingDirectory=$INSTALL_DIR
ExecStart=$exec_start
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/${service_name}.log
StandardError=append:$INSTALL_DIR/logs/${service_name}.error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "Создана служба ${service_name}"
}

# Резервное копирование файла
backup_file() {
    local file=$1
    if [[ -f "$file" ]]; then
        cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Создана резервная копия $file"
    fi
}

# Генерация случайного пароля
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-20
}

# Проверка зависимостей
check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        log_error "Команда '$cmd' не найдена"
        return 1
    fi
    return 0
}

# Проверка версии Python пакета
check_python_package() {
    local package=$1
    local version=${2:-}
    
    if python3 -c "import $package" 2>/dev/null; then
        if [[ -n "$version" ]]; then
            local installed_version=$(python3 -c "import $package; print($package.__version__)" 2>/dev/null)
            if [[ "$installed_version" == "$version" ]]; then
                return 0
            else
                log_warn "Пакет $package версии $installed_version (требуется $version)"
                return 1
            fi
        fi
        return 0
    fi
    return 1
}
