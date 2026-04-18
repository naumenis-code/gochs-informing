#!/bin/bash

################################################################################
# Валидация глобальных переменных Asterisk
################################################################################

CONFIG_FILE="/etc/asterisk/gochs/global.conf"
ERRORS=0
WARNINGS=0

echo "====================================="
echo "Проверка глобальных переменных GO-CHS"
echo "====================================="

# Проверка существования файла
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Файл $CONFIG_FILE не найден!"
    exit 1
fi

# Функция проверки переменной
check_variable() {
    local var_name="$1"
    local var_value="$2"
    local required="$3"
    
    if [[ -z "$var_value" ]]; then
        if [[ "$required" == "yes" ]]; then
            echo "❌ $var_name: не задана (обязательная)"
            ((ERRORS++))
        else
            echo "⚠️  $var_name: не задана (опциональная)"
            ((WARNINGS++))
        fi
    else
        echo "✅ $var_name: $var_value"
    fi
}

# Функция проверки пути
check_path() {
    local path="$1"
    local create="$2"
    
    if [[ ! -d "$path" ]]; then
        if [[ "$create" == "yes" ]]; then
            echo "📁 Создание директории: $path"
            mkdir -p "$path"
            chown asterisk:asterisk "$path"
        else
            echo "⚠️  Директория не существует: $path"
            ((WARNINGS++))
        fi
    else
        echo "✅ Директория существует: $path"
    fi
}

echo ""
echo "Проверка обязательных переменных:"
echo "--------------------------------"

# Извлечение значений переменных из конфига
extract_var() {
    grep "^$1 = " "$CONFIG_FILE" | cut -d'=' -f2- | xargs
}

# Проверка системных путей
GOCHS_BASE=$(extract_var "GOCHS_BASE")
check_variable "GOCHS_BASE" "$GOCHS_BASE" "yes"
check_path "$GOCHS_BASE" "no"

# Проверка путей для записей
GOCHS_RECORDINGS=$(extract_var "GOCHS_RECORDINGS")
check_path "$GOCHS_RECORDINGS" "yes"
check_path "${GOCHS_RECORDINGS}/inbound" "yes"
check_path "${GOCHS_RECORDINGS}/outbound" "yes"

# Проверка путей для плейбуков
GOCHS_PLAYBOOKS=$(extract_var "GOCHS_PLAYBOOKS")
check_path "$GOCHS_PLAYBOOKS" "yes"

# Проверка путей для голосовых файлов
GOCHS_VOICE=$(extract_var "GOCHS_VOICE")
check_path "$GOCHS_VOICE" "yes"

# Проверка таймаутов
echo ""
echo "Проверка таймаутов:"
echo "------------------"
DIAL_TIMEOUT=$(extract_var "DIAL_TIMEOUT")
check_variable "DIAL_TIMEOUT" "$DIAL_TIMEOUT" "yes"
if [[ -n "$DIAL_TIMEOUT" ]] && [[ "$DIAL_TIMEOUT" -lt 10 ]] || [[ "$DIAL_TIMEOUT" -gt 120 ]]; then
    echo "⚠️  DIAL_TIMEOUT = $DIAL_TIMEOUT (рекомендуется 30-60)"
    ((WARNINGS++))
fi

ANSWER_TIMEOUT=$(extract_var "ANSWER_TIMEOUT")
check_variable "ANSWER_TIMEOUT" "$ANSWER_TIMEOUT" "yes"

# Проверка лимитов
echo ""
echo "Проверка лимитов каналов:"
echo "------------------------"
MAX_CONCURRENT_CALLS=$(extract_var "MAX_CONCURRENT_CALLS")
check_variable "MAX_CONCURRENT_CALLS" "$MAX_CONCURRENT_CALLS" "yes"

# Проверка Redis
echo ""
echo "Проверка Redis:"
echo "---------------"
REDIS_HOST=$(extract_var "REDIS_HOST")
REDIS_PORT=$(extract_var "REDIS_PORT")
check_variable "REDIS_HOST" "$REDIS_HOST" "yes"
check_variable "REDIS_PORT" "$REDIS_PORT" "yes"

if [[ -n "$REDIS_HOST" ]] && [[ -n "$REDIS_PORT" ]]; then
    if nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; then
        echo "✅ Redis доступен: $REDIS_HOST:$REDIS_PORT"
    else
        echo "❌ Redis недоступен: $REDIS_HOST:$REDIS_PORT"
        ((ERRORS++))
    fi
fi

# Проверка FreePBX
echo ""
echo "Проверка FreePBX:"
echo "-----------------"
FREEPBX_ENABLED=$(extract_var "FREEPBX_ENABLED")
if [[ "$FREEPBX_ENABLED" == "yes" ]]; then
    FREEPBX_HOST=$(extract_var "FREEPBX_HOST")
    FREEPBX_PORT=$(extract_var "FREEPBX_PORT")
    check_variable "FREEPBX_HOST" "$FREEPBX_HOST" "yes"
    check_variable "FREEPBX_PORT" "$FREEPBX_PORT" "yes"
    
    if [[ -n "$FREEPBX_HOST" ]] && [[ -n "$FREEPBX_PORT" ]]; then
        if nc -z "$FREEPBX_HOST" "$FREEPBX_PORT" 2>/dev/null; then
            echo "✅ FreePBX доступен: $FREEPBX_HOST:$FREEPBX_PORT"
        else
            echo "⚠️  FreePBX недоступен: $FREEPBX_HOST:$FREEPBX_PORT"
            ((WARNINGS++))
        fi
    fi
fi

# Проверка API
echo ""
echo "Проверка API:"
echo "-------------"
API_URL=$(extract_var "API_URL")
check_variable "API_URL" "$API_URL" "yes"

if [[ -n "$API_URL" ]]; then
    if curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" | grep -q "200"; then
        echo "✅ API доступен: $API_URL"
    else
        echo "⚠️  API недоступен: $API_URL"
        ((WARNINGS++))
    fi
fi

# Проверка TTS/STT
echo ""
echo "Проверка TTS/STT:"
echo "-----------------"
TTS_ENABLED=$(extract_var "TTS_ENABLED")
STT_ENABLED=$(extract_var "STT_ENABLED")
check_variable "TTS_ENABLED" "$TTS_ENABLED" "no"
check_variable "STT_ENABLED" "$STT_ENABLED" "no"

# Итоги
echo ""
echo "====================================="
echo "РЕЗУЛЬТАТЫ ПРОВЕРКИ"
echo "====================================="
echo "Ошибок: $ERRORS"
echo "Предупреждений: $WARNINGS"
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo "❌ Обнаружены критические ошибки!"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo "⚠️  Проверка завершена с предупреждениями"
    exit 0
else
    echo "✅ Все проверки пройдены успешно!"
    exit 0
fi
