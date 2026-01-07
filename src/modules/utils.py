import sounddevice as sd
import numpy as np
from config import SILENCE_THRESHOLD

def is_silent(audio_chunk, threshold=SILENCE_THRESHOLD):
    return np.max(np.abs(audio_chunk)) < threshold

def choose_microphone():
    """List input devices and allow user to select one."""
    input_devices = []
    print("Available input devices:")
    for i, dev in enumerate(sd.query_devices()):
        if dev['max_input_channels'] > 0:
            input_devices.append((i, dev['name']))
            print(f"{i}: {dev['name']}")

    # Prompt user to select one
    while True:
        try:
            choice = int(input("\nEnter the number of the microphone to use: "))
            if any(choice == i for i, _ in input_devices):
                sd.default.device = choice
                break
            else:
                print("Invalid selection, try again.")
        except ValueError:
            print("Please enter a valid number.")

    # Print chosen mic
    mic_info = sd.query_devices(sd.default.device[0])
    print(f"\nUsing input device: {mic_info['name']}")
    return mic_info['name']
