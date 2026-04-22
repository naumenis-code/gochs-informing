#!/bin/bash

################################################################################
# Скрипт добавления модуля Аудита и Настроек в существующую установку
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="${SCRIPT_DIR}/modules"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     Добавление модуля Аудита и Настроек в ГО-ЧС${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}ОШИБКА: Скрипт должен запускаться от root!${NC}"
    echo "Выполните: sudo bash add_audit_settings.sh"
    exit 1
fi

# Проверка существования установки
if [[ ! -d "/opt/gochs-informing" ]]; then
    echo -e "${RED}ОШИБКА: Система ГО-ЧС не установлена!${NC}"
    echo "Сначала выполните полную установку через install.sh"
    exit 1
fi

# Проверка наличия модуля
if [[ ! -f "${MODULES_DIR}/09-web-audit-settings.sh" ]]; then
    echo -e "${RED}ОШИБКА: Файл модуля 09-web-audit-settings.sh не найден!${NC}"
    echo "Убедитесь, что файл находится в папке modules/"
    exit 1
fi

# Проверка, не установлен ли уже модуль
if grep -q "09-web-audit-settings" "/opt/gochs-informing/.modules_state" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Модуль уже отмечен как установленный.${NC}"
    read -p "Переустановить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    # Удаляем старую запись
    sed -i '/09-web-audit-settings/d' "/opt/gochs-informing/.modules_state"
fi

# Запуск установки модуля
echo -e "${GREEN}[INFO]${NC} Запуск установки модуля..."
echo ""

if bash "${MODULES_DIR}/09-web-audit-settings.sh" install; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}     ✓ Модуль успешно добавлен!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Теперь доступны новые разделы в веб-интерфейсе:"
    echo -e "  ${BLUE}▶ Настройки:${NC} /settings"
    echo -e "  ${BLUE}▶ Аудит:${NC} /audit"
    echo ""
    echo -e "Для проверки статуса выполните:"
    echo -e "  ${YELLOW}bash ${MODULES_DIR}/09-web-audit-settings.sh status${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}     ✗ Ошибка при установке модуля${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Проверьте логи и попробуйте:"
    echo "  bash ${MODULES_DIR}/09-web-audit-settings.sh status"
    exit 1
fi
