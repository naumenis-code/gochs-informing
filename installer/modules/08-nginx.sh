#!/bin/bash

################################################################################
# Модуль: 08-nginx.sh
# Назначение: Установка и настройка Nginx веб-сервера
# Версия: 1.0.3 (исправленная полная версия)
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
        openssl rand -base64 16 2>/dev/null | tr -d "=+/" | cut -c1-16 || echo "ChangeMe$(date +%s)"
    }
fi

MODULE_NAME="08-nginx"
MODULE_DESCRIPTION="Nginx веб-сервер и прокси"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
    DOMAIN_OR_IP="${DOMAIN_OR_IP:-localhost}"
    ADMIN_EMAIL="${ADMIN_EMAIL:-admin@localhost}"
    HTTP_PORT="${HTTP_PORT:-80}"
    HTTPS_PORT="${HTTPS_PORT:-443}"
    SSL_MODE="${SSL_MODE:-none}"
    GOCHS_USER="${GOCHS_USER:-gochs}"
    GOCHS_GROUP="${GOCHS_GROUP:-gochs}"
fi

# Переменные для отслеживания SSL
SSL_SUCCESS=false

install() {
    log_step "Установка и настройка Nginx"
    
    check_dependencies
    install_nginx
    create_directories
    configure_nginx
    
    # Настройка SSL в зависимости от выбора пользователя
    case "$SSL_MODE" in
        letsencrypt)
            setup_letsencrypt
            ;;
        selfsigned)
            create_self_signed_cert
            enable_https_config
            ;;
        none)
            log_info "SSL не настраивается (режим: $SSL_MODE)"
            ;;
        *)
            log_warn "Неизвестный режим SSL: $SSL_MODE, пропускаем"
            ;;
    esac
    
    optimize_nginx
    setup_monitoring
    create_test_frontend
    start_nginx
    create_management_scripts
    
    # Настройка fail2ban для Nginx
    setup_fail2ban
    
    # Настройка ротации логов
    setup_logrotate
    
    mark_module_installed "$MODULE_NAME"
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ДОСТУП К СИСТЕМЕ:${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${WHITE}Web интерфейс:${NC}     ${GREEN}http://$DOMAIN_OR_IP${NC}"
    if [[ "$SSL_SUCCESS" == "true" ]]; then
        echo -e "  ${WHITE}HTTPS:${NC}             ${GREEN}https://$DOMAIN_OR_IP${NC}"
    fi
    echo -e "  ${WHITE}API документация:${NC}  ${GREEN}http://$DOMAIN_OR_IP/docs${NC}"
    echo ""
    
    return 0
}

check_dependencies() {
    log_info "Проверка зависимостей..."
    
    # Проверка бэкенда
    if ! systemctl is-active --quiet gochs-api.service 2>/dev/null; then
        log_warn "Бэкенд не запущен. API прокси может не работать."
    fi
    
    # Проверка существования директории установки
    if [[ ! -d "$INSTALL_DIR" ]]; then
        ensure_dir "$INSTALL_DIR"
    fi
    
    # Проверка наличия curl
    if ! command -v curl &>/dev/null; then
        apt-get install -y curl 2>/dev/null || true
    fi
    
    log_info "Зависимости проверены"
}

install_nginx() {
    log_info "Установка Nginx..."
    
    if command -v nginx &> /dev/null; then
        NGINX_VER=$(nginx -v 2>&1 | grep -oP 'nginx/\K[\d.]+')
        log_info "Nginx уже установлен (версия $NGINX_VER)"
        return 0
    fi
    
    # Попытка установки из официального репозитория
    log_info "Добавление репозитория Nginx..."
    if curl -fsSL https://nginx.org/keys/nginx_signing.key 2>/dev/null | gpg --dearmor > /usr/share/keyrings/nginx-archive-keyring.gpg 2>/dev/null; then
        echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/debian $(lsb_release -cs 2>/dev/null || echo 'bookworm') nginx" > /etc/apt/sources.list.d/nginx.list
        apt-get update -qq
        apt-get install -y nginx
    else
        # Fallback на стандартный репозиторий
        log_warn "Не удалось добавить репозиторий Nginx, используется стандартный"
        apt-get update -qq
        apt-get install -y nginx
    fi
    
    log_info "Nginx установлен"
}

create_directories() {
    log_info "Создание директорий..."
    
    ensure_dir "/etc/nginx/sites-available"
    ensure_dir "/etc/nginx/sites-enabled"
    ensure_dir "/etc/nginx/ssl"
    ensure_dir "/etc/nginx/conf.d"
    ensure_dir "/var/log/nginx"
    ensure_dir "/var/cache/nginx"
    ensure_dir "$INSTALL_DIR/frontend/build"
    ensure_dir "$INSTALL_DIR/logs"
    ensure_dir "$INSTALL_DIR/recordings"
    ensure_dir "$INSTALL_DIR/scripts"
    
    # Установка прав
    chown -R www-data:www-data /var/log/nginx 2>/dev/null || true
    chown -R www-data:www-data /var/cache/nginx 2>/dev/null || true
    
    log_info "Директории созданы"
}

configure_nginx() {
    log_info "Настройка конфигурации Nginx..."
    
    backup_file "/etc/nginx/nginx.conf"
    
    # Расчет оптимальных параметров
    local cpu_cores=$(nproc)
    local worker_connections=$((cpu_cores * 1024))
    
    cat > "/etc/nginx/nginx.conf" << EOF
user www-data;
worker_processes auto;
worker_rlimit_nofile 65535;
pid /run/nginx.pid;

include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections $worker_connections;
    use epoll;
    multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    server_names_hash_bucket_size 128;
    
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';
    
    log_format json escape=json '{'
        '"time_local":"\$time_local",'
        '"remote_addr":"\$remote_addr",'
        '"request":"\$request",'
        '"status":\$status,'
        '"body_bytes_sent":\$body_bytes_sent,'
        '"request_time":\$request_time,'
        '"http_referrer":"\$http_referer",'
        '"http_user_agent":"\$http_user_agent"'
    '}';
    
    access_log /var/log/nginx/access.log json;
    error_log /var/log/nginx/error.log warn;
    
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
    
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    client_max_body_size 100M;
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;
    
    client_body_timeout 12;
    client_header_timeout 12;
    send_timeout 10;
    
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOF

    # Создание HTTP конфигурации
    cat > "/etc/nginx/sites-available/gochs" << EOF
# GO-CHS Информирование - HTTP конфигурация
server {
    listen ${HTTP_PORT} default_server;
    listen [::]:${HTTP_PORT} default_server;
    server_name _;
    
    root $INSTALL_DIR/frontend/build;
    index index.html index.htm;
    
    access_log /var/log/nginx/gochs-access.log json;
    error_log /var/log/nginx/gochs-error.log;
    
    location / {
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
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
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
        proxy_request_buffering off;
    }
    
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
    
    location /recordings {
        alias $INSTALL_DIR/recordings;
        add_header Accept-Ranges bytes;
        add_header Access-Control-Allow-Origin *;
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
        proxy_set_header Host \$host;
    }
    
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host \$host;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        allow ::1;
        deny all;
    }
    
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

    # Активация HTTP
    ln -sf /etc/nginx/sites-available/gochs /etc/nginx/sites-enabled/gochs
    rm -f /etc/nginx/sites-enabled/default
    
    # Проверка конфигурации
    if nginx -t 2>&1; then
        log_info "Конфигурация Nginx корректна"
    else
        log_error "Ошибка в конфигурации Nginx"
        return 1
    fi
}

setup_letsencrypt() {
    log_info "Настройка Let's Encrypt SSL..."
    
    # Проверка, является ли DOMAIN_OR_IP IP-адресом
    if [[ "$DOMAIN_OR_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_warn "Let's Encrypt не работает с IP-адресами"
        log_info "Переключение на самоподписанный сертификат..."
        create_self_signed_cert
        enable_https_config
        return 0
    fi
    
    # Установка certbot
    if ! command -v certbot &>/dev/null; then
        log_info "Установка certbot..."
        apt-get update -qq
        apt-get install -y certbot python3-certbot-nginx 2>/dev/null || {
            log_error "Не удалось установить certbot"
            return 1
        }
    fi
    
    # Проверка доступности домена
    log_info "Проверка доступности домена $DOMAIN_OR_IP..."
    if ! host "$DOMAIN_OR_IP" &>/dev/null; then
        log_warn "Домен $DOMAIN_OR_IP не резолвится в DNS"
    fi
    
    log_info "Получение сертификата для $DOMAIN_OR_IP..."
    
    if certbot --nginx -d "$DOMAIN_OR_IP" --non-interactive --agree-tos -m "$ADMIN_EMAIL" --redirect 2>&1 | tee -a /tmp/certbot.log; then
        log_info "✅ SSL сертификат Let's Encrypt успешно установлен!"
        
        # Автоматическое обновление
        (crontab -l 2>/dev/null | grep -v "certbot renew"; echo "0 0 * * * certbot renew --quiet --post-hook 'nginx -s reload'") | crontab - 2>/dev/null || true
        log_info "Настроено автоматическое обновление сертификата"
        
        SSL_SUCCESS=true
    else
        log_error "Не удалось получить сертификат Let's Encrypt"
        log_info "Проверьте, что домен $DOMAIN_OR_IP направлен на этот сервер и порт 80 доступен"
        
        # Автоматически переключаемся на самоподписанный если не в интерактивном режиме
        if [[ -t 0 ]]; then
            echo ""
            echo -e "${YELLOW}Создать самоподписанный сертификат вместо этого? (y/N):${NC} "
            read -r create_self
            if [[ "$create_self" =~ ^[Yy]$ ]]; then
                create_self_signed_cert
                enable_https_config
            fi
        else
            log_info "Неинтерактивный режим - SSL пропущен"
        fi
    fi
}

create_self_signed_cert() {
    log_info "Создание самоподписанного SSL сертификата..."
    
    ensure_dir "/etc/nginx/ssl"
    
    # Генерация сертификата
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/gochs.key \
        -out /etc/nginx/ssl/gochs.crt \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=GOCHS/CN=$DOMAIN_OR_IP" 2>/dev/null
    
    chmod 600 /etc/nginx/ssl/gochs.key
    chmod 644 /etc/nginx/ssl/gochs.crt
    
    log_info "✅ Самоподписанный сертификат создан"
    log_warn "⚠️  Браузер будет показывать предупреждение о недоверенном сертификате"
    
    SSL_SUCCESS=true
}

enable_https_config() {
    log_info "Включение HTTPS конфигурации..."
    
    # Создание HTTPS конфигурации
    cat > "/etc/nginx/sites-available/gochs-ssl" << EOF
# GO-CHS Информирование - HTTPS конфигурация
server {
    listen ${HTTPS_PORT} ssl http2 default_server;
    listen [::]:${HTTPS_PORT} ssl http2 default_server;
    server_name _;
    
    ssl_certificate /etc/nginx/ssl/gochs.crt;
    ssl_certificate_key /etc/nginx/ssl/gochs.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    add_header Strict-Transport-Security "max-age=31536000" always;
    
    root $INSTALL_DIR/frontend/build;
    index index.html;
    
    access_log /var/log/nginx/gochs-ssl-access.log json;
    error_log /var/log/nginx/gochs-ssl-error.log;
    
    location / {
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
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
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }
    
    location /recordings {
        alias $INSTALL_DIR/recordings;
        add_header Accept-Ranges bytes;
        add_header Access-Control-Allow-Origin *;
    }
    
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    location ~ /\. {
        deny all;
    }
}

# Редирект с HTTP на HTTPS
server {
    listen ${HTTP_PORT};
    listen [::]:${HTTP_PORT};
    server_name _;
    return 301 https://\$server_name\$request_uri;
}
EOF

    # Замена HTTP конфигурации на HTTPS
    rm -f /etc/nginx/sites-enabled/gochs
    ln -sf /etc/nginx/sites-available/gochs-ssl /etc/nginx/sites-enabled/gochs-ssl
    
    if nginx -t 2>&1; then
        log_info "HTTPS конфигурация активирована"
    else
        log_error "Ошибка в HTTPS конфигурации"
        return 1
    fi
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

    sysctl -p /etc/sysctl.d/99-nginx.conf 2>/dev/null || true
    
    log_info "Nginx оптимизирован"
}

setup_monitoring() {
    log_info "Настройка мониторинга Nginx..."
    
    cat > "$INSTALL_DIR/scripts/nginx_metrics.sh" << 'EOF'
#!/bin/bash
METRICS_FILE="/opt/gochs-informing/logs/nginx_metrics.prom"
STATUS=$(curl -s http://localhost/nginx_status 2>/dev/null)

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
nginx_connections_active ${ACTIVE:-0}
nginx_connections_reading ${READING:-0}
nginx_connections_writing ${WRITING:-0}
nginx_connections_waiting ${WAITING:-0}
nginx_http_requests_total ${REQUESTS:-0}
PROM
fi
EOF

    chmod +x "$INSTALL_DIR/scripts/nginx_metrics.sh"
    (crontab -l 2>/dev/null | grep -v "nginx_metrics.sh"; echo "* * * * * $INSTALL_DIR/scripts/nginx_metrics.sh") | crontab - 2>/dev/null || true
    
    log_info "Мониторинг Nginx настроен"
}

setup_fail2ban() {
    log_info "Настройка fail2ban для Nginx..."
    
    # Установка fail2ban если не установлен
    if ! command -v fail2ban-server &>/dev/null; then
        apt-get install -y fail2ban 2>/dev/null || true
    fi
    
    if [[ -d /etc/fail2ban ]]; then
        cat > /etc/fail2ban/jail.d/nginx.local << 'EOF'
[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 3600

[nginx-botsearch]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
bantime = 1800
EOF

        systemctl restart fail2ban 2>/dev/null || true
        log_info "fail2ban настроен для Nginx"
    fi
}

setup_logrotate() {
    log_info "Настройка ротации логов Nginx..."
    
    cat > /etc/logrotate.d/nginx-gochs << EOF
/var/log/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 www-data adm
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 \$(cat /var/run/nginx.pid)
        fi
    endscript
}
EOF

    log_info "Ротация логов настроена"
}

create_test_frontend() {
    log_info "Создание тестового фронтенда..."
    
    if [[ ! -f "$INSTALL_DIR/frontend/build/index.html" ]]; then
        cat > "$INSTALL_DIR/frontend/build/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ГО-ЧС Информирование</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 700px;
            width: 100%;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #1a1a2e;
            font-size: 32px;
            margin-bottom: 8px;
        }
        .header .badge {
            display: inline-block;
            background: #e94560;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .status-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .status-icon {
            font-size: 28px;
            margin-bottom: 8px;
        }
        .status-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
            font-size: 14px;
        }
        .status-value {
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 20px;
            display: inline-block;
        }
        .status-online { background: #10b981; color: white; }
        .status-offline { background: #ef4444; color: white; }
        .status-checking { background: #f59e0b; color: white; }
        .info-section {
            background: #f0f4ff;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .info-section h3 {
            color: #1a1a2e;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .info-item {
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid #ddd;
        }
        .info-item:last-child {
            border-bottom: none;
        }
        .info-label {
            font-weight: 500;
            color: #555;
            width: 100px;
        }
        .info-value {
            color: #333;
            font-family: monospace;
        }
        .commands {
            background: #1e1e1e;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }
        .commands code {
            color: #d4d4d4;
            font-family: monospace;
            font-size: 13px;
            display: block;
            margin: 5px 0;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            color: #999;
            font-size: 12px;
        }
        a {
            color: #e94560;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 ГО-ЧС Информирование</h1>
            <span class="badge">Система оповещения v1.0</span>
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <div class="status-icon">🌐</div>
                <div class="status-name">Nginx</div>
                <span class="status-value status-online" id="nginx-status">✓ Онлайн</span>
            </div>
            <div class="status-card">
                <div class="status-icon">⚡</div>
                <div class="status-name">API</div>
                <span class="status-value status-checking" id="api-status">⏳ Проверка</span>
            </div>
            <div class="status-card">
                <div class="status-icon">🗄️</div>
                <div class="status-name">PostgreSQL</div>
                <span class="status-value status-checking" id="db-status">⏳ Проверка</span>
            </div>
            <div class="status-card">
                <div class="status-icon">📦</div>
                <div class="status-name">Redis</div>
                <span class="status-value status-checking" id="redis-status">⏳ Проверка</span>
            </div>
            <div class="status-card">
                <div class="status-icon">📞</div>
                <div class="status-name">Asterisk</div>
                <span class="status-value status-checking" id="asterisk-status">⏳ Проверка</span>
            </div>
        </div>
        
        <div class="info-section">
            <h3>📋 Учетные данные для входа</h3>
            <div class="info-item">
                <span class="info-label">Логин:</span>
                <span class="info-value">admin</span>
            </div>
            <div class="info-item">
                <span class="info-label">Пароль:</span>
                <span class="info-value">Admin123!</span>
            </div>
            <div class="info-item">
                <span class="info-label">API Docs:</span>
                <span class="info-value"><a href="/docs" target="_blank">/docs</a></span>
            </div>
        </div>
        
        <div class="info-section">
            <h3>🔧 Управление системой</h3>
            <div class="commands">
                <code># Статус всех сервисов</code>
                <code>systemctl status gochs-* redis-server asterisk nginx</code>
                <code style="margin-top: 10px;"># Просмотр логов API</code>
                <code>journalctl -u gochs-api -f</code>
                <code style="margin-top: 10px;"># Перезапуск сервисов</code>
                <code>systemctl restart gochs-api gochs-worker</code>
            </div>
        </div>
        
        <div class="footer">
            © 2026 ГО-ЧС Информирование | Все права защищены
        </div>
    </div>
    
    <script>
        async function checkStatus() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                
                document.getElementById('api-status').innerHTML = '✓ Онлайн';
                document.getElementById('api-status').className = 'status-value status-online';
                
                if (data.database) {
                    document.getElementById('db-status').innerHTML = '✓ Онлайн';
                    document.getElementById('db-status').className = 'status-value status-online';
                }
                if (data.redis) {
                    document.getElementById('redis-status').innerHTML = '✓ Онлайн';
                    document.getElementById('redis-status').className = 'status-value status-online';
                }
                if (data.asterisk) {
                    document.getElementById('asterisk-status').innerHTML = '✓ Онлайн';
                    document.getElementById('asterisk-status').className = 'status-value status-online';
                }
            } catch (error) {
                document.getElementById('api-status').innerHTML = '✗ Офлайн';
                document.getElementById('api-status').className = 'status-value status-offline';
            }
        }
        
        checkStatus();
        setInterval(checkStatus, 10000);
    </script>
</body>
</html>
EOF
        log_info "Тестовый фронтенд создан"
    else
        log_info "Фронтенд уже существует"
    fi
    
    chown -R www-data:www-data "$INSTALL_DIR/frontend/build" 2>/dev/null || true
    chmod -R 755 "$INSTALL_DIR/frontend/build"
}

start_nginx() {
    log_info "Запуск Nginx..."
    
    systemctl enable nginx
    systemctl restart nginx
    
    sleep 2
    
    if systemctl is-active --quiet nginx; then
        log_info "Nginx успешно запущен"
    else
        log_error "Ошибка запуска Nginx"
        systemctl status nginx --no-pager -l
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
curl -s http://localhost/nginx_status 2>/dev/null || echo "Статус недоступен"

echo -e "\n=== Последние ошибки ==="
tail -20 /var/log/nginx/error.log 2>/dev/null || echo "Лог ошибок пуст"

echo -e "\n=== Последние запросы ==="
tail -10 /var/log/nginx/gochs-access.log 2>/dev/null || tail -10 /var/log/nginx/access.log 2>/dev/null
EOF

    # Скрипт для просмотра логов
    cat > "$INSTALL_DIR/scripts/nginx_logs.sh" << 'EOF'
#!/bin/bash
if [[ "$1" == "error" ]]; then
    tail -f /var/log/nginx/error.log
elif [[ "$1" == "access" ]]; then
    tail -f /var/log/nginx/gochs-access.log 2>/dev/null || tail -f /var/log/nginx/access.log
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

echo -n "HTTP: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "301" ]] || [[ "$HTTP_CODE" == "302" ]]; then
    echo "OK ($HTTP_CODE)"
else
    echo "FAILED ($HTTP_CODE)"
fi

echo -n "API: "
if curl -s http://localhost/health 2>/dev/null | grep -q "healthy"; then
    echo "OK"
else
    echo "FAILED (API недоступен)"
fi

echo -n "Static: "
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200\|301\|302"; then
    echo "OK"
else
    echo "FAILED"
fi
EOF

    # Скрипт проверки SSL сертификата
    cat > "$INSTALL_DIR/scripts/nginx_ssl_check.sh" << 'EOF'
#!/bin/bash
if [[ -f /etc/nginx/ssl/gochs.crt ]]; then
    echo "=== Информация о SSL сертификате ==="
    openssl x509 -in /etc/nginx/ssl/gochs.crt -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After :"
else
    echo "SSL сертификат не найден"
fi
EOF

    chmod +x "$INSTALL_DIR"/scripts/nginx_*.sh
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/scripts" 2>/dev/null || true
    
    log_info "Скрипты управления созданы в $INSTALL_DIR/scripts"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    systemctl stop nginx 2>/dev/null
    systemctl disable nginx 2>/dev/null
    
    rm -f /etc/nginx/sites-enabled/gochs
    rm -f /etc/nginx/sites-enabled/gochs-ssl
    rm -f /etc/nginx/sites-available/gochs
    rm -f /etc/nginx/sites-available/gochs-ssl
    
    crontab -l 2>/dev/null | grep -v "nginx_metrics.sh" | crontab - 2>/dev/null || true
    crontab -l 2>/dev/null | grep -v "certbot renew" | crontab - 2>/dev/null || true
    
    rm -f "$INSTALL_DIR"/scripts/nginx_*.sh
    rm -rf /etc/nginx/ssl
    
    read -p "Удалить Nginx полностью? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt-get remove --purge -y nginx nginx-common nginx-full 2>/dev/null
        apt-get autoremove -y 2>/dev/null
        log_info "Nginx удален"
    fi
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    if systemctl is-active --quiet nginx; then
        log_info "✓ Сервис Nginx: активен"
        
        NGINX_VER=$(nginx -v 2>&1 | grep -oP 'nginx/\K[\d.]+')
        log_info "  Версия: $NGINX_VER"
        
        if nginx -t &>/dev/null; then
            log_info "  Конфигурация: OK"
        else
            log_error "  Конфигурация: Ошибка"
            status=1
        fi
        
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null)
        if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "301" ]] || [[ "$HTTP_CODE" == "302" ]]; then
            log_info "  HTTP доступ: OK ($HTTP_CODE)"
        else
            log_warn "  HTTP доступ: Ошибка ($HTTP_CODE)"
            status=1
        fi
        
    else
        log_error "✗ Сервис Nginx: не активен"
        status=1
    fi
    
    if [[ -f /etc/nginx/ssl/gochs.crt ]]; then
        log_info "✓ SSL сертификат: установлен"
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/nginx/ssl/gochs.crt 2>/dev/null | cut -d= -f2)
        if [[ -n "$EXPIRY" ]]; then
            log_info "  Срок действия: $EXPIRY"
        fi
    else
        log_info "SSL: не настроен"
    fi
    
    if [[ -f "$INSTALL_DIR/frontend/build/index.html" ]]; then
        log_info "✓ Фронтенд: найден"
    else
        log_warn "✗ Фронтенд: отсутствует"
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
        if [[ "${2:-}" == "error" ]]; then
            tail -f /var/log/nginx/error.log
        else
            tail -f /var/log/nginx/gochs-access.log 2>/dev/null || tail -f /var/log/nginx/access.log
        fi
        ;;
    test)
        if [[ -f "$INSTALL_DIR/scripts/nginx_test.sh" ]]; then
            bash "$INSTALL_DIR/scripts/nginx_test.sh"
        else
            curl -s http://localhost/health 2>/dev/null | python3 -m json.tool 2>/dev/null || curl -s http://localhost/health
        fi
        ;;
    ssl-setup)
        if [[ "$SSL_MODE" == "letsencrypt" ]]; then
            setup_letsencrypt
        elif [[ "$SSL_MODE" == "selfsigned" ]]; then
            create_self_signed_cert
            enable_https_config
        else
            echo "SSL_MODE=$SSL_MODE - настройка SSL не требуется"
        fi
        systemctl restart nginx
        ;;
    ssl-check)
        if [[ -f "$INSTALL_DIR/scripts/nginx_ssl_check.sh" ]]; then
            bash "$INSTALL_DIR/scripts/nginx_ssl_check.sh"
        fi
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|reload|restart|logs [error|access]|test|ssl-setup|ssl-check}"
        exit 1
        ;;
esac
