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
from backends import cuda_whisper
import modules.file_streamer as file_streamer
import config

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


# -----------------------------
# GPU / MODEL CLEANUP
# -----------------------------

def debug_vram(label=""):
    if not torch.cuda.is_available():
        print(f"[VRAM DEBUG] {label} | CUDA not available")
        return
    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    print(f"[VRAM DEBUG] {label} | Allocated: {allocated:.2f} GB | Reserved: {reserved:.2f} GB")


def free_gpu_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    debug_vram("After cleanup")


def unload_whisper():
    global cuda_whisper
    print("Unloading Whisper...")
    try:
        del cuda_whisper.model
    except Exception:
        pass
    try:
        del cuda_whisper.tokenizer
    except Exception:
        pass
    try:
        del cuda_whisper
    except Exception:
        pass
    free_gpu_memory()
    print("Whisper unloaded")


def reload_whisper():
    global cuda_whisper
    print("Reloading Whisper...")
    from backends import cuda_whisper as whisper_backend
    cuda_whisper = whisper_backend
    free_gpu_memory()
    print("Whisper reloaded")


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
# GPT EXPORT HELPERS
# -----------------------------

def get_full_transcription_text():
    children = dpg.get_item_children("transcription_container", 1)
    lines = []
    for child in children:
        value = dpg.get_value(child)
        if value:
            lines.append(value)
    return "\n".join(lines)


def open_gpt_prompt_window():
    dpg.configure_item("system_prompt_window", show=True)


def run_gpt_export():
    from backends.qwen3_generate import run_llm, unload_llm

    # Pause streaming if active
    was_streaming = config.streaming_active
    if was_streaming:
        config.streaming_active = False
        print("Streaming paused for GPT export")

    debug_vram("Before unloading Whisper")

    # Unload Whisper to free VRAM
    unload_whisper()

    debug_vram("Before GPT load")

    # Build prompt
    system_prompt = dpg.get_value("system_prompt_input")
    transcript = get_full_transcription_text()
    full_prompt = f"<system>{system_prompt}</system>\n\n{transcript}"

    # Run LLM
    print("Running GPT export...")
    try:
        response = run_llm(full_prompt)
    except Exception as e:
        print("Error during GPT export:", e)
        response = f"[ERROR] {e}"

    # Display output
    dpg.set_value("gpt_output_text", response)
    dpg.configure_item("gpt_output_window", show=True)

    # Unload LLM
    print("Unloading GPT model...")
    try:
        unload_llm()
    except Exception as e:
        print("Error unloading GPT model:", e)
    free_gpu_memory()
    debug_vram("After GPT unload")

    # Reload Whisper
    reload_whisper()

    # Resume streaming
    if was_streaming:
        config.streaming_active = True
        print("Streaming resumed after GPT export")


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
    children = dpg.get_item_children("transcription_container", 1)
    for child in children:
        dpg.delete_item(child)

# -----------------------------
# GUI
# -----------------------------

def create_main_window():
    dpg.create_context()

    layout = layout_manager.load_layout()

    vw = layout["viewport"]["width"]
    vh = layout["viewport"]["height"]

    t_pos = layout["windows"]["transcription_window"]["pos"]
    t_size = layout["windows"]["transcription_window"]["size"]

    c_pos = layout["windows"]["control_panel"]["pos"]
    c_size = layout["windows"]["control_panel"]["size"]

    dpg.create_viewport(title="Class Bot", width=vw, height=vh)

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

    # SYSTEM PROMPT WINDOW

    system_prompt = """
                    # Role
                    You are a high-efficiency text processor specialized in transcript cleaning.

                    # Task
                    1. ANALYZE the provided transcript text.
                    2. IGNORE all timestamps (e.g., 00:00, [12:15], 14:02:10), speaker IDs, and technical metadata.
                    3. SUMMARIZE the core message into a well-organized Markdown list.

                    # Output Format
                    - Use a bold "### Summary" header.
                    - Use bullet points (-) for main ideas.
                    - Use nested indents for supporting details.
                    - Use bold text for key terms or names.
                    - Do not provide an introduction or a conclusion—output the bullet points only.
                    """

    with dpg.window(label="System Prompt", tag="system_prompt_window", show=False, width=500, height=300):
        dpg.add_text("System Prompt:")
        dpg.add_input_text(tag="system_prompt_input", multiline=True, width=-1, height=150,
                           default_value=system_prompt)
        dpg.add_button(label="Run GPT Export", callback=lambda: run_gpt_export())

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
        with dpg.child_window(width=-1, height=-1, tag="transcription_container"):
            pass

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
    threading.Thread(target=gui_updater_thread, daemon=True).start()

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
            dpg.add_menu_item(label="Export GPT", callback=open_gpt_prompt_window)

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