import sounddevice as sd
import numpy as np
import time
import config


def start_stream(audio_queue, cuda_whisper):
    """
    Continuously streams audio in chunks and pushes them into audio_queue.
    Automatically stops/starts based on config.streaming_active.
    Automatically reopens the audio stream when the microphone changes.
    """
    samplerate = config.FS
    blocksize = int(config.FS * config.CHUNK_DURATION)
    print("Audio streaming thread started")
    while True:
        if not config.streaming_active:
            time.sleep(0.1)
            continue
        try:
            with sd.InputStream(
                samplerate=samplerate,
                channels=1,
                device=sd.default.device,
                blocksize=blocksize,
                dtype="float32"
            ) as stream:
                print(f"Streaming from microphone: {sd.query_devices(sd.default.device)['name']}")
                while config.streaming_active:
                    audio, overflowed = stream.read(blocksize)
                    if overflowed:
                        print("Warning: audio buffer overflow")
                    audio = np.squeeze(audio)
                    audio_queue.put((audio, 0))
        except Exception as e:
            print("Error in audio stream:", e)
            time.sleep(0.5)
