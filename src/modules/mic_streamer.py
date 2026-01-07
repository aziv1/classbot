import sounddevice as sd
import numpy as np
from modules.utils import is_silent, choose_microphone
from config import FS, CHUNK_DURATION

def record_chunk():
    #Mic Chunk to float32 array
    audio = sd.rec(int(CHUNK_DURATION * FS), samplerate=FS, channels=1, dtype='int16')
    sd.wait()
    return (audio.astype(np.float32) / 32768.0).flatten()

def run_stream(backend):
    #Stream mic data into selected backend, as float32 array
    offset = 0.0
    mic_name = choose_microphone()

    # Add interuption so you dont need to kill proc every time
    print(f"\nPress Ctrl+C to stop streaming from {mic_name}.\n")
    try:
        while True:
            audio_chunk = record_chunk()
            if is_silent(audio_chunk):
                print("Silence detected, skipping chunk.")
                offset += CHUNK_DURATION
                continue
            segments = backend.transcribe(audio_chunk)
            for segment in segments:
                print(f"[{segment.start + offset:.2f} → {segment.end + offset:.2f}] {segment.text}")
            offset += CHUNK_DURATION
    except KeyboardInterrupt:
        print("\nStreaming stopped by user.")

def start_stream(queue, backend):
    # Keep recording chunks and add to queue so you dont loose speech data
    offset = 0.0
    mic_name = choose_microphone()
    print(f"\nStarting live stream from {mic_name}...\n")

    try:
        while True:
            audio_chunk = record_chunk()
            if is_silent(audio_chunk):
                offset += CHUNK_DURATION
                continue
            # Push chunk and offset into the queue
            queue.put((audio_chunk, offset))
            offset += CHUNK_DURATION
    except KeyboardInterrupt:
        print("\nStreaming stopped by user.")
