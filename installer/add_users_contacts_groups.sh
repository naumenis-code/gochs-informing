#!/bin/bash

################################################################################
# Скрипт добавления страниц Пользователей, Контактов, Групп и Плейбуков
# Аналог add_audit_settings.sh
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="${SCRIPT_DIR}/modules"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Добавление Пользователей, Контактов, Групп и Плейбуков${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}ОШИБКА: Скрипт должен запускаться от root!${NC}"
    echo "Выполните: sudo bash add_users_contacts_groups.sh"
    exit 1
fi

# Проверка существования установки
if [[ ! -d "/opt/gochs-informing" ]]; then
    echo -e "${RED}ОШИБКА: Система ГО-ЧС не установлена!${NC}"
    echo "Сначала выполните полную установку через install.sh"
    exit 1
fi

# Проверка наличия модуля
MODULE_FILE="${MODULES_DIR}/10-users-contacts-groups-playbooks.sh"
if [[ ! -f "$MODULE_FILE" ]]; then
    echo -e "${RED}ОШИБКА: Файл модуля 10-users-contacts-groups-playbooks.sh не найден!${NC}"
    echo "Путь: ${MODULE_FILE}"
    echo "Убедитесь, что файл находится в папке modules/"
    exit 1
fi

# Проверка, не установлен ли уже модуль
if grep -q "10-users-contacts-groups-playbooks" "/opt/gochs-informing/.modules_state" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Модуль уже отмечен как установленный.${NC}"
    echo ""
    echo -e "  ${CYAN}Что вы хотите сделать?${NC}"
    echo -e "  ${GREEN}1${NC}. Переустановить модуль"
    echo -e "  ${GREEN}2${NC}. Выйти без изменений"
    echo ""
    read -p "  ▶ Ваш выбор (1-2) [2]: " reinstall_choice
    reinstall_choice="${reinstall_choice:-2}"
    
    if [[ "$reinstall_choice" != "1" ]]; then
        echo -e "${YELLOW}Выход. Модуль уже установлен.${NC}"
        exit 0
    fi
    
    # Удаляем старую запись
    sed -i '/10-users-contacts-groups-playbooks/d' "/opt/gochs-informing/.modules_state"
    echo -e "${YELLOW}Старая запись удалена. Будет выполнена переустановка.${NC}"
fi

echo ""
echo -e "${CYAN}Этот модуль добавит в систему:${NC}"
echo ""
echo -e "  ${GREEN}Backend (Python/FastAPI):${NC}"
echo "    ✅ Модели: Contact, ContactGroup, Tag, Playbook"
echo "    ✅ Схемы: User, Contact, Group, Playbook, Common"
echo "    ✅ Сервисы: UserService, ContactService, GroupService, PlaybookService"
echo "    ✅ API эндпоинты: /users, /contacts, /groups, /playbooks"
echo ""
echo -e "  ${GREEN}Frontend (React):${NC}"
echo "    ✅ Страницы: Пользователи, Контакты, Группы, Плейбуки"
echo "    ✅ Сервисы: userService, contactService, groupService, playbookService"
echo "    ✅ Компоненты: AudioPlayer, ImportModal"
echo ""
echo -e "  ${GREEN}Функционал согласно ТЗ:${NC}"
echo "    ✅ Раздел 10: Контактная база (500+ контактов, группы, теги, импорт CSV/XLSX)"
echo "    ✅ Раздел 19: Playbook входящих звонков (TTS, загрузка аудио, шаблоны)"
echo "    ✅ Раздел 22: Роли пользователей (администратор, оператор, наблюдатель)"
echo ""

read -p "  ▶ Продолжить установку? (Y/n): " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}Установка отменена пользователем${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}[INFO]${NC} Запуск установки модуля..."
echo ""

# Запуск установки модуля
if bash "$MODULE_FILE" install; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}     ✓ Модуль успешно добавлен!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Теперь доступны новые разделы в веб-интерфейсе:"
    echo ""
    echo -e "  ${BLUE}▶ Пользователи:${NC}  /users"
    echo -e "  ${BLUE}▶ Контакты:${NC}      /contacts"
    echo -e "  ${BLUE}▶ Группы:${NC}        /groups"
    echo -e "  ${BLUE}▶ Плейбуки:${NC}     /playbooks"
    echo ""
    echo -e "  ${BLUE}▶ API документация:${NC} /docs"
    echo ""
    echo -e "${CYAN}Учетные данные для входа:${NC}"
    echo -e "  Логин:  ${WHITE}admin${NC}"
    echo -e "  Пароль: ${WHITE}Admin123!${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Рекомендуется изменить пароль администратора при первом входе.${NC}"
    echo ""
    echo -e "Для проверки статуса выполните:"
    echo -e "  ${GREEN}bash ${MODULE_FILE} status${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}     ✗ Ошибка при установке модуля${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Проверьте логи и попробуйте:"
    echo -e "  ${YELLOW}bash ${MODULE_FILE} status${NC}"
    echo ""
    echo -e "Если проблема сохраняется, выполните установку модулей по отдельности:"
    echo -e "  ${YELLOW}bash install.sh${NC} (выбрать пункт 2 - Выборочная установка)"
    echo ""
    exit 1
fi
