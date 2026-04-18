#!/bin/bash

################################################################################
# ГО-ЧС Информирование - Функции валидации
# Версия: 1.0.0
# Назначение: Проверка корректности настроек и компонентов системы
################################################################################

# Загрузка общих функций
source "${UTILS_DIR}/common.sh" 2>/dev/null || {
    echo "Ошибка: не найден файл common.sh"
    exit 1
}

# ============================================================================
# ВАЛИДАЦИЯ СИСТЕМНЫХ ТРЕБОВАНИЙ
# ============================================================================

validate_os() {
    log_info "Проверка операционной системы..."
    
    # Проверка Debian 12
    if [[ ! -f /etc/debian_version ]]; then
        log_error "Система не является Debian"
        return 1
    fi
    
    local version=$(lsb_release -rs 2>/dev/null || cat /etc/debian_version)
    if [[ "$version" != "12"* ]] && [[ "$version" != "bookworm"* ]]; then
        log_error "Требуется Debian 12 (Bookworm), обнаружена версия: $version"
        return 1
    fi
    
    log_info "✓ ОС: Debian 12 - OK"
    return 0
}

validate_resources() {
    log_info "Проверка системных ресурсов..."
    local errors=0
    
    # Проверка CPU
    local cpu_cores=$(nproc)
    if [[ $cpu_cores -lt 4 ]]; then
        log_warn "Рекомендуется минимум 4 ядра CPU, обнаружено: $cpu_cores"
        ((errors++))
    else
        log_info "✓ CPU ядер: $cpu_cores - OK"
    fi
    
    # Проверка RAM
    local total_ram=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $total_ram -lt 8 ]]; then
        log_warn "Рекомендуется минимум 8 GB RAM, обнаружено: ${total_ram}GB"
        ((errors++))
    else
        log_info "✓ RAM: ${total_ram}GB - OK"
    fi
    
    # Проверка дискового пространства
    local available_space=$(df /opt --output=avail 2>/dev/null | tail -1)
    if [[ $available_space -lt 50000000 ]]; then  # 50 GB в KB
        log_warn "Рекомендуется минимум 50 GB свободного места в /opt"
        ((errors++))
    else
        local space_gb=$((available_space / 1024 / 1024))
        log_info "✓ Свободное место: ${space_gb}GB - OK"
    fi
    
    return $errors
}

validate_network() {
    log_info "Проверка сетевых настроек..."
    local errors=0
    
    # Проверка интернета (опционально)
    if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
        log_info "✓ Интернет доступен"
    else
        log_warn "Интернет недоступен (может потребоваться для загрузки пакетов)"
    fi
    
    # Проверка DNS
    if nslookup google.com &>/dev/null || dig google.com &>/dev/null; then
        log_info "✓ DNS работает"
    else
        log_warn "Проблемы с DNS разрешением"
        ((errors++))
    fi
    
    # Проверка локального IP
    local local_ip=$(ip route get 1 2>/dev/null | awk '{print $NF;exit}')
    if [[ -n "$local_ip" ]] && [[ "$local_ip" != "127.0.0.1" ]]; then
        log_info "✓ Локальный IP: $local_ip"
    else
        log_warn "Не удалось определить локальный IP"
        ((errors++))
    fi
    
    return $errors
}

# ============================================================================
# ВАЛИДАЦИЯ КОНФИГУРАЦИИ
# ============================================================================

validate_config_file() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Файл конфигурации не найден: $config_file"
        return 1
    fi
    
    log_info "Проверка конфигурации: $(basename $config_file)"
    local errors=0
    
    # Проверка синтаксиса
    bash -n "$config_file" 2>/dev/null || {
        log_error "Синтаксическая ошибка в $config_file"
        ((errors++))
    }
    
    # Загрузка и проверка обязательных переменных
    source "$config_file"
    
    # Обязательные переменные
    local required_vars=(
        "INSTALL_DIR"
        "DOMAIN_OR_IP"
        "POSTGRES_DB"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Не задана обязательная переменная: $var"
            ((errors++))
        fi
    done
    
    # Проверка значений
    validate_ip_or_domain "$DOMAIN_OR_IP" || ((errors++))
    validate_port "$HTTP_PORT" || ((errors++))
    validate_port "$HTTPS_PORT" || ((errors++))
    validate_port "$POSTGRES_PORT" || ((errors++))
    validate_port "$REDIS_PORT" || ((errors++))
    
    # Проверка паролей
    if [[ ${#POSTGRES_PASSWORD} -lt 8 ]]; then
        log_warn "Пароль PostgreSQL слишком короткий (минимум 8 символов)"
        ((errors++))
    fi
    
    if [[ ${#REDIS_PASSWORD} -lt 8 ]]; then
        log_warn "Пароль Redis слишком короткий (минимум 8 символов)"
        ((errors++))
    fi
    
    return $errors
}

validate_ip_or_domain() {
    local value="$1"
    
    # Проверка IP адреса
    if [[ "$value" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        local IFS='.'
        local ip_parts=($value)
        for part in "${ip_parts[@]}"; do
            if [[ $part -gt 255 ]]; then
                log_error "Неверный IP адрес: $value"
                return 1
            fi
        done
        return 0
    fi
    
    # Проверка доменного имени
    if [[ "$value" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    fi
    
    # Проверка localhost
    if [[ "$value" == "localhost" ]]; then
        return 0
    fi
    
    log_error "Неверный формат IP/домена: $value"
    return 1
}

validate_port() {
    local port="$1"
    
    if [[ ! "$port" =~ ^[0-9]+$ ]]; then
        log_error "Порт должен быть числом: $port"
        return 1
    fi
    
    if [[ $port -lt 1 ]] || [[ $port -gt 65535 ]]; then
        log_error "Порт должен быть в диапазоне 1-65535: $port"
        return 1
    fi
    
    return 0
}

validate_email() {
    local email="$1"
    
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        log_error "Неверный формат email: $email"
        return 1
    fi
    
    return 0
}

validate_phone() {
    local phone="$1"
    local allow_internal="${2:-true}"
    
    # Удаление всех нецифровых символов
    local clean_phone=$(echo "$phone" | tr -cd '0-9')
    
    # Внутренний номер (3-4 цифры)
    if [[ "$allow_internal" == "true" ]] && [[ ${#clean_phone} -le 4 ]]; then
        return 0
    fi
    
    # Мобильный номер (11 цифр, начинается с 7 или 8)
    if [[ ${#clean_phone} -eq 11 ]] && [[ "$clean_phone" =~ ^[78] ]]; then
        return 0
    fi
    
    # Городской номер (5-10 цифр)
    if [[ ${#clean_phone} -ge 5 ]] && [[ ${#clean_phone} -le 10 ]]; then
        return 0
    fi
    
    log_error "Неверный формат телефона: $phone"
    return 1
}

# ============================================================================
# ВАЛИДАЦИЯ ЗАВИСИМОСТЕЙ
# ============================================================================

validate_python() {
    log_info "Проверка Python..."
    
    if ! command -v python3 &>/dev/null; then
        log_error "Python3 не установлен"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | awk '{print $2}')
    local major_version=$(echo "$python_version" | cut -d. -f1)
    local minor_version=$(echo "$python_version" | cut -d. -f2)
    
    if [[ $major_version -lt 3 ]] || [[ $major_version -eq 3 && $minor_version -lt 9 ]]; then
        log_error "Требуется Python 3.9+, обнаружена версия: $python_version"
        return 1
    fi
    
    log_info "✓ Python: $python_version - OK"
    
    # Проверка pip
    if ! command -v pip3 &>/dev/null; then
        log_warn "pip3 не установлен"
        return 1
    fi
    
    # Проверка venv
    if ! python3 -m venv --help &>/dev/null; then
        log_warn "Модуль venv не установлен"
        return 1
    fi
    
    log_info "✓ Python окружение - OK"
    return 0
}

validate_nodejs() {
    log_info "Проверка Node.js..."
    
    if ! command -v node &>/dev/null; then
        log_warn "Node.js не установлен (требуется для фронтенда)"
        return 1
    fi
    
    local node_version=$(node --version | tr -d 'v')
    local major_version=$(echo "$node_version" | cut -d. -f1)
    
    if [[ $major_version -lt 18 ]]; then
        log_error "Требуется Node.js 18+, обнаружена версия: $node_version"
        return 1
    fi
    
    log_info "✓ Node.js: v$node_version - OK"
    
    # Проверка npm или yarn
    if command -v npm &>/dev/null; then
        log_info "✓ npm: $(npm --version) - OK"
    elif command -v yarn &>/dev/null; then
        log_info "✓ yarn: $(yarn --version) - OK"
    else
        log_warn "npm или yarn не установлен"
        return 1
    fi
    
    return 0
}

validate_postgresql() {
    log_info "Проверка PostgreSQL..."
    
    if ! command -v psql &>/dev/null; then
        log_error "PostgreSQL клиент не установлен"
        return 1
    fi
    
    # Проверка сервера
    if ! systemctl is-active --quiet postgresql; then
        log_warn "PostgreSQL сервер не запущен"
        return 1
    fi
    
    local pg_version=$(psql --version | awk '{print $3}' | cut -d. -f1)
    if [[ $pg_version -lt 14 ]]; then
        log_error "Требуется PostgreSQL 14+, обнаружена версия: $pg_version"
        return 1
    fi
    
    log_info "✓ PostgreSQL: версия $pg_version - OK"
    
    # Проверка подключения
    if sudo -u postgres psql -c "SELECT 1" &>/dev/null; then
        log_info "✓ PostgreSQL подключение - OK"
    else
        log_warn "Не удалось подключиться к PostgreSQL"
        return 1
    fi
    
    return 0
}

validate_redis() {
    log_info "Проверка Redis..."
    
    if ! command -v redis-cli &>/dev/null; then
        log_error "Redis клиент не установлен"
        return 1
    fi
    
    # Проверка сервера
    if ! systemctl is-active --quiet redis-server; then
        log_warn "Redis сервер не запущен"
        return 1
    fi
    
    local redis_version=$(redis-server --version | awk '{print $3}' | cut -d= -f2)
    log_info "✓ Redis: версия $redis_version - OK"
    
    # Проверка подключения
    if redis-cli ping &>/dev/null; then
        log_info "✓ Redis подключение - OK"
    else
        log_warn "Не удалось подключиться к Redis"
        return 1
    fi
    
    return 0
}

validate_asterisk() {
    log_info "Проверка Asterisk..."
    
    if ! command -v asterisk &>/dev/null; then
        log_error "Asterisk не установлен"
        return 1
    fi
    
    # Проверка сервера
    if ! systemctl is-active --quiet asterisk; then
        log_warn "Asterisk сервер не запущен"
        return 1
    fi
    
    local ast_version=$(asterisk -V | grep -oP 'Asterisk \K[0-9.]+')
    local major_version=$(echo "$ast_version" | cut -d. -f1)
    
    if [[ $major_version -lt 20 ]]; then
        log_error "Требуется Asterisk 20+, обнаружена версия: $ast_version"
        return 1
    fi
    
    log_info "✓ Asterisk: версия $ast_version - OK"
    
    # Проверка AMI
    if asterisk -rx "manager show connected" &>/dev/null; then
        log_info "✓ Asterisk AMI - OK"
    else
        log_warn "Проблема с Asterisk AMI"
        return 1
    fi
    
    return 0
}

validate_nginx() {
    log_info "Проверка Nginx..."
    
    if ! command -v nginx &>/dev/null; then
        log_warn "Nginx не установлен"
        return 1
    fi
    
    # Проверка конфигурации
    if nginx -t &>/dev/null; then
        log_info "✓ Nginx конфигурация - OK"
    else
        log_error "Ошибка в конфигурации Nginx"
        return 1
    fi
    
    # Проверка сервера
    if systemctl is-active --quiet nginx; then
        log_info "✓ Nginx сервер запущен"
    else
        log_warn "Nginx сервер не запущен"
        return 1
    fi
    
    return 0
}

# ============================================================================
# ВАЛИДАЦИЯ СЕРВИСОВ
# ============================================================================

validate_service() {
    local service="$1"
    local required="${2:-false}"
    
    if systemctl is-active --quiet "$service"; then
        log_info "✓ Сервис $service: активен"
        return 0
    else
        if [[ "$required" == "true" ]]; then
            log_error "✗ Сервис $service: не активен (обязательный)"
            return 1
        else
            log_warn "⚠ Сервис $service: не активен"
            return 1
        fi
    fi
}

validate_all_services() {
    log_step "Проверка всех сервисов"
    local errors=0
    
    # Обязательные сервисы
    validate_service "postgresql" true || ((errors++))
    validate_service "redis-server" true || ((errors++))
    validate_service "asterisk" true || ((errors++))
    
    # Опциональные сервисы
    validate_service "gochs-api" false || ((errors++))
    validate_service "gochs-worker" false || ((errors++))
    validate_service "gochs-scheduler" false || ((errors++))
    validate_service "nginx" false || ((errors++))
    
    return $errors
}

# ============================================================================
# ВАЛИДАЦИЯ API И ВЕБ-ИНТЕРФЕЙСА
# ============================================================================

validate_api() {
    local api_url="${1:-http://localhost:8000}"
    local timeout="${2:-5}"
    
    log_info "Проверка API: $api_url"
    
    # Проверка health endpoint
    if curl -s -f -m "$timeout" "${api_url}/health" &>/dev/null; then
        local health=$(curl -s "${api_url}/health")
        log_info "✓ API health: $health"
        
        # Проверка статуса
        if echo "$health" | grep -q '"status":"healthy"'; then
            log_info "✓ API статус: healthy"
            return 0
        else
            log_warn "API вернул нездоровый статус"
            return 1
        fi
    else
        log_error "API недоступен: $api_url"
        return 1
    fi
}

validate_web_interface() {
    local web_url="${1:-http://localhost}"
    local timeout="${2:-5}"
    
    log_info "Проверка веб-интерфейса: $web_url"
    
    if curl -s -f -m "$timeout" "$web_url" &>/dev/null; then
        local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$web_url")
        if [[ "$status_code" == "200" ]]; then
            log_info "✓ Веб-интерфейс доступен (HTTP 200)"
            return 0
        else
            log_warn "Веб-интерфейс вернул код: $status_code"
            return 1
        fi
    else
        log_error "Веб-интерфейс недоступен: $web_url"
        return 1
    fi
}

validate_websocket() {
    local ws_url="${1:-ws://localhost:8000/ws}"
    local timeout="${2:-3}"
    
    log_info "Проверка WebSocket: $ws_url"
    
    # Базовая проверка через curl (только HTTP upgrade)
    if curl -s -m "$timeout" -H "Upgrade: websocket" -H "Connection: Upgrade" \
        "${ws_url/http:/}" &>/dev/null; then
        log_info "✓ WebSocket endpoint отвечает"
        return 0
    else
        log_warn "WebSocket endpoint не отвечает"
        return 1
    fi
}

# ============================================================================
# ВАЛИДАЦИЯ ТЕЛЕФОНИИ
# ============================================================================

validate_freepbx_connection() {
    local freepbx_host="$1"
    local freepbx_port="${2:-5060}"
    local timeout="${3:-5}"
    
    log_info "Проверка подключения к FreePBX: $freepbx_host:$freepbx_port"
    
    # Проверка SIP порта
    if nc -z -w "$timeout" "$freepbx_host" "$freepbx_port" 2>/dev/null; then
        log_info "✓ FreePBX SIP порт доступен"
    else
        log_warn "FreePBX SIP порт недоступен"
        return 1
    fi
    
    # Проверка регистрации в Asterisk
    if asterisk -rx "pjsip show registrations" | grep -q "$freepbx_host.*Registered"; then
        log_info "✓ FreePBX регистрация активна"
        return 0
    else
        log_warn "FreePBX не зарегистрирован в Asterisk"
        return 1
    fi
}

validate_sip_trunk() {
    local trunk_name="$1"
    
    log_info "Проверка SIP транка: $trunk_name"
    
    if asterisk -rx "pjsip show endpoints" | grep -q "$trunk_name"; then
        local status=$(asterisk -rx "pjsip show endpoint $trunk_name" | grep "DeviceState")
        log_info "✓ Транк $trunk_name: $status"
        return 0
    else
        log_error "Транк $trunk_name не найден"
        return 1
    fi
}

validate_audio_formats() {
    log_info "Проверка аудио форматов..."
    local errors=0
    
    # Проверка sox
    if command -v sox &>/dev/null; then
        log_info "✓ SoX установлен"
        
        # Проверка форматов
        if sox --help 2>&1 | grep -q "wav"; then
            log_info "  - WAV поддерживается"
        else
            log_warn "  - WAV не поддерживается"
            ((errors++))
        fi
        
        if sox --help 2>&1 | grep -q "mp3"; then
            log_info "  - MP3 поддерживается"
        else
            log_warn "  - MP3 не поддерживается"
        fi
    else
        log_warn "SoX не установлен"
        ((errors++))
    fi
    
    # Проверка ffmpeg
    if command -v ffmpeg &>/dev/null; then
        log_info "✓ FFmpeg установлен"
    else
        log_warn "FFmpeg не установлен"
    fi
    
    return $errors
}

# ============================================================================
# ВАЛИДАЦИЯ TTS/STT
# ============================================================================

validate_tts() {
    log_info "Проверка TTS (Text-to-Speech)..."
    
    # Проверка Festival
    if command -v festival &>/dev/null; then
        log_info "✓ Festival TTS установлен"
        
        # Проверка русского голоса
        if festival -b "(voice.list)" 2>&1 | grep -q "russian"; then
            log_info "  - Русский голос доступен"
        else
            log_warn "  - Русский голос не найден"
        fi
    else
        log_warn "Festival не установлен"
    fi
    
    # Проверка Coqui TTS (Python)
    if python3 -c "import TTS" 2>/dev/null; then
        log_info "✓ Coqui TTS установлен"
    else
        log_info "Coqui TTS не установлен (опционально)"
    fi
    
    return 0
}

validate_stt() {
    log_info "Проверка STT (Speech-to-Text)..."
    
    # Проверка Vosk
    if python3 -c "import vosk" 2>/dev/null; then
        log_info "✓ Vosk STT установлен"
        
        # Проверка модели
        local model_path="$INSTALL_DIR/models/vosk/model-ru"
        if [[ -d "$model_path" ]]; then
            log_info "  - Русская модель найдена: $model_path"
        else
            log_warn "  - Русская модель не найдена"
        fi
    else
        log_info "Vosk не установлен (опционально)"
    fi
    
    return 0
}

# ============================================================================
# ВАЛИДАЦИЯ БЕЗОПАСНОСТИ
# ============================================================================

validate_ssl_certificate() {
    local cert_file="${1:-/etc/nginx/ssl/gochs.crt}"
    local key_file="${2:-/etc/nginx/ssl/gochs.key}"
    
    log_info "Проверка SSL сертификата..."
    
    if [[ ! -f "$cert_file" ]]; then
        log_warn "SSL сертификат не найден: $cert_file"
        return 1
    fi
    
    if [[ ! -f "$key_file" ]]; then
        log_warn "SSL ключ не найден: $key_file"
        return 1
    fi
    
    # Проверка срока действия
    local expiry=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
    if [[ -n "$expiry" ]]; then
        local expiry_epoch=$(date -d "$expiry" +%s)
        local now_epoch=$(date +%s)
        local days_left=$(( ($expiry_epoch - $now_epoch) / 86400 ))
        
        if [[ $days_left -lt 30 ]]; then
            log_warn "SSL сертификат истекает через $days_left дней"
        else
            log_info "✓ SSL сертификат действителен ещё $days_left дней"
        fi
    fi
    
    # Проверка прав доступа
    local key_perms=$(stat -c %a "$key_file")
    if [[ "$key_perms" != "600" ]]; then
        log_warn "Небезопасные права на ключ: $key_perms (должны быть 600)"
    else
        log_info "✓ Права на SSL ключ: OK"
    fi
    
    return 0
}

validate_firewall() {
    log_info "Проверка настроек файрвола..."
    
    if command -v ufw &>/dev/null; then
        local ufw_status=$(ufw status | grep "Status:" | awk '{print $2}')
        log_info "UFW статус: $ufw_status"
        
        if [[ "$ufw_status" == "active" ]]; then
            # Проверка открытых портов
            local required_ports=("22" "80" "443" "5060")
            for port in "${required_ports[@]}"; do
                if ufw status | grep -q "$port.*ALLOW"; then
                    log_info "  ✓ Порт $port открыт"
                else
                    log_warn "  ✗ Порт $port не открыт"
                fi
            done
        fi
    else
        log_info "UFW не установлен"
    fi
    
    return 0
}

validate_file_permissions() {
    log_info "Проверка прав доступа..."
    local errors=0
    
    # Проверка прав на конфигурационные файлы
    local config_files=(
        "$INSTALL_DIR/config/config.yaml"
        "$INSTALL_DIR/.env"
        "/root/.gochs_credentials"
    )
    
    for file in "${config_files[@]}"; do
        if [[ -f "$file" ]]; then
            local perms=$(stat -c %a "$file")
            if [[ "$perms" != "600" ]]; then
                log_warn "Небезопасные права на $file: $perms (должны быть 600)"
                ((errors++))
            fi
        fi
    done
    
    # Проверка владельца
    if [[ -d "$INSTALL_DIR" ]]; then
        local owner=$(stat -c %U "$INSTALL_DIR")
        if [[ "$owner" != "$GOCHS_USER" ]]; then
            log_warn "Неверный владелец $INSTALL_DIR: $owner (должен быть $GOCHS_USER)"
            ((errors++))
        fi
    fi
    
    return $errors
}

# ============================================================================
# КОМПЛЕКСНАЯ ВАЛИДАЦИЯ
# ============================================================================

validate_all() {
    log_step "КОМПЛЕКСНАЯ ПРОВЕРКА СИСТЕМЫ"
    local total_errors=0
    
    # Системные проверки
    validate_os || ((total_errors++))
    validate_resources || ((total_errors++))
    validate_network || ((total_errors++))
    
    # Проверка конфигурации
    local config_file="${CONFIG_DIR}/config.env"
    if [[ -f "$config_file" ]]; then
        validate_config_file "$config_file" || ((total_errors++))
    fi
    
    # Проверка зависимостей
    echo ""
    log_info "Проверка зависимостей:"
    validate_python || ((total_errors++))
    validate_nodejs || ((total_errors++))
    validate_postgresql || ((total_errors++))
    validate_redis || ((total_errors++))
    validate_asterisk || ((total_errors++))
    validate_nginx || ((total_errors++))
    
    # Проверка сервисов
    echo ""
    validate_all_services || ((total_errors++))
    
    # Проверка API и веб
    echo ""
    validate_api || ((total_errors++))
    validate_web_interface || ((total_errors++))
    
    # Проверка телефонии
    echo ""
    if [[ -n "$FREEPBX_HOST" ]]; then
        validate_freepbx_connection "$FREEPBX_HOST" "$FREEPBX_PORT" || ((total_errors++))
    fi
    validate_audio_formats || ((total_errors++))
    
    # Проверка TTS/STT
    echo ""
    validate_tts
    validate_stt
    
    # Проверка безопасности
    echo ""
    validate_ssl_certificate || ((total_errors++))
    validate_firewall
    validate_file_permissions || ((total_errors++))
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    
    if [[ $total_errors -eq 0 ]]; then
        log_info "✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!"
        return 0
    else
        log_error "❌ ОБНАРУЖЕНО ОШИБОК: $total_errors"
        return 1
    fi
}

# ============================================================================
# БЫСТРЫЕ ПРОВЕРКИ
# ============================================================================

quick_check() {
    log_info "Быстрая проверка системы..."
    local errors=0
    
    # Проверка основных сервисов
    systemctl is-active --quiet postgresql || { log_error "PostgreSQL не запущен"; ((errors++)); }
    systemctl is-active --quiet redis-server || { log_error "Redis не запущен"; ((errors++)); }
    systemctl is-active --quiet asterisk || { log_error "Asterisk не запущен"; ((errors++)); }
    systemctl is-active --quiet gochs-api || { log_warn "API не запущен"; ((errors++)); }
    systemctl is-active --quiet nginx || { log_warn "Nginx не запущен"; ((errors++)); }
    
    # Проверка API
    curl -s -f http://localhost:8000/health &>/dev/null || { log_error "API не отвечает"; ((errors++)); }
    
    # Проверка веб-интерфейса
    curl -s -f http://localhost &>/dev/null || { log_warn "Веб-интерфейс не отвечает"; ((errors++)); }
    
    if [[ $errors -eq 0 ]]; then
        log_info "✅ Быстрая проверка пройдена"
        return 0
    else
        log_error "❌ Обнаружено проблем: $errors"
        return 1
    fi
}

# ============================================================================
# ГЕНЕРАЦИЯ ОТЧЕТА
# ============================================================================

generate_validation_report() {
    local report_file="${1:-/tmp/gochs_validation_report.txt}"
    
    log_info "Генерация отчета о валидации: $report_file"
    
    {
        echo "═══════════════════════════════════════════════════════════════"
        echo "   ГО-ЧС Информирование - Отчет о валидации системы"
        echo "   Дата: $(date)"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        
        echo "=== СИСТЕМНАЯ ИНФОРМАЦИЯ ==="
        echo "ОС: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"
        echo "Ядро: $(uname -r)"
        echo "CPU: $(nproc) ядер"
        echo "RAM: $(free -h | awk '/^Mem:/{print $2}')"
        echo "Диск: $(df -h /opt | tail -1 | awk '{print $4}') свободно"
        echo ""
        
        echo "=== ВЕРСИИ КОМПОНЕНТОВ ==="
        echo "Python: $(python3 --version 2>&1)"
        echo "Node.js: $(node --version 2>/dev/null || echo 'не установлен')"
        echo "PostgreSQL: $(psql --version 2>/dev/null | head -1 || echo 'не установлен')"
        echo "Redis: $(redis-server --version 2>/dev/null | head -1 || echo 'не установлен')"
        echo "Asterisk: $(asterisk -V 2>/dev/null | head -1 || echo 'не установлен')"
        echo "Nginx: $(nginx -v 2>&1 | cut -d/ -f2 || echo 'не установлен')"
        echo ""
        
        echo "=== СТАТУС СЕРВИСОВ ==="
        for service in postgresql redis-server asterisk gochs-api gochs-worker gochs-scheduler nginx; do
            if systemctl is-active --quiet $service 2>/dev/null; then
                echo "✓ $service: активен"
            else
                echo "✗ $service: не активен"
            fi
        done
        echo ""
        
        echo "=== СЕТЕВЫЕ ПОРТЫ ==="
        netstat -tlnp 2>/dev/null | grep -E ":(80|443|5060|5432|6379|8000|8088)" | while read line; do
            echo "$line"
        done
        echo ""
        
        echo "=== ПОСЛЕДНИЕ ОШИБКИ ==="
        echo "--- Asterisk ---"
        tail -5 /var/log/asterisk/full 2>/dev/null | grep -i error || echo "Нет ошибок"
        echo ""
        echo "--- GOCHS API ---"
        tail -5 "$INSTALL_DIR/logs/api_error.log" 2>/dev/null || echo "Нет логов"
        echo ""
        echo "--- Nginx ---"
        tail -5 /var/log/nginx/error.log 2>/dev/null || echo "Нет ошибок"
        
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "Отчет сохранен: $report_file"
        
    } > "$report_file"
    
    log_info "Отчет сгенерирован: $report_file"
}

# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

case "${1:-}" in
    all)
        validate_all
        ;;
    quick)
        quick_check
        ;;
    os)
        validate_os
        ;;
    resources)
        validate_resources
        ;;
    config)
        validate_config_file "${2:-${CONFIG_DIR}/config.env}"
        ;;
    services)
        validate_all_services
        ;;
    api)
        validate_api "${2:-http://localhost:8000}"
        ;;
    web)
        validate_web_interface "${2:-http://localhost}"
        ;;
    freepbx)
        validate_freepbx_connection "${2:-$FREEPBX_HOST}" "${3:-5060}"
        ;;
    report)
        generate_validation_report "${2:-/tmp/gochs_validation_report.txt}"
        ;;
    *)
        echo "Использование: $0 {all|quick|os|resources|config|services|api|web|freepbx|report}"
        echo ""
        echo "  all       - Комплексная проверка всей системы"
        echo "  quick     - Быстрая проверка основных компонентов"
        echo "  os        - Проверка ОС"
        echo "  resources - Проверка системных ресурсов"
        echo "  config    - Проверка конфигурации"
        echo "  services  - Проверка сервисов"
        echo "  api       - Проверка API"
        echo "  web       - Проверка веб-интерфейса"
        echo "  freepbx   - Проверка подключения к FreePBX"
        echo "  report    - Генерация полного отчета"
        exit 1
        ;;
esac
