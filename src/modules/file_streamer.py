# Currently Obselete

import os
from config import CHUNK_DURATION

def run_batch(backend, folder):
    #Open files and transcribe batch
    files = [f for f in os.listdir(folder) if f.lower().endswith((".wav", ".mp3", ".flac", ".m4a"))]
    if not files:
        print("No audio files found in", folder)
        return

    for f in files:
        filepath = os.path.join(folder, f)
        print(f"\nTranscribing file: {f}")
        segments = backend.transcribe(filepath)
        for segment in segments:
            print(f"[{segment.start:.2f} → {segment.end:.2f}] {segment.text}")
