#!/bin/bash

################################################################################
# Скрипт распознавания речи через Vosk
################################################################################

AUDIO_FILE="$1"
LANGUAGE="${2:-ru}"
MODEL_PATH="/opt/gochs-informing/models/vosk/model-${LANGUAGE}"
VOSK_DIR="/opt/gochs-informing/venv/bin"

if [[ ! -f "$AUDIO_FILE" ]]; then
    echo "Файл не найден: $AUDIO_FILE"
    exit 1
fi

if [[ ! -d "$MODEL_PATH" ]]; then
    echo "Модель не найдена: $MODEL_PATH"
    exit 1
fi

# Распознавание через Python скрипт
source /opt/gochs-informing/venv/bin/activate

python3 << EOF
import sys
import json
from vosk import Model, KaldiRecognizer
import wave

try:
    wf = wave.open("$AUDIO_FILE", "rb")
    
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Аудио должно быть mono 16-bit")
        sys.exit(1)
    
    model = Model("$MODEL_PATH")
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)
    rec.SetPartialWords(True)
    
    results = []
    
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            results.append(result.get("text", ""))
    
    final_result = json.loads(rec.FinalResult())
    results.append(final_result.get("text", ""))
    
    # Вывод результата
    print(" ".join(results))
    
except Exception as e:
    print(f"Ошибка распознавания: {e}", file=sys.stderr)
    sys.exit(1)
EOF

deactivate
