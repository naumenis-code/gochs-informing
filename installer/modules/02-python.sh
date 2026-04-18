#!/bin/bash

################################################################################
# Модуль: 02-python.sh
# Назначение: Настройка Python окружения и установка зависимостей
################################################################################

# Определение путей
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Загрузка общих функций
if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

MODULE_NAME="02-python"
MODULE_DESCRIPTION="Python окружение и зависимости"

# Версии пакетов (зафиксированы для стабильности)
PYTHON_VERSION="3.11"
PIP_VERSION="23.3.1"

install() {
    log_step "Настройка Python окружения"
    
    # Проверка установки Python
    log_info "Проверка Python..."
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 не установлен. Сначала выполните модуль 01-system"
        return 1
    fi
    
    PYTHON_VER=$(python3 --version | awk '{print $2}')
    log_info "Установлен Python: $PYTHON_VER"
    
    # Создание виртуального окружения
    log_info "Создание виртуального окружения в $INSTALL_DIR/venv"
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Активация виртуального окружения
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Обновление pip
    log_info "Обновление pip..."
    pip install --upgrade pip=="$PIP_VERSION"
    
    # Создание requirements.txt
    log_info "Создание файла зависимостей..."
    cat > "$INSTALL_DIR/requirements.txt" << 'EOF'
################################################################################
# ГО-ЧС Информирование - Python зависимости
################################################################################

# Web Framework
# ------------------------------------------------------------------------------
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
websockets==12.0
sse-starlette==1.6.5

# Database
# ------------------------------------------------------------------------------
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
asyncpg==0.29.0
greenlet==3.0.1

# Redis & Queue
# ------------------------------------------------------------------------------
redis==5.0.1
celery==5.3.4
flower==2.0.1
kombu==5.3.2

# Security
# ------------------------------------------------------------------------------
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
bcrypt==4.0.1
python-multipart==0.0.6
cryptography==41.0.7

# Asterisk Integration
# ------------------------------------------------------------------------------
pyst2==0.5.1
py-asterisk==0.1.6
panoramisk==1.4.1
aioari==0.3.2
websocket-client==1.6.4

# TTS (offline) - Coqui TTS
# ------------------------------------------------------------------------------
TTS==0.22.0
torch==2.1.0
torchaudio==2.1.0
numpy==1.24.3
scipy==1.11.4
librosa==0.10.1
soundfile==0.12.1
resampy==0.4.2

# STT (offline) - Vosk
# ------------------------------------------------------------------------------
vosk==0.3.45
sounddevice==0.4.6

# Audio Processing
# ------------------------------------------------------------------------------
pydub==0.25.1
wave==0.0.2
audioop-lts==0.2.1
pyaudio==0.2.13

# File Processing
# ------------------------------------------------------------------------------
pandas==2.1.3
openpyxl==3.1.2
xlrd==2.0.1
python-magic==0.4.27
aiofiles==23.2.1

# Data Validation
# ------------------------------------------------------------------------------
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0
phonenumbers==8.13.25

# Utilities
# ------------------------------------------------------------------------------
httpx==0.25.2
aiohttp==3.9.0
requests==2.31.0
python-dateutil==2.8.2
pytz==2023.3
click==8.1.7
pyyaml==6.0.1
jinja2==3.1.2
python-json-logger==2.0.7

# Monitoring & Metrics
# ------------------------------------------------------------------------------
prometheus-client==0.19.0
psutil==5.9.6

# Development & Debug
# ------------------------------------------------------------------------------
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
mypy==1.7.0
ipython==8.18.1
EOF

    # Установка зависимостей
    log_info "Установка Python пакетов (это может занять несколько минут)..."
    
    # Установка основных пакетов
    if pip install -r "$INSTALL_DIR/requirements.txt"; then
        log_info "Основные пакеты установлены успешно"
    else
        log_error "Ошибка при установке пакетов"
        return 1
    fi
    
    # Установка PyTorch отдельно (может быть проблематично)
    log_info "Установка PyTorch..."
    pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu
    
    # Загрузка моделей для Vosk (русская модель)
    log_info "Загрузка модели Vosk для русского языка..."
    mkdir -p "$INSTALL_DIR/models/vosk"
    cd "$INSTALL_DIR/models/vosk"
    
    # Загрузка маленькой русской модели (примерно 40MB)
    if [[ ! -f "vosk-model-small-ru-0.22.zip" ]]; then
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
        unzip -q vosk-model-small-ru-0.22.zip
        mv vosk-model-small-ru-0.22 model-ru
        rm vosk-model-small-ru-0.22.zip
    fi
    
    # Загрузка моделей для Coqui TTS (русский голос)
    log_info "Загрузка моделей TTS для русского языка..."
    mkdir -p "$INSTALL_DIR/models/tts"
    
    # Создание скрипта для загрузки моделей TTS
    cat > "$INSTALL_DIR/download_tts_models.py" << 'PYEOF'
#!/usr/bin/env python3
import sys
import os
sys.path.append('/opt/gochs-informing/venv/lib/python3.11/site-packages')

try:
    from TTS.api import TTS
    
    # Загрузка русской модели
    print("Загрузка русской TTS модели...")
    tts = TTS(model_name="tts_models/ru/ruslan/tacotron2-DDC", progress_bar=True)
    print("Модель TTS загружена успешно")
    
except Exception as e:
    print(f"Ошибка загрузки модели TTS: {e}")
    sys.exit(1)
PYEOF

    chmod +x "$INSTALL_DIR/download_tts_models.py"
    
    # Запуск загрузки моделей
    source "$INSTALL_DIR/venv/bin/activate"
    if python "$INSTALL_DIR/download_tts_models.py"; then
        log_info "Модели TTS загружены успешно"
    else
        log_warn "Не удалось загрузить модели TTS. Их можно будет загрузить позже."
    fi
    
    # Создание скрипта активации окружения
    cat > "$INSTALL_DIR/activate_env.sh" << 'EOF'
#!/bin/bash
source /opt/gochs-informing/venv/bin/activate
export PYTHONPATH="/opt/gochs-informing/app:$PYTHONPATH"
export GOCHS_CONFIG="/opt/gochs-informing/config/config.yaml"
EOF
    
    chmod +x "$INSTALL_DIR/activate_env.sh"
    
    # Создание конфигурационного файла
    mkdir -p "$INSTALL_DIR/config"
    cat > "$INSTALL_DIR/config/config.yaml" << EOF
# Конфигурация ГО-ЧС Информирование
app:
  name: "ГО-ЧС Информирование"
  version: "1.0.0"
  debug: false
  secret_key: "$(generate_password)"

database:
  host: "localhost"
  port: 5432
  name: "$POSTGRES_DB"
  user: "$POSTGRES_USER"
  password: "$POSTGRES_PASSWORD"

redis:
  host: "localhost"
  port: $REDIS_PORT
  password: "$REDIS_PASSWORD"
  db: 0

asterisk:
  host: "localhost"
  ami_port: $ASTERISK_AMI_PORT
  ami_user: "$ASTERISK_AMI_USER"
  ami_password: "$ASTERISK_AMI_PASSWORD"
  
tts:
  model_path: "$INSTALL_DIR/models/tts"
  language: "ru"
  voice: "ruslan"
  
stt:
  model_path: "$INSTALL_DIR/models/vosk/model-ru"
  sample_rate: 16000
  
logging:
  level: "$LOG_LEVEL"
  file: "$INSTALL_DIR/logs/app.log"
  max_size: "100MB"
  backup_count: 10
  
security:
  jwt_expire_minutes: 60
  refresh_token_expire_days: 7
  max_login_attempts: 5
  lockout_minutes: 15
EOF
    
    # Создание файла .env
    cat > "$INSTALL_DIR/.env" << EOF
# Environment variables for GO-CHS
GOCHS_ENV=production
GOCHS_CONFIG=$INSTALL_DIR/config/config.yaml
PYTHONPATH=$INSTALL_DIR/app
PATH=$INSTALL_DIR/venv/bin:$PATH
EOF
    
    # Установка прав
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/venv"
    chown -R "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/models"
    chown "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/config"
    chmod 600 "$INSTALL_DIR/config/config.yaml"
    chmod 600 "$INSTALL_DIR/.env"
    
    # Проверка установки
    log_info "Проверка установленных пакетов..."
    source "$INSTALL_DIR/venv/bin/activate"
    
    PACKAGES_TO_CHECK=(
        "fastapi"
        "uvicorn"
        "sqlalchemy"
        "redis"
        "celery"
        "vosk"
        "TTS"
    )
    
    for package in "${PACKAGES_TO_CHECK[@]}"; do
        if python -c "import $package" 2>/dev/null; then
            version=$(python -c "import $package; print(getattr($package, '__version__', 'unknown'))" 2>/dev/null)
            log_info "  ✓ $package ($version)"
        else
            log_warn "  ✗ $package не установлен"
        fi
    done
    
    # Деактивация виртуального окружения
    deactivate
    
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    log_info "Python окружение: $INSTALL_DIR/venv"
    log_info "Для активации выполните: source $INSTALL_DIR/activate_env.sh"
    
    return 0
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    
    # Удаление виртуального окружения
    if [[ -d "$INSTALL_DIR/venv" ]]; then
        rm -rf "$INSTALL_DIR/venv"
        log_info "Виртуальное окружение удалено"
    fi
    
    # Удаление моделей
    if [[ -d "$INSTALL_DIR/models" ]]; then
        rm -rf "$INSTALL_DIR/models"
        log_info "Модели удалены"
    fi
    
    # Удаление конфигураций
    rm -f "$INSTALL_DIR/requirements.txt"
    rm -f "$INSTALL_DIR/config/config.yaml"
    rm -f "$INSTALL_DIR/.env"
    rm -f "$INSTALL_DIR/activate_env.sh"
    rm -f "$INSTALL_DIR/download_tts_models.py"
    
    log_info "Модуль ${MODULE_NAME} удален"
    return 0
}

check_status() {
    local status=0
    
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    # Проверка Python
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version | awk '{print $2}')
        log_info "Python: $PYTHON_VER - OK"
    else
        log_error "Python: не установлен"
        status=1
    fi
    
    # Проверка виртуального окружения
    if [[ -d "$INSTALL_DIR/venv" ]]; then
        log_info "Виртуальное окружение: $INSTALL_DIR/venv - OK"
        
        # Проверка установленных пакетов
        if [[ -f "$INSTALL_DIR/venv/bin/python" ]]; then
            source "$INSTALL_DIR/venv/bin/activate"
            
            CRITICAL_PACKAGES=("fastapi" "uvicorn" "sqlalchemy" "redis" "celery")
            for package in "${CRITICAL_PACKAGES[@]}"; do
                if python -c "import $package" 2>/dev/null; then
                    log_info "  Пакет $package: установлен"
                else
                    log_warn "  Пакет $package: не установлен"
                    status=1
                fi
            done
            
            deactivate
        fi
    else
        log_warn "Виртуальное окружение: отсутствует"
        status=1
    fi
    
    # Проверка моделей
    if [[ -d "$INSTALL_DIR/models/vosk/model-ru" ]]; then
        log_info "Модель Vosk: установлена"
    else
        log_warn "Модель Vosk: не установлена"
        status=1
    fi
    
    # Проверка конфигурации
    if [[ -f "$INSTALL_DIR/config/config.yaml" ]]; then
        log_info "Конфигурация: создана"
    else
        log_warn "Конфигурация: отсутствует"
        status=1
    fi
    
    return $status
}

# Функция для создания Python скрипта тестирования
create_test_script() {
    cat > "$INSTALL_DIR/test_python_env.py" << 'EOF'
#!/usr/bin/env python3
"""Скрипт для тестирования Python окружения ГО-ЧС"""

import sys
import os

def test_imports():
    """Проверка импорта основных пакетов"""
    packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'redis',
        'celery',
        'pydantic',
        'jinja2',
        'aiohttp',
    ]
    
    print("Проверка импорта пакетов:")
    for package in packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError as e:
            print(f"  ✗ {package}: {e}")
            return False
    
    return True

def test_asterisk():
    """Проверка пакетов Asterisk"""
    try:
        from Asterisk import Manager
        print("  ✓ pyst2")
    except ImportError:
        print("  ✗ pyst2 не установлен")
        return False
    
    return True

def test_audio():
    """Проверка аудио пакетов"""
    try:
        from pydub import AudioSegment
        print("  ✓ pydub")
    except ImportError:
        print("  ✗ pydub не установлен")
        return False
    
    return True

def test_vosk():
    """Проверка Vosk"""
    try:
        import vosk
        print(f"  ✓ vosk (версия: {vosk.__version__})")
        
        # Проверка наличия модели
        model_path = "/opt/gochs-informing/models/vosk/model-ru"
        if os.path.exists(model_path):
            print(f"  ✓ модель Vosk найдена: {model_path}")
        else:
            print(f"  ✗ модель Vosk не найдена: {model_path}")
            return False
            
    except ImportError:
        print("  ✗ vosk не установлен")
        return False
    
    return True

def main():
    print("=" * 60)
    print("Тестирование Python окружения ГО-ЧС")
    print("=" * 60)
    
    print(f"\nPython версия: {sys.version}")
    print(f"Python путь: {sys.executable}\n")
    
    results = []
    results.append(("Основные пакеты", test_imports()))
    results.append(("Asterisk", test_asterisk()))
    results.append(("Аудио", test_audio()))
    results.append(("Vosk STT", test_vosk()))
    
    print("\n" + "=" * 60)
    print("Результаты тестирования:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ ПРОЙДЕН" if passed else "✗ ПРОВАЛЕН"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
EOF
    
    chmod +x "$INSTALL_DIR/test_python_env.py"
    chown "$GOCHS_USER":"$GOCHS_USER" "$INSTALL_DIR/test_python_env.py"
}

# Дополнительная функция для обновления пакетов
update_packages() {
    log_step "Обновление Python пакетов"
    
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        log_error "Виртуальное окружение не найдено"
        return 1
    fi
    
    source "$INSTALL_DIR/venv/bin/activate"
    
    log_info "Проверка устаревших пакетов..."
    pip list --outdated
    
    read -p "Обновить все пакеты? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install --upgrade -r "$INSTALL_DIR/requirements.txt"
        log_info "Пакеты обновлены"
    else
        log_info "Обновление отменено"
    fi
    
    deactivate
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
    test)
        create_test_script
        source "$INSTALL_DIR/venv/bin/activate"
        python "$INSTALL_DIR/test_python_env.py"
        deactivate
        ;;
    update)
        update_packages
        ;;
    *)
        echo "Использование: $0 {install|uninstall|status|test|update}"
        exit 1
        ;;
esac
