#!/bin/bash

################################################################################
# Модуль: 05-asterisk.sh
# Назначение: Установка и настройка Asterisk 20 LTS
################################################################################

source "${UTILS_DIR}/common.sh"

MODULE_NAME="05-asterisk"
MODULE_DESCRIPTION="Asterisk 20 LTS - ядро телефонии"

# Версия Asterisk
ASTERISK_VERSION="20"
ASTERISK_FULL_VERSION="20.7.0"  # Актуальная LTS версия

install() {
    log_step "Установка Asterisk $ASTERISK_VERSION LTS"
    
    # Проверка наличия Asterisk
    if command -v asterisk &> /dev/null; then
        ASTERISK_VER=$(asterisk -V | grep -oP '\d+\.\d+\.\d+')
        log_info "Asterisk уже установлен (версия $ASTERISK_VER)"
        
        # Проверка версии
        if [[ "$ASTERISK_VER" < "20.0.0" ]]; then
            log_warn "Установлена устаревшая версия Asterisk. Рекомендуется обновление до 20 LTS"
        fi
    else
        log_info "Установка Asterisk $ASTERISK_FULL_VERSION..."
        
        # Установка зависимостей для компиляции
        log_info "Установка зависимостей для компиляции..."
        apt-get install -y \
            wget build-essential subversion \
            libjansson-dev libxml2-dev libncurses5-dev libsqlite3-dev \
            libssl-dev libsrtp2-dev uuid-dev libedit-dev libpcap-dev \
            libspandsp-dev libopenr2-dev libiksemel-dev libcurl4-openssl-dev \
            libical-dev libneon27-dev libgmime-3.0-dev liburiparser-dev \
            libpq-dev libmariadb-dev libsnmp-dev libldap2-dev \
            libpopt-dev libnewt-dev libtiff-dev libresample1-dev libltdl-dev \
            libvorbis-dev libogg-dev libopus-dev libgsm1-dev \
            libspeex-dev libspeexdsp-dev libsndfile1-dev unixodbc-dev
        
        # Скачивание Asterisk
        cd /usr/src
        log_info "Скачивание Asterisk $ASTERISK_FULL_VERSION..."
        wget -q --show-progress http://downloads.asterisk.org/pub/telephony/asterisk/asterisk-${ASTERISK_FULL_VERSION}.tar.gz
        
        # Распаковка
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
            --with-sndfile
        
        # Сборка
        log_info "Сборка Asterisk (это может занять 10-15 минут)..."
        make -j$(nproc)
        
        # Установка
        log_info "Установка Asterisk..."
        make install
        make samples
        make config
        make install-logrotate
        
        # Установка дополнительных звуковых файлов (русские)
        log_info "Установка звуковых файлов..."
        make install sounds/ru
        
        # Создание пользователя asterisk
        if ! id -u asterisk &>/dev/null; then
            useradd -r -d /var/lib/asterisk -s /sbin/nologin asterisk
        fi
        
        # Добавление пользователя в группы
        usermod -aG audio asterisk
        usermod -aG "$GOCHS_GROUP" asterisk
        
        # Установка прав
        chown -R asterisk:asterisk /var/lib/asterisk
        chown -R asterisk:asterisk /var/log/asterisk
        chown -R asterisk:asterisk /var/spool/asterisk
        chown -R asterisk:asterisk /usr/lib/asterisk
        
        # Очистка
        cd /
        rm -rf /usr/src/asterisk-${ASTERISK_FULL_VERSION}*
        
        log_info "Asterisk $ASTERISK_FULL_VERSION установлен"
    fi
    
    # Настройка Asterisk для работы с FreePBX
    log_info "Настройка конфигурации Asterisk..."
    configure_asterisk
    
    # Создание директорий для ГО-ЧС
    create_directories
    
    # Настройка systemd службы
    configure_systemd
    
    # Запуск Asterisk
    systemctl enable asterisk
    systemctl start asterisk
    
    # Ожидание запуска
    wait_for_service "asterisk" 30
    
    # Проверка работы
    if asterisk -rx "core show version" &>/dev/null; then
        log_info "Asterisk запущен и работает"
    else
        log_error "Проблема с запуском Asterisk"
        return 1
    fi
    
    # Создание скриптов управления
    create_management_scripts
    
    # Настройка интеграции с FastAPI
    setup_api_integration
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Asterisk версия: $ASTERISK_FULL_VERSION"
    log_info "AMI порт: $ASTERISK_AMI_PORT"
    log_info "AMI пользователь: $ASTERISK_AMI_USER"
    log_info "Пароль AMI сохранен в /root/.gochs_credentials"
    
    return 0
}

configure_asterisk() {
    local asterisk_conf_dir="/etc/asterisk"
    
    # Резервное копирование оригинальных конфигураций
    for conf in asterisk.conf http.conf manager.conf sip.conf pjsip.conf extensions.conf; do
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
server_uri = sip:${DOMAIN_OR_IP}:5060
client_uri = sip:gochs@${DOMAIN_OR_IP}:5060
contact_user = gochs
retry_interval = 30
max_retries = 10
forbidden_retry_interval = 300

[freepbx-auth]
type = auth
auth_type = userpass
username = $ASTERISK_AMI_USER
password = $ASTERISK_AMI_PASSWORD

; Эндпоинт для FreePBX
[freepbx-endpoint](${gochs-outbound})
type = endpoint
aors = freepbx-aor
outbound_auth = freepbx-auth
context = gochs-outbound
callerid = "ГО-ЧС Информирование" <1000>

[freepbx-aor](${gochs-aor})
type = aor
contact = sip:${DOMAIN_OR_IP}:5060

; Локальные расширения для тестирования
[1000](!)
type = endpoint
context = gochs-local
auth = 1000-auth
aors = 1000-aor
callerid = "Test User" <1000>

[1000-auth](!)
type = auth
auth_type = userpass
password = test123
username = 1000

[1000-aor](!)
type = aor
max_contacts = 1
EOF

    # extensions.conf
    cat > "$asterisk_conf_dir/extensions.conf" << EOF
[globals]
GOCHS_RECORDING_DIR = /opt/gochs-informing/recordings
GOCHS_PLAYBOOK_DIR = /opt/gochs-informing/playbooks
GOCHS_VOICE_DIR = /opt/gochs-informing/generated_voice

[default]

[gochs-inbound]
; Обработка входящих звонков от FreePBX
exten => _X.,1,NoOp(Входящий звонок от \${CALLERID(num)})
 same => n,Set(CHANNEL(language)=ru)
 same => n,Answer()
 same => n,Wait(1)
 same => n,Playback(${GOCHS_PLAYBOOK_DIR}/welcome)
 same => n,Playback(beep)
 same => n,Set(FILENAME=\${STRFTIME(\${EPOCH},,%Y%m%d_%H%M%S)}_\${CALLERID(num)})
 same => n,MixMonitor(${GOCHS_RECORDING_DIR}/\${FILENAME}.wav)
 same => n,Wait(300)  ; Максимальная длительность 5 минут
 same => n,Hangup()

[gochs-outbound]
; Исходящие вызовы через FreePBX
exten => _X.,1,NoOp(Исходящий вызов на \${EXTEN})
 same => n,Set(CHANNEL(language)=ru)
 same => n,Dial(PJSIP/\${EXTEN}@freepbx-endpoint,60,${DIAL_OPTIONS})
 same => n,Hangup()

[gochs-local]
; Локальные вызовы для тестирования
exten => 1000,1,Answer()
 same => n,Playback(hello-world)
 same => n,Hangup()

[gochs-dialer]
; Контекст для массового обзвона
exten => s,1,NoOp(Массовый обзвон)
 same => n,Set(CALLERID(all)=ГО-ЧС <1000>)
 same => n,Set(CHANNEL(language)=ru)
 same => n,Set(TIMEOUT(response)=10)
 same => n,Set(TIMEOUT(digit)=5)
 same => n,Dial(PJSIP/\${DEST}@freepbx-endpoint,40,gM(gochs-answer^${SCENARIO_ID})${DIAL_OPTIONS})
 same => n,NoOp(Статус звонка: \${DIALSTATUS})
 same => n,GotoIf($["\${DIALSTATUS}" = "BUSY"]?busy)
 same => n,GotoIf($["\${DIALSTATUS}" = "NOANSWER"]?noanswer)
 same => n,GotoIf($["\${DIALSTATUS}" = "CONGESTION"]?congestion)
 same => n,GotoIf($["\${DIALSTATUS}" = "CHANUNAVAIL"]?failed)
 same => n,Hangup()
 
 same => n(busy),Set(STATUS=BUSY)
 same => n,Return(\${STATUS})
 
 same => n(noanswer),Set(STATUS=NOANSWER)
 same => n,Return(\${STATUS})
 
 same => n(congestion),Set(STATUS=CONGESTION)
 same => n,Return(\${STATUS})
 
 same => n(failed),Set(STATUS=FAILED)
 same => n,Return(\${STATUS})

[gochs-answer]
; Макрос для воспроизведения сообщения после ответа
exten => s,1,NoOp(Воспроизведение сценария \${ARG1})
 same => n,Wait(1)
 same => n,Playback(${GOCHS_VOICE_DIR}/scenario_\${ARG1})
 same => n,Wait(2)
 same => n,Set(STATUS=ANSWERED)
 same => n,Return(\${STATUS})

[gochs-api]
; Контекст для управления через API
exten => dial,1,NoOp(API Dial Request)
 same => n,Set(DEST=\${ARG1})
 same => n,Set(SCENARIO_ID=\${ARG2})
 same => n,Set(CALL_ID=\${ARG3})
 same => n,Originate(PJSIP/\${DEST}@freepbx-endpoint,app,Dial,gochs-dialer,\${DEST},\${SCENARIO_ID},g)
 same => n,Set(STATUS=INITIATED)
 same => n,Return(\${STATUS})

exten => hangup,1,NoOp(API Hangup Request)
 same => n,Set(CHANNEL=\${ARG1})
 same => n,SoftHangup(\${CHANNEL})
 same => n,Return(SUCCESS)

exten => status,1,NoOp(API Status Request)
 same => n,Set(CHANNEL=\${ARG1})
 same => n,ChannelStatus(\${CHANNEL})
 same => n,Return(\${CHANNEL_STATUS})
EOF

    # modules.conf
    cat > "$asterisk_conf_dir/modules.conf" << EOF
[modules]
autoload = yes

; Отключаем ненужные модули
noload => chan_sip.so
noload => chan_skinny.so
noload => chan_unistim.so
noload => chan_mgcp.so
noload => chan_oss.so
noload => chan_alsa.so
noload => chan_console.so
noload => chan_phone.so
noload => res_hep.so
noload => res_hep_pjsip.so
noload => res_hep_rtcp.so
noload => res_statsd.so

; Включаем PJSIP
load => res_pjsip.so
load => res_pjsip_authenticator_digest.so
load => res_pjsip_endpoint_identifier_ip.so
load => res_pjsip_endpoint_identifier_user.so
load => res_pjsip_outbound_authenticator_digest.so
load => res_pjsip_outbound_publish.so
load => res_pjsip_outbound_registration.so
load => res_pjsip_pubsub.so
load => res_pjsip_session.so
load => res_pjsip_t38.so
load => res_pjsip_transport_websocket.so
load => chan_pjsip.so

; Аудио кодеки
load => codec_ulaw.so
load => codec_alaw.so
load => codec_g729.so
load => codec_gsm.so
load => codec_opus.so
load => codec_speex.so
load => format_wav.so
load => format_gsm.so
load => format_pcm.so
load => format_sln.so

; Функции
load => func_callerid.so
load => func_cdr.so
load => func_channel.so
load => func_db.so
load => func_devstate.so
load => func_dialgroup.so
load => func_env.so
load => func_extstate.so
load => func_global.so
load => func_logic.so
load => func_math.so
load => func_strings.so
load => func_timeout.so
load => func_uri.so

; Приложения
load => app_dial.so
load => app_playback.so
load => app_mixmonitor.so
load => app_record.so
load => app_verbose.so
load => app_waitforsilence.so
load => app_waituntil.so
load => app_read.so
load => app_senddtmf.so
load => app_userevent.so

; Ресурсы
load => res_agi.so
load => res_ari.so
load => res_http_websocket.so
load => res_musiconhold.so
load => res_odbc.so
load => res_phoneprov.so
load => res_pjproject.so
load => res_sorcery_astdb.so
load => res_sorcery_config.so
load => res_sorcery_memory.so
load => res_sorcery_realtime.so
load => res_srtp.so
load => res_timing_pthread.so

; Мониторинг
load => res_monitor.so
load => res_snmp.so
EOF

    # logger.conf
    cat > "$asterisk_conf_dir/logger.conf" << EOF
[general]
dateformat = %F %T.%q
queue_log = yes

[logfiles]
console => notice,warning,error
messages => notice,warning,error,verbose(3)
full => notice,warning,error,debug,verbose(9)
security => security
gochs => notice,warning,error,call,event

[gochs]
file = /var/log/asterisk/gochs
levels = notice,warning,error,call,event,dtmf,fax
EOF

    log_info "Конфигурация Asterisk создана"
}

create_directories() {
    log_info "Создание директорий для ГО-ЧС"
    
    # Директории для записей и плейбуков
    mkdir -p "$INSTALL_DIR/recordings/inbound"
    mkdir -p "$INSTALL_DIR/recordings/outbound"
    mkdir -p "$INSTALL_DIR/playbooks"
    mkdir -p "$INSTALL_DIR/generated_voice"
    
    # Установка прав
    chown -R asterisk:asterisk "$INSTALL_DIR/recordings"
    chown -R asterisk:asterisk "$INSTALL_DIR/playbooks"
    chown -R asterisk:asterisk "$INSTALL_DIR/generated_voice"
    chmod 755 "$INSTALL_DIR/recordings"
    chmod 755 "$INSTALL_DIR/playbooks"
    chmod 755 "$INSTALL_DIR/generated_voice"
    
    # Создание тестового приветствия
    cat > "$INSTALL_DIR/playbooks/welcome.txt" << EOF
Здравствуйте.
Вы позвонили в систему ГО и ЧС информирования предприятия.
После звукового сигнала оставьте ваше сообщение.
EOF
    
    log_info "Директории созданы"
}

configure_systemd() {
    log_info "Настройка systemd службы Asterisk"
    
    cat > /etc/systemd/system/asterisk.service << EOF
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
LimitCORE=infinity
UMask=0007
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=full
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
}

create_management_scripts() {
    log_info "Создание скриптов управления Asterisk"
    
    mkdir -p "$INSTALL_DIR/scripts"
    
    # Скрипт для подключения к консоли Asterisk
    cat > "$INSTALL_DIR/scripts/asterisk_console.sh" << 'EOF'
#!/bin/bash
asterisk -rvvvv
EOF

    # Скрипт для проверки статуса
    cat > "$INSTALL_DIR/scripts/asterisk_status.sh" << 'EOF'
#!/bin/bash
echo "=== Статус Asterisk ==="
asterisk -rx "core show uptime"
echo
asterisk -rx "core show channels"
echo
asterisk -rx "pjsip show registrations"
echo
asterisk -rx "pjsip show endpoints"
echo
asterisk -rx "pjsip show channels"
EOF

    # Скрипт для просмотра активных звонков
    cat > "$INSTALL_DIR/scripts/asterisk_active_calls.sh" << 'EOF'
#!/bin/bash
watch -n 1 'asterisk -rx "core show channels concise" | column -t -s "!"'
EOF

    # Скрипт для перезагрузки конфигурации
    cat > "$INSTALL_DIR/scripts/asterisk_reload.sh" << 'EOF'
#!/bin/bash
echo "Перезагрузка конфигурации Asterisk..."
asterisk -rx "core reload"
asterisk -rx "pjsip reload"
asterisk -rx "dialplan reload"
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
asterisk -rx "channel originate PJSIP/$1@freepbx-endpoint application Playback hello-world"
EOF

    # Скрипт для мониторинга
    cat > "$INSTALL_DIR/scripts/asterisk_monitor.sh" << 'EOF'
#!/bin/bash
while true; do
    clear
    echo "=== МОНИТОРИНГ ASTERISK ==="
    echo "Время: $(date '+%Y-%m-%d %H:%M:%S')"
    echo
    asterisk -rx "core show channels count"
    echo
    asterisk -rx "core show calls"
    echo
    asterisk -rx "pjsip show registrations" | grep freepbx
    echo
    echo "Последние события:"
    tail -5 /var/log/asterisk/messages
    sleep 5
done
EOF

    chmod +x "$INSTALL_DIR"/scripts/asterisk_*.sh
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts"
    
    log_info "Скрипты управления созданы в $INSTALL_DIR/scripts"
}

setup_api_integration() {
    log_info "Настройка интеграции с API"
    
    # Создание конфигурации для ARI
    cat > "/etc/asterisk/ari.conf" << EOF
[general]
enabled = yes
pretty = yes
allowed_origins = http://localhost:8000,https://$DOMAIN_OR_IP

[gochs]
type = user
read_only = no
password = $ASTERISK_AMI_PASSWORD
password_format = plain
EOF

    # Создание Python скрипта для тестирования AMI
    cat > "$INSTALL_DIR/scripts/test_ami.py" << EOF
#!/usr/bin/env python3
import sys
sys.path.append('$INSTALL_DIR/venv/lib/python3.11/site-packages')

from Asterisk import Manager

def test_ami():
    try:
        manager = Manager.Manager(
            ('127.0.0.1', $ASTERISK_AMI_PORT),
            '$ASTERISK_AMI_USER',
            '$ASTERISK_AMI_PASSWORD'
        )
        
        response = manager.send_action({'Action': 'Ping'})
        if response and response.get('Response') == 'Success':
            print("✓ AMI подключение успешно")
            
            # Получение статуса
            status = manager.send_action({'Action': 'Status'})
            channels = len([e for e in status if e.get('Event') == 'Status'])
            print(f"  Активных каналов: {channels}")
            
            manager.close()
            return True
        else:
            print("✗ Ошибка AMI подключения")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

if __name__ == "__main__":
    test_ami()
EOF

    chmod +x "$INSTALL_DIR/scripts/test_ami.py"
    chown "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/scripts/test_ami.py"
    
    log_info "Интеграция с API настроена"
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Остановка сервиса
    systemctl stop asterisk
    systemctl disable asterisk
    
    # Удаление файлов
    read -p "Удалить Asterisk полностью? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Удаление установленных файлов
        rm -rf /usr/lib/asterisk
        rm -rf /var/lib/asterisk
        rm -rf /var/spool/asterisk
        rm -rf /var/log/asterisk
        rm -rf /etc/asterisk
        rm -f /usr/sbin/asterisk
        
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
        log_info "Сервис Asterisk: активен"
        
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
            log_info "  FreePBX регистрация: Зарегистрирован"
        else
            log_warn "  FreePBX регистрация: Не зарегистрирован"
            status=1
        fi
        
        # Проверка AMI
        if grep -q "^\[$ASTERISK_AMI_USER\]" /etc/asterisk/manager.conf; then
            log_info "  AMI пользователь: Настроен"
            
            # Тест AMI
            if python3 "$INSTALL_DIR/scripts/test_ami.py" 2>/dev/null; then
                log_info "  AMI подключение: OK"
            else
                log_warn "  AMI подключение: Ошибка"
                status=1
            fi
        fi
        
    else
        log_error "Сервис Asterisk: не активен"
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
        asterisk -rx "core reload"
        asterisk -rx "pjsip reload"
        ;;
    test)
        if [[ -n "${2:-}" ]]; then
            asterisk -rx "channel originate PJSIP/$2@freepbx-endpoint application Playback hello-world"
        else
            echo "Использование: $0 test <номер>"
        fi
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|console|reload|test <номер>}"
        exit 1
        ;;
esac
