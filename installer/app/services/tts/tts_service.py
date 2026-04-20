# app/services/tts/tts_service.py
from TTS.api import TTS

class TTSService:
    def __init__(self):
        self.model = TTS(model_path=settings.TTS_MODEL_PATH)
    
    def generate_audio(self, text: str, voice: str = "ru") -> str:
        """Генерирует аудиофайл из текста"""
        output_path = f"{settings.GENERATED_VOICE_DIR}/scenario_{uuid4()}.wav"
        self.model.tts_to_file(text=text, file_path=output_path)
        return output_path
