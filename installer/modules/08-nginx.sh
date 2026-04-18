#!/bin/bash

################################################################################
# Модуль: 08-nginx.sh
# Назначение: Установка и настройка Nginx веб-сервера
################################################################################

source "${UTILS_DIR}/common.sh"

MODULE_NAME="08-nginx"
MODULE_DESCRIPTION="Nginx веб-сервер и прокси"

install() {
    log_step "Установка и настройка Nginx"
    
    # Проверка зависимостей
    check_dependencies
    
    # Установка Nginx
    install_nginx
    
    # Настройка Nginx
    configure_nginx
    
    # Настройка SSL (опционально)
    setup_ssl
    
    # Настройка оптимизации
    optimize_nginx
    
    # Настройка мониторинга
    setup_monitoring
    
    # Запуск Nginx
    start_nginx
    
    # Создание скриптов управления
    create_management_scripts
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Web интерфейс доступен по адресу: https://$DOMAIN_OR_IP"
    
    return 0
}

check_dependencies() {
    log_info "Проверка зависимостей..."
    
    # Проверка бэкенда
    if ! systemctl is-active --quiet gochs-api.service; then
        log_error "Бэкенд не запущен. Сначала выполните модуль 06-backend"
        return 1
    fi
    
    # Проверка фронтенда
    if [[ ! -d "$INSTALL_DIR/frontend/build" ]]; then
        log_error "Фронтенд не собран. Сначала выполните модуль 07-frontend"
        return 1
    fi
    
    log_info "Все зависимости удовлетворены"
}

install_nginx() {
    log_info "Установка Nginx..."
    
    if command -v nginx &> /dev/null; then
        NGINX_VER=$(nginx -v 2>&1 | grep -oP 'nginx/\K[\d.]+')
        log_info "Nginx уже установлен (версия $NGINX_VER)"
    else
        # Установка из официального репозитория Nginx
        curl -fsSL https://nginx.org/keys/nginx_signing.key | gpg --dearmor > /usr/share/keyrings/nginx-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/debian $(lsb_release -cs) nginx" > /etc/apt/sources.list.d/nginx.list
        
        apt-get update
        apt-get install -y nginx
        
        log_info "Nginx установлен"
    fi
}

configure_nginx() {
    log_info "Настройка конфигурации Nginx..."
    
    # Резервное копирование оригинальной конфигурации
    backup_file "/etc/nginx/nginx.conf"
    
    # Основная конфигурация nginx.conf
    cat > "/etc/nginx/nginx.conf" << 'EOF'
user www-data;
worker_processes auto;
worker_rlimit_nofile 65535;
pid /run/nginx.pid;

# Загрузка модулей
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    # Базовые настройки
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    server_names_hash_bucket_size 128;
    
    # MIME типы
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Логирование
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    log_format json escape=json '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"remote_user":"$remote_user",'
        '"request":"$request",'
        '"status":$status,'
        '"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"http_referrer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"http_x_forwarded_for":"$http_x_forwarded_for"'
    '}';
    
    access_log /var/log/nginx/access.log json;
    error_log /var/log/nginx/error.log warn;
    
    # Сжатие
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_disable "msie6";
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/rss+xml
        application/atom+xml
        image/svg+xml
        application/vnd.ms-fontobject
        application/x-font-ttf
        font/opentype;
    
    # Кэширование
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
    
    # Защита
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Лимиты
    client_max_body_size 100M;
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;
    
    # Таймауты
    client_body_timeout 12;
    client_header_timeout 12;
    send_timeout 10;
    
    # Подключение конфигураций сайтов
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOF

    # Конфигурация сайта GO-CHS
    cat > "/etc/nginx/sites-available/gochs" << EOF
# GO-CHS Информирование - Nginx конфигурация
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN_OR_IP;
    
    # Редирект на HTTPS (если SSL настроен)
    # return 301 https://\$server_name\$request_uri;
    
    # Для HTTP (без SSL)
    root $INSTALL_DIR/frontend/build;
    index index.html;
    
    # Логи
    access_log /var/log/nginx/gochs-access.log json;
    error_log /var/log/nginx/gochs-error.log;
    
    # Статические файлы фронтенда
    location / {
        try_files \$uri \$uri/ /index.html;
        
        # Кэширование статики
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API прокси
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Таймауты для API
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Буферизация
        proxy_buffering off;
        proxy_request_buffering off;
    }
    
    # WebSocket для real-time обновлений
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
    
    # Доступ к записям звонков
    location /recordings {
        alias $INSTALL_DIR/recordings;
        
        # Защита от прямого доступа
        auth_request /auth;
        
        # Поддержка range запросов для аудио
        add_header Accept-Ranges bytes;
        
        # CORS для аудио
        add_header Access-Control-Allow-Origin *;
    }
    
    # Внутренняя аутентификация для записей
    location = /auth {
        internal;
        proxy_pass http://127.0.0.1:8000/api/v1/auth/verify;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URI \$request_uri;
    }
    
    # Документация API
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host \$host;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # Статус Nginx (только для localhost)
    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
    
    # Запрет доступа к скрытым файлам
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}

# HTTPS конфигурация (если SSL настроен)
# server {
#     listen 443 ssl http2;
#     listen [::]:443 ssl http2;
#     server_name $DOMAIN_OR_IP;
#     
#     # SSL сертификаты
#     ssl_certificate /etc/nginx/ssl/gochs.crt;
#     ssl_certificate_key /etc/nginx/ssl/gochs.key;
#     
#     # SSL настройки
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers HIGH:!aNULL:!MD5;
#     ssl_prefer_server_ciphers on;
#     ssl_session_cache shared:SSL:10m;
#     ssl_session_timeout 10m;
#     ssl_session_tickets off;
#     
#     # HSTS
#     add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
#     
#     # Остальные настройки аналогичны HTTP
#     root $INSTALL_DIR/frontend/build;
#     index index.html;
#     
#     access_log /var/log/nginx/gochs-ssl-access.log json;
#     error_log /var/log/nginx/gochs-ssl-error.log;
#     
#     include /etc/nginx/sites-available/gochs_common;
# }
EOF

    # Создание общего файла конфигурации
    cat > "/etc/nginx/sites-available/gochs_common" << 'EOF'
# Общие настройки для HTTP и HTTPS
    
    # Статические файлы фронтенда
    location / {
        try_files $uri $uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API прокси
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
        proxy_request_buffering off;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
    
    # Записи звонков
    location /recordings {
        alias /opt/gochs-informing/recordings;
        auth_request /auth;
        add_header Accept-Ranges bytes;
        add_header Access-Control-Allow-Origin *;
    }
    
    location = /auth {
        internal;
        proxy_pass http://127.0.0.1:8000/api/v1/auth/verify;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URI $request_uri;
    }
    
    # Документация
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
        proxy_set_header Host $host;
    }
    
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host $host;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # Статус
    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
    
    # Защита
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
EOF

    # Активация сайта
    ln -sf /etc/nginx/sites-available/gochs /etc/nginx/sites-enabled/gochs
    rm -f /etc/nginx/sites-enabled/default
    
    # Проверка конфигурации
    nginx -t
    
    log_info "Конфигурация Nginx создана"
}

setup_ssl() {
    log_info "Настройка SSL сертификатов..."
    
    read -p "Настроить SSL с помощью Let's Encrypt? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Проверка домена
        if [[ "$DOMAIN_OR_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            log_warn "Let's Encrypt не работает с IP-адресами. Создаю самоподписанный сертификат."
            create_self_signed_cert
        else
            # Let's Encrypt
            certbot --nginx -d "$DOMAIN_OR_IP" --non-interactive --agree-tos -m "$ADMIN_EMAIL"
            
            # Автоматическое обновление
            (crontab -l 2>/dev/null; echo "0 0 * * * certbot renew --quiet --post-hook 'nginx -s reload'") | crontab -
            
            log_info "SSL сертификат Let's Encrypt установлен"
        fi
    else
        log_info "SSL не настроен (используется HTTP)"
    fi
}

create_self_signed_cert() {
    log_info "Создание самоподписанного SSL сертификата..."
    
    mkdir -p /etc/nginx/ssl
    
    # Генерация сертификата
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/gochs.key \
        -out /etc/nginx/ssl/gochs.crt \
        -subj "/C=RU/ST=State/L=City/O=GOCHS/CN=$DOMAIN_OR_IP"
    
    chmod 600 /etc/nginx/ssl/gochs.key
    chmod 644 /etc/nginx/ssl/gochs.crt
    
    log_info "Самоподписанный сертификат создан"
}

optimize_nginx() {
    log_info "Оптимизация Nginx..."
    
    # Системные лимиты
    cat > /etc/security/limits.d/nginx.conf << EOF
nginx soft nofile 65535
nginx hard nofile 65535
EOF

    # Оптимизация sysctl
    cat >> /etc/sysctl.d/99-nginx.conf << EOF
# Nginx optimizations
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_keepalive_probes = 3
EOF

    sysctl -p /etc/sysctl.d/99-nginx.conf
    
    log_info "Nginx оптимизирован"
}

setup_monitoring() {
    log_info "Настройка мониторинга Nginx..."
    
    # Создание скрипта для сбора метрик
    cat > "$INSTALL_DIR/scripts/nginx_metrics.sh" << 'EOF'
#!/bin/bash
# Сбор метрик Nginx

METRICS_FILE="/opt/gochs-informing/logs/nginx_metrics.prom"

# Получение статуса
STATUS=$(curl -s http://localhost/nginx_status)

if [[ -n "$STATUS" ]]; then
    ACTIVE=$(echo "$STATUS" | grep "Active connections" | awk '{print $3}')
    ACCEPTS=$(echo "$STATUS" | grep -A 1 "server accepts" | tail -1 | awk '{print $1}')
    HANDLED=$(echo "$STATUS" | grep -A 1 "server accepts" | tail -1 | awk '{print $2}')
    REQUESTS=$(echo "$STATUS" | grep -A 1 "server accepts" | tail -1 | awk '{print $3}')
    READING=$(echo "$STATUS" | grep "Reading" | awk '{print $2}')
    WRITING=$(echo "$STATUS" | grep "Writing" | awk '{print $4}')
    WAITING=$(echo "$STATUS" | grep "Waiting" | awk '{print $6}')
    
    cat > "$METRICS_FILE" << PROM
# HELP nginx_connections_active Active client connections
# TYPE nginx_connections_active gauge
nginx_connections_active $ACTIVE

# HELP nginx_connections_reading Reading client connections
# TYPE nginx_connections_reading gauge
nginx_connections_reading $READING

# HELP nginx_connections_writing Writing client connections
# TYPE nginx_connections_writing gauge
nginx_connections_writing $WRITING

# HELP nginx_connections_waiting Waiting client connections
# TYPE nginx_connections_waiting gauge
nginx_connections_waiting $WAITING

# HELP nginx_http_requests_total Total http requests
# TYPE nginx_http_requests_total counter
nginx_http_requests_total $REQUESTS
PROM
fi
EOF

    chmod +x "$INSTALL_DIR/scripts/nginx_metrics.sh"
    
    # Добавление в crontab
    (crontab -l 2>/dev/null | grep -v "nginx_metrics.sh"; echo "* * * * * $INSTALL_DIR/scripts/nginx_metrics.sh") | crontab -
    
    log_info "Мониторинг Nginx настроен"
}

start_nginx() {
    log_info "Запуск Nginx..."
    
    systemctl enable nginx
    systemctl restart nginx
    
    # Ожидание запуска
    wait_for_service "nginx" 10
    
    if systemctl is-active --quiet nginx; then
        log_info "Nginx успешно запущен"
    else
        log_error "Ошибка запуска Nginx"
        return 1
    fi
}

create_management_scripts() {
    log_info "Создание скриптов управления Nginx..."
    
    # Скрипт проверки статуса
    cat > "$INSTALL_DIR/scripts/nginx_status.sh" << 'EOF'
#!/bin/bash
echo "=== Статус Nginx ==="
systemctl status nginx --no-pager

echo -e "\n=== Активные соединения ==="
curl -s http://localhost/nginx_status

echo -e "\n=== Последние ошибки ==="
tail -20 /var/log/nginx/error.log

echo -e "\n=== Последние запросы ==="
tail -10 /var/log/nginx/gochs-access.log
EOF

    # Скрипт для просмотра логов
    cat > "$INSTALL_DIR/scripts/nginx_logs.sh" << 'EOF'
#!/bin/bash
if [[ "$1" == "error" ]]; then
    tail -f /var/log/nginx/error.log
elif [[ "$1" == "access" ]]; then
    tail -f /var/log/nginx/gochs-access.log
else
    echo "Использование: $0 {error|access}"
fi
EOF

    # Скрипт перезагрузки
    cat > "$INSTALL_DIR/scripts/nginx_reload.sh" << 'EOF'
#!/bin/bash
echo "Перезагрузка Nginx..."
nginx -t && systemctl reload nginx
echo "Готово"
EOF

    # Скрипт тестирования
    cat > "$INSTALL_DIR/scripts/nginx_test.sh" << 'EOF'
#!/bin/bash
echo "Тестирование Nginx..."

# Проверка HTTP
echo -n "HTTP: "
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "OK"
else
    echo "FAILED"
fi

# Проверка API
echo -n "API: "
if curl -s http://localhost/health | grep -q "healthy"; then
    echo "OK"
else
    echo "FAILED"
fi

# Проверка статики
echo -n "Static: "
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "OK"
else
    echo "FAILED"
fi
EOF

    chmod +x "$INSTALL_DIR"/scripts/nginx_*.sh
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts"
    
    log_info "Скрипты управления созданы в $INSTALL_DIR/scripts"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Остановка Nginx
    systemctl stop nginx
    systemctl disable nginx
    
    # Удаление конфигураций
    rm -f /etc/nginx/sites-enabled/gochs
    rm -f /etc/nginx/sites-available/gochs
    rm -f /etc/nginx/sites-available/gochs_common
    
    # Удаление crontab задач
    crontab -l | grep -v "nginx_metrics.sh" | crontab -
    crontab -l | grep -v "certbot renew" | crontab -
    
    # Удаление пакетов
    read -p "Удалить Nginx полностью? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt-get remove --purge -y nginx nginx-common nginx-full
        apt-get autoremove -y
        log_info "Nginx удален"
    fi
    
    # Удаление скриптов
    rm -f "$INSTALL_DIR"/scripts/nginx_*.sh
    
    # Удаление SSL сертификатов
    rm -rf /etc/nginx/ssl
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка сервиса
    if systemctl is-active --quiet nginx; then
        log_info "Сервис Nginx: активен"
        
        # Проверка версии
        NGINX_VER=$(nginx -v 2>&1 | grep -oP 'nginx/\K[\d.]+')
        log_info "  Версия: $NGINX_VER"
        
        # Проверка конфигурации
        if nginx -t &>/dev/null; then
            log_info "  Конфигурация: OK"
        else
            log_error "  Конфигурация: Ошибка"
            status=1
        fi
        
        # Проверка HTTP
        if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
            log_info "  HTTP доступ: OK"
        else
            log_warn "  HTTP доступ: Ошибка"
            status=1
        fi
        
        # Проверка API
        if curl -s http://localhost/health | grep -q "healthy"; then
            log_info "  API прокси: OK"
        else
            log_warn "  API прокси: Ошибка"
            status=1
        fi
        
        # Статистика соединений
        STATUS=$(curl -s http://localhost/nginx_status 2>/dev/null)
        if [[ -n "$STATUS" ]]; then
            ACTIVE=$(echo "$STATUS" | grep "Active connections" | awk '{print $3}')
            log_info "  Активных соединений: $ACTIVE"
        fi
        
    else
        log_error "Сервис Nginx: не активен"
        status=1
    fi
    
    # Проверка SSL
    if [[ -f /etc/nginx/ssl/gochs.crt ]]; then
        log_info "SSL сертификат: установлен"
        
        # Проверка срока действия
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/nginx/ssl/gochs.crt 2>/dev/null | cut -d= -f2)
        if [[ -n "$EXPIRY" ]]; then
            log_info "  Срок действия до: $EXPIRY"
        fi
    else
        log_info "SSL: не настроен"
    fi
    
    return $status
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
    reload)
        nginx -t && systemctl reload nginx
        ;;
    restart)
        systemctl restart nginx
        ;;
    logs)
        journalctl -u nginx -f
        ;;
    test)
        bash "$INSTALL_DIR/scripts/nginx_test.sh"
        ;;
    ssl)
        setup_ssl
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|reload|restart|logs|test|ssl}"
        exit 1
        ;;
esac
