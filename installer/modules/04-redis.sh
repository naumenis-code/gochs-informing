#!/bin/bash

################################################################################
# Модуль: 04-redis.sh
# Назначение: Установка и настройка Redis для очередей и кэширования
################################################################################

source "${UTILS_DIR}/common.sh"

MODULE_NAME="04-redis"
MODULE_DESCRIPTION="Redis для очередей задач и кэширования"

# Версия Redis
REDIS_VERSION="7.2"

install() {
    log_step "Установка и настройка Redis"
    
    # Проверка наличия Redis
    if command -v redis-server &> /dev/null; then
        REDIS_VER=$(redis-server --version | awk '{print $3}' | cut -d'=' -f2)
        log_info "Redis уже установлен (версия $REDIS_VER)"
    else
        log_info "Установка Redis $REDIS_VERSION..."
        
        # Добавление официального репозитория Redis
        curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list
        
        apt-get update
        apt-get install -y redis-server redis-tools
        
        log_info "Redis $REDIS_VERSION установлен"
    fi
    
    # Остановка Redis для настройки
    systemctl stop redis-server
    
    # Настройка Redis
    log_info "Настройка конфигурации Redis..."
    configure_redis
    
    # Запуск Redis
    systemctl start redis-server
    systemctl enable redis-server
    
    # Ожидание запуска
    wait_for_service "redis-server" 10
    
    # Проверка подключения
    log_info "Проверка подключения к Redis..."
    if redis-cli -a "$REDIS_PASSWORD" ping &>/dev/null; then
        log_info "Redis отвечает на PING"
    else
        log_error "Redis не отвечает"
        return 1
    fi
    
    # Создание скриптов для работы с Redis
    create_redis_scripts
    
    # Настройка мониторинга Redis
    setup_monitoring
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Redis порт: $REDIS_PORT"
    log_info "Пароль сохранен в /root/.gochs_credentials"
    
    return 0
}

configure_redis() {
    local redis_conf="/etc/redis/redis.conf"
    
    # Резервное копирование оригинальной конфигурации
    backup_file "$redis_conf"
    
    # Расчет оптимальных параметров
    local total_ram=$(free -m | awk '/^Mem:/{print $2}')
    local maxmemory=$((total_ram / 4))  # 25% от общей RAM
    local save_seconds=300
    local save_changes=100
    
    # Создание новой конфигурации
    cat > "$redis_conf" << EOF
# ================================================
# ГО-ЧС Информирование - Конфигурация Redis
# Версия: $REDIS_VERSION
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
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16
always-show-logo no

# Сохранение данных (RDB)
save $save_seconds $save_changes
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

    # Создание директории для логов если не существует
    mkdir -p /var/log/redis
    chown redis:redis /var/log/redis
    
    log_info "Конфигурация Redis создана"
}

create_redis_scripts() {
    log_info "Создание скриптов для работы с Redis"
    
    mkdir -p "$INSTALL_DIR/scripts"
    
    # Скрипт для проверки состояния Redis
    cat > "$INSTALL_DIR/scripts/check_redis.sh" << 'EOF'
#!/bin/bash
source /opt/gochs-informing/.env

echo "=== Статистика Redis ==="
redis-cli -a $REDIS_PASSWORD INFO stats | grep -E "total_connections_received|total_commands_processed|instantaneous_ops_per_sec|keyspace_hits|keyspace_misses|evicted_keys|expired_keys"

echo -e "\n=== Память ==="
redis-cli -a $REDIS_PASSWORD INFO memory | grep -E "used_memory_human|used_memory_peak_human|maxmemory_human|mem_fragmentation_ratio"

echo -e "\n=== Клиенты ==="
redis-cli -a $REDIS_PASSWORD INFO clients | grep -E "connected_clients|blocked_clients"

echo -e "\n=== Ключи ==="
redis-cli -a $REDIS_PASSWORD INFO keyspace

echo -e "\n=== Очереди Celery ==="
redis-cli -a $REDIS_PASSWORD LLEN celery
for queue in default high_priority low_priority; do
    count=$(redis-cli -a $REDIS_PASSWORD LLEN $queue 2>/dev/null || echo "0")
    echo "  $queue: $count задач"
done
EOF

    # Скрипт для очистки очередей
    cat > "$INSTALL_DIR/scripts/clear_redis_queues.sh" << 'EOF'
#!/bin/bash
source /opt/gochs-informing/.env

echo "ВНИМАНИЕ: Будут очищены все очереди Redis!"
read -p "Продолжить? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Очистка очередей..."
    redis-cli -a $REDIS_PASSWORD DEL celery
    redis-cli -a $REDIS_PASSWORD DEL default
    redis-cli -a $REDIS_PASSWORD DEL high_priority
    redis-cli -a $REDIS_PASSWORD DEL low_priority
    echo "Очереди очищены"
fi
EOF

    # Скрипт для резервного копирования Redis
    cat > "$INSTALL_DIR/scripts/backup_redis.sh" << 'EOF'
#!/bin/bash
source /opt/gochs-informing/.env

BACKUP_DIR="/opt/gochs-informing/backups/redis"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Запуск сохранения RDB..."
redis-cli -a $REDIS_PASSWORD BGSAVE

# Ожидание завершения сохранения
while [ $(redis-cli -a $REDIS_PASSWORD INFO persistence | grep -c "rdb_bgsave_in_progress:1") -eq 1 ]; do
    sleep 1
done

# Копирование файла
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/dump_$DATE.rdb"
echo "Резервная копия создана: $BACKUP_DIR/dump_$DATE.rdb"

# Удаление старых бэкапов (старше 7 дней)
find "$BACKUP_DIR" -name "dump_*.rdb" -mtime +7 -delete
EOF

    # Скрипт для мониторинга очередей в реальном времени
    cat > "$INSTALL_DIR/scripts/monitor_redis_queues.sh" << 'EOF'
#!/bin/bash
source /opt/gochs-informing/.env

watch -n 1 "redis-cli -a $REDIS_PASSWORD INFO keyspace | grep -v '^#' && echo && redis-cli -a $REDIS_PASSWORD LLEN celery"
EOF

    chmod +x "$INSTALL_DIR"/scripts/*redis*.sh
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts"
    
    log_info "Скрипты для Redis созданы в $INSTALL_DIR/scripts"
}

setup_monitoring() {
    log_info "Настройка мониторинга Redis"
    
    # Создание скрипта для сбора метрик
    cat > "$INSTALL_DIR/scripts/redis_metrics.sh" << 'EOF'
#!/bin/bash
# Сбор метрик Redis для Prometheus формата
source /opt/gochs-informing/.env

METRICS_FILE="/opt/gochs-informing/logs/redis_metrics.prom"

# Сбор метрик
redis-cli -a $REDIS_PASSWORD INFO | awk -F: '
/^connected_clients/ {print "redis_connected_clients " $2}
/^used_memory/ {print "redis_used_memory_bytes " $2}
/^maxmemory/ {print "redis_maxmemory_bytes " $2}
/^total_commands_processed/ {print "redis_commands_processed_total " $2}
/^instantaneous_ops_per_sec/ {print "redis_operations_per_second " $2}
/^keyspace_hits/ {print "redis_keyspace_hits_total " $2}
/^keyspace_misses/ {print "redis_keyspace_misses_total " $2}
/^evicted_keys/ {print "redis_evicted_keys_total " $2}
/^expired_keys/ {print "redis_expired_keys_total " $2}
' > "$METRICS_FILE"

# Добавление метрик по очередям
for queue in celery default high_priority low_priority; do
    count=$(redis-cli -a $REDIS_PASSWORD LLEN $queue 2>/dev/null || echo "0")
    echo "redis_queue_length{queue=\"$queue\"} $count" >> "$METRICS_FILE"
done
EOF

    chmod +x "$INSTALL_DIR/scripts/redis_metrics.sh"
    chown "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts/redis_metrics.sh"
    
    # Добавление в crontab для сбора метрик каждую минуту
    (crontab -l 2>/dev/null | grep -v "redis_metrics.sh"; echo "* * * * * $INSTALL_DIR/scripts/redis_metrics.sh") | crontab -
    
    log_info "Мониторинг Redis настроен (метрики собираются каждую минуту)"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Остановка сервиса
    systemctl stop redis-server
    systemctl disable redis-server
    
    # Удаление crontab задач
    crontab -l | grep -v "redis_metrics.sh" | crontab -
    
    # Удаление пакетов
    read -p "Удалить пакеты Redis? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt-get remove --purge -y redis-server redis-tools
        apt-get autoremove -y
        log_info "Пакеты Redis удалены"
    fi
    
    # Удаление данных
    read -p "Удалить данные Redis? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf /var/lib/redis/*
        log_info "Данные Redis удалены"
    fi
    
    # Удаление скриптов
    rm -f "$INSTALL_DIR"/scripts/*redis*.sh
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка сервиса Redis
    if systemctl is-active --quiet redis-server; then
        log_info "Сервис Redis: активен"
    else
        log_error "Сервис Redis: не активен"
        status=1
    fi
    
    # Проверка подключения
    if redis-cli -a "$REDIS_PASSWORD" ping &>/dev/null; then
        log_info "Подключение к Redis: успешно"
        
        # Сбор статистики
        REDIS_INFO=$(redis-cli -a "$REDIS_PASSWORD" INFO)
        
        # Версия
        VERSION=$(echo "$REDIS_INFO" | grep "redis_version:" | cut -d':' -f2 | xargs)
        log_info "  Версия: $VERSION"
        
        # Память
        USED_MEMORY=$(echo "$REDIS_INFO" | grep "used_memory_human:" | cut -d':' -f2 | xargs)
        MAX_MEMORY=$(echo "$REDIS_INFO" | grep "maxmemory_human:" | cut -d':' -f2 | xargs)
        log_info "  Память: $USED_MEMORY / $MAX_MEMORY"
        
        # Клиенты
        CLIENTS=$(echo "$REDIS_INFO" | grep "connected_clients:" | cut -d':' -f2 | xargs)
        log_info "  Подключено клиентов: $CLIENTS"
        
        # Ключи
        KEY_COUNT=$(redis-cli -a "$REDIS_PASSWORD" DBSIZE | xargs)
        log_info "  Количество ключей: $KEY_COUNT"
        
        # Очереди
        log_info "  Очереди:"
        for queue in celery default high_priority low_priority; do
            count=$(redis-cli -a "$REDIS_PASSWORD" LLEN $queue 2>/dev/null || echo "0")
            log_info "    $queue: $count задач"
        done
        
    else
        log_error "Подключение к Redis: ошибка"
        status=1
    fi
    
    # Проверка персистентности
    if redis-cli -a "$REDIS_PASSWORD" INFO persistence | grep -q "rdb_last_save_time:[1-9]"; then
        LAST_SAVE=$(redis-cli -a "$REDIS_PASSWORD" INFO persistence | grep "rdb_last_save_time:" | cut -d':' -f2)
        SAVE_TIME=$(date -d "@$LAST_SAVE" "+%Y-%m-%d %H:%M:%S")
        log_info "  Последнее сохранение: $SAVE_TIME"
    fi
    
    return $status
}

# Функция для тестирования производительности Redis
benchmark() {
    log_step "Тестирование производительности Redis"
    
    if ! command -v redis-benchmark &> /dev/null; then
        log_error "redis-benchmark не установлен"
        return 1
    fi
    
    log_info "Запуск бенчмарка Redis..."
    redis-benchmark -a "$REDIS_PASSWORD" -q -n 10000 -c 50 --csv
}

# Функция для очистки кэша
clear_cache() {
    log_step "Очистка кэша Redis"
    
    read -p "Очистить весь кэш? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        redis-cli -a "$REDIS_PASSWORD" FLUSHDB
        log_info "Кэш очищен"
    fi
}

# Функция для просмотра информации
show_info() {
    log_step "Информация о Redis"
    
    echo -e "${CYAN}=== Общая информация ===${NC}"
    redis-cli -a "$REDIS_PASSWORD" INFO server | grep -E "redis_version|os|process_id"
    
    echo -e "\n${CYAN}=== Статистика ===${NC}"
    redis-cli -a "$REDIS_PASSWORD" INFO stats | grep -E "total_connections|total_commands|ops_per_sec|keyspace_hits|keyspace_misses"
    
    echo -e "\n${CYAN}=== Память ===${NC}"
    redis-cli -a "$REDIS_PASSWORD" INFO memory | grep -E "used_memory|maxmemory|mem_fragmentation"
    
    echo -e "\n${CYAN}=== Персистентность ===${NC}"
    redis-cli -a "$REDIS_PASSWORD" INFO persistence | grep -E "rdb_last_save|aof_enabled|aof_current_size"
    
    echo -e "\n${CYAN}=== Очереди ===${NC}"
    redis-cli -a "$REDIS_PASSWORD" INFO keyspace
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
    clear)
        clear_cache
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
            watch -n 1 "redis-cli -a $REDIS_PASSWORD INFO keyspace"
        fi
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|benchmark|clear|info|backup|monitor}"
        exit 1
        ;;
esac
