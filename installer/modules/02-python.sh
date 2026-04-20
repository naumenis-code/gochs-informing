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
fastapi>=0.104.1,<1.0.0
uvicorn[standard]>=0.24.0,<1.0.0
python-multipart>=0.0.6,<1.0.0
websockets>=12.0,<14.0
sse-starlette>=1.6.0,<2.0.0
aiofiles>=23.0.0,<25.0.0

# Database
# ------------------------------------------------------------------------------
sqlalchemy>=2.0.23,<3.0.0
alembic>=1.12.0,<2.0.0
psycopg2-binary>=2.9.9,<3.0.0
asyncpg>=0.29.0,<1.0.0
greenlet>=3.0.0,<4.0.0

# Redis & Queue
# ------------------------------------------------------------------------------
redis>=5.0.0,<6.0.0
celery>=5.3.0,<6.0.0
flower>=2.0.0,<3.0.0
kombu>=5.3.0,<6.0.0
vine>=5.1.0,<6.0.0
billiard>=4.2.0,<5.0.0
amqp>=5.2.0,<6.0.0

# Security
# ------------------------------------------------------------------------------
python-jose[cryptography]>=3.3.0,<4.0.0
passlib[bcrypt]>=1.7.4,<2.0.0
python-dotenv>=1.0.0,<2.0.0
bcrypt>=4.0.0,<5.0.0
cryptography>=41.0.0,<45.0.0
pycparser>=2.21,<3.0.0

# Asterisk Integration
# ------------------------------------------------------------------------------
pyst2>=0.5.0,<1.0.0
py-asterisk>=0.5.0,<1.0.0
panoramisk>=1.4.0,<2.0.0
aioari>=0.10.0,<1.0.0
websocket-client>=1.6.0,<2.0.0

# TTS (offline) - Coqui TTS
# ------------------------------------------------------------------------------
TTS>=0.22.0,<1.0.0
torch>=2.0.0,<3.0.0
torchaudio>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
scipy>=1.11.0,<2.0.0
librosa>=0.10.0,<1.0.0
soundfile>=0.12.0,<1.0.0
resampy>=0.4.0,<1.0.0
inflect>=7.0.0,<8.0.0
tqdm>=4.65.0,<5.0.0
anyascii>=0.3.0,<1.0.0

# STT (offline) - Vosk
# ------------------------------------------------------------------------------
vosk>=0.3.45,<1.0.0
sounddevice>=0.4.0,<1.0.0
srt>=3.5.0,<4.0.0

# Audio Processing
# ------------------------------------------------------------------------------
pydub>=0.25.0,<1.0.0
#wave>=0.0.2,<1.0.0
#pyaudio>=0.2.13,<1.0.0

# File Processing
# ------------------------------------------------------------------------------
pandas>=1.5.0,<2.0.0
openpyxl>=3.1.0,<4.0.0
xlrd>=2.0.0,<3.0.0
python-magic>=0.4.27,<1.0.0
et-xmlfile>=1.1.0,<2.0.0

# Data Validation
# ------------------------------------------------------------------------------
pydantic>=2.5.0,<3.0.0
pydantic-settings>=2.1.0,<3.0.0
pydantic-core>=2.14.0,<3.0.0
email-validator>=2.0.0,<3.0.0
phonenumbers>=8.13.0,<9.0.0
dnspython>=2.4.0,<3.0.0
annotated-types>=0.6.0,<1.0.0

# HTTP & Network
# ------------------------------------------------------------------------------
httpx>=0.25.0,<1.0.0
aiohttp>=3.9.0,<4.0.0
requests>=2.31.0,<3.0.0
httpcore>=1.0.0,<2.0.0
h11>=0.14.0,<1.0.0
certifi>=2023.0.0
urllib3>=2.0.0,<3.0.0
charset-normalizer>=3.0.0,<4.0.0
idna>=3.0.0,<4.0.0

# Date & Time
# ------------------------------------------------------------------------------
python-dateutil>=2.8.0,<3.0.0
pytz>=2023.0
tzdata>=2023.0

# CLI & Config
# ------------------------------------------------------------------------------
click>=8.1.0,<9.0.0
pyyaml>=6.0.0,<7.0.0

# Templates
# ------------------------------------------------------------------------------
jinja2>=3.1.0,<4.0.0
MarkupSafe>=2.1.0,<3.0.0

# Logging
# ------------------------------------------------------------------------------
python-json-logger>=2.0.0,<3.0.0

# Monitoring & Metrics
# ------------------------------------------------------------------------------
prometheus-client>=0.19.0,<1.0.0
psutil>=5.9.0,<6.0.0

# Development & Debug
# ------------------------------------------------------------------------------
pytest>=7.4.0,<9.0.0
pytest-asyncio>=0.21.0,<1.0.0
pytest-cov>=4.1.0,<6.0.0
black>=23.0.0,<25.0.0
flake8>=6.1.0,<8.0.0
mypy>=1.7.0,<2.0.0
ipython>=8.18.0,<9.0.0
EOF
     # Настройка pip на использование зеркала (для обхода блокировок/ускорения)
    log_info "Настройка pip на использование зеркала..."
    
    # Пробуем Яндекс
    if curl -s --connect-timeout 5 https://mirror.yandex.ru/pypi/simple/ > /dev/null 2>&1; then
        pip config set global.index-url https://mirror.yandex.ru/pypi/simple/
        pip config set global.trusted-host mirror.yandex.ru
        log_info "✓ Используется зеркало Яндекса"
    # Fallback на официальный PyPI
    else
        pip config set global.index-url https://pypi.org/simple/
        log_info "✓ Используется официальный PyPI"
    fi
    
    # Увеличиваем таймаут
    export PIP_DEFAULT_TIMEOUT=300
    
    # Устанавливаем критически важные пакеты явно (страховка)
    log_info "Установка критических пакетов..."
    pip install --timeout 300 fastapi uvicorn[standard] sqlalchemy redis celery pydantic python-dotenv || {
        log_warn "Не удалось установить через pip, пробуем альтернативные зеркала..."
        # Альтернативные зеркала
        for mirror in "https://pypi.tuna.tsinghua.edu.cn/simple" "https://pypi.org/simple"; do
            log_info "Пробуем зеркало: $mirror"
            pip config set global.index-url "$mirror"
            if pip install --timeout 300 fastapi uvicorn[standard] sqlalchemy redis celery pydantic python-dotenv; then
                log_info "✓ Пакеты установлены через $mirror"
                break
            fi
        done
    }
    
    # Увеличиваем таймаут по умолчанию для надежности
    export PIP_DEFAULT_TIMEOUT=120

    # Установка зависимостей с умным подбором версий
    log_info "Установка Python пакетов (умный подбор версий)..."
    
    # Функция для умной установки пакета
    smart_install() {
        local package="$1"
        local min_version="$2"
        local max_version="${3:-}"
        
        if [[ -n "$max_version" ]]; then
            if pip install "$package>=$min_version,$max_version" --quiet 2>/dev/null; then
                return 0
            fi
        else
            if pip install "$package>=$min_version" --quiet 2>/dev/null; then
                return 0
            fi
        fi
        
        # Если не получилось - пробуем без ограничения версии
        log_warn "Не удалось установить $package с ограничениями, пробуем последнюю версию..."
        if pip install "$package" --quiet 2>/dev/null; then
            return 0
        fi
        
        return 1
    }
    
    # Сначала пробуем установить всё из requirements.txt с флагом --upgrade-strategy eager
    if pip install --upgrade-strategy only-if-needed -r "$INSTALL_DIR/requirements.txt" 2>&1 | tee /tmp/pip_install.log; then
        log_info "Основные пакеты установлены успешно"
    else
        log_warn "Некоторые пакеты не установились с ограничениями, пробуем без них..."
        
        # Установка по одному с игнорированием ошибок
        while IFS= read -r line; do
            [[ "$line" =~ ^[[:space:]]*$ ]] && continue
            [[ "$line" =~ ^# ]] && continue
            [[ "$line" =~ ^-- ]] && continue
            
            pkg=$(echo "$line" | cut -d'#' -f1 | xargs)
            [[ -z "$pkg" ]] && continue
            
            pip install "$pkg" --quiet 2>/dev/null || log_warn "Не удалось установить: $pkg"
        done < "$INSTALL_DIR/requirements.txt"
    fi
    
    # Сохраняем реально установленные версии для будущих обновлений
    log_info "Сохранение установленных версий..."
    pip freeze | grep -E "fastapi|uvicorn|sqlalchemy|redis|celery|pydantic|TTS|vosk|pandas|torch" > "$INSTALL_DIR/requirements.lock"
    
    log_info "Установленные версии сохранены в requirements.lock"
    
    # Установка PyTorch (попытка с зеркалом или основного репозитория)
    log_info "Установка PyTorch..."
    # Сначала попробуем установить CPU-версию из официального источника, но с большим таймаутом
    if ! pip install --timeout 300 'torch>=2.0.0,<3.0.0' 'torchaudio>=2.0.0,<3.0.0' --index-url https://download.pytorch.org/whl/cpu 2>/dev/null; then
        log_warn "Не удалось установить PyTorch с download.pytorch.org, пробуем через зеркало..."
        # Попробуем через стандартный индекс (возможно, там есть wheel'ы, или установим из source, что дольше)
        pip install --timeout 300 'torch>=2.0.0,<3.0.0' 'torchaudio>=2.0.0,<3.0.0' || {
            log_warn "Не удалось установить PyTorch. Продолжаем без него (функционал TTS может быть ограничен)."
        }
    fi
    
    # ============================================================
    # Загрузка моделей для Vosk с вашего зеркала
    # ============================================================
    log_info "Загрузка модели Vosk для русского языка..."
    mkdir -p "$INSTALL_DIR/models/vosk"
    cd "$INSTALL_DIR/models/vosk"
    
    if [[ ! -f "vosk-model-small-ru-0.22.zip" ]]; then
        log_info "Скачивание с https://mexok.narod.ru/gochs-informin/vosk-model-small-ru-0.22.zip"
        wget -q --show-progress --timeout=120 https://mexok.narod.ru/gochs-informin/vosk-model-small-ru-0.22.zip || {
            log_warn "Не удалось скачать модель Vosk. Продолжаем без неё."
        }
        
        if [[ -f "vosk-model-small-ru-0.22.zip" ]]; then
            log_info "Распаковка модели Vosk..."
            unzip -q vosk-model-small-ru-0.22.zip
            mv vosk-model-small-ru-0.22 model-ru
            rm vosk-model-small-ru-0.22.zip
            chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/models/vosk"
            log_info "✅ Модель Vosk установлена"
        fi
    else
        log_info "Модель Vosk уже существует, пропускаем загрузку"
    fi
    
    # ============================================================
    # Загрузка моделей для Coqui TTS с быстрого зеркала Hugging Face
    # ============================================================
    log_info "Загрузка модели TTS для русского языка с Hugging Face..."
    mkdir -p "$INSTALL_DIR/models/tts"
    cd "$INSTALL_DIR/models/tts"

    log_info "Скачивание model.pth (около 1.7 ГБ)..."
    if [[ ! -f "model.pth" ]]; then
        wget -q --show-progress --timeout=120 https://huggingface.co/coqui/XTTS-v2/resolve/main/model.pth || {
            log_warn "Не удалось скачать model.pth с Hugging Face"
        }
    fi
    
    log_info "Скачивание config.json..."
    if [[ ! -f "config.json" ]]; then
        wget -q --show-progress --timeout=60 https://huggingface.co/coqui/XTTS-v2/resolve/main/config.json || {
            log_warn "Не удалось скачать config.json"
        }
    fi
    
    log_info "Скачивание vocab.json..."
    if [[ ! -f "vocab.json" ]]; then
        wget -q --show-progress --timeout=60 https://huggingface.co/coqui/XTTS-v2/resolve/main/vocab.json || {
            log_warn "Не удалось скачать vocab.json"
        }
    fi
    
    if [[ -f "model.pth" ]]; then
        log_info "✅ Модель TTS загружена успешно"
        chown -R "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/models/tts"
    else
        log_warn "⚠️ Модель TTS не загружена. Будет использоваться espeak."
    fi
    
    cd "$SCRIPT_DIR"
    
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
