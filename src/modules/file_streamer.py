import os

def run_single(backend, filepath, out_queue):
    filename = os.path.basename(filepath)

    # Header
    out_queue.put("\n" + "="*60)
    out_queue.put(f"TRANSCRIBING FILE: {filename}")
    out_queue.put("="*60)
    segments = backend.transcribe(filepath)
    for segment in segments:
        out_queue.put(f"[{segment.start:.2f} -> {segment.end:.2f}] {segment.text}")


def run_batch(backend, file_list, out_queue):
    for filepath in file_list:
        filename = os.path.basename(filepath)
        # Header
        out_queue.put("\n" + "="*60)
        out_queue.put(f"TRANSCRIBING FILE: {filename}")
        out_queue.put("="*60)
        segments = backend.transcribe(filepath)
        for segment in segments:
            out_queue.put(f"[{segment.start:.2f} -> {segment.end:.2f}] {segment.text}")
