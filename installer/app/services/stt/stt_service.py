# app/services/stt/stt_service.py
import vosk
import wave

class STTService:
    def __init__(self):
        self.model = vosk.Model(settings.STT_MODEL_PATH)
    
    def transcribe(self, audio_path: str) -> str:
        """Распознает речь из аудиофайла"""
        wf = wave.open(audio_path, "rb")
        recognizer = vosk.KaldiRecognizer(self.model, wf.getframerate())
        
        result_text = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                result_text += result.get("text", "") + " "
        
        return result_text.strip()
