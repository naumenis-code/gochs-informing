#!/bin/bash

################################################################################
# Модуль: 04-redis.sh
# Назначение: Установка и настройка Redis для очередей и кэширования
# Версия: 1.0.5 (исправленная полная версия)
################################################################################

# Определение путей
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Загрузка общих функций
if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

# Если common.sh не найден - определяем функции локально
if ! type log_info &>/dev/null; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
    NC='\033[0m'
    
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
    log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { 
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}  $*${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    }
    backup_file() { 
        local file="$1"
        if [[ -f "$file" ]]; then
            cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
            log_info "Создана резервная копия: $file"
        fi
    }
    wait_for_service() { 
        local service="$1"
        local max_wait="${2:-30}"
        local count=0
        while ! systemctl is-active --quiet "$service" 2>/dev/null; do
            sleep 1
            ((count++))
            [[ $count -ge $max_wait ]] && return 1
        done
        return 0
    }
    mark_module_installed() {
        local module="$1"
        local state_file="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"
        mkdir -p "$(dirname "$state_file")"
        echo "$module:$(date +%s)" >> "$state_file"
    }
    ensure_dir() {
        local dir="$1"
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
        fi
    }
    generate_password() {
        openssl rand -base64 16 2>/dev/null | tr -d "=+/" | cut -c1-16 || echo "RedisPass$(date +%s)"
    }
    check_port_free() {
        local port="$1"
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            return 1
        fi
        return 0
    }
fi

MODULE_NAME="04-redis"
MODULE_DESCRIPTION="Redis для очередей задач и кэширования"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Fallback: загрузка из .env
if [[ -z "$REDIS_PASSWORD" ]] && [[ -f "$INSTALL_DIR/.env" ]]; then
    source "$INSTALL_DIR/.env"
fi

# Fallback: парсинг из credentials
if [[ -z "$REDIS_PASSWORD" ]] && [[ -f "/root/.gochs_credentials" ]]; then
    REDIS_PASSWORD=$(grep -A 2 "REDIS:" /root/.gochs_credentials | grep -oP 'Пароль: \K.*')
fi

INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-$(generate_password)}"
REDIS_MAXMEMORY="${REDIS_MAXMEMORY:-512mb}"
GOCHS_USER="${GOCHS_USER:-gochs}"
GOCHS_GROUP="${GOCHS_GROUP:-gochs}"

install() {
    log_step "Установка и настройка Redis"
    
    check_dependencies
    install_redis
    configure_redis
    start_redis
    create_redis_scripts
    setup_monitoring
    
    mark_module_installed "$MODULE_NAME"
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Redis порт: $REDIS_PORT"
    log_info "Пароль сохранен в конфигурации"
    
    return 0
}

check_dependencies() {
    log_info "Проверка зависимостей..."
    
    if [[ $EUID -ne 0 ]]; then
        log_error "Скрипт должен запускаться от root!"
        return 1
    fi
    
    if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
        log_warn "Установка curl..."
        apt-get update -qq 2>/dev/null || true
        apt-get install -y curl 2>/dev/null || true
    fi
    
    # Проверка занятости порта
    if ! check_port_free "$REDIS_PORT"; then
        log_warn "Порт $REDIS_PORT уже используется"
    fi
    
    log_info "Зависимости проверены"
}

install_redis() {
    log_info "Установка Redis..."
    
    if command -v redis-server &> /dev/null; then
        REDIS_VER=$(redis-server --version 2>/dev/null | awk '{print $3}' | cut -d'=' -f2)
        log_info "Redis уже установлен (версия $REDIS_VER)"
        
        local major_version=$(echo "$REDIS_VER" | cut -d. -f1)
        if [[ $major_version -ge 7 ]]; then
            log_info "Версия Redis 7+ - OK"
        else
            log_warn "Установлена версия $REDIS_VER, рекомендуется 7+"
            read -p "Переустановить Redis? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                return 0
            fi
        fi
    fi
    
    # Пробуем официальный репозиторий Redis
    log_info "Добавление официального репозитория Redis..."
    
    local redis_installed=false
    
    if curl -fsSL --connect-timeout 10 https://packages.redis.io/gpg 2>/dev/null | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg 2>/dev/null; then
        echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs 2>/dev/null || echo 'bookworm') main" > /etc/apt/sources.list.d/redis.list
        
        log_info "Официальный репозиторий добавлен, установка Redis..."
        if apt-get update -qq 2>/dev/null && apt-get install -y redis-server redis-tools 2>/dev/null; then
            redis_installed=true
            log_info "✅ Redis установлен из официального репозитория"
        else
            log_warn "Не удалось установить Redis из официального репозитория"
            rm -f /etc/apt/sources.list.d/redis.list
        fi
    else
        log_warn "Не удалось подключиться к официальному репозиторию Redis"
    fi
    
    # Fallback на стандартный репозиторий Debian
    if [[ "$redis_installed" != "true" ]]; then
        log_info "Установка Redis из стандартного репозитория Debian..."
        rm -f /etc/apt/sources.list.d/redis.list 2>/dev/null
        apt-get update -qq
        apt-get install -y redis-server redis-tools || {
            log_error "Не удалось установить Redis"
            return 1
        }
        log_info "✅ Redis установлен из стандартного репозитория Debian"
    fi
}

configure_redis() {
    log_info "Настройка конфигурации Redis..."
    
    local redis_conf="/etc/redis/redis.conf"
    
    # Резервное копирование оригинальной конфигурации
    backup_file "$redis_conf"
    
    # Расчет оптимальных параметров памяти
    local total_ram=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "2048")
    local maxmemory=$((total_ram / 4))
    
    # Создание новой конфигурации с правильным синтаксисом
    cat > "$redis_conf" << EOF
# ================================================
# ГО-ЧС Информирование - Конфигурация Redis
# Версия: 7.2
# ================================================

# Сеть
bind 127.0.0.1
port $REDIS_PORT
protected-mode yes
tcp-backlog 511
timeout 300
tcp-keepalive 300

# Безопасность
requirepass $REDIS_PASSWORD
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Общие настройки
daemonize no
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16
always-show-logo no

# Сохранение данных (RDB)
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Репликация
replica-serve-stale-data yes
replica-read-only yes
repl-diskless-sync no
repl-disable-tcp-nodelay no
replica-priority 100

# Ограничения памяти
maxmemory ${maxmemory}mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# AOF (Append Only File)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite yes
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
aof-use-rdb-preamble yes

# Lua скрипты
lua-time-limit 5000

# Кластер
cluster-enabled no

# Медленный лог
slowlog-log-slower-than 10000
slowlog-max-len 128

# Мониторинг задержек
latency-monitor-threshold 100

# Уведомления о событиях
notify-keyspace-events Ex

# Оптимизация
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
hll-sparse-max-bytes 3000
stream-node-max-bytes 4096
stream-node-max-entries 100
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
hz 10
dynamic-hz yes
aof-rewrite-incremental-fsync yes
rdb-save-incremental-fsync yes

# IO threads
io-threads 4
io-threads-do-reads yes
EOF

    # Создание директорий
    ensure_dir "/var/log/redis"
    ensure_dir "/var/lib/redis"
    ensure_dir "/var/run/redis"
    
    chown redis:redis /var/log/redis 2>/dev/null || true
    chown redis:redis /var/lib/redis 2>/dev/null || true
    chown redis:redis /var/run/redis 2>/dev/null || true
    
    log_info "Конфигурация Redis создана"
}

start_redis() {
    log_info "Запуск Redis..."
    
    # Остановка если запущен
    systemctl stop redis-server 2>/dev/null || true
    
    # Запуск
    systemctl enable redis-server
    systemctl start redis-server
    
    # Ожидание запуска
    if wait_for_service "redis-server" 10; then
        log_info "Redis успешно запущен"
    else
        log_error "Ошибка запуска Redis"
        systemctl status redis-server --no-pager -l
        return 1
    fi
    
    # Проверка подключения
    if redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q "PONG"; then
        log_info "Redis отвечает на PING"
    else
        # Пробуем без пароля (возможно не применился)
        if redis-cli ping 2>/dev/null | grep -q "PONG"; then
            log_warn "Redis работает без пароля"
        else
            log_error "Redis не отвечает"
            return 1
        fi
    fi
}

create_redis_scripts() {
    log_info "Создание скриптов для работы с Redis..."
    
    ensure_dir "$INSTALL_DIR/scripts"
    
    # Скрипт для проверки состояния Redis
    cat > "$INSTALL_DIR/scripts/check_redis.sh" << 'EOF'
#!/bin/bash

REDIS_PASS="${REDIS_PASSWORD:-$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')}"
REDIS_AUTH=""
if [[ -n "$REDIS_PASS" ]]; then
    REDIS_AUTH="-a $REDIS_PASS"
fi

echo "=== Статистика Redis ==="
redis-cli $REDIS_AUTH INFO stats 2>/dev/null | grep -E "total_connections_received|total_commands_processed|instantaneous_ops_per_sec|keyspace_hits|keyspace_misses|evicted_keys|expired_keys"

echo -e "\n=== Память ==="
redis-cli $REDIS_AUTH INFO memory 2>/dev/null | grep -E "used_memory_human|used_memory_peak_human|maxmemory_human|mem_fragmentation_ratio"

echo -e "\n=== Клиенты ==="
redis-cli $REDIS_AUTH INFO clients 2>/dev/null | grep -E "connected_clients|blocked_clients"

echo -e "\n=== Ключи ==="
redis-cli $REDIS_AUTH INFO keyspace 2>/dev/null

echo -e "\n=== Очереди ==="
for queue in celery default high_priority low_priority; do
    count=$(redis-cli $REDIS_AUTH LLEN $queue 2>/dev/null || echo "0")
    echo "  $queue: $count задач"
done
EOF

    # Скрипт для очистки очередей
    cat > "$INSTALL_DIR/scripts/clear_redis_queues.sh" << 'EOF'
#!/bin/bash

REDIS_PASS="${REDIS_PASSWORD:-$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')}"
REDIS_AUTH=""
if [[ -n "$REDIS_PASS" ]]; then
    REDIS_AUTH="-a $REDIS_PASS"
fi

echo "ВНИМАНИЕ: Будут очищены все очереди Redis!"
read -p "Продолжить? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Очистка очередей..."
    redis-cli $REDIS_AUTH DEL celery 2>/dev/null
    redis-cli $REDIS_AUTH DEL default 2>/dev/null
    redis-cli $REDIS_AUTH DEL high_priority 2>/dev/null
    redis-cli $REDIS_AUTH DEL low_priority 2>/dev/null
    echo "Очереди очищены"
fi
EOF

    # Скрипт для резервного копирования Redis
    cat > "$INSTALL_DIR/scripts/backup_redis.sh" << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/gochs-informing/backups/redis"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)

REDIS_PASS="${REDIS_PASSWORD:-$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')}"
REDIS_AUTH=""
if [[ -n "$REDIS_PASS" ]]; then
    REDIS_AUTH="-a $REDIS_PASS"
fi

echo "Запуск сохранения RDB..."
redis-cli $REDIS_AUTH BGSAVE 2>/dev/null

# Ожидание завершения сохранения
for i in {1..30}; do
    if redis-cli $REDIS_AUTH INFO persistence 2>/dev/null | grep -q "rdb_bgsave_in_progress:0"; then
        break
    fi
    sleep 1
done

# Копирование файла
if cp /var/lib/redis/dump.rdb "$BACKUP_DIR/dump_$DATE.rdb" 2>/dev/null; then
    echo "Резервная копия создана: $BACKUP_DIR/dump_$DATE.rdb"
else
    echo "Ошибка создания резервной копии"
    exit 1
fi

# Удаление старых бэкапов (старше 7 дней)
find "$BACKUP_DIR" -name "dump_*.rdb" -mtime +7 -delete 2>/dev/null

echo "Готово"
EOF

    # Скрипт для мониторинга очередей в реальном времени
    cat > "$INSTALL_DIR/scripts/monitor_redis_queues.sh" << 'EOF'
#!/bin/bash

REDIS_PASS="${REDIS_PASSWORD:-$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')}"
REDIS_AUTH=""
if [[ -n "$REDIS_PASS" ]]; then
    REDIS_AUTH="-a $REDIS_PASS"
fi

watch -n 1 "redis-cli $REDIS_AUTH INFO keyspace 2>/dev/null | grep -v '^#' && echo && redis-cli $REDIS_AUTH LLEN celery 2>/dev/null"
EOF

    # Скрипт для подключения к Redis CLI
    cat > "$INSTALL_DIR/scripts/redis_cli.sh" << 'EOF'
#!/bin/bash

REDIS_PASS="${REDIS_PASSWORD:-$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')}"
REDIS_AUTH=""
if [[ -n "$REDIS_PASS" ]]; then
    REDIS_AUTH="-a $REDIS_PASS"
fi

redis-cli $REDIS_AUTH "$@"
EOF

    chmod +x "$INSTALL_DIR"/scripts/*redis*.sh
    chmod +x "$INSTALL_DIR"/scripts/redis_cli.sh
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/scripts" 2>/dev/null || true
    
    log_info "Скрипты для Redis созданы в $INSTALL_DIR/scripts"
}

setup_monitoring() {
    log_info "Настройка мониторинга Redis..."
    
    # Создание скрипта для сбора метрик
    cat > "$INSTALL_DIR/scripts/redis_metrics.sh" << 'EOF'
#!/bin/bash
# Сбор метрик Redis для Prometheus

REDIS_PASS="${REDIS_PASSWORD:-$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')}"
REDIS_AUTH=""
if [[ -n "$REDIS_PASS" ]]; then
    REDIS_AUTH="-a $REDIS_PASS"
fi

METRICS_FILE="/opt/gochs-informing/logs/redis_metrics.prom"

# Сбор метрик
redis-cli $REDIS_AUTH INFO 2>/dev/null | awk -F: '
/^connected_clients/ {print "redis_connected_clients " $2}
/^used_memory/ {print "redis_used_memory_bytes " $2}
/^maxmemory/ && $2 ~ /^[0-9]/ {print "redis_maxmemory_bytes " $2}
/^total_commands_processed/ {print "redis_commands_processed_total " $2}
/^instantaneous_ops_per_sec/ {print "redis_operations_per_second " $2}
/^keyspace_hits/ {print "redis_keyspace_hits_total " $2}
/^keyspace_misses/ {print "redis_keyspace_misses_total " $2}
/^evicted_keys/ {print "redis_evicted_keys_total " $2}
/^expired_keys/ {print "redis_expired_keys_total " $2}
' > "$METRICS_FILE"

# Добавление метрик по очередям
for queue in celery default high_priority low_priority; do
    count=$(redis-cli $REDIS_AUTH LLEN $queue 2>/dev/null || echo "0")
    echo "redis_queue_length{queue=\"$queue\"} $count" >> "$METRICS_FILE"
done
EOF

    chmod +x "$INSTALL_DIR/scripts/redis_metrics.sh"
    chown "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/scripts/redis_metrics.sh" 2>/dev/null || true
    
    # Добавление в crontab
    (crontab -l 2>/dev/null | grep -v "redis_metrics.sh"; echo "* * * * * $INSTALL_DIR/scripts/redis_metrics.sh") | crontab - 2>/dev/null || true
    
    log_info "Мониторинг Redis настроен (метрики собираются каждую минуту)"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Остановка сервиса
    systemctl stop redis-server 2>/dev/null
    systemctl disable redis-server 2>/dev/null
    
    # Удаление crontab задач
    crontab -l 2>/dev/null | grep -v "redis_metrics.sh" | crontab - 2>/dev/null || true
    
    # Удаление пакетов
    read -p "Удалить пакеты Redis? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt-get remove --purge -y redis-server redis-tools 2>/dev/null
        apt-get autoremove -y 2>/dev/null
        log_info "Пакеты Redis удалены"
    fi
    
    # Удаление данных
    read -p "Удалить данные Redis? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf /var/lib/redis/*
        rm -rf /var/log/redis/*
        log_info "Данные Redis удалены"
    fi
    
    # Удаление скриптов
    rm -f "$INSTALL_DIR"/scripts/*redis*.sh
    rm -f "$INSTALL_DIR"/scripts/redis_cli.sh
    
    # Удаление репозитория
    rm -f /etc/apt/sources.list.d/redis.list
    rm -f /usr/share/keyrings/redis-archive-keyring.gpg
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка сервиса
    if systemctl is-active --quiet redis-server; then
        log_info "✓ Сервис Redis: активен"
    else
        log_error "✗ Сервис Redis: не активен"
        status=1
    fi
    
    # Проверка подключения
    REDIS_PASS=$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')
    REDIS_AUTH=""
    if [[ -n "$REDIS_PASS" ]]; then
        REDIS_AUTH="-a $REDIS_PASS"
    fi
    
    if redis-cli $REDIS_AUTH ping 2>/dev/null | grep -q "PONG"; then
        log_info "✓ Подключение к Redis: успешно"
        
        # Сбор статистики
        REDIS_INFO=$(redis-cli $REDIS_AUTH INFO 2>/dev/null)
        
        # Версия
        VERSION=$(echo "$REDIS_INFO" | grep "redis_version:" | cut -d':' -f2 | xargs)
        log_info "  Версия: $VERSION"
        
        # Память
        USED_MEMORY=$(echo "$REDIS_INFO" | grep "used_memory_human:" | cut -d':' -f2 | xargs)
        MAX_MEMORY=$(echo "$REDIS_INFO" | grep "maxmemory_human:" | cut -d':' -f2 | xargs)
        log_info "  Память: $USED_MEMORY / ${MAX_MEMORY:-не ограничено}"
        
        # Клиенты
        CLIENTS=$(echo "$REDIS_INFO" | grep "connected_clients:" | cut -d':' -f2 | xargs)
        log_info "  Подключено клиентов: $CLIENTS"
        
        # Ключи
        KEY_COUNT=$(redis-cli $REDIS_AUTH DBSIZE 2>/dev/null | xargs)
        log_info "  Количество ключей: ${KEY_COUNT:-0}"
        
        # Очереди
        log_info "  Очереди:"
        for queue in celery default high_priority low_priority; do
            count=$(redis-cli $REDIS_AUTH LLEN $queue 2>/dev/null || echo "0")
            log_info "    $queue: $count задач"
        done
        
        # Персистентность
        LAST_SAVE=$(echo "$REDIS_INFO" | grep "rdb_last_save_time:" | cut -d':' -f2 | xargs)
        if [[ -n "$LAST_SAVE" ]] && [[ "$LAST_SAVE" != "0" ]]; then
            SAVE_TIME=$(date -d "@$LAST_SAVE" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$LAST_SAVE")
            log_info "  Последнее сохранение: $SAVE_TIME"
        fi
        
    else
        log_error "✗ Подключение к Redis: ошибка"
        status=1
    fi
    
    # Проверка конфигурации
    if [[ -f /etc/redis/redis.conf ]]; then
        log_info "✓ Конфигурация: найдена"
    else
        log_error "✗ Конфигурация: отсутствует"
        status=1
    fi
    
    return $status
}

# Функция для тестирования производительности
benchmark() {
    log_step "Тестирование производительности Redis"
    
    if ! command -v redis-benchmark &> /dev/null; then
        log_error "redis-benchmark не установлен"
        return 1
    fi
    
    REDIS_PASS=$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')
    REDIS_AUTH=""
    if [[ -n "$REDIS_PASS" ]]; then
        REDIS_AUTH="-a $REDIS_PASS"
    fi
    
    log_info "Запуск бенчмарка Redis..."
    redis-benchmark $REDIS_AUTH -q -n 10000 -c 50 --csv 2>/dev/null
}

# Функция для очистки всего кэша
flush_all() {
    log_step "Очистка всей базы Redis"
    
    read -p "ВНИМАНИЕ: Будут удалены ВСЕ данные Redis! Продолжить? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Точно? Введите 'DELETE': " confirmation
        if [[ "$confirmation" == "DELETE" ]]; then
            REDIS_PASS=$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')
            REDIS_AUTH=""
            if [[ -n "$REDIS_PASS" ]]; then
                REDIS_AUTH="-a $REDIS_PASS"
            fi
            
            redis-cli $REDIS_AUTH FLUSHALL 2>/dev/null
            log_info "База данных Redis очищена"
        else
            log_info "Операция отменена"
        fi
    fi
}

# Функция для просмотра информации
show_info() {
    log_step "Информация о Redis"
    
    REDIS_PASS=$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')
    REDIS_AUTH=""
    if [[ -n "$REDIS_PASS" ]]; then
        REDIS_AUTH="-a $REDIS_PASS"
    fi
    
    echo -e "${CYAN}=== Общая информация ===${NC}"
    redis-cli $REDIS_AUTH INFO server 2>/dev/null | grep -E "redis_version|os|process_id|tcp_port"
    
    echo -e "\n${CYAN}=== Статистика ===${NC}"
    redis-cli $REDIS_AUTH INFO stats 2>/dev/null | grep -E "total_connections|total_commands|ops_per_sec|keyspace_hits|keyspace_misses"
    
    echo -e "\n${CYAN}=== Память ===${NC}"
    redis-cli $REDIS_AUTH INFO memory 2>/dev/null | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio"
    
    echo -e "\n${CYAN}=== Персистентность ===${NC}"
    redis-cli $REDIS_AUTH INFO persistence 2>/dev/null | grep -E "rdb_last_save_time|aof_enabled|aof_current_size"
    
    echo -e "\n${CYAN}=== Ключи ===${NC}"
    redis-cli $REDIS_AUTH INFO keyspace 2>/dev/null
    
    echo -e "\n${CYAN}=== Очереди ===${NC}"
    for queue in celery default high_priority low_priority; do
        count=$(redis-cli $REDIS_AUTH LLEN $queue 2>/dev/null || echo "0")
        echo "  $queue: $count"
    done
}

# Обработка аргументов
case "${1:-}" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    status)
        check_status
        ;;
    benchmark)
        benchmark
        ;;
    flush)
        flush_all
        ;;
    info)
        show_info
        ;;
    backup)
        if [[ -f "$INSTALL_DIR/scripts/backup_redis.sh" ]]; then
            bash "$INSTALL_DIR/scripts/backup_redis.sh"
        else
            log_error "Скрипт резервного копирования не найден"
            exit 1
        fi
        ;;
    monitor)
        if [[ -f "$INSTALL_DIR/scripts/monitor_redis_queues.sh" ]]; then
            bash "$INSTALL_DIR/scripts/monitor_redis_queues.sh"
        else
            REDIS_PASS=$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')
            REDIS_AUTH=""
            if [[ -n "$REDIS_PASS" ]]; then
                REDIS_AUTH="-a $REDIS_PASS"
            fi
            watch -n 1 "redis-cli $REDIS_AUTH INFO keyspace 2>/dev/null"
        fi
        ;;
    cli)
        shift
        REDIS_PASS=$(grep requirepass /etc/redis/redis.conf 2>/dev/null | awk '{print $2}')
        REDIS_AUTH=""
        if [[ -n "$REDIS_PASS" ]]; then
            REDIS_AUTH="-a $REDIS_PASS"
        fi
        redis-cli $REDIS_AUTH "$@"
        ;;
    restart)
        systemctl restart redis-server
        ;;
    logs)
        tail -f /var/log/redis/redis-server.log
        ;;
    clean)
        log_info "Очистка временных файлов Redis..."
        rm -rf /var/lib/redis/dump.rdb 2>/dev/null || true
        rm -rf /var/lib/redis/appendonly.aof 2>/dev/null || true
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|benchmark|flush|info|backup|monitor|cli|restart|logs|clean}"
        echo ""
        echo "  install    - Установка Redis"
        echo "  uninstall  - Удаление Redis"
        echo "  status     - Проверка статуса"
        echo "  benchmark  - Тест производительности"
        echo "  flush      - Очистка ВСЕХ данных"
        echo "  info       - Подробная информация"
        echo "  backup     - Создать резервную копию"
        echo "  monitor    - Мониторинг очередей"
        echo "  cli        - Подключение к Redis CLI"
        echo "  restart    - Перезапуск сервиса"
        echo "  logs       - Просмотр логов"
        echo "  clean      - Очистка временных файлов"
        exit 1
        ;;
esac
