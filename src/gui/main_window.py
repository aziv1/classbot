import os
import gc
import time
import queue
import threading
from datetime import datetime
from tkinter import Tk, filedialog
import dearpygui.dearpygui as dpg
import torch
from modules import mic_streamer, layout_manager
from modules.utils import list_microphones, choose_microphone
from backends.cuda_whisper import CudaWhisperBackend
cuda_whisper = CudaWhisperBackend()
cuda_whisper.load()
import modules.file_streamer as file_streamer
import config
import subprocess
import json
import sys
import asyncio
import websockets
import json
import threading

# Use expandable segments to reduce fragmentation
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

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

def start_streaming_callback():
    config.streaming_active = True
    print("Streaming started")


def stop_streaming_callback():
    config.streaming_active = False
    print("Streaming stopped")

# -----------------------------
# RAW EXPORT CALLBACK
# -----------------------------

def save_raw_callback(sender, app_data):
    file_path = app_data["file_path_name"]

    children = dpg.get_item_children("transcription_container", 1)
    lines = []
    for child in children:
        value = dpg.get_value(child)
        if value:
            lines.append(value)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Saved RAW transcription to: {file_path}")
    except Exception as e:
        print("Error saving file:", e)

# -----------------------------
# MICROPHONE + FILE MODE
# -----------------------------

def on_microphone_changed(sender, app_data):
    for idx, name in mic_list:
        if name == app_data:
            selected_index = idx
            break
    was_streaming = config.streaming_active
    if was_streaming:
        config.streaming_active = False
        time.sleep(0.3)
    choose_microphone(selected_index)
    config.streaming_active = was_streaming
    print(
        "Microphone changed -> Streaming On"
        if was_streaming
        else "Microphone changed -> Streaming Off"
    )

def append_transcription(text):
    old = dpg.get_value("transcription_text") or ""
    dpg.set_value("transcription_text", old + text + "\n")

def start_transcription_queue_reader(out_queue):
    def reader():
        while True:
            try:
                text = out_queue.get()
                append_transcription(text)
            except Exception:
                time.sleep(0.01)

    threading.Thread(target=reader, daemon=True).start()

# -----------------------------
# EXPORT GPT
# -----------------------------

def chunk_text_no_split_lines(text: str, max_chars: int = 2000):
    lines = text.splitlines(keepends=True)
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) > max_chars:
            if current.strip():
                chunks.append(current)
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current)
    return chunks

def export_gpt():
    transcription_text = dpg.get_value("transcription_text")
    # Handle None or empty safely
    if not transcription_text or not transcription_text.strip():
        log_packet("No transcription text available.")
        return
    dpg.set_value("packet_log_text", "")
    dpg.set_value("gpt_output_text", "")
    chunks = chunk_text_no_split_lines(transcription_text, max_chars=2000)
    log_packet(f"Prepared {len(chunks)} chunks.")
    def runner():
        asyncio.run(run_gpt_export(chunks))
    threading.Thread(target=runner, daemon=True).start()

def log_packet(packet: str):
    old = dpg.get_value("packet_log_text")
    new = old + packet + "\n\n"
    dpg.set_value("packet_log_text", new)

def show_gpt_output(summary_text: str):
    dpg.set_value("gpt_output_text", summary_text)
    dpg.configure_item("gpt_output_window", show=True)

async def run_gpt_export(chunks):
    try:
        async with websockets.connect(config.SERVER_URL, max_size=None) as ws:

            # Send each chunk
            for idx, chunk in enumerate(chunks):
                packet = {
                    "command": "summarize",
                    "chunk_id": idx,
                    "text": chunk
                }

                raw_out = json.dumps(packet, ensure_ascii=False)
                log_packet(f"CLIENT -> SERVER:\n{raw_out}")
                await ws.send(raw_out)

                response_raw = await ws.recv()
                log_packet(f"SERVER -> CLIENT:\n{response_raw}")

            # Send finish
            finish_packet = {"command": "finish"}
            raw_out = json.dumps(finish_packet, ensure_ascii=False)
            log_packet(f"CLIENT -> SERVER:\n{raw_out}")
            await ws.send(raw_out)

            # Receive final output
            final_raw = await ws.recv()
            log_packet(f"SERVER -> CLIENT:\n{final_raw}")

            final_response = json.loads(final_raw)

            if final_response.get("command") == "final_output":
                summary_text = final_response.get("summary", "")
                show_gpt_output(summary_text)

    except Exception as e:
        log_packet(f"Error during GPT export: {e}")

# -----------------------------
# FILE MODE
# -----------------------------

def start_file_mode():
    was_streaming = config.streaming_active
    if was_streaming:
        config.streaming_active = False
        print("Streaming paused for file mode")

    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select audio file(s)",
        filetypes=[("Audio Files", "*.wav *.mp3 *.flac *.m4a")],
    )
    root.destroy()

    if not file_paths:
        print("No files selected")
        config.streaming_active = was_streaming
        return

    threading.Thread(
        target=run_file_mode_thread, args=(file_paths, was_streaming), daemon=True
    ).start()


def run_file_mode_thread(file_paths, resume_streaming):
    if len(file_paths) == 1:
        file_streamer.run_single(cuda_whisper, file_paths[0], transcription_queue)
    else:
        file_streamer.run_batch(cuda_whisper, file_paths, transcription_queue)
    if resume_streaming:
        config.streaming_active = True

# -----------------------------
# LAYOUT + CLEAR
# -----------------------------

def save_current_layout():
    data = {
        "viewport": {
            "width": dpg.get_viewport_width(),
            "height": dpg.get_viewport_height(),
        },
        "windows": {
            "transcription_window": {
                "pos": dpg.get_item_pos("transcription_window"),
                "size": [
                    dpg.get_item_width("transcription_window"),
                    dpg.get_item_height("transcription_window"),
                ],
            },
            "control_panel": {
                "pos": dpg.get_item_pos("control_panel"),
                "size": [
                    dpg.get_item_width("control_panel"),
                    dpg.get_item_height("control_panel"),
                ],
            },
        },
    }
    layout_manager.save_layout(data)

def clear_transcription_box():
    dpg.set_value("transcription_text", "")

# -----------------------------
# GUI
# -----------------------------

def create_main_window():
    dpg.create_context()
    
    layout = layout_manager.load_layout()
    start_transcription_queue_reader(transcription_queue)

    vw = layout["viewport"]["width"]
    vh = layout["viewport"]["height"]

    t_pos = layout["windows"]["transcription_window"]["pos"]
    t_size = layout["windows"]["transcription_window"]["size"]

    c_pos = layout["windows"]["control_panel"]["pos"]
    c_size = layout["windows"]["control_panel"]["size"]

    dpg.create_viewport(title="Class Bot", width=vw, height=vh)

    with dpg.theme(tag="packet_log_theme"):
        with dpg.theme_component(dpg.mvInputText):
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 80, 80, 255))

    # RAW EXPORT FILE DIALOG
    with dpg.file_dialog(
        directory_selector=False,
        show=False,
        callback=save_raw_callback,
        id="save_raw_dialog",
        width=600,
        height=400
    ):
        dpg.add_file_extension(".txt", color=(0, 255, 0, 255))

    with dpg.window(label="Export GPT", tag="export_gpt_window", show=False, width=500, height=350):
        dpg.add_text("Server Packets:")
        dpg.add_input_text(
            tag="packet_log_text",
            multiline=True,
            readonly=True,
            width=-1,
            height=275
        )
        dpg.add_button(label="Run GPT Export", callback=export_gpt)

    # GPT OUTPUT WINDOW
    with dpg.window(label="GPT Output", tag="gpt_output_window", show=False, width=600, height=400):
        dpg.add_input_text(tag="gpt_output_text", multiline=True, width=-1, height=-1)

    # TRANSCRIPTION WINDOW
    with dpg.window(
    label="Live Transcription",
    tag="transcription_window",
    pos=t_pos,
    width=t_size[0],
    height=t_size[1]
    ):
        with dpg.child_window(
            tag="transcription_container",
            width=-1,
            height=-1,
            border=True
        ):
            dpg.add_input_text(
                tag="transcription_text",
                multiline=True,
                readonly=True,
                width=-1,
                height=-1
            )

    # CONTROL PANEL
    with dpg.window(
        label="Control Panel",
        tag="control_panel",
        pos=c_pos,
        width=c_size[0],
        height=c_size[1]
    ):
        dpg.add_text("File Mode")
        dpg.add_button(label="Open File(s)", callback=start_file_mode)

        global mic_list
        mic_list = list_microphones()
        mic_names = [name for _, name in mic_list]

        dpg.add_text("\nMicrophone Input")
        dpg.add_combo(
            items=mic_names,
            default_value=mic_names[0],
            callback=on_microphone_changed
        )
        dpg.add_button(label="Start Streaming", callback=start_streaming_callback)
        dpg.add_button(label="Stop Streaming", callback=stop_streaming_callback)

        dpg.add_text("\nLayout")
        dpg.add_button(label="Clear Text", callback=clear_transcription_box)
        dpg.add_button(label="Reset Layout", callback=lambda: layout_manager.reset_layout())
    
    # THREADS
    threading.Thread(target=mic_streamer.start_stream, args=(audio_queue, cuda_whisper), daemon=True).start()
    threading.Thread(target=transcriber_thread, daemon=True).start()

    dpg.setup_dearpygui()
    dpg.show_viewport()

    # MENU BAR
    with dpg.viewport_menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Open File(s)...", callback=start_file_mode)
            dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())

        with dpg.menu(label="Edit"):
            dpg.add_menu_item(label="Clear Text", callback=clear_transcription_box)

        with dpg.menu(label="Export"):
            dpg.add_menu_item(label="Export RAW", callback=lambda: dpg.show_item("save_raw_dialog"))
            dpg.add_menu_item(label="Export GPT", callback=lambda: dpg.configure_item("export_gpt_window", show=True))

        with dpg.menu(label="View"):
            dpg.add_menu_item(
                label="Toggle Transcription Window",
                callback=lambda: dpg.configure_item("transcription_window",
                                                    show=not dpg.is_item_shown("transcription_window"))
            )
            dpg.add_menu_item(
                label="Toggle Control Panel",
                callback=lambda: dpg.configure_item("control_panel",
                                                    show=not dpg.is_item_shown("control_panel"))
            )

    dpg.start_dearpygui()
    save_current_layout()
    dpg.destroy_context()