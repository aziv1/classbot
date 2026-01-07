import dearpygui.dearpygui as dpg
import threading
import queue
from modules import mic_streamer
from backends import cuda_whisper
from config import *

# -----------------------------
# QUEUES AND THREADING
# -----------------------------

audio_queue = queue.Queue()
transcription_queue = queue.Queue()

def transcriber_thread():
    while True:
        audio_chunk, offset = audio_queue.get()
        segments = cuda_whisper.transcribe(audio_chunk)
        for segment in segments:
            transcription_queue.put(segment.text)  # raw text only
        audio_queue.task_done()

def gui_updater_thread():
    while True:
        text = transcription_queue.get()
        if text:
            # Use DearPyGui's thread-safe function to update the GUI
            dpg.add_text(text, parent="transcription_container")
        transcription_queue.task_done()

# -----------------------------
# GUI
# -----------------------------
def create_main_window():
    dpg.create_context()
    dpg.create_viewport(title="Class Bot", width=1024, height=1024)

    # Transcription Window
    with dpg.window(label="Live Transcription", width=580, height=380):
        #dpg.add_text("Live Transcription", color=(200, 200, 255))
        with dpg.child_window(width=560, height=300, tag="transcription_container"):
            pass  # all transcribed text will go here
    
    # Control Panel
    with dpg.window(label="Control Panel", width= 250, height=250):
        dpg.add_text("stand-in", color=(200, 200, 255))

    # User Settings
    ## Not Implemented 

    # Start threads
    threading.Thread(target=mic_streamer.start_stream, args=(audio_queue, cuda_whisper), daemon=True).start()
    threading.Thread(target=transcriber_thread, daemon=True).start()
    threading.Thread(target=gui_updater_thread, daemon=True).start()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

