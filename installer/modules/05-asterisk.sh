#!/bin/bash

################################################################################
# Модуль: 05-asterisk.sh
# Назначение: Установка и настройка Asterisk 20 LTS
# Версия: 1.0.2 (исправленная - полная версия)
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

MODULE_NAME="05-asterisk"
MODULE_DESCRIPTION="Asterisk 20 LTS - ядро телефонии"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
    DOMAIN_OR_IP="${DOMAIN_OR_IP:-localhost}"
    FREEPBX_HOST="${FREEPBX_HOST:-192.168.1.10}"
    FREEPBX_PORT="${FREEPBX_PORT:-5060}"
    FREEPBX_EXTENSION="${FREEPBX_EXTENSION:-gochs}"
    FREEPBX_USERNAME="${FREEPBX_USERNAME:-gochs}"
    FREEPBX_PASSWORD="${FREEPBX_PASSWORD:-changeme}"
    ASTERISK_AMI_PORT="${ASTERISK_AMI_PORT:-5038}"
    ASTERISK_AMI_USER="${ASTERISK_AMI_USER:-gochs_ami}"
    ASTERISK_AMI_PASSWORD="${ASTERISK_AMI_PASSWORD:-$(generate_password)}"
    ASTERISK_ARI_PASSWORD="${ASTERISK_ARI_PASSWORD:-$(generate_password)}"
    ASTERISK_ADMIN_PASSWORD="${ASTERISK_ADMIN_PASSWORD:-$(generate_password)}"
    ASTERISK_MONITOR_PASSWORD="${ASTERISK_MONITOR_PASSWORD:-$(generate_password)}"
    GOCHS_USER="${GOCHS_USER:-gochs}"
    GOCHS_GROUP="${GOCHS_GROUP:-gochs}"
fi

# Версия Asterisk
ASTERISK_VERSION="20"
ASTERISK_FALLBACK_VERSION="20.11.1"
ASTERISK_FULL_VERSION="20.11.0"
ASTERISK_DOWNLOAD_URL="http://downloads.asterisk.org/pub/telephony/asterisk"

# ============================================================================
# ИСПРАВЛЕНИЕ 1: Функция проверки доступности версии и автоопределения
# ============================================================================
check_version_availability() {
    log_info "Проверка доступности Asterisk $ASTERISK_FULL_VERSION..."
    
    # Проверяем существование файла
    if wget --spider --timeout=10 "$ASTERISK_DOWNLOAD_URL/asterisk-${ASTERISK_FULL_VERSION}.tar.gz" 2>/dev/null; then
        log_info "Версия $ASTERISK_FULL_VERSION доступна"
        return 0
    fi
    
    log_warn "Версия $ASTERISK_FULL_VERSION не найдена на сервере"
    
    # Пытаемся получить список доступных версий
    local latest_version=$(wget -q -O- http://downloads.asterisk.org/pub/telephony/asterisk/ 2>/dev/null | \
                          grep -oP "asterisk-20\.\d+\.\d+" | \
                          sort -V | tail -1 | cut -d'-' -f2)
    
    if [[ -n "$latest_version" ]]; then
        ASTERISK_FULL_VERSION="$latest_version"
        log_info "Найдена актуальная версия: $ASTERISK_FULL_VERSION"
        return 0
    fi
    
    # Альтернативные версии
    local fallbacks=("20.11.1" "20.10.0" "20.9.0" "20.8.0" "20.7.0")
    for ver in "${fallbacks[@]}"; do
        if wget --spider --timeout=5 "$ASTERISK_DOWNLOAD_URL/asterisk-${ver}.tar.gz" 2>/dev/null; then
            ASTERISK_FULL_VERSION="$ver"
            log_info "Используем fallback версию: $ASTERISK_FULL_VERSION"
            return 0
        fi
    done
    
    log_error "Не удалось найти доступную версию Asterisk 20"
    return 1
}

install() {
    log_step "Установка Asterisk $ASTERISK_VERSION LTS"
    
    # Проверка зависимостей
    check_dependencies
    
    # ИСПРАВЛЕНИЕ: Проверка доступности версии перед установкой
    check_version_availability || return 1
    
    # Установка Asterisk
    install_asterisk
    
    # Настройка Asterisk
    configure_asterisk
    
    # Создание директорий для ГО-ЧС
    create_directories
    
    # Настройка systemd службы
    configure_systemd
    
    # Запуск Asterisk
    start_asterisk
    
    # Создание скриптов управления
    create_management_scripts
    
    # Настройка интеграции с API
    setup_api_integration
    
    # Отметка об установке
    mark_module_installed "$MODULE_NAME"
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Asterisk версия: $ASTERISK_FULL_VERSION"
    log_info "AMI порт: $ASTERISK_AMI_PORT"
    log_info "AMI пользователь: $ASTERISK_AMI_USER"
    
    return 0
}

check_dependencies() {
    log_info "Проверка зависимостей..."
    
    # Проверка прав root
    if [[ $EUID -ne 0 ]]; then
        log_error "Скрипт должен запускаться от root!"
        return 1
    fi
    
    # Проверка наличия необходимых инструментов
    local missing_tools=""
    for tool in wget tar make gcc; do
        if ! command -v $tool &>/dev/null; then
            missing_tools="$missing_tools $tool"
        fi
    done
    
    if [[ -n "$missing_tools" ]]; then
        log_warn "Установка недостающих инструментов:$missing_tools"
        apt-get update -qq
        apt-get install -y $missing_tools
    fi
    
    log_info "Зависимости проверены"
}

install_asterisk() {
    log_info "Установка Asterisk $ASTERISK_FULL_VERSION..."
    
    # Проверка, установлен ли уже Asterisk
    if command -v asterisk &> /dev/null; then
        ASTERISK_VER=$(asterisk -V 2>/dev/null | grep -oP 'Asterisk \K[0-9.]+' || echo "unknown")
        log_info "Asterisk уже установлен (версия $ASTERISK_VER)"
        
        # Проверка версии
        if [[ "$ASTERISK_VER" == "20."* ]]; then
            log_info "Версия Asterisk 20 LTS - OK"
            return 0
        else
            log_warn "Установлена версия $ASTERISK_VER, рекомендуется 20 LTS"
            read -p "Переустановить Asterisk? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                return 0
            fi
        fi
    fi
    
    # Установка зависимостей для компиляции
    log_info "Установка зависимостей для компиляции..."
    apt-get update -qq
    apt-get install -y \
        wget build-essential subversion git \
        libjansson-dev libxml2-dev libncurses5-dev libsqlite3-dev \
        libssl-dev libsrtp2-dev uuid-dev libedit-dev libpcap-dev \
        libspandsp-dev libopenr2-dev libiksemel-dev libcurl4-openssl-dev \
        libical-dev libneon27-dev libgmime-3.0-dev liburiparser-dev \
        libpq-dev libmariadb-dev libsnmp-dev libldap2-dev \
        libpopt-dev libnewt-dev libtiff-dev libresample1-dev libltdl-dev \
        libvorbis-dev libogg-dev libopus-dev libgsm1-dev \
        libspeex-dev libspeexdsp-dev libsndfile1-dev unixodbc-dev \
        libsrtp2-dev libspandsp-dev libopenr2-dev \
        libgmime-3.0-dev liburiparser-dev 2>/dev/null || true

    # Скачивание Asterisk
    log_info "Скачивание Asterisk $ASTERISK_FULL_VERSION..."
    cd /usr/src
    
    # Удаление старых архивов если есть
    rm -rf asterisk-${ASTERISK_FULL_VERSION}* 2>/dev/null || true
    
    # ИСПРАВЛЕНИЕ 2: Добавлены дополнительные зеркала
    local download_success=false
    local mirrors=(
        "$ASTERISK_DOWNLOAD_URL/asterisk-${ASTERISK_FULL_VERSION}.tar.gz"
        "https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-${ASTERISK_FULL_VERSION}.tar.gz"
        "http://downloads.asterisk.org/pub/telephony/asterisk/asterisk-${ASTERISK_FULL_VERSION}.tar.gz"
        "https://downloads.asterisk.org/pub/telephony/asterisk/old-releases/asterisk-${ASTERISK_FULL_VERSION}.tar.gz"
    )
    
    for mirror in "${mirrors[@]}"; do
        log_info "Попытка скачать с: $mirror"
        if wget -q --show-progress --timeout=30 "$mirror" 2>/dev/null; then
            download_success=true
            break
        fi
    done
    
    if [[ "$download_success" != "true" ]]; then
        log_error "Не удалось скачать Asterisk. Проверьте версию."
        return 1
    fi
    
    # Распаковка
    log_info "Распаковка архива..."
    tar xzf asterisk-${ASTERISK_FULL_VERSION}.tar.gz
    cd asterisk-${ASTERISK_FULL_VERSION}
    
    # Конфигурация
    log_info "Конфигурация Asterisk..."
    ./configure \
        --with-jansson-bundled \
        --with-pjproject-bundled \
        --with-srtp \
        --with-ssl \
        --with-ogg \
        --with-vorbis \
        --with-opus \
        --with-speex \
        --with-gsm \
        --with-sndfile 2>&1 | tee /tmp/asterisk_configure.log
    
    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        log_error "Ошибка конфигурации Asterisk"
        tail -20 /tmp/asterisk_configure.log
        return 1
    fi
    
    # Настройка menuselect
    log_info "Настройка модулей..."
    make menuselect.makeopts
    menuselect/menuselect --enable chan_pjsip --enable app_macro --enable app_playback \
        --enable codec_opus --enable codec_g729 --enable res_srtp \
        --enable res_ari --enable res_ari_applications --enable res_ari_channels \
        menuselect.makeopts 2>/dev/null || true
    
    # Сборка
    log_info "Сборка Asterisk (это может занять 10-15 минут)..."
    make -j$(nproc) 2>&1 | tee /tmp/asterisk_make.log
    
    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        log_error "Ошибка сборки Asterisk"
        tail -20 /tmp/asterisk_make.log
        return 1
    fi
    
    # Установка
    log_info "Установка Asterisk..."
    make install
    make samples
    make config
    make install-logrotate
    
    # Установка звуковых файлов
    log_info "Установка звуковых файлов..."
    make install sounds/ru 2>/dev/null || log_warn "Русские звуковые файлы не установлены"
    
    # Создание пользователя asterisk
    if ! id -u asterisk &>/dev/null; then
        useradd -r -d /var/lib/asterisk -s /sbin/nologin asterisk
        log_info "Пользователь asterisk создан"
    fi
    
    # Добавление пользователя в группы
    usermod -aG audio asterisk 2>/dev/null || true
    usermod -aG "$GOCHS_GROUP" asterisk 2>/dev/null || true
    
    # Установка прав
    chown -R asterisk:asterisk /var/lib/asterisk
    chown -R asterisk:asterisk /var/log/asterisk
    chown -R asterisk:asterisk /var/spool/asterisk
    chown -R asterisk:asterisk /usr/lib/asterisk
    
    # Очистка
    cd /
    rm -rf /usr/src/asterisk-${ASTERISK_FULL_VERSION}*

      # ============================================================
    # Установка русских звуковых файлов Asterisk (ИСПРАВЛЕНО)
    # ============================================================
    log_info "Установка русских звуковых файлов Asterisk..."
    cd /var/lib/asterisk/sounds

    # Создаем директорию для русского языка
    mkdir -p /var/lib/asterisk/sounds/ru

    # Скачиваем базовые звуки на русском
    log_info "Загрузка asterisk-core-sounds-ru-wav-current.tar.gz..."
    if ! wget -q --show-progress --timeout=30 https://downloads.asterisk.org/pub/telephony/sounds/asterisk-core-sounds-ru-wav-current.tar.gz 2>/dev/null; then
        log_warn "Не удалось скачать с основного зеркала, пробуем альтернативное..."
        if ! wget -q --show-progress --timeout=30 http://downloads.asterisk.org/pub/telephony/sounds/asterisk-core-sounds-ru-wav-current.tar.gz 2>/dev/null; then
            log_warn "Не удалось скачать русские звуки. Продолжаем без них."
        fi
    fi

    # Распаковываем если архив существует
    if [ -f asterisk-core-sounds-ru-wav-current.tar.gz ]; then
        log_info "Распаковка русских звуковых файлов..."
        tar -xzf asterisk-core-sounds-ru-wav-current.tar.gz
        rm -f asterisk-core-sounds-ru-wav-current.tar.gz
        
        # Перемещаем файлы в правильную директорию если они распаковались в поддиректорию
        if [ -d "ru" ]; then
            mv ru/* . 2>/dev/null || true
        fi
        
        log_info "Русские звуковые файлы установлены"
    fi

    # Устанавливаем права на все звуковые файлы
    chown -R asterisk:asterisk /var/lib/asterisk/sounds/
    chmod -R 755 /var/lib/asterisk/sounds/
    
    # ============================================================
    # Генерация аудио Playbook через TTS (ИСПРАВЛЕНО)
    # ============================================================
    if [ -f /opt/gochs-informing/playbooks/welcome.txt ]; then
        log_info "Генерация аудио Playbook через TTS..."
        
        # Устанавливаем espeak если его нет
        if ! command -v espeak &> /dev/null; then
            log_info "Установка espeak для синтеза речи..."
            apt-get update -qq
            apt-get install -y espeak espeak-data 2>/dev/null || {
                log_warn "Не удалось установить espeak. Пропускаем генерацию аудио."
            }
        fi
        
        # Генерируем WAV файл из текста
        if command -v espeak &> /dev/null; then
            log_info "Синтез речи через espeak..."
            espeak -v ru -s 150 -p 50 -f /opt/gochs-informing/playbooks/welcome.txt -w /opt/gochs-informing/playbooks/welcome.wav
            
            # Проверяем что файл создан
            if [ -f /opt/gochs-informing/playbooks/welcome.wav ]; then
                # Конвертируем в формат совместимый с Asterisk (8kHz, mono)
                if command -v sox &> /dev/null; then
                    sox /opt/gochs-informing/playbooks/welcome.wav -r 8000 -c 1 -b 16 /opt/gochs-informing/playbooks/welcome_8k.wav
                    mv /opt/gochs-informing/playbooks/welcome_8k.wav /opt/gochs-informing/playbooks/welcome.wav
                fi
                
                chown asterisk:asterisk /opt/gochs-informing/playbooks/welcome.wav
                chmod 644 /opt/gochs-informing/playbooks/welcome.wav
                log_info "Аудио Playbook создан: /opt/gochs-informing/playbooks/welcome.wav"
            else
                log_warn "Не удалось создать аудио Playbook"
            fi
        else
            log_warn "espeak не установлен, аудио Playbook не создан"
        fi
    else
        log_warn "Файл /opt/gochs-informing/playbooks/welcome.txt не найден"
    fi
    
    log_info "Asterisk $ASTERISK_FULL_VERSION установлен"
}

configure_asterisk() {
    log_info "Настройка конфигурации Asterisk..."
    
    local asterisk_conf_dir="/etc/asterisk"
    
    # Создание директорий если нет
    mkdir -p "$asterisk_conf_dir"
    
    # Резервное копирование оригинальных конфигураций
    for conf in asterisk.conf http.conf manager.conf pjsip.conf extensions.conf modules.conf logger.conf rtp.conf; do
        backup_file "$asterisk_conf_dir/$conf"
    done
    
    # asterisk.conf
    cat > "$asterisk_conf_dir/asterisk.conf" << EOF
[directories]
astetcdir => /etc/asterisk
astmoddir => /usr/lib/asterisk/modules
astvarlibdir => /var/lib/asterisk
astdbdir => /var/lib/asterisk
astkeydir => /var/lib/asterisk
astdatadir => /var/lib/asterisk
astagidir => /var/lib/asterisk/agi-bin
astspooldir => /var/spool/asterisk
astrundir => /var/run/asterisk
astlogdir => /var/log/asterisk
astsbindir => /usr/sbin

[options]
verbose = 3
debug = 0
alwaysfork = yes
nofork = no
quiet = no
timestamp = yes
execincludes = yes
internal_timing = yes
systemname = gochs-pbx
languageprefix = yes
maxcalls = 100
maxload = 0.9
minmemfree = 100

[compat]
pbx_realtime = 1.6
res_agi = 1.6
app_set = 1.6

[files]
astctlpermissions = 0660
astctlowner = asterisk
astctlgroup = asterisk
astctl = asterisk.ctl
EOF

    # http.conf (для ARI)
    cat > "$asterisk_conf_dir/http.conf" << EOF
[general]
enabled = yes
bindaddr = 127.0.0.1
bindport = 8088
tlsenable = no
prefix = ari
enablestatic = yes
sessionlimit = 100

[gochs]
read_only = no
password_format = plain
password = $ASTERISK_ARI_PASSWORD
EOF

    # manager.conf (AMI)
    cat > "$asterisk_conf_dir/manager.conf" << EOF
[general]
enabled = yes
port = $ASTERISK_AMI_PORT
bindaddr = 127.0.0.1
displayconnects = yes
timestampevents = yes
webenabled = yes
httptimeout = 60

[$ASTERISK_AMI_USER]
secret = $ASTERISK_AMI_PASSWORD
deny = 0.0.0.0/0.0.0.0
permit = 127.0.0.1/255.255.255.255
read = all
write = all
eventfilter = Event: Newchannel
eventfilter = Event: Hangup
eventfilter = Event: Dial
eventfilter = Event: Bridge
EOF

    # pjsip.conf
    cat > "$asterisk_conf_dir/pjsip.conf" << EOF
[global]
debug = no
endpoint_identifier_order = ip,username,anonymous

[transport-udp]
type = transport
protocol = udp
bind = 0.0.0.0:5060
external_media_address = $DOMAIN_OR_IP
external_signaling_address = $DOMAIN_OR_IP

[transport-tcp]
type = transport
protocol = tcp
bind = 0.0.0.0:5060
external_media_address = $DOMAIN_OR_IP
external_signaling_address = $DOMAIN_OR_IP

; Шаблон для исходящих вызовов
[gochs-outbound](!)
type = endpoint
context = gochs-outbound
disallow = all
allow = ulaw
allow = alaw
allow = g729
allow = opus
dtmf_mode = rfc4733
rtp_symmetric = yes
force_rport = yes
rewrite_contact = yes
direct_media = no
send_pai = yes
send_rpid = yes
trust_id_outbound = yes
device_state_busy_at = 1

; Шаблон для входящих вызовов
[gochs-inbound](!)
type = endpoint
context = gochs-inbound
disallow = all
allow = ulaw
allow = alaw
allow = g729
allow = opus
dtmf_mode = rfc4733
rtp_symmetric = yes
force_rport = yes
rewrite_contact = yes
direct_media = no

; Шаблон AOR
[gochs-aor](!)
type = aor
max_contacts = 1
remove_existing = yes

; Регистрация на FreePBX
[freepbx]
type = registration
outbound_auth = freepbx-auth
server_uri = sip:$FREEPBX_HOST:$FREEPBX_PORT
client_uri = sip:$FREEPBX_EXTENSION@$FREEPBX_HOST:$FREEPBX_PORT
contact_user = $FREEPBX_EXTENSION
retry_interval = 30
max_retries = 10
forbidden_retry_interval = 300

[freepbx-auth]
type = auth
auth_type = userpass
username = $FREEPBX_USERNAME
password = $FREEPBX_PASSWORD

; Эндпоинт для FreePBX
[freepbx-endpoint]
type = endpoint
aors = freepbx-aor
outbound_auth = freepbx-auth
context = gochs-outbound
callerid = "ГО-ЧС Информирование" <$FREEPBX_EXTENSION>
disallow = all
allow = ulaw
allow = alaw
allow = g729
allow = opus
dtmf_mode = rfc4733
rtp_symmetric = yes
force_rport = yes
rewrite_contact = yes
direct_media = no

[freepbx-aor]
type = aor
contact = sip:$FREEPBX_HOST:$FREEPBX_PORT
qualify_frequency = 60
EOF

    # extensions.conf
    cat > "$asterisk_conf_dir/extensions.conf" << 'EOF'
[globals]
GOCHS_RECORDING_DIR = /opt/gochs-informing/recordings
GOCHS_PLAYBOOK_DIR = /opt/gochs-informing/playbooks
GOCHS_VOICE_DIR = /opt/gochs-informing/generated_voice

[default]

[gochs-inbound]
; Обработка входящих звонков от FreePBX
exten => _X.,1,NoOp(Входящий звонок от ${CALLERID(num)})
 same => n,Set(CHANNEL(language)=ru)
 same => n,Answer()
 same => n,Wait(1)
 same => n,Playback(${GOCHS_PLAYBOOK_DIR}/welcome)
 same => n,Playback(beep)
 same => n,Set(FILENAME=${STRFTIME(${EPOCH},,%Y%m%d_%H%M%S)}_${CALLERID(num)})
 same => n,Record(${GOCHS_RECORDING_DIR}/${FILENAME}.wav,10,120,sk)
 same => n,Hangup()

[gochs-outbound]
; Исходящие вызовы через FreePBX
exten => _X.,1,NoOp(Исходящий вызов на ${EXTEN})
 same => n,Set(CHANNEL(language)=ru)
 same => n,Dial(PJSIP/${EXTEN}@freepbx-endpoint,60)
 same => n,Hangup()

[gochs-dialer]
; Контекст для массового обзвона
exten => s,1,NoOp(Массовый обзвон)
 same => n,Set(CALLERID(all)=ГО-ЧС <1000>)
 same => n,Dial(PJSIP/${DEST}@freepbx-endpoint,40,g)
 same => n,Hangup()

[gochs-answer]
exten => s,1,NoOp(Воспроизведение сценария)
 same => n,Wait(1)
 same => n,Playback(${GOCHS_VOICE_DIR}/scenario_${SCENARIO_ID})
 same => n,Wait(2)
 same => n,Hangup()
EOF

    # modules.conf
    cat > "$asterisk_conf_dir/modules.conf" << 'EOF'
[modules]
autoload = yes

; Отключаем устаревшие модули
noload => chan_sip.so
noload => chan_skinny.so
noload => chan_mgcp.so
noload => chan_oss.so
noload => chan_alsa.so
noload => chan_console.so

; Включаем PJSIP
load => res_pjsip.so
load => res_pjsip_authenticator_digest.so
load => res_pjsip_endpoint_identifier_ip.so
load => res_pjsip_outbound_registration.so
load => chan_pjsip.so

; Аудио кодеки
load => codec_ulaw.so
load => codec_alaw.so
load => codec_g729.so
load => codec_opus.so
load => codec_gsm.so
load => format_wav.so

; Функции
load => func_callerid.so
load => func_channel.so
load => func_strings.so
load => func_timeout.so

; Приложения
load => app_dial.so
load => app_playback.so
load => app_mixmonitor.so
load => app_record.so
load => app_echo.so

; Ресурсы
load => res_agi.so
load => res_ari.so
load => res_http_websocket.so
load => res_musiconhold.so
load => res_srtp.so
EOF

    # logger.conf
    cat > "$asterisk_conf_dir/logger.conf" << 'EOF'
[general]
dateformat = %F %T.%q

[logfiles]
console => notice,warning,error
messages => notice,warning,error,verbose(3)
full => notice,warning,error,debug,verbose(9)
gochs => notice,warning,error,call,event

[gochs]
file = /var/log/asterisk/gochs
levels = notice,warning,error,call,event
EOF

    # rtp.conf
    cat > "$asterisk_conf_dir/rtp.conf" << 'EOF'
[general]
rtpstart = 10000
rtpend = 20000
rtpchecksums = no
strictrtp = yes
EOF

    log_info "Конфигурация Asterisk создана"
}

create_directories() {
    log_info "Создание директорий для ГО-ЧС..."
    
    # Директории для записей и плейбуков
    mkdir -p "$INSTALL_DIR/recordings/inbound"
    mkdir -p "$INSTALL_DIR/recordings/outbound"
    mkdir -p "$INSTALL_DIR/playbooks"
    mkdir -p "$INSTALL_DIR/generated_voice"
    mkdir -p "$INSTALL_DIR/logs"
    
    # Установка прав
    chown -R asterisk:asterisk "$INSTALL_DIR/recordings" 2>/dev/null || true
    chown -R asterisk:asterisk "$INSTALL_DIR/playbooks" 2>/dev/null || true
    chown -R asterisk:asterisk "$INSTALL_DIR/generated_voice" 2>/dev/null || true
    chmod 755 "$INSTALL_DIR/recordings"
    chmod 755 "$INSTALL_DIR/playbooks"
    chmod 755 "$INSTALL_DIR/generated_voice"
    
    # Создание тестового приветствия
    if [[ ! -f "$INSTALL_DIR/playbooks/welcome.wav" ]]; then
        cat > "$INSTALL_DIR/playbooks/welcome.txt" << EOF
Здравствуйте.
Вы позвонили в систему ГО и ЧС информирования предприятия.
После звукового сигнала оставьте ваше сообщение.
EOF
        log_info "Создан текстовый файл приветствия"
    fi
    
    log_info "Директории созданы"
}

configure_systemd() {
    log_info "Настройка systemd службы Asterisk..."
    
    cat > /etc/systemd/system/asterisk.service << 'EOF'
[Unit]
Description=Asterisk PBX
Documentation=man:asterisk(8)
After=network.target
Wants=network.target

[Service]
Type=forking
Environment=HOME=/var/lib/asterisk
WorkingDirectory=/var/lib/asterisk
User=asterisk
Group=asterisk
ExecStart=/usr/sbin/asterisk -g -f -U asterisk -G asterisk
ExecStop=/usr/sbin/asterisk -rx 'core stop gracefully'
ExecReload=/usr/sbin/asterisk -rx 'core reload'
Restart=on-failure
RestartSec=10
LimitNOFILE=65536
LimitNPROC=32768
UMask=0007

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "Systemd служба создана"
}

start_asterisk() {
    log_info "Запуск Asterisk..."
    
    systemctl enable asterisk
    systemctl restart asterisk
    
    # Ожидание запуска
    sleep 5
    
    if systemctl is-active --quiet asterisk; then
        log_info "Asterisk успешно запущен"
        
        # Проверка версии
        asterisk -rx "core show version" 2>/dev/null | head -1

        # Проверка регистрации на FreePBX
        log_info "Проверка регистрации на FreePBX..."
        sleep 3
        if asterisk -rx "pjsip show registrations" 2>/dev/null | grep -q "freepbx.*Registered"; then
            log_info "✓ Регистрация на FreePBX успешна"
        else
            log_warn "✗ Регистрация на FreePBX не удалась"
            log_warn "  Проверьте настройки в config.env:"
            log_warn "  FREEPBX_HOST=$FREEPBX_HOST:$FREEPBX_PORT"
            log_warn "  FREEPBX_EXTENSION=$FREEPBX_EXTENSION"
            log_warn "  FREEPBX_USERNAME=$FREEPBX_USERNAME"
        fi
    else
        log_error "Проблема с запуском Asterisk"
        systemctl status asterisk --no-pager -l
        return 1
    fi
}

create_management_scripts() {
    log_info "Создание скриптов управления Asterisk..."
    
    mkdir -p "$INSTALL_DIR/scripts"
    
    # Скрипт для подключения к консоли
    cat > "$INSTALL_DIR/scripts/asterisk_console.sh" << 'EOF'
#!/bin/bash
asterisk -rvvvv
EOF

    # Скрипт для проверки статуса
    cat > "$INSTALL_DIR/scripts/asterisk_status.sh" << 'EOF'
#!/bin/bash
echo "=== Статус Asterisk ==="
asterisk -rx "core show uptime" 2>/dev/null || echo "Asterisk не запущен"
echo
asterisk -rx "core show channels" 2>/dev/null
echo
asterisk -rx "pjsip show registrations" 2>/dev/null
echo
asterisk -rx "pjsip show endpoints" 2>/dev/null
EOF

    # Скрипт для просмотра активных звонков
    cat > "$INSTALL_DIR/scripts/asterisk_active_calls.sh" << 'EOF'
#!/bin/bash
watch -n 1 'asterisk -rx "core show channels concise" 2>/dev/null | column -t -s "!"'
EOF

    # Скрипт для перезагрузки конфигурации
    cat > "$INSTALL_DIR/scripts/asterisk_reload.sh" << 'EOF'
#!/bin/bash
echo "Перезагрузка конфигурации Asterisk..."
asterisk -rx "core reload" 2>/dev/null
asterisk -rx "pjsip reload" 2>/dev/null
asterisk -rx "dialplan reload" 2>/dev/null
echo "Готово"
EOF

    # Скрипт для тестирования звонка
    cat > "$INSTALL_DIR/scripts/asterisk_test_call.sh" << 'EOF'
#!/bin/bash
if [ -z "$1" ]; then
    echo "Использование: $0 <номер>"
    exit 1
fi
echo "Тестовый звонок на номер $1"
asterisk -rx "channel originate PJSIP/$1@freepbx-endpoint application Playback hello-world" 2>/dev/null
EOF

    # Скрипт для мониторинга
    cat > "$INSTALL_DIR/scripts/asterisk_monitor.sh" << 'EOF'
#!/bin/bash
while true; do
    clear
    echo "=== МОНИТОРИНГ ASTERISK ==="
    echo "Время: $(date '+%Y-%m-%d %H:%M:%S')"
    echo
    asterisk -rx "core show channels count" 2>/dev/null
    echo
    asterisk -rx "pjsip show registrations" 2>/dev/null | grep freepbx
    echo
    tail -5 /var/log/asterisk/messages 2>/dev/null
    sleep 5
done
EOF

    chmod +x "$INSTALL_DIR"/scripts/asterisk_*.sh
    chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/scripts" 2>/dev/null || true
    
    log_info "Скрипты управления созданы в $INSTALL_DIR/scripts"
}

setup_api_integration() {
    log_info "Настройка интеграции с API..."
    
    # Создание конфигурации ARI
    cat > "/etc/asterisk/ari.conf" << EOF
[general]
enabled = yes
pretty = yes
allowed_origins = http://localhost:8000,https://$DOMAIN_OR_IP

[gochs]
type = user
read_only = no
password = $ASTERISK_ARI_PASSWORD
password_format = plain
EOF

    # Создание Python скрипта для тестирования AMI (исправлено: socket вместо telnetlib)
    cat > "$INSTALL_DIR/scripts/test_ami.py" << EOF
#!/usr/bin/env python3
import socket
import sys

def test_ami():
    try:
        # Подключение к AMI
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('127.0.0.1', $ASTERISK_AMI_PORT))
        
        # Читаем приветствие
        data = sock.recv(1024).decode()
        if 'Asterisk Call Manager' not in data:
            print("✗ Не получено приветствие AMI")
            return False
        
        # Логин
        login_cmd = f"Action: Login\r\nUsername: $ASTERISK_AMI_USER\r\nSecret: $ASTERISK_AMI_PASSWORD\r\n\r\n"
        sock.send(login_cmd.encode())
        
        response = sock.recv(1024).decode()
        if 'Success' in response:
            print("✓ AMI подключение успешно")
            
            # Ping
            sock.send(b"Action: Ping\r\n\r\n")
            ping_response = sock.recv(1024).decode()
            if 'Success' in ping_response:
                print("  Ping: OK")
            
            sock.send(b"Action: Logoff\r\n\r\n")
            sock.close()
            return True
        else:
            print("✗ Ошибка AMI подключения")
            print(f"  Ответ: {response[:100]}")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

if __name__ == "__main__":
    test_ami()
EOF

    chmod +x "$INSTALL_DIR/scripts/test_ami.py"
    chown "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/scripts/test_ami.py" 2>/dev/null || true
    
    log_info "Интеграция с API настроена"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Остановка сервиса
    systemctl stop asterisk 2>/dev/null
    systemctl disable asterisk 2>/dev/null
    
    # Удаление файлов службы
    rm -f /etc/systemd/system/asterisk.service
    systemctl daemon-reload
    
    # Удаление файлов Asterisk
    read -p "Удалить Asterisk полностью? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf /usr/lib/asterisk
        rm -rf /var/lib/asterisk
        rm -rf /var/spool/asterisk
        rm -rf /var/log/asterisk
        rm -rf /etc/asterisk
        rm -f /usr/sbin/asterisk
        rm -f /usr/sbin/astgenkey
        rm -f /usr/sbin/autosupport
        
        # Удаление пользователя
        userdel asterisk 2>/dev/null || true
        
        log_info "Asterisk полностью удален"
    fi
    
    # Удаление скриптов
    rm -f "$INSTALL_DIR"/scripts/asterisk_*.sh
    rm -f "$INSTALL_DIR"/scripts/test_ami.py
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка сервиса
    if systemctl is-active --quiet asterisk; then
        log_info "✓ Сервис Asterisk: активен"
        
        # Проверка версии
        VERSION=$(asterisk -rx "core show version" 2>/dev/null | head -1)
        log_info "  $VERSION"
        
        # Проверка uptime
        UPTIME=$(asterisk -rx "core show uptime" 2>/dev/null | grep "System uptime")
        log_info "  $UPTIME"
        
        # Проверка каналов
        CHANNELS=$(asterisk -rx "core show channels" 2>/dev/null | grep "active channels")
        log_info "  $CHANNELS"
        
        # Проверка регистрации на FreePBX
        REGISTRATION=$(asterisk -rx "pjsip show registrations" 2>/dev/null | grep freepbx)
        if echo "$REGISTRATION" | grep -q "Registered"; then
            log_info "  ✓ FreePBX регистрация: Зарегистрирован"
        else
            log_warn "  ✗ FreePBX регистрация: Не зарегистрирован"
            status=1
        fi
        
        # Проверка AMI
        if grep -q "^\[$ASTERISK_AMI_USER\]" /etc/asterisk/manager.conf 2>/dev/null; then
            log_info "  ✓ AMI пользователь: Настроен"
            
            # Тест AMI
            if python3 "$INSTALL_DIR/scripts/test_ami.py" 2>/dev/null | grep -q "успешно"; then
                log_info "  ✓ AMI подключение: OK"
            else
                log_warn "  ✗ AMI подключение: Ошибка"
                status=1
            fi
        fi
        
    else
        log_error "✗ Сервис Asterisk: не активен"
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
    console)
        asterisk -rvvvv
        ;;
    reload)
        asterisk -rx "core reload" 2>/dev/null
        asterisk -rx "pjsip reload" 2>/dev/null
        ;;
    restart)
        systemctl restart asterisk
        ;;
    logs)
        tail -f /var/log/asterisk/messages
        ;;
    test)
        if [[ -n "${2:-}" ]]; then
            asterisk -rx "channel originate PJSIP/$2@freepbx-endpoint application Playback hello-world" 2>/dev/null
            echo "Тестовый звонок на $2"
        else
            echo "Использование: $0 test <номер>"
        fi
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|console|reload|restart|logs|test <номер>}"
        exit 1
        ;;
esac
