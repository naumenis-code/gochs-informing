#!/bin/bash

################################################################################
# ГО-ЧС Информирование - Общие функции для модулей установки
# Версия: 1.0.5 (полная исправленная версия)
################################################################################

# Запрет на выполнение напрямую
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Этот скрипт должен подключаться через source, а не выполняться напрямую."
    exit 1
fi

# ============================================================================
# ЦВЕТА ДЛЯ ВЫВОДА
# ============================================================================
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export WHITE='\033[1;37m'
export NC='\033[0m'

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================
export INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
export GOCHS_USER="${GOCHS_USER:-gochs}"
export GOCHS_GROUP="${GOCHS_GROUP:-gochs}"
export LOG_FILE="${LOG_FILE:-${INSTALL_DIR}/install.log}"
export MODULES_STATE_FILE="${INSTALL_DIR}/.modules_state"
export CONFIG_DIR="${SCRIPT_DIR:-/opt/gochs-informing/installer}/config"

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ЛОГИРОВАНИЯ
# ============================================================================

init_logging() {
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    touch "$LOG_FILE" 2>/dev/null || true
}

# ============================================================================
# ФУНКЦИИ ЛОГИРОВАНИЯ
# ============================================================================

log_info() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO]${NC} ${timestamp} - $*" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $*" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR]${NC} ${timestamp} - $*" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}✓${NC} ${timestamp} - $*" | tee -a "$LOG_FILE" 2>/dev/null || echo "✓ $*"
}

log_fail() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}✗${NC} ${timestamp} - $*" | tee -a "$LOG_FILE" 2>/dev/null || echo "✗ $*"
}

log_step() {
    echo "" | tee -a "$LOG_FILE" 2>/dev/null || echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE" 2>/dev/null
    echo -e "${BLUE}  $*${NC}" | tee -a "$LOG_FILE" 2>/dev/null
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE" 2>/dev/null
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo -e "${PURPLE}[DEBUG]${NC} ${timestamp} - $*" | tee -a "$LOG_FILE" 2>/dev/null
    fi
}

# ============================================================================
# ФУНКЦИИ РАБОТЫ С ФАЙЛАМИ И ДИРЕКТОРИЯМИ
# ============================================================================

backup_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        local backup_name="${file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$file" "$backup_name"
        log_info "Создана резервная копия: $backup_name"
        echo "$backup_name"
    else
        log_debug "Файл не существует, резервная копия не создана: $file"
        return 1
    fi
}

restore_backup() {
    local backup_file="$1"
    local original_file="${backup_file%.backup.*}"
    
    if [[ -f "$backup_file" ]]; then
        cp "$backup_file" "$original_file"
        log_info "Восстановлено из резервной копии: $original_file"
        return 0
    else
        log_error "Резервная копия не найдена: $backup_file"
        return 1
    fi
}

ensure_dir() {
    local dir="$1"
    local owner="${2:-root}"
    local perms="${3:-755}"
    
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_info "Создана директория: $dir"
    fi
    
    chown "$owner" "$dir" 2>/dev/null || true
    chmod "$perms" "$dir" 2>/dev/null || true
}

# ============================================================================
# ФУНКЦИИ ПРОВЕРКИ СИСТЕМЫ
# ============================================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт должен запускаться от root!"
        log_info "Выполните: sudo bash $0"
        return 1
    fi
    return 0
}

check_os() {
    if [[ ! -f /etc/debian_version ]]; then
        log_error "Система не является Debian/Ubuntu!"
        return 1
    fi
    
    local version=$(lsb_release -rs 2>/dev/null || cat /etc/debian_version 2>/dev/null)
    if [[ -z "$version" ]]; then
        log_warn "Не удалось определить версию ОС"
        return 0
    fi
    
    if [[ "$version" != "12"* ]] && [[ "$version" != "bookworm"* ]]; then
        log_warn "Рекомендуется Debian 12 (Bookworm). Обнаружена версия: $version"
    else
        log_info "ОС: Debian $version - OK"
    fi
    return 0
}

check_arch() {
    local arch=$(uname -m)
    if [[ "$arch" == "x86_64" ]]; then
        log_info "Архитектура: x86_64 - OK"
        return 0
    elif [[ "$arch" == "aarch64" ]]; then
        log_warn "Архитектура: ARM64 (может работать нестабильно)"
        return 0
    else
        log_error "Неподдерживаемая архитектура: $arch"
        return 1
    fi
}

check_resources() {
    local min_cpu="${1:-4}"
    local min_ram="${2:-8}"
    local min_disk="${3:-50}"
    
    local warnings=0
    
    # CPU
    local cpu_cores=$(nproc)
    if [[ $cpu_cores -lt $min_cpu ]]; then
        log_warn "CPU: $cpu_cores ядер (рекомендуется $min_cpu+)"
        ((warnings++))
    else
        log_success "CPU: $cpu_cores ядер"
    fi
    
    # RAM (в GB)
    local total_ram=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}')
    if [[ -z "$total_ram" ]]; then
        total_ram=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}')
        total_ram=$((total_ram / 1024))
    fi
    if [[ $total_ram -lt $min_ram ]]; then
        log_warn "RAM: ${total_ram}GB (рекомендуется ${min_ram}GB+)"
        ((warnings++))
    else
        log_success "RAM: ${total_ram}GB"
    fi
    
    # Диск (в GB)
    local disk_free=$(df -BG "$INSTALL_DIR" 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//')
    if [[ -n "$disk_free" ]] && [[ "$disk_free" =~ ^[0-9]+$ ]]; then
        if [[ $disk_free -lt $min_disk ]]; then
            log_warn "Диск: ${disk_free}GB свободно (рекомендуется ${min_disk}GB+)"
            ((warnings++))
        else
            log_success "Диск: ${disk_free}GB свободно"
        fi
    else
        log_warn "Не удалось определить свободное место на диске"
        ((warnings++))
    fi
    
    return $warnings
}

check_internet() {
    local test_hosts=("8.8.8.8" "1.1.1.1" "google.com")
    
    for host in "${test_hosts[@]}"; do
        if ping -c 1 -W 2 "$host" &>/dev/null; then
            log_success "Интернет доступен"
            return 0
        fi
    done
    
    log_warn "Интернет недоступен. Некоторые компоненты могут не установиться."
    return 1
}

check_dns() {
    if nslookup google.com &>/dev/null || dig google.com &>/dev/null || host google.com &>/dev/null; then
        log_success "DNS работает"
        return 0
    else
        log_warn "Проблемы с DNS разрешением"
        return 1
    fi
}

check_port_free() {
    local port="$1"
    
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        log_warn "Порт $port уже используется"
        return 1
    fi
    return 0
}

check_port_open() {
    local host="$1"
    local port="$2"
    local timeout="${3:-3}"
    
    if nc -z -w "$timeout" "$host" "$port" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# ФУНКЦИИ РАБОТЫ С СЕРВИСАМИ
# ============================================================================

wait_for_service() {
    local service="$1"
    local max_wait="${2:-30}"
    local count=0
    
    log_info "Ожидание запуска $service..."
    
    while ! systemctl is-active --quiet "$service" 2>/dev/null; do
        sleep 1
        ((count++))
        if [[ $count -ge $max_wait ]]; then
            log_error "Сервис $service не запустился за ${max_wait} секунд"
            return 1
        fi
        if [[ $((count % 5)) -eq 0 ]]; then
            log_debug "Ожидание $service: $count сек"
        fi
    done
    
    log_success "Сервис $service запущен"
    return 0
}

check_service() {
    local service="$1"
    
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        log_success "$service: активен"
        return 0
    else
        log_fail "$service: не активен"
        return 1
    fi
}

restart_service() {
    local service="$1"
    
    log_info "Перезапуск $service..."
    systemctl restart "$service"
    
    if wait_for_service "$service" 10; then
        log_success "$service перезапущен"
        return 0
    else
        log_error "Ошибка перезапуска $service"
        return 1
    fi
}

create_systemd_service() {
    local service_name="$1"
    local description="$2"
    local exec_start="$3"
    local user="${4:-$GOCHS_USER}"
    local group="${5:-$GOCHS_GROUP}"
    local working_dir="${6:-$INSTALL_DIR}"
    
    cat > "/etc/systemd/system/${service_name}.service" << EOF
[Unit]
Description=$description
After=network.target

[Service]
Type=simple
User=$user
Group=$group
WorkingDirectory=$working_dir
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

# ============================================================================
# ФУНКЦИИ РАБОТЫ С МОДУЛЯМИ
# ============================================================================

check_module_installed() {
    local module="$1"
    
    if [[ -f "$MODULES_STATE_FILE" ]] && grep -q "^${module}:" "$MODULES_STATE_FILE" 2>/dev/null; then
        return 0
    fi
    return 1
}

mark_module_installed() {
    local module="$1"
    
    ensure_dir "$(dirname "$MODULES_STATE_FILE")"
    echo "$module:$(date +%s)" >> "$MODULES_STATE_FILE"
    log_info "Модуль $module отмечен как установленный"
}

unmark_module_installed() {
    local module="$1"
    
    if [[ -f "$MODULES_STATE_FILE" ]]; then
        sed -i "/^${module}:/d" "$MODULES_STATE_FILE"
        log_info "Отметка об установке модуля $module удалена"
    fi
}

get_installed_modules() {
    if [[ -f "$MODULES_STATE_FILE" ]]; then
        cut -d':' -f1 "$MODULES_STATE_FILE"
    fi
}

# ============================================================================
# ФУНКЦИИ ГЕНЕРАЦИИ И ВАЛИДАЦИИ
# ============================================================================

generate_password() {
    local length="${1:-16}"
    
    if command -v openssl &>/dev/null; then
        openssl rand -base64 32 2>/dev/null | tr -d "=+/" | cut -c1-"$length"
    elif [[ -c /dev/urandom ]]; then
        tr -dc 'A-Za-z0-9!@#$%^&*()_+' < /dev/urandom | head -c "$length"
    else
        echo "ChangeMe$(date +%s | sha256sum 2>/dev/null | base64 2>/dev/null | head -c 8 || echo "Pass123!")"
    fi
}

validate_ip() {
    local ip="$1"
    
    if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        local IFS='.'
        local parts=($ip)
        for part in "${parts[@]}"; do
            if [[ $part -gt 255 ]]; then
                return 1
            fi
        done
        return 0
    fi
    return 1
}

validate_domain() {
    local domain="$1"
    
    if [[ "$domain" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    fi
    return 1
}

validate_email() {
    local email="$1"
    
    if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    fi
    return 1
}

validate_port() {
    local port="$1"
    
    if [[ "$port" =~ ^[0-9]+$ ]] && [[ $port -ge 1 ]] && [[ $port -le 65535 ]]; then
        return 0
    fi
    return 1
}

validate_phone() {
    local phone="$1"
    local allow_internal="${2:-true}"
    
    local clean_phone=$(echo "$phone" | tr -cd '0-9')
    
    if [[ "$allow_internal" == "true" ]] && [[ ${#clean_phone} -le 4 ]] && [[ ${#clean_phone} -ge 3 ]]; then
        return 0
    fi
    
    if [[ ${#clean_phone} -eq 11 ]] && [[ "$clean_phone" =~ ^[78] ]]; then
        return 0
    fi
    
    if [[ ${#clean_phone} -ge 5 ]] && [[ ${#clean_phone} -le 10 ]]; then
        return 0
    fi
    
    return 1
}

# ============================================================================
# ФУНКЦИИ РАБОТЫ С ПАКЕТАМИ
# ============================================================================

is_package_installed() {
    local pkg="$1"
    
    if dpkg -l 2>/dev/null | grep -q "^ii  $pkg "; then
        return 0
    fi
    return 1
}

ensure_package() {
    local pkg="$1"
    
    if ! is_package_installed "$pkg"; then
        log_info "Установка пакета: $pkg"
        apt-get install -y "$pkg" 2>/dev/null
    else
        log_debug "Пакет уже установлен: $pkg"
    fi
}

check_command() {
    local cmd="$1"
    
    if command -v "$cmd" &>/dev/null; then
        log_debug "Команда '$cmd' найдена"
        return 0
    else
        log_warn "Команда '$cmd' не найдена"
        return 1
    fi
}

# ============================================================================
# ФУНКЦИИ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# ============================================================================

create_system_user() {
    local username="$1"
    local home_dir="${2:-/nonexistent}"
    local shell="${3:-/sbin/nologin}"
    
    if id -u "$username" &>/dev/null; then
        log_debug "Пользователь $username уже существует"
        return 0
    fi
    
    useradd -r -d "$home_dir" -s "$shell" "$username"
    log_info "Создан пользователь: $username"
}

add_user_to_group() {
    local username="$1"
    local group="$2"
    
    if groups "$username" 2>/dev/null | grep -q "\b$group\b"; then
        log_debug "Пользователь $username уже в группе $group"
        return 0
    fi
    
    usermod -aG "$group" "$username"
    log_info "Пользователь $username добавлен в группу $group"
}

# ============================================================================
# ФУНКЦИИ РАБОТЫ С СЕТЬЮ
# ============================================================================

get_primary_ip() {
    local ip=$(ip route get 1 2>/dev/null | awk '{print $NF;exit}')
    if [[ -n "$ip" ]] && [[ "$ip" != "127.0.0.1" ]]; then
        echo "$ip"
    else
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        echo "${ip:-192.168.1.100}"
    fi
}

get_external_ip() {
    local ip
    
    for service in "ifconfig.me" "icanhazip.com" "api.ipify.org"; do
        ip=$(curl -s --max-time 3 "$service" 2>/dev/null)
        if [[ -n "$ip" ]] && validate_ip "$ip"; then
            echo "$ip"
            return 0
        fi
    done
    
    echo ""
    return 1
}

check_url() {
    local url="$1"
    local timeout="${2:-5}"
    
    if curl -s -f -m "$timeout" -o /dev/null "$url" 2>/dev/null; then
        return 0
    fi
    return 1
}

# ============================================================================
# ФУНКЦИИ ДЛЯ БАЗ ДАННЫХ
# ============================================================================

check_postgres_connection() {
    local host="${1:-localhost}"
    local port="${2:-5432}"
    local user="${3:-postgres}"
    local db="${4:-postgres}"
    
    if PGPASSWORD="" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1" &>/dev/null; then
        return 0
    fi
    return 1
}

check_redis_connection() {
    local host="${1:-localhost}"
    local port="${2:-6379}"
    local password="${3:-}"
    
    local auth=""
    if [[ -n "$password" ]]; then
        auth="-a $password"
    fi
    
    if redis-cli -h "$host" -p "$port" $auth ping 2>/dev/null | grep -q "PONG"; then
        return 0
    fi
    return 1
}

# ============================================================================
# ФУНКЦИИ ДЛЯ РЕЗЕРВНОГО КОПИРОВАНИЯ
# ============================================================================

backup_directory() {
    local source_dir="$1"
    local backup_name="${2:-$(basename "$source_dir")}"
    local backup_dir="${3:-$INSTALL_DIR/backups}"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/${backup_name}_${timestamp}.tar.gz"
    
    ensure_dir "$backup_dir"
    
    log_info "Создание резервной копии: $source_dir"
    tar -czf "$backup_file" -C "$(dirname "$source_dir")" "$(basename "$source_dir")" 2>/dev/null
    
    if [[ -f "$backup_file" ]]; then
        log_success "Резервная копия создана: $backup_file"
        echo "$backup_file"
    else
        log_error "Ошибка создания резервной копии"
        return 1
    fi
}

cleanup_old_backups() {
    local backup_dir="$1"
    local days="${2:-30}"
    
    if [[ -d "$backup_dir" ]]; then
        log_info "Удаление резервных копий старше $days дней..."
        find "$backup_dir" -name "*.tar.gz" -mtime "+$days" -delete 2>/dev/null
        find "$backup_dir" -name "*.sql" -mtime "+$days" -delete 2>/dev/null
        find "$backup_dir" -name "*.rdb" -mtime "+$days" -delete 2>/dev/null
        log_info "Очистка завершена"
    fi
}

# ============================================================================
# ФУНКЦИИ ДЛЯ ЛОГОВ
# ============================================================================

rotate_logs() {
    local log_file="$1"
    local max_size="${2:-100M}"
    local max_files="${3:-10}"
    
    if [[ -f "$log_file" ]]; then
        local size=$(stat -c%s "$log_file" 2>/dev/null || echo "0")
        local max_bytes=$(numfmt --from=iec "$max_size" 2>/dev/null || echo "104857600")
        
        if [[ $size -gt $max_bytes ]]; then
            for i in $(seq $((max_files - 1)) -1 1); do
                if [[ -f "${log_file}.$i" ]]; then
                    mv "${log_file}.$i" "${log_file}.$((i + 1))"
                fi
            done
            mv "$log_file" "${log_file}.1"
            touch "$log_file"
            log_info "Лог ротирован: $log_file"
        fi
    fi
}

# ============================================================================
# ФУНКЦИИ ДЛЯ ПРОГРЕСС-БАРА
# ============================================================================

show_progress() {
    local current="$1"
    local total="$2"
    local width="${3:-50}"
    
    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "] %3d%%" "$percent"
    
    if [[ $current -eq $total ]]; then
        echo ""
    fi
}

spinner() {
    local pid="$1"
    local message="${2:-Выполнение...}"
    local delay=0.1
    local spinstr='|/-\'
    
    while kill -0 "$pid" 2>/dev/null; do
        local temp=${spinstr#?}
        printf "\r[%c] %s" "$spinstr" "$message"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
    done
    printf "\r[✓] %s - Готово\n" "$message"
}

# ============================================================================
# ФУНКЦИИ РАБОТЫ СО СТРОКАМИ
# ============================================================================

strip_colors() {
    echo "$1" | sed 's/\x1b\[[0-9;]*m//g'
}

truncate_string() {
    local str="$1"
    local max_len="${2:-80}"
    
    if [[ ${#str} -gt $max_len ]]; then
        echo "${str:0:$((max_len - 3))}..."
    else
        echo "$str"
    fi
}

urlencode() {
    local str="$1"
    local encoded=""
    local char
    
    for ((i=0; i<${#str}; i++)); do
        char="${str:i:1}"
        case "$char" in
            [a-zA-Z0-9.~_-]) encoded+="$char" ;;
            *) encoded+=$(printf '%%%02X' "'$char") ;;
        esac
    done
    echo "$encoded"
}

# ============================================================================
# ФУНКЦИИ РАБОТЫ С JSON
# ============================================================================

json_get() {
    local json="$1"
    local key="$2"
    
    if command -v jq &>/dev/null; then
        echo "$json" | jq -r ".$key" 2>/dev/null
    else
        echo "$json" | grep -o "\"$key\":\"[^\"]*\"" | cut -d'"' -f4
    fi
}

json_create() {
    local result="{"
    local first=true
    
    while [[ $# -gt 0 ]]; do
        local key="$1"
        local value="$2"
        shift 2
        
        if [[ "$first" == "true" ]]; then
            first=false
        else
            result+=","
        fi
        
        if [[ "$value" =~ ^[0-9]+$ ]] || [[ "$value" == "true" ]] || [[ "$value" == "false" ]] || [[ "$value" == "null" ]]; then
            result+="\"$key\":$value"
        else
            value=$(echo "$value" | sed 's/"/\\"/g')
            result+="\"$key\":\"$value\""
        fi
    done
    
    result+="}"
    echo "$result"
}

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================================

init_logging

# Экспорт всех функций
export -f log_info log_warn log_error log_success log_fail log_step log_debug
export -f backup_file restore_backup ensure_dir
export -f check_root check_os check_arch check_resources check_internet check_dns
export -f check_port_free check_port_open
export -f wait_for_service check_service restart_service create_systemd_service
export -f check_module_installed mark_module_installed unmark_module_installed get_installed_modules
export -f generate_password
export -f validate_ip validate_domain validate_email validate_port validate_phone
export -f is_package_installed ensure_package check_command
export -f create_system_user add_user_to_group
export -f get_primary_ip get_external_ip check_url
export -f check_postgres_connection check_redis_connection
export -f backup_directory cleanup_old_backups
export -f rotate_logs show_progress spinner
export -f strip_colors truncate_string urlencode
export -f json_get json_create
