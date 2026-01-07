import sounddevice as sd
import numpy as np
from config import SILENCE_THRESHOLD

def is_silent(audio_chunk, threshold=SILENCE_THRESHOLD):
    return np.max(np.abs(audio_chunk)) < threshold

def list_microphones():
    """Return a list of (index, name) for input-capable devices."""
    devices = sd.query_devices()
    return [(i, dev['name']) for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]


def choose_microphone(index):
    """Set the default microphone by index."""
    sd.default.device = index
    mic_info = sd.query_devices(index)
    print(f"Microphone switched to: {mic_info['name']}")
    return mic_info['name']
