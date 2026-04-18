#!/bin/bash

################################################################################
# Утилита управления конфигурацией
################################################################################

CONFIG_FILE="${SCRIPT_DIR}/../config/config.env"

load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        source "$CONFIG_FILE"
        log_info "Конфигурация загружена из $CONFIG_FILE"
    else
        log_error "Файл конфигурации не найден: $CONFIG_FILE"
        return 1
    fi
}

validate_config() {
    local errors=0
    
    log_info "Проверка конфигурации..."
    
    # Проверка обязательных параметров
    [[ -z "$DOMAIN_OR_IP" ]] && { log_error "DOMAIN_OR_IP не задан"; ((errors++)); }
    [[ -z "$POSTGRES_PASSWORD" ]] && { log_error "POSTGRES_PASSWORD не задан"; ((errors++)); }
    [[ -z "$REDIS_PASSWORD" ]] && { log_error "REDIS_PASSWORD не задан"; ((errors++)); }
    
    # Проверка портов
    check_port "$HTTP_PORT" || ((errors++))
    check_port "$API_PORT" || ((errors++))
    
    # Проверка путей
    [[ -d "$INSTALL_DIR" ]] || { log_error "Директория $INSTALL_DIR не существует"; ((errors++)); }
    
    if [[ $errors -eq 0 ]]; then
        log_info "Конфигурация валидна"
        return 0
    else
        log_error "Найдено $errors ошибок в конфигурации"
        return 1
    fi
}

edit_config() {
    local editor="${EDITOR:-vim}"
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Файл конфигурации не найден"
        return 1
    fi
    
    backup_file "$CONFIG_FILE"
    $editor "$CONFIG_FILE"
    
    # Обновление времени модификации
    sed -i "s/CONFIG_LAST_MODIFIED=.*/CONFIG_LAST_MODIFIED=\"$(date '+%Y-%m-%d %H:%M:%S')\"/" "$CONFIG_FILE"
    
    log_info "Конфигурация обновлена"
}

show_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Файл конфигурации не найден"
        return 1
    fi
    
    # Фильтрация паролей
    grep -v "PASSWORD\|SECRET\|KEY" "$CONFIG_FILE" | grep -v "^#"
    
    echo -e "\n${YELLOW}Примечание: Пароли и секретные ключи скрыты${NC}"
}

export_config() {
    local output_file="${1:-/tmp/gochs_config_export.env}"
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Файл конфигурации не найден"
        return 1
    fi
    
    cp "$CONFIG_FILE" "$output_file"
    log_info "Конфигурация экспортирована в $output_file"
}

import_config() {
    local input_file="$1"
    
    if [[ ! -f "$input_file" ]]; then
        log_error "Файл $input_file не найден"
        return 1
    fi
    
    backup_file "$CONFIG_FILE"
    cp "$input_file" "$CONFIG_FILE"
    
    log_info "Конфигурация импортирована из $input_file"
}

reset_config() {
    log_warn "Сброс конфигурации к значениям по умолчанию"
    read -p "Продолжить? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        backup_file "$CONFIG_FILE"
        cp "${CONFIG_FILE}.template" "$CONFIG_FILE" 2>/dev/null || {
            log_error "Шаблон конфигурации не найден"
            return 1
        }
        log_info "Конфигурация сброшена"
    fi
}

# Обработка аргументов
case "${1:-}" in
    load)
        load_config
        ;;
    validate)
        load_config && validate_config
        ;;
    edit)
        edit_config
        ;;
    show)
        show_config
        ;;
    export)
        export_config "${2:-}"
        ;;
    import)
        import_config "${2:-}"
        ;;
    reset)
        reset_config
        ;;
    *)
        echo "Использование: $0 {load|validate|edit|show|export|import|reset}"
        exit 1
        ;;
esac
