#!/bin/bash

################################################################################
# Модуль: 06a-coqui-tts.sh
# Назначение: Настройка Coqui TTS и генерация аудио для сценариев/плейбуков
# Версия: 1.0.0
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Загрузка общих функций
if [[ -f "${SCRIPT_DIR}/utils/common.sh" ]]; then
    source "${SCRIPT_DIR}/utils/common.sh"
fi

# Если common.sh не найден - определяем функции локально
if ! type log_info &>/dev/null; then
    GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
    log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
    log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
    log_step() { echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}\n${BLUE}  $*${NC}\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"; }
    ensure_dir() { mkdir -p "$1"; }
    mark_module_installed() {
        local m="$1"; local f="${INSTALL_DIR:-/opt/gochs-informing}/.modules_state"
        mkdir -p "$(dirname "$f")"; echo "$m:$(date +%s)" >> "$f"
    }
fi

MODULE_NAME="06a-coqui-tts"
MODULE_DESCRIPTION="Настройка Coqui TTS и аудио-ассетов"

# Загрузка конфигурации
CONFIG_FILE="${SCRIPT_DIR}/config/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

INSTALL_DIR="${INSTALL_DIR:-/opt/gochs-informing}"
GOCHS_USER="${GOCHS_USER:-gochs}"
GOCHS_GROUP="${GOCHS_GROUP:-gochs}"

# Путь к исходной папке с моделями (предполагается, что они уже скачаны модулем 02-python)
SOURCE_MODELS_DIR="$INSTALL_DIR/models/tts"
TARGET_MODELS_DIR="$INSTALL_DIR/app/models/tts"

install() {
    log_step "Настройка Coqui TTS и генерация стартовых аудио"
    
    check_prerequisites
    copy_models_to_app
    create_tts_script
    generate_initial_audio
    
    mark_module_installed "$MODULE_NAME"
    log_info "Модуль ${MODULE_NAME} успешно установлен"
    return 0
}

check_prerequisites() {
    log_info "Проверка предварительных условий..."
    
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        log_error "Виртуальное окружение Python не найдено. Сначала установите 02-python."
        return 1
    fi
    
    if [[ ! -f "$SOURCE_MODELS_DIR/model.pth" ]]; then
        log_warn "Модель Coqui TTS (model.pth) не найдена в $SOURCE_MODELS_DIR"
        log_warn "Убедитесь, что модуль 02-python отработал успешно, либо скачайте модель вручную."
        read -p "Продолжить без моделей TTS? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
        return 0
    fi
    
    log_info "Все проверки пройдены."
}

copy_models_to_app() {
    log_info "Копирование моделей TTS в app/models/tts..."
    
    if [[ -f "$SOURCE_MODELS_DIR/model.pth" ]]; then
        ensure_dir "$TARGET_MODELS_DIR"
        
        # Копируем основные файлы моделей
        cp "$SOURCE_MODELS_DIR/model.pth" "$TARGET_MODELS_DIR/" 2>/dev/null || log_warn "Не удалось скопировать model.pth"
        cp "$SOURCE_MODELS_DIR/config.json" "$TARGET_MODELS_DIR/" 2>/dev/null || log_warn "Не удалось скопировать config.json"
        cp "$SOURCE_MODELS_DIR/vocab.json" "$TARGET_MODELS_DIR/" 2>/dev/null || log_warn "Не удалось скопировать vocab.json"
        
        chown -R "$GOCHS_USER:$GOCHS_GROUP" "$TARGET_MODELS_DIR"
        log_info "Модели TTS скопированы в $TARGET_MODELS_DIR"
    else
        log_warn "Модели не найдены, копирование пропущено."
    fi
}

create_tts_script() {
    log_info "Создание Python-скрипта для генерации TTS (tts_generator.py)..."
    
    cat > "$INSTALL_DIR/app/tts_generator.py" << 'EOF'
#!/usr/bin/env python3
"""
Генератор TTS для сценариев и плейбуков ГО-ЧС.
Может вызываться из командной строки или из других модулей.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Попытка импорта TTS
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
    logger.info("Coqui TTS успешно импортирован.")
except ImportError as e:
    logger.warning(f"Coqui TTS не импортирован: {e}. Будет использоваться espeak.")
    TTS_AVAILABLE = False

class TTSGenerator:
    def __init__(self):
        self.tts = None
        if TTS_AVAILABLE:
            model_path = os.environ.get('COQUI_MODEL_PATH', '/opt/gochs-informing/app/models/tts/')
            try:
                # Используем XTTS v2 для русского языка
                self.tts = TTS(model_path=model_path, config_path=os.path.join(model_path, 'config.json'), progress_bar=False)
                logger.info("Модель Coqui TTS загружена.")
            except Exception as e:
                logger.error(f"Не удалось загрузить модель Coqui TTS: {e}")
                self.tts = None

    def generate(self, text: str, output_path: str, speaker: str = "ru") -> bool:
        """Генерирует WAV файл из текста."""
        
        if self.tts:
            try:
                self.tts.tts_to_file(text=text, file_path=output_path, speaker=speaker)
                logger.info(f"Аудио сгенерировано через Coqui TTS: {output_path}")
                return True
            except Exception as e:
                logger.error(f"Ошибка генерации через Coqui TTS: {e}")
                # Fallback к espeak
                return self._fallback_espeak(text, output_path)
        else:
            return self._fallback_espeak(text, output_path)

    def _fallback_espeak(self, text: str, output_path: str) -> bool:
        """Резервный метод синтеза речи через espeak."""
        import subprocess
        try:
            # Конвертация текста в WAV через espeak
            cmd = ['espeak', '-v', 'ru', '-s', '150', '-p', '50', '-w', output_path, text]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Аудио сгенерировано через espeak: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка генерации через espeak: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Генерация аудио из текста')
    parser.add_argument('--text', required=True, help='Текст для озвучивания')
    parser.add_argument('--output', required=True, help='Путь для сохранения WAV файла')
    parser.add_argument('--speaker', default='ru', help='Идентификатор голоса')
    
    args = parser.parse_args()
    
    generator = TTSGenerator()
    if generator.generate(args.text, args.output, args.speaker):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

    chmod +x "$INSTALL_DIR/app/tts_generator.py"
    chown "$GOCHS_USER:$GOCHS_GROUP" "$INSTALL_DIR/app/tts_generator.py"
    log_info "Скрипт tts_generator.py создан."
}

generate_initial_audio() {
    log_info "Генерация начальных аудио-файлов..."
    
    # Активируем виртуальное окружение
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Проверяем, доступен ли Python и наш скрипт
    if [[ ! -f "$INSTALL_DIR/app/tts_generator.py" ]]; then
        log_warn "Скрипт tts_generator.py не найден, пропускаем генерацию аудио."
        return
    fi
    
    # Устанавливаем espeak на всякий случай, если он не установлен
    if ! command -v espeak &> /dev/null; then
        log_info "Установка espeak как fallback-синтезатора..."
        apt-get update -qq
        apt-get install -y espeak 2>/dev/null || log_warn "Не удалось установить espeak."
    fi
    
    # Создаем тестовый сценарий "Пожар" и плейбук
    generate_audio_file "Внимание! В здании пожар. Просьба немедленно покинуть помещения согласно плану эвакуации. Сохраняйте спокойствие." "$INSTALL_DIR/generated_voice/fire_alert.wav"
    generate_audio_file "Здравствуйте. Вы позвонили в систему ГО и ЧС информирования предприятия. После звукового сигнала оставьте ваше сообщение." "$INSTALL_DIR/playbooks/welcome.wav"
    
    deactivate
    log_info "Начальные аудио-файлы созданы."
}

generate_audio_file() {
    local text="$1"
    local output="$2"
    
    log_info "Генерация: $(basename "$output")"
    if python "$INSTALL_DIR/app/tts_generator.py" --text "$text" --output "$output"; then
        chown "$GOCHS_USER:$GOCHS_GROUP" "$output" 2>/dev/null || true
        log_info "  Файл создан: $output"
    else
        log_warn "  Не удалось сгенерировать файл: $output"
    fi
}

uninstall() {
    log_step "Удаление модуля ${MODULE_NAME}"
    log_info "Модуль ${MODULE_NAME} не требует сложной деинсталляции."
    return 0
}

check_status() {
    local status=0
    log_info "Проверка статуса модуля ${MODULE_NAME}"
    
    if [[ -f "$TARGET_MODELS_DIR/model.pth" ]]; then
        log_info "✓ Модель TTS: установлена в $TARGET_MODELS_DIR"
    else
        log_warn "✗ Модель TTS: не найдена в $TARGET_MODELS_DIR"
        status=1
    fi
    
    if [[ -f "$INSTALL_DIR/app/tts_generator.py" ]]; then
        log_info "✓ Скрипт генерации: создан"
    else
        log_warn "✗ Скрипт генерации: отсутствует"
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
