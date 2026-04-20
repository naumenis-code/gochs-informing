#!/bin/bash

################################################################################
# Модуль: 08-nginx.sh
# Назначение: Установка и настройка Nginx веб-сервера
# Версия: 1.0.6 (полная исправленная версия)
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
        openssl rand -base64 16 2>/dev/null | tr -d "=+/" | cut -c1-16 || echo "NginxPass$(date +%s)"
    }
    check_port_free() {
        local port="$1"
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            return 1
        fi
        return 0
    }
fi

MODULE_NAME="08-nginx"
MODULE_DESCRIPTION="Nginx веб-сервер и прокси"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Fallback: загрузка из .env
if [[ -z "$DOMAIN_OR_IP" ]] && [[ -f "$INSTALL_DIR/.env" ]]; then
    source "$INSTALL_DIR/.env"
fi

INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
DOMAIN_OR_IP="${DOMAIN_OR_IP:-localhost}"
SSL_MODE="${SSL_MODE:-selfsigned}"
GOCHS_USER="${GOCHS_USER:-gochs}"
GOCHS_GROUP="${GOCHS_GROUP:-gochs}"

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
            log_warn "Неизвестный режим SSL: $SSL_MODE, создаем самоподписанный"
            create_self_signed_cert
            enable_https_config
            ;;
    esac
    
    optimize_nginx
    setup_monitoring
    create_test_frontend
    start_nginx
    create_management_scripts
    setup_fail2ban
    setup_logrotate
    
    mark_module_installed "$MODULE_NAME"
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ДОСТУП К СИСТЕМЕ:${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${WHITE}Web интерфейс:${NC}     ${GREEN}https://$DOMAIN_OR_IP${NC}"
    echo -e "  ${WHITE}API документация:${NC}  ${GREEN}https://$DOMAIN_OR_IP/docs${NC}"
    echo -e "  ${WHITE}Health check:${NC}     ${GREEN}https://$DOMAIN_OR_IP/health${NC}"
    echo ""
    echo -e "  ${YELLOW}⚠️  Используется самоподписанный SSL сертификат${NC}"
    echo -e "  ${YELLOW}   Примите предупреждение в браузере${NC}"
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
    
    # Проверка портов
    if ! check_port_free "$HTTP_PORT"; then
        log_warn "Порт $HTTP_PORT уже используется"
    fi
    if ! check_port_free "$HTTPS_PORT"; then
        log_warn "Порт $HTTPS_PORT уже используется"
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
    
    ensure_dir "/etc/nginx/ssl"
    ensure_dir "/etc/nginx/conf.d"
    ensure_dir "/var/log/nginx"
    ensure_dir "/var/cache/nginx"
    ensure_dir "$INSTALL_DIR/frontend/build"
    ensure_dir "$INSTALL_DIR/logs"
    ensure_dir "$INSTALL_DIR/recordings"
    ensure_dir "$INSTALL_DIR/scripts"
    
    # Очистка старых конфигов - ИСПРАВЛЕНИЕ
    rm -f /etc/nginx/sites-enabled/* 2>/dev/null || true
    rm -f /etc/nginx/conf.d/*.conf 2>/dev/null || true
    rm -f /etc/nginx/sites-available/* 2>/dev/null || true
    
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
}
EOF

    log_info "Основная конфигурация Nginx создана"
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
    
    log_info "Получение сертификата для $DOMAIN_OR_IP..."
    
    if certbot --nginx -d "$DOMAIN_OR_IP" --non-interactive --agree-tos -m "$ADMIN_EMAIL" --redirect 2>&1 | tee -a /tmp/certbot.log; then
        log_info "✅ SSL сертификат Let's Encrypt успешно установлен!"
        
        # Автоматическое обновление
        (crontab -l 2>/dev/null | grep -v "certbot renew"; echo "0 0 * * * certbot renew --quiet --post-hook 'nginx -s reload'") | crontab - 2>/dev/null || true
        log_info "Настроено автоматическое обновление сертификата"
        
        SSL_SUCCESS=true
    else
        log_error "Не удалось получить сертификат Let's Encrypt"
        log_info "Создаем самоподписанный сертификат..."
        create_self_signed_cert
        enable_https_config
    fi
}

create_self_signed_cert() {
    log_info "Создание самоподписанного SSL сертификата..."
    
    ensure_dir "/etc/nginx/ssl"
    
    # Генерация сертификата
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/gochs.key \
        -out /etc/nginx/ssl/gochs.crt \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=GOCHS/CN=$DOMAIN_OR_IP" 2>/dev/null
    
    chmod 600 /etc/nginx/ssl/gochs.key
    chmod 644 /etc/nginx/ssl/gochs.crt
    
    log_info "✅ Самоподписанный сертификат создан (срок действия 10 лет)"
    log_warn "⚠️  Браузер будет показывать предупреждение о недоверенном сертификате"
    
    SSL_SUCCESS=true
}

enable_https_config() {
    log_info "Создание HTTPS конфигурации..."
    
    # ИСПРАВЛЕНИЕ: Правильная конфигурация с редиректом и прокси
    cat > "/etc/nginx/conf.d/gochs.conf" << 'EOF'
# HTTP -> HTTPS редирект
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS сервер
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;
    
    ssl_certificate /etc/nginx/ssl/gochs.crt;
    ssl_certificate_key /etc/nginx/ssl/gochs.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    root /opt/gochs-informing/frontend/build;
    index index.html;
    
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }
    
    # WebSocket - ВАЖНО: должен быть ДО location /
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
    
    # Статические файлы - ВАЖНО: должен быть ПОСЛЕДНИМ
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

    # Замена переменных в конфиге
    sed -i "s|/opt/gochs-informing|$INSTALL_DIR|g" /etc/nginx/conf.d/gochs.conf
    
    if nginx -t 2>&1; then
        log_info "HTTPS конфигурация создана и проверена"
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
            max-width: 800px;
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
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
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
            font-size: 32px;
            margin-bottom: 10px;
        }
        .status-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        .status-value {
            font-size: 14px;
            padding: 4px 12px;
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
            width: 120px;
        }
        .info-value {
            color: #333;
            font-family: monospace;
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
            <h3>📋 Учетные данные</h3>
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
                <span class="info-value"><a href="/docs">/docs</a></span>
            </div>
            <div class="info-item">
                <span class="info-label">Health:</span>
                <span class="info-value"><a href="/health">/health</a></span>
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
    
    # ИСПРАВЛЕНИЕ: Полная остановка перед запуском
    systemctl stop nginx 2>/dev/null || true
    pkill -f nginx 2>/dev/null || true
    sleep 2
    
    systemctl enable nginx
    systemctl start nginx
    
    if wait_for_service "nginx" 10; then
        log_info "Nginx успешно запущен"
        
        # Проверка HTTPS
        sleep 2
        if curl -sk https://localhost/health 2>/dev/null | grep -q "status"; then
            log_info "HTTPS и API прокси работают корректно"
        fi
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

echo -e "\n=== Порты ==="
netstat -tlnp 2>/dev/null | grep nginx

echo -e "\n=== Тест HTTP -> HTTPS ==="
curl -sI http://localhost/ 2>/dev/null | head -3

echo -e "\n=== Тест HTTPS API ==="
curl -sk https://localhost/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "API недоступен"

echo -e "\n=== Последние ошибки ==="
tail -10 /var/log/nginx/error.log 2>/dev/null || echo "Лог ошибок пуст"
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

echo -n "HTTP (редирект): "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null)
if [[ "$HTTP_CODE" == "301" ]] || [[ "$HTTP_CODE" == "302" ]]; then
    echo "OK ($HTTP_CODE)"
else
    echo "FAILED ($HTTP_CODE)"
fi

echo -n "HTTPS: "
HTTPS_CODE=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/ 2>/dev/null)
if [[ "$HTTPS_CODE" == "200" ]]; then
    echo "OK (200)"
else
    echo "FAILED ($HTTPS_CODE)"
fi

echo -n "API health: "
if curl -sk https://localhost/health 2>/dev/null | grep -q "status"; then
    echo "OK"
    curl -sk https://localhost/health 2>/dev/null | python3 -m json.tool 2>/dev/null | head -7
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
    
    rm -f /etc/nginx/conf.d/gochs.conf
    rm -f /etc/nginx/ssl/gochs.*
    
    crontab -l 2>/dev/null | grep -v "nginx_metrics.sh" | crontab - 2>/dev/null || true
    crontab -l 2>/dev/null | grep -v "certbot renew" | crontab - 2>/dev/null || true
    
    rm -f "$INSTALL_DIR"/scripts/nginx_*.sh
    
    read -p "Удалить Nginx полностью? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt-get remove --purge -y nginx nginx-common nginx-full 2>/dev/null
        apt-get autoremove -y 2>/dev/null
        rm -rf /etc/nginx
        rm -rf /var/log/nginx
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
    
    if curl -sk https://localhost/health 2>/dev/null | grep -q "status"; then
        log_info "✓ API прокси: работает"
    else
        log_warn "✗ API прокси: не работает"
        status=1
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
            curl -sk https://localhost/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "API недоступен"
        fi
        ;;
    ssl-check)
        if [[ -f "$INSTALL_DIR/scripts/nginx_ssl_check.sh" ]]; then
            bash "$INSTALL_DIR/scripts/nginx_ssl_check.sh"
        fi
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|reload|restart|logs [error|access]|test|ssl-check}"
        exit 1
        ;;
esac
