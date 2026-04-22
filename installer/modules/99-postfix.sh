#!/bin/bash

################################################################################
# Модуль: 99-postfix.sh
# Назначение: Финальный перезапуск сервисов
# Версия: 1.0.0
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

if ! type log_info &>/dev/null; then
    GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}\n${BLUE}  $*${NC}\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"; }
    mark_module_installed() {
        local m="$1"
        local f="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"
        mkdir -p "$(dirname "$f")"
        echo "$m:$(date +%s)" >> "$f"
    }
fi

MODULE_NAME="99-postfix"
MODULE_DESCRIPTION="Финальный перезапуск сервисов"

install() {
    log_step "Финальный перезапуск сервисов"
    
    log_info "Перезапуск сервисов..."
    systemctl restart gochs-api 2>/dev/null || true
    systemctl restart gochs-worker 2>/dev/null || true
    systemctl restart gochs-scheduler 2>/dev/null || true
    systemctl restart nginx 2>/dev/null || true
    systemctl restart asterisk 2>/dev/null || true
    
    sleep 5
    
    log_info "Статус сервисов:"
    for service in postgresql redis-server asterisk gochs-api gochs-worker gochs-scheduler nginx; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            log_info "  ✓ $service"
        else
            log_error "  ✗ $service"
        fi
    done
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль $MODULE_NAME успешно установлен"
    
    return 0
}

uninstall() { return 0; }
check_status() { return 0; }

case "${1:-}" in
    install) install ;;
    uninstall) uninstall ;;
    status) check_status ;;
    *) echo "Использование: $0 {install|uninstall|status}" ;;
esac
