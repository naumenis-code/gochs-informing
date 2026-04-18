#!/bin/bash

################################################################################
# ГО-ЧС Информирование - Главный установочный скрипт
# Модульная установка системы
################################################################################

set -e

# Определение директорий
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="${SCRIPT_DIR}/modules"
CONFIG_DIR="${SCRIPT_DIR}/config"
UTILS_DIR="${SCRIPT_DIR}/utils"
INSTALL_DIR="/opt/gochs-informing"

# Загрузка общих функций
source "${UTILS_DIR}/common.sh"
source "${UTILS_DIR}/validators.sh"

# Версия системы
VERSION="1.0.0"

################################################################################
# Функции управления установкой
################################################################################

show_banner() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║      _____   ____       _____  _____         _____                ║
║     / ____| / __ \     / ____|/ ____|       |_   _|              ║
║    | |  __ | |  | |   | |     | (___          | |                ║
║    | | |_ || |  | |   | |      \___ \         | |                ║
║    | |__| || |__| |   | |____  ____) |       _| |_               ║
║     \_____| \____/     \_____||_____/       |_____|              ║
║                                                                   ║
║    ____                  __ _           _                         ║
║   / __ \                / _(_)         | |                        ║
║  | |  | |_ __   ___ _ _| |_ _ _ __   __| | ___ _ __               ║
║  | |  | | '_ \ / _ \ '_ \  _| | '_ \ / _` |/ _ \ '__|              ║
║  | |__| | |_) |  __/ | | | | | | | | (_| |  __/ |                 ║
║   \____/| .__/ \___|_| |_|_| |_| |_|\__,_|\___|_|                 ║
║         | |                                                       ║
║         |_|                                                       ║
║                                                                   ║
║         Система ГО-ЧС информирования и оповещения                 ║
║                    Версия ${VERSION}                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

show_menu() {
    echo -e "\n${GREEN}Выберите действие:${NC}"
    echo "1. Полная установка (все модули)"
    echo "2. Выборочная установка модулей"
    echo "3. Проверить установленные модули"
    echo "4. Удалить систему"
    echo "5. Показать конфигурацию"
    echo "6. Выход"
    echo
    read -p "Ваш выбор (1-6): " choice
}

show_modules_menu() {
    echo -e "\n${GREEN}Доступные модули:${NC}"
    echo "1. system     - Системные зависимости"
    echo "2. python     - Python окружение"
    echo "3. db         - PostgreSQL"
    echo "4. redis      - Redis"
    echo "5. asterisk   - Asterisk"
    echo "6. backend    - FastAPI Backend"
    echo "7. frontend   - React Frontend"
    echo "8. nginx      - Nginx"
    echo "9. Все модули"
    echo "0. Назад"
    echo
    read -p "Введите номера модулей через пробел (например: 1 3 5): " modules_choice
}

install_module() {
    local module=$1
    local module_script="${MODULES_DIR}/${module}.sh"
    
    if [[ ! -f "$module_script" ]]; then
        log_error "Модуль ${module} не найден!"
        return 1
    fi
    
    log_step "Установка модуля: ${module}"
    
    # Проверка зависимостей модуля
    if ! check_module_dependencies "$module"; then
        log_error "Зависимости для модуля ${module} не удовлетворены!"
        return 1
    fi
    
    # Запуск установки модуля
    if bash "$module_script" "install"; then
        log_info "Модуль ${module} успешно установлен"
        mark_module_installed "$module"
        return 0
    else
        log_error "Ошибка при установке модуля ${module}"
        return 1
    fi
}

uninstall_module() {
    local module=$1
    local module_script="${MODULES_DIR}/${module}.sh"
    
    if [[ ! -f "$module_script" ]]; then
        log_error "Модуль ${module} не найден!"
        return 1
    fi
    
    log_step "Удаление модуля: ${module}"
    
    if bash "$module_script" "uninstall"; then
        log_info "Модуль ${module} успешно удален"
        unmark_module_installed "$module"
        return 0
    else
        log_error "Ошибка при удалении модуля ${module}"
        return 1
    fi
}

check_module_dependencies() {
    local module=$1
    
    case $module in
        "02-python")
            check_module_installed "01-system" || return 1
            ;;
        "03-db"|"04-redis"|"05-asterisk")
            check_module_installed "01-system" || return 1
            ;;
        "06-backend")
            check_module_installed "02-python" || return 1
            check_module_installed "03-db" || return 1
            check_module_installed "04-redis" || return 1
            ;;
        "07-frontend")
            check_module_installed "01-system" || return 1
            ;;
        "08-nginx")
            check_module_installed "06-backend" || return 1
            check_module_installed "07-frontend" || return 1
            ;;
    esac
    
    return 0
}

full_install() {
    log_step "Запуск полной установки системы"
    
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
    
    for module in "${modules[@]}"; do
        if ! install_module "$module"; then
            log_error "Установка прервана на модуле ${module}"
            return 1
        fi
    done
    
    log_info "Полная установка завершена успешно!"
    show_post_install_info
}

selective_install() {
    show_modules_menu
    read -p "Введите номера модулей через пробел: " -a selected
    
    for num in "${selected[@]}"; do
        case $num in
            1) install_module "01-system" ;;
            2) install_module "02-python" ;;
            3) install_module "03-db" ;;
            4) install_module "04-redis" ;;
            5) install_module "05-asterisk" ;;
            6) install_module "06-backend" ;;
            7) install_module "07-frontend" ;;
            8) install_module "08-nginx" ;;
            9) full_install; break ;;
            0) return ;;
            *) log_warn "Неизвестный номер модуля: $num" ;;
        esac
    done
}

check_installed() {
    log_step "Проверка установленных модулей"
    
    for i in {01..08}; do
        if check_module_installed "$i-*"; then
            log_info "Модуль $i: ${GREEN}УСТАНОВЛЕН${NC}"
        else
            log_info "Модуль $i: ${RED}НЕ УСТАНОВЛЕН${NC}"
        fi
    done
}

show_config() {
    log_step "Текущая конфигурация"
    
    if [[ -f "${CONFIG_DIR}/config.env" ]]; then
        cat "${CONFIG_DIR}/config.env"
    else
        log_warn "Файл конфигурации не найден"
    fi
}

show_post_install_info() {
    echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}              УСТАНОВКА УСПЕШНО ЗАВЕРШЕНА!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo
    echo -e "${YELLOW}Важная информация:${NC}"
    echo "───────────────────────────────────────────────────────────"
    
    if [[ -f "/root/.gochs_credentials" ]]; then
        cat "/root/.gochs_credentials"
    fi
    
    echo
    echo -e "${YELLOW}Управление службами:${NC}"
    echo "  systemctl status gochs-*"
    echo "  systemctl start gochs-api"
    echo "  systemctl stop gochs-worker"
    echo
    echo -e "${YELLOW}Логи:${NC}"
    echo "  journalctl -u gochs-api -f"
    echo "  tail -f /opt/gochs-informing/logs/*.log"
    echo
    echo -e "${YELLOW}Web интерфейс:${NC}"
    echo "  https://${DOMAIN_OR_IP}"
    echo
    echo "═══════════════════════════════════════════════════════════"
}

uninstall_system() {
    log_warn "ВНИМАНИЕ! Это действие удалит всю систему ГО-ЧС!"
    read -p "Вы уверены? Для подтверждения введите 'DELETE': " confirmation
    
    if [[ "$confirmation" != "DELETE" ]]; then
        log_info "Удаление отменено"
        return
    fi
    
    log_step "Удаление системы"
    
    # Остановка всех служб
    systemctl stop gochs-* 2>/dev/null || true
    systemctl disable gochs-* 2>/dev/null || true
    
    # Удаление модулей в обратном порядке
    local modules=(
        "08-nginx"
        "07-frontend"
        "06-backend"
        "05-asterisk"
        "04-redis"
        "03-db"
        "02-python"
        "01-system"
    )
    
    for module in "${modules[@]}"; do
        if check_module_installed "$module"; then
            uninstall_module "$module"
        fi
    done
    
    # Удаление директории установки
    rm -rf "$INSTALL_DIR"
    rm -f "/root/.gochs_credentials"
    rm -f "/var/log/gochs-install.log"
    
    log_info "Система полностью удалена"
}

################################################################################
# Главная функция
################################################################################

main() {
    # Проверка прав
    if [[ $EUID -ne 0 ]]; then
        echo "Этот скрипт должен запускаться от root!"
        exit 1
    fi
    
    # Инициализация
    show_banner
    init_logging
    load_config
    
    # Главное меню
    while true; do
        show_menu
        
        case $choice in
            1)
                full_install
                ;;
            2)
                selective_install
                ;;
            3)
                check_installed
                ;;
            4)
                uninstall_system
                ;;
            5)
                show_config
                ;;
            6)
                echo "Выход"
                exit 0
                ;;
            *)
                log_error "Неверный выбор"
                ;;
        esac
        
        echo
        read -p "Нажмите Enter для продолжения..."
    done
}

# Запуск
main "$@"
