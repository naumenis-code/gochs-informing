#!/bin/bash

################################################################################
# Скрипт загрузки моделей TTS
# Можно запустить отдельно, если автоматическая загрузка не сработала
################################################################################

source "${UTILS_DIR}/common.sh"

download_tts_models() {
    log_step "Ручная загрузка моделей TTS"
    
    source "$INSTALL_DIR/venv/bin/activate"
    
    cat > /tmp/download_tts.py << 'EOF'
import sys
sys.path.append('/opt/gochs-informing/venv/lib/python3.11/site-packages')

from TTS.api import TTS
import os

models = {
    "ru": "tts_models/ru/ruslan/tacotron2-DDC",
    "en": "tts_models/en/ljspeech/tacotron2-DDC",
    "multi": "tts_models/multilingual/multi-dataset/xtts_v2"
}

print("Доступные модели TTS:")
for lang, model in models.items():
    print(f"  {lang}: {model}")

print("\nЗагрузка русской модели...")
try:
    tts = TTS(model_name=models["ru"], progress_bar=True)
    print("✓ Русская модель загружена успешно")
except Exception as e:
    print(f"✗ Ошибка загрузки русской модели: {e}")

print("\nДля загрузки дополнительных моделей используйте:")
print("  python -c 'from TTS.api import TTS; TTS(\"model_name\")'")
EOF

    python /tmp/download_tts.py
    rm /tmp/download_tts.py
    
    deactivate
}

download_tts_models
