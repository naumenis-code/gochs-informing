#!/bin/bash

################################################################################
# Модуль: 01-system.sh
# Назначение: Установка системных зависимостей и подготовка ОС
################################################################################

# Определение путей
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Загрузка общих функций
if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

install() {
    log_step "Установка системных зависимостей"
    
    # Проверка ОС
    if [[ ! -f /etc/debian_version ]] || [[ $(lsb_release -rs) != "12" ]]; then
        log_error "Требуется Debian 12 (Bookworm)"
        return 1
    fi
    
    # Обновление системы
    log_info "Обновление пакетов..."
    apt-get update
    apt-get upgrade -y
    
    # Установка основных утилит
    log_info "Установка основных системных утилит..."
    apt-get install -y \
        wget curl git unzip tar \
        build-essential pkg-config automake autoconf \
        libtool binutils \
        sudo net-tools htop iotop \
        vim nano \
        ufw fail2ban \
        certbot \
        software-properties-common \
        lsb-release gnupg2 \
        ca-certificates \
        locales \
        tzdata
    
    # Настройка локали
    log_info "Настройка локали..."
    locale-gen ru_RU.UTF-8
    update-locale LANG=ru_RU.UTF-8
    
    # Настройка часового пояса
    log_info "Настройка часового пояса..."
    timedatectl set-timezone Europe/Moscow
    
    # Установка библиотек для работы с аудио
    log_info "Установка аудио библиотек..."
    apt-get install -y \
        ffmpeg \
        sox \
        libsox-fmt-all \
        lame \
        libmp3lame-dev \
        libvorbis-dev \
        libogg-dev \
        libopus-dev \
        libsndfile1-dev \
        portaudio19-dev \
        pulseaudio \
        alsa-utils
    
    # Установка библиотек для Asterisk
    log_info "Установка библиотек для Asterisk..."
    apt-get install -y \
        libjansson-dev \
        libxml2-dev \
        libncurses5-dev \
        libsqlite3-dev \
        libssl-dev \
        libsrtp2-dev \
        uuid-dev \
        libedit-dev \
        libpcap-dev \
        libspandsp-dev \
        libopenr2-dev \
        libiksemel-dev \
        libcurl4-openssl-dev \
        libical-dev \
        libneon27-dev \
        libgmime-3.0-dev \
        liburiparser-dev \
        libpq-dev \
        libmariadb-dev \
        libsnmp-dev \
        libldap2-dev \
        libpopt-dev \
        libnewt-dev \
        libtiff-dev \
        unixodbc-dev \
        libresample1-dev \
        libltdl-dev
    
    # Установка библиотек для Python
    log_info "Установка библиотек для Python..."
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-setuptools \
        python3-wheel
    
    # Создание пользователя системы
    log_info "Создание системного пользователя..."
    if ! id -u "$GOCHS_USER" &>/dev/null; then
        useradd -r -m -d "$INSTALL_DIR" -s /bin/bash "$GOCHS_USER"
        usermod -aG audio "$GOCHS_USER"
        usermod -aG www-data "$GOCHS_USER"
    fi
    
    # Создание структуры каталогов
    log_info "Создание структуры каталогов..."
    mkdir -p "$INSTALL_DIR"/{app,frontend,logs,recordings,generated_voice,playbooks,backups,exports}
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    
    # Настройка firewall
    log_info "Настройка firewall (UFW)..."
    ufw --force disable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    ufw allow 5060/udp comment 'SIP'
    ufw allow 10000:20000/udp comment 'RTP'
    ufw --force enable
    
    # Настройка fail2ban
    log_info "Настройка fail2ban..."
    systemctl enable fail2ban
    systemctl start fail2ban
    
    # Оптимизация системы
    log_info "Оптимизация системных параметров..."
    
    # Увеличение лимитов
    cat >> /etc/security/limits.conf << EOF
# GO-CHS System Limits
$GOCHS_USER soft nofile 65536
$GOCHS_USER hard nofile 65536
$GOCHS_USER soft nproc 32768
$GOCHS_USER hard nproc 32768
EOF
    
    # Оптимизация сетевых параметров
    cat >> /etc/sysctl.d/99-gochs.conf << EOF
# GO-CHS Network Optimization
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.ip_local_port_range = 1024 65535
EOF
    
    sysctl -p /etc/sysctl.d/99-gochs.conf
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    return 0
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Удаление пользователя
    if id -u "$GOCHS_USER" &>/dev/null; then
        userdel -r "$GOCHS_USER" 2>/dev/null || true
    fi
    
    # Удаление конфигурационных файлов
    rm -f /etc/sysctl.d/99-gochs.conf
    sed -i '/# GO-CHS System Limits/d' /etc/security/limits.conf
    sed -i '/gochs/d' /etc/security/limits.conf
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    # Проверка версии ОС
    if [[ -f /etc/debian_version ]] && [[ $(lsb_release -rs) == "12" ]]; then
        log_info "ОС: Debian 12 - OK"
    else
        log_error "ОС: Не соответствует требованиям"
        status=1
    fi
    
    # Проверка пользователя
    if id -u "$GOCHS_USER" &>/dev/null; then
        log_info "Пользователь $GOCHS_USER: Создан"
    else
        log_warn "Пользователь $GOCHS_USER: Не создан"
        status=1
    fi
    
    # Проверка директорий
    if [[ -d "$INSTALL_DIR" ]]; then
        log_info "Директория $INSTALL_DIR: Существует"
    else
        log_warn "Директория $INSTALL_DIR: Отсутствует"
        status=1
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
    *)
        echo "Использование: $0 {install|uninstall|status}"
        exit 1
        ;;
esac
