import os
import gc
import torch
from faster_whisper import WhisperModel
from config import MODEL_NAME


class CudaWhisperBackend:
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Use ../models as HF cache folder
        os.environ["HF_HOME"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../models")
        )

    def load(self):
        print(f"[CUDA Backend] Loading Whisper model '{MODEL_NAME}' on {self.device}...")
        self.model = WhisperModel(MODEL_NAME, device=self.device)

    def unload(self):
        print("Unloading Whisper...")
        try:
            del self.model
        except:
            pass

        self.model = None
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

        print("Whisper unloaded")

    def transcribe(self, audio_input, language="en", beam_size=5, temperature=0.0):
        """
        audio_input can be:
        - a file path (str)
        - a numpy array / audio chunk
        """

        if self.model is None:
            raise RuntimeError("Whisper model not loaded")

        segments, _ = self.model.transcribe(
            audio_input,
            language=language,
            beam_size=beam_size,
            temperature=temperature,
        )

        return segments