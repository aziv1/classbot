import os
import torch
from faster_whisper import WhisperModel
from config import MODEL_NAME

# Use ../models as cache folder
os.environ["HF_HOME"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[CUDA Backend] Loading Whisper model '{MODEL_NAME}' on {DEVICE}...")
model = WhisperModel(MODEL_NAME, device=DEVICE)

def transcribe(audio_chunk, language="en", beam_size=5, temperature=0.0):
    segments, _ = model.transcribe(
        audio_chunk,
        language=language,
        beam_size=beam_size,
        temperature=temperature
    )
    return segments
