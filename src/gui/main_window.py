import dearpygui.dearpygui as dpg
import threading
import queue
import time
from modules import mic_streamer, layout_manager
from modules.utils import list_microphones, choose_microphone
from backends import cuda_whisper
import config
from datetime import datetime

# -----------------------------
# QUEUES AND FUNCTIONS
# -----------------------------

audio_queue = queue.Queue()
transcription_queue = queue.Queue()

def transcriber_thread():
    while True:
        audio_chunk, offset = audio_queue.get()
        segments = cuda_whisper.transcribe(audio_chunk)
        for segment in segments:
            text = segment.text.strip()
            if segment.no_speech_prob > (1 - config.SILENCE_THRESHOLD):
                continue
            timestamp = datetime.now().strftime("%H:%M:%S")
            transcription_queue.put(f"[{timestamp}] {text}")
        audio_queue.task_done()


def gui_updater_thread():
    while True:
        text = transcription_queue.get()
        if text:
            dpg.add_text(text, parent="transcription_container")
        transcription_queue.task_done()

def start_streaming_callback():
    config.streaming_active = True
    print("Streaming started")

def stop_streaming_callback():
    config.streaming_active = False
    print("Streaming stopped")

def on_microphone_changed(sender, app_data):
    for idx, name in mic_list:
        if name == app_data:
            selected_index = idx
            break

    was_streaming = config.streaming_active

    if was_streaming:
        config.streaming_active = False
        time.sleep(0.3)  # allow stream to close cleanly
    choose_microphone(selected_index)
    config.streaming_active = was_streaming
    if was_streaming:
        print("Microphone changed -> Streaming On")
    else:
        print("Microphone changed -> Streaming Off")


def save_current_layout():
    data = {
        "viewport": {
            "width": dpg.get_viewport_width(),
            "height": dpg.get_viewport_height()
        },
        "windows": {
            "transcription_window": {
                "pos": dpg.get_item_pos("transcription_window"),
                "size": [
                    dpg.get_item_width("transcription_window"),
                    dpg.get_item_height("transcription_window")
                ]
            },
            "control_panel": {
                "pos": dpg.get_item_pos("control_panel"),
                "size": [
                    dpg.get_item_width("control_panel"),
                    dpg.get_item_height("control_panel")
                ]
            }
        }
    }
    layout_manager.save_layout(data)

# -----------------------------
# GUI
# -----------------------------

def create_main_window():
    dpg.create_context()

    # Load layout.json
    layout = layout_manager.load_layout()

    vw = layout["viewport"]["width"]
    vh = layout["viewport"]["height"]

    t_pos = layout["windows"]["transcription_window"]["pos"]
    t_size = layout["windows"]["transcription_window"]["size"]

    c_pos = layout["windows"]["control_panel"]["pos"]
    c_size = layout["windows"]["control_panel"]["size"]

    # Viewport
    dpg.create_viewport(title="Class Bot", width=vw, height=vh)

    # Transcription Window
    with dpg.window(
        label="Live Transcription",
        tag="transcription_window",
        pos=t_pos,
        width=t_size[0],
        height=t_size[1]
    ):
        with dpg.child_window(width=-1, height=-1, tag="transcription_container"):
            pass


    # Control Panel
    with dpg.window(
        label="Control Panel",
        tag="control_panel",
        pos=c_pos,
        width=c_size[0],
        height=c_size[1]
    ):
        dpg.add_text("Controls")
        dpg.add_button(label="Start Streaming", callback=start_streaming_callback)
        dpg.add_button(label="Stop Streaming", callback=stop_streaming_callback)
        dpg.add_button(label="Reset Layout", callback=lambda: layout_manager.reset_layout())

        # Microphone dropdown
        global mic_list
        mic_list = list_microphones()
        mic_names = [name for _, name in mic_list]

        dpg.add_text("\n Microphone Input")
        dpg.add_combo(
            items=mic_names,
            default_value=mic_names[0],
            callback=on_microphone_changed
        )


    # Start threads
    threading.Thread(target=mic_streamer.start_stream, args=(audio_queue, cuda_whisper), daemon=True).start()
    threading.Thread(target=transcriber_thread, daemon=True).start()
    threading.Thread(target=gui_updater_thread, daemon=True).start()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    save_current_layout()
    dpg.destroy_context()