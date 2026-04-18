#!/bin/bash

################################################################################
# ГО-ЧС Информирование - Главный установочный скрипт
# Модульная установка системы с улучшенной обработкой ошибок
################################################################################

set -e  # Прерывать при ошибке, но с обработкой

# Определение директорий
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="${SCRIPT_DIR}/modules"
CONFIG_DIR="${SCRIPT_DIR}/config"
UTILS_DIR="${SCRIPT_DIR}/utils"
INSTALL_DIR="/opt/gochs-informing"

# Загрузка общих функций (если есть)
if [[ -f "${UTILS_DIR}/common.sh" ]]; then
    source "${UTILS_DIR}/common.sh"
fi

# Версия системы
VERSION="1.0.0"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Файл лога
LOG_FILE="/var/log/gochs-install.log"
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

################################################################################
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}  $*${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
}

# Функция для проверки и установки базовых зависимостей
ensure_basic_deps() {
    log_info "Проверка базовых зависимостей..."
    
    # Проверка прав root
    if [[ $EUID -ne 0 ]]; then
        log_error "Скрипт должен запускаться от root!"
        echo "Выполните: sudo bash install.sh"
        exit 1
    fi
    
    # Проверка и установка lsb-release если отсутствует
    if ! command -v lsb_release &>/dev/null; then
        log_warn "lsb-release не установлен. Устанавливаю..."
        apt-get update -qq
        apt-get install -y lsb-release
    fi
    
    # Проверка ОС
    if [[ ! -f /etc/debian_version ]]; then
        log_error "Система не является Debian/Ubuntu!"
        exit 1
    fi
    
    local os_version=$(lsb_release -rs 2>/dev/null || cat /etc/debian_version)
    if [[ "$os_version" != "12" ]] && [[ "$os_version" != "12."* ]] && [[ "$os_version" != "bookworm"* ]]; then
        log_warn "Рекомендуется Debian 12 (Bookworm). Обнаружена версия: $os_version"
        echo -n "Продолжить установку? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "ОС: Debian 12 - OK"
    fi
    
    # Установка минимально необходимых пакетов
    local required_pkgs="wget curl git build-essential net-tools"
    local missing_pkgs=""
    
    for pkg in $required_pkgs; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            missing_pkgs="$missing_pkgs $pkg"
        fi
    done
    
    if [[ -n "$missing_pkgs" ]]; then
        log_info "Установка недостающих пакетов:$missing_pkgs"
        apt-get update -qq
        apt-get install -y $missing_pkgs
    fi
    
    log_info "Базовые зависимости установлены"
}

# Функция для создания структуры директорий
ensure_directories() {
    log_info "Создание структуры директорий..."
    
    mkdir -p "$INSTALL_DIR"/{app,frontend,logs,recordings,generated_voice,playbooks,backups,exports,scripts}
    mkdir -p "$INSTALL_DIR"/app/{core,api,models,schemas,services,tasks,utils}
    mkdir -p "$MODULES_DIR"
    mkdir -p "$CONFIG_DIR"/asterisk/gochs
    mkdir -p "$UTILS_DIR"
    
    log_info "Директории созданы"
}

# Функция для проверки интернета
check_internet() {
    log_info "Проверка интернет-соединения..."
    
    # Проверка DNS
    if ! nslookup google.com &>/dev/null && ! dig google.com &>/dev/null; then
        log_warn "Проблемы с DNS разрешением"
        echo "nameserver 8.8.8.8" >> /etc/resolv.conf
        echo "nameserver 1.1.1.1" >> /etc/resolv.conf
    fi
    
    # Проверка подключения
    if ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
        log_info "Интернет доступен"
        return 0
    else
        log_warn "Интернет недоступен. Некоторые компоненты могут не установиться."
        echo -n "Продолжить установку в офлайн-режиме? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
        return 1
    fi
}

# Функция для определения IP
detect_ip() {
    local ip=$(ip route get 1 2>/dev/null | awk '{print $NF;exit}')
    if [[ -n "$ip" ]] && [[ "$ip" != "127.0.0.1" ]]; then
        echo "$ip"
    else
        # Альтернативный способ
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        echo "${ip:-192.168.1.100}"
    fi
}

# Функция для получения параметров от пользователя
get_user_input() {
    log_step "Начальная конфигурация"
    
    # Определение IP
    local default_ip=$(detect_ip)
    
    echo ""
    echo -e "${CYAN}Введите параметры установки:${NC}"
    echo ""
    
    # Домен или IP
    read -p "Домен или IP-адрес сервера [$default_ip]: " input_ip
    DOMAIN_OR_IP="${input_ip:-$default_ip}"
    
    # Email администратора
    read -p "Email администратора [admin@localhost]: " input_email
    ADMIN_EMAIL="${input_email:-admin@localhost}"
    
    # FreePBX настройки
    echo ""
    echo -e "${CYAN}Настройки подключения к FreePBX:${NC}"
    read -p "IP адрес FreePBX [192.168.1.10]: " freepbx_host
    FREEPBX_HOST="${freepbx_host:-192.168.1.10}"
    
    read -p "Порт FreePBX [5060]: " freepbx_port
    FREEPBX_PORT="${freepbx_port:-5060}"
    
    read -p "Внутренний номер/Extension [gochs]: " freepbx_ext
    FREEPBX_EXTENSION="${freepbx_ext:-gochs}"
    
    read -p "Пароль для регистрации: " freepbx_pass
    while [[ -z "$freepbx_pass" ]]; do
        read -p "Пароль не может быть пустым. Введите пароль: " freepbx_pass
    done
    FREEPBX_PASSWORD="$freepbx_pass"
    
    # Генерация паролей для БД и Redis
    POSTGRES_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    ASTERISK_AMI_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    ASTERISK_ARI_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    
    # Создание конфигурационного файла
    generate_config
    
    # Сохранение учетных данных
    save_credentials
    
    echo ""
    log_info "Конфигурация сохранена"
}

# Генерация конфигурационного файла
generate_config() {
    local config_file="${CONFIG_DIR}/config.env"
    
    cat > "$config_file" << EOF
################################################################################
# ГО-ЧС Информирование - Конфигурация
# Сгенерировано: $(date)
################################################################################

# Система
SYSTEM_NAME="ГО-ЧС Информирование"
SYSTEM_VERSION="$VERSION"
INSTALL_DIR="$INSTALL_DIR"
TIMEZONE="Europe/Moscow"

# Сеть
DOMAIN_OR_IP="$DOMAIN_OR_IP"
HTTP_PORT=80
HTTPS_PORT=443
API_PORT=8000

# База данных
POSTGRES_VERSION="15"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_DB="gochs"
POSTGRES_USER="gochs_user"
POSTGRES_PASSWORD="$POSTGRES_PASSWORD"

# Redis
REDIS_VERSION="7.2"
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_PASSWORD="$REDIS_PASSWORD"
REDIS_DB="0"

# Asterisk
ASTERISK_VERSION="20"
ASTERISK_SIP_PORT="5060"
ASTERISK_AMI_PORT="5038"
ASTERISK_AMI_USER="gochs_ami"
ASTERISK_AMI_PASSWORD="$ASTERISK_AMI_PASSWORD"
ASTERISK_ARI_PORT="8088"
ASTERISK_ARI_USER="gochs"
ASTERISK_ARI_PASSWORD="$ASTERISK_ARI_PASSWORD"

# FreePBX
FREEPBX_ENABLED="yes"
FREEPBX_HOST="$FREEPBX_HOST"
FREEPBX_PORT="$FREEPBX_PORT"
FREEPBX_EXTENSION="$FREEPBX_EXTENSION"
FREEPBX_USERNAME="$FREEPBX_EXTENSION"
FREEPBX_PASSWORD="$FREEPBX_PASSWORD"

# Email
ADMIN_EMAIL="$ADMIN_EMAIL"

# Логирование
LOG_LEVEL="INFO"
LOG_DIR="$INSTALL_DIR/logs"
EOF

    log_info "Конфигурация сохранена в $config_file"
}

# Сохранение учетных данных
save_credentials() {
    local cred_file="/root/.gochs_credentials"
    
    cat > "$cred_file" << EOF
═══════════════════════════════════════════════════════════════
   ГО-ЧС Информирование - Учетные данные
   Дата установки: $(date)
   СОХРАНИТЕ ЭТОТ ФАЙЛ В БЕЗОПАСНОМ МЕСТЕ!
═══════════════════════════════════════════════════════════════

СЕТЕВОЙ ДОСТУП:
  URL: http://$DOMAIN_OR_IP
  URL (HTTPS): https://$DOMAIN_OR_IP (если настроен SSL)

АДМИНИСТРАТОР:
  Логин: admin
  Пароль: Admin123! (ИЗМЕНИТЕ ПРИ ПЕРВОМ ВХОДЕ!)

БАЗА ДАННЫХ POSTGRESQL:
  База данных: gochs
  Пользователь: gochs_user
  Пароль: $POSTGRES_PASSWORD
  Порт: 5432

REDIS:
  Пароль: $REDIS_PASSWORD
  Порт: 6379

ASTERISK:
  AMI пользователь: gochs_ami
  AMI пароль: $ASTERISK_AMI_PASSWORD
  AMI порт: 5038
  ARI пользователь: gochs
  ARI пароль: $ASTERISK_ARI_PASSWORD
  ARI порт: 8088

FREE PBX:
  Хост: $FREEPBX_HOST:$FREEPBX_PORT
  Extension: $FREEPBX_EXTENSION
  Пароль: $FREEPBX_PASSWORD

ДИРЕКТОРИИ:
  Установка: $INSTALL_DIR
  Записи звонков: $INSTALL_DIR/recordings
  Логи: $INSTALL_DIR/logs

УПРАВЛЕНИЕ:
  Запуск API: systemctl start gochs-api
  Статус: systemctl status gochs-api
  Логи API: journalctl -u gochs-api -f

═══════════════════════════════════════════════════════════════
EOF

    chmod 600 "$cred_file"
    log_info "Учетные данные сохранены в $cred_file"
}

# Функция установки модуля с обработкой ошибок
install_module() {
    local module="$1"
    local module_script="${MODULES_DIR}/${module}.sh"
    
    if [[ ! -f "$module_script" ]]; then
        log_error "Модуль $module не найден: $module_script"
        return 1
    fi
    
    log_step "Установка модуля: $module"
    
    # Попытка установки с повторными попытками
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Попытка $attempt из $max_attempts..."
        
        if bash "$module_script" "install" 2>&1 | tee -a "$LOG_FILE"; then
            log_info "Модуль $module успешно установлен"
            echo "$module:$(date +%s)" >> "$INSTALL_DIR/.modules_state"
            return 0
        else
            log_warn "Ошибка при установке модуля $module (попытка $attempt)"
            
            if [[ $attempt -lt $max_attempts ]]; then
                log_info "Ожидание перед повторной попыткой..."
                sleep 5
                
                # Очистка перед повторной попыткой
                bash "$module_script" "clean" 2>/dev/null || true
            fi
            
            ((attempt++))
        fi
    done
    
    log_error "Модуль $module не удалось установить после $max_attempts попыток"
    return 1
}

# Полная установка
full_install() {
    log_step "ЗАПУСК ПОЛНОЙ УСТАНОВКИ"
    
    local start_time=$(date +%s)
    
    # Список модулей
    local modules=(
        "01-system"
        "02-python"
        "03-db"
        "04-redis"
        "05-asterisk"
        "06-backend"
        "07-frontend"
        "08-nginx"
    )
    
    local failed_modules=""
    
    for module in "${modules[@]}"; do
        if ! install_module "$module"; then
            failed_modules="$failed_modules $module"
            log_error "КРИТИЧЕСКАЯ ОШИБКА: модуль $module не установлен"
            
            echo -n "Продолжить установку? (y/N): "
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                log_error "Установка прервана пользователем"
                exit 1
            fi
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo ""
    log_step "УСТАНОВКА ЗАВЕРШЕНА"
    log_info "Время установки: ${minutes} мин ${seconds} сек"
    
    if [[ -n "$failed_modules" ]]; then
        log_warn "Следующие модули не были установлены:$failed_modules"
    else
        log_info "✅ Все модули установлены успешно!"
    fi
    
    show_post_install_info
}

# Показать информацию после установки
show_post_install_info() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}              УСТАНОВКА ЗАВЕРШЕНА!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Проверка статуса сервисов
    echo -e "${CYAN}Статус сервисов:${NC}"
    for service in postgresql redis-server asterisk gochs-api gochs-worker gochs-scheduler nginx; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $service"
        else
            echo -e "  ${RED}✗${NC} $service"
        fi
    done
    
    echo ""
    echo -e "${CYAN}Доступ к системе:${NC}"
    echo "  Web интерфейс: http://$DOMAIN_OR_IP"
    echo "  API документация: http://$DOMAIN_OR_IP/docs"
    echo ""
    echo -e "${CYAN}Учетные данные:${NC}"
    echo "  Файл с паролями: /root/.gochs_credentials"
    echo ""
    echo -e "${CYAN}Управление:${NC}"
    echo "  Просмотр логов: journalctl -u gochs-api -f"
    echo "  Перезапуск API: systemctl restart gochs-api"
    echo "  Статус всех сервисов: systemctl status gochs-*"
    echo ""
    echo -e "${YELLOW}ВАЖНО: Измените пароль администратора при первом входе!${NC}"
    echo "  Логин: admin"
    echo "  Пароль: Admin123!"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Главное меню
show_menu() {
    clear
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║         ГО-ЧС ИНФОРМИРОВАНИЕ - УСТАНОВКА v$VERSION              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "1. Полная установка (все модули)"
    echo "2. Выборочная установка модулей"
    echo "3. Проверить систему перед установкой"
    echo "4. Показать статус установленных модулей"
    echo "5. Перезапустить сервисы"
    echo "6. Просмотреть логи"
    echo "7. Выход"
    echo ""
    read -p "Ваш выбор (1-7): " choice
}

# Проверка системы перед установкой
pre_install_check() {
    log_step "ПРОВЕРКА СИСТЕМЫ ПЕРЕД УСТАНОВКОЙ"
    
    local errors=0
    
    echo ""
    echo "► Проверка прав root..."
    if [[ $EUID -eq 0 ]]; then
        echo "  ✓ OK"
    else
        echo "  ✗ Требуются права root"
        ((errors++))
    fi
    
    echo "► Проверка ОС..."
    if [[ -f /etc/debian_version ]]; then
        echo "  ✓ Debian $(cat /etc/debian_version)"
    else
        echo "  ✗ Требуется Debian/Ubuntu"
        ((errors++))
    fi
    
    echo "► Проверка ресурсов..."
    cpu=$(nproc)
    ram=$(free -g | awk '/^Mem:/{print $2}')
    echo "  CPU: $cpu ядер $([ $cpu -ge 4 ] && echo '✓' || echo '⚠ (рекомендуется 4+)')"
    echo "  RAM: ${ram}GB $([ $ram -ge 8 ] && echo '✓' || echo '⚠ (рекомендуется 8GB+)')"
    
    echo "► Проверка сети..."
    if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
        echo "  ✓ Интернет доступен"
    else
        echo "  ⚠ Интернет недоступен"
    fi
    
    echo "► Свободное место в /opt..."
    df -h /opt 2>/dev/null | tail -1 | awk '{print "  " $4 " свободно"}'
    
    echo ""
    if [[ $errors -eq 0 ]]; then
        log_info "✅ Система готова к установке"
    else
        log_warn "⚠ Обнаружены проблемы, установка может не выполниться"
    fi
}

# Выборочная установка
selective_install() {
    echo ""
    echo "Доступные модули:"
    echo "  1. system    - Системные зависимости"
    echo "  2. python    - Python окружение"
    echo "  3. db        - PostgreSQL"
    echo "  4. redis     - Redis"
    echo "  5. asterisk  - Asterisk"
    echo "  6. backend   - FastAPI Backend"
    echo "  7. frontend  - React Frontend"
    echo "  8. nginx     - Nginx"
    echo ""
    read -p "Введите номера модулей через пробел (например: 1 3 5): " modules
    
    declare -A module_map=(
        [1]="01-system"
        [2]="02-python"
        [3]="03-db"
        [4]="04-redis"
        [5]="05-asterisk"
        [6]="06-backend"
        [7]="07-frontend"
        [8]="08-nginx"
    )
    
    for num in $modules; do
        if [[ -n "${module_map[$num]}" ]]; then
            install_module "${module_map[$num]}"
        fi
    done
}

# Показать статус модулей
show_modules_status() {
    log_step "СТАТУС УСТАНОВЛЕННЫХ МОДУЛЕЙ"
    
    declare -A modules=(
        ["01-system"]="Системные зависимости"
        ["02-python"]="Python окружение"
        ["03-db"]="PostgreSQL"
        ["04-redis"]="Redis"
        ["05-asterisk"]="Asterisk"
        ["06-backend"]="FastAPI Backend"
        ["07-frontend"]="React Frontend"
        ["08-nginx"]="Nginx"
    )
    
    for module in "${!modules[@]}"; do
        if grep -q "^$module:" "$INSTALL_DIR/.modules_state" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} ${modules[$module]}"
        else
            echo -e "  ${RED}✗${NC} ${modules[$module]}"
        fi
    done
    
    echo ""
    echo "Статус сервисов:"
    for service in postgresql redis-server asterisk gochs-api gochs-worker gochs-scheduler nginx; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $service"
        else
            echo -e "  ${RED}✗${NC} $service"
        fi
    done
}

# Перезапуск сервисов
restart_services() {
    log_step "ПЕРЕЗАПУСК СЕРВИСОВ"
    
    for service in postgresql redis-server asterisk gochs-api gochs-worker gochs-scheduler nginx; do
        if systemctl is-enabled $service &>/dev/null; then
            log_info "Перезапуск $service..."
            systemctl restart $service
        fi
    done
    
    log_info "Сервисы перезапущены"
}

# Просмотр логов
view_logs() {
    echo ""
    echo "Выберите лог для просмотра:"
    echo "  1. API (gochs-api)"
    echo "  2. Worker (gochs-worker)"
    echo "  3. Asterisk"
    echo "  4. Nginx error"
    echo "  5. Установка"
    echo ""
    read -p "Выбор (1-5): " log_choice
    
    case $log_choice in
        1) journalctl -u gochs-api -f ;;
        2) journalctl -u gochs-worker -f ;;
        3) tail -f /var/log/asterisk/full ;;
        4) tail -f /var/log/nginx/error.log ;;
        5) tail -f "$LOG_FILE" ;;
        *) echo "Неверный выбор" ;;
    esac
}

################################################################################
# ГЛАВНАЯ ФУНКЦИЯ
################################################################################

main() {
    # Инициализация
    ensure_basic_deps
    ensure_directories
    
    # Основной цикл
    while true; do
        show_menu
        
        case $choice in
            1)
                check_internet
                get_user_input
                full_install
                ;;
            2)
                get_user_input
                selective_install
                ;;
            3)
                pre_install_check
                ;;
            4)
                show_modules_status
                ;;
            5)
                restart_services
                ;;
            6)
                view_logs
                ;;
            7)
                echo "Выход"
                exit 0
                ;;
            *)
                echo "Неверный выбор"
                ;;
        esac
        
        echo ""
        read -p "Нажмите Enter для продолжения..."
    done
}

# Запуск
main "$@"
