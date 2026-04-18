#!/bin/bash

################################################################################
# Применение конфигурации Asterisk
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SRC="${SCRIPT_DIR}/../config/asterisk"
CONFIG_DST="/etc/asterisk"

# Загрузка переменных
source "${SCRIPT_DIR}/../config/config.env"

# Замена переменных в конфигах
apply_template() {
    local src="$1"
    local dst="$2"
    
    sed -e "s|{{DOMAIN_OR_IP}}|${DOMAIN_OR_IP}|g" \
        -e "s|{{FREEPBX_HOST}}|${FREEPBX_HOST}|g" \
        -e "s|{{FREEPBX_PORT}}|${FREEPBX_PORT}|g" \
        -e "s|{{FREEPBX_EXTENSION}}|${FREEPBX_EXTENSION}|g" \
        -e "s|{{FREEPBX_USERNAME}}|${FREEPBX_USERNAME}|g" \
        -e "s|{{FREEPBX_PASSWORD}}|${FREEPBX_PASSWORD}|g" \
        -e "s|{{ASTERISK_AMI_PASSWORD}}|${ASTERISK_AMI_PASSWORD}|g" \
        -e "s|{{ASTERISK_ARI_PASSWORD}}|${ASTERISK_ARI_PASSWORD}|g" \
        -e "s|{{ASTERISK_ADMIN_PASSWORD}}|${ASTERISK_ADMIN_PASSWORD}|g" \
        -e "s|{{ASTERISK_MONITOR_PASSWORD}}|${ASTERISK_MONITOR_PASSWORD}|g" \
        "$src" > "$dst"
}

# Копирование конфигураций
echo "Применение конфигурации Asterisk..."

# Создание резервной копии
if [[ -d "$CONFIG_DST" ]]; then
    BACKUP_DIR="${CONFIG_DST}.backup.$(date +%Y%m%d_%H%M%S)"
    cp -r "$CONFIG_DST" "$BACKUP_DIR"
    echo "Резервная копия создана: $BACKUP_DIR"
fi

# Применение шаблонов
for file in "$CONFIG_SRC"/*.conf; do
    filename=$(basename "$file")
    if [[ "$filename" == "pjsip.conf" ]] || [[ "$filename" == "manager.conf" ]] || [[ "$filename" == "http.conf" ]]; then
        apply_template "$file" "${CONFIG_DST}/${filename}"
        echo "Применен шаблон: $filename"
    else
        cp "$file" "${CONFIG_DST}/${filename
