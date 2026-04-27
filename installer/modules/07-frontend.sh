#!/bin/bash
################################################################################
# Модуль: 07-frontend.sh (ИСПРАВЛЕННЫЙ - копирует готовые файлы)
################################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${SCRIPT_DIR}/utils/common.sh" 2>/dev/null || {
    log_info() { echo -e "\033[0;32m[INFO]\033[0m $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }
    log_step() { echo -e "\n\033[0;34m═══ $* ═══\033[0m"; }
    ensure_dir() { mkdir -p "$1"; }
}

MODULE_NAME="07-frontend"
INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
INSTALLER_FRONTEND="${SCRIPT_DIR}/frontend"
TARGET_FRONTEND="$INSTALL_DIR/frontend"

install() {
    log_step "Установка React фронтенда"
    
    # Node.js
    if ! command -v node &>/dev/null; then
        log_info "Установка Node.js 20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null
        apt-get install -y nodejs
    fi
    log_info "Node.js: $(node --version)"
    
    # Копирование готовых файлов
    log_info "Копирование готовых файлов из installer/frontend/..."
    
    # Конфигурационные файлы
    for f in package.json vite.config.ts tsconfig.json tsconfig.node.json index.html .env; do
        if [ -f "$INSTALLER_FRONTEND/$f" ]; then
            cp "$INSTALLER_FRONTEND/$f" "$TARGET_FRONTEND/$f"
            log_info "  ✓ $f"
        fi
    done
    
    # Исходники
    ensure_dir "$TARGET_FRONTEND/src"
    
    # Копируем файлы src
    if [ -f "$INSTALLER_FRONTEND/src/App.tsx" ]; then
        cp "$INSTALLER_FRONTEND/src/App.tsx" "$TARGET_FRONTEND/src/App.tsx"
        log_info "  ✓ App.tsx"
    fi
    if [ -f "$INSTALLER_FRONTEND/src/main.tsx" ]; then
        cp "$INSTALLER_FRONTEND/src/main.tsx" "$TARGET_FRONTEND/src/main.tsx"
        log_info "  ✓ main.tsx"
    fi
    
    # Страницы
    ensure_dir "$TARGET_FRONTEND/src/pages"
    for page in Dashboard Login Contacts Groups Campaigns Scenarios Inbound Playbooks Users Settings Audit; do
        if [ -f "$INSTALLER_FRONTEND/src/pages/${page}.tsx" ]; then
            cp "$INSTALLER_FRONTEND/src/pages/${page}.tsx" "$TARGET_FRONTEND/src/pages/${page}.tsx"
            log_info "  ✓ pages/${page}.tsx"
        fi
    done
    
    # Сервисы
    ensure_dir "$TARGET_FRONTEND/src/services"
    for svc in api authService contactService groupService campaignService scenarioService settingsService auditService monitoringService playbookService userService; do
        if [ -f "$INSTALLER_FRONTEND/src/services/${svc}.ts" ]; then
            cp "$INSTALLER_FRONTEND/src/services/${svc}.ts" "$TARGET_FRONTEND/src/services/${svc}.ts"
            log_info "  ✓ services/${svc}.ts"
        fi
    done
    
    # Компоненты
    for comp in Layout/index AudioPlayer ImportModal; do
        if [ -f "$INSTALLER_FRONTEND/src/components/${comp}.tsx" ]; then
            ensure_dir "$(dirname "$TARGET_FRONTEND/src/components/${comp}.tsx")"
            cp "$INSTALLER_FRONTEND/src/components/${comp}.tsx" "$TARGET_FRONTEND/src/components/${comp}.tsx"
            log_info "  ✓ components/${comp}.tsx"
        fi
    done
    
    # Хуки, store, context, styles
    for dir in hooks store/slices context styles; do
        if [ -d "$INSTALLER_FRONTEND/src/$dir" ]; then
            ensure_dir "$TARGET_FRONTEND/src/$dir"
            cp -r "$INSTALLER_FRONTEND/src/$dir/"* "$TARGET_FRONTEND/src/$dir/" 2>/dev/null
            log_info "  ✓ $dir/"
        fi
    done
    
    chown -R gochs:gochs "$TARGET_FRONTEND/src" 2>/dev/null || true
    
    # Сборка
    log_info "Сборка React приложения..."
    cd "$TARGET_FRONTEND"
    npm install --legacy-peer-deps 2>&1 | tail -3
    npm run build 2>&1 | tail -5
    
    if [ -d "build" ]; then
        chown -R www-data:www-data build
        log_info "✓ Фронтенд собран: $(du -sh build | cut -f1)"
    else
        log_error "✗ Сборка не удалась"
    fi
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль $MODULE_NAME установлен"
}

uninstall() {
    rm -rf "$TARGET_FRONTEND"
    log_info "Модуль $MODULE_NAME удален"
}

case "${1:-}" in
    install) install ;;
    uninstall) uninstall ;;
    *) echo "Использование: $0 {install|uninstall}" ;;
esac
