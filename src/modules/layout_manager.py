import json
import os

LAYOUT_FILE = "layout.json"

DEFAULT_LAYOUT = {
    "viewport": {
        "width": 1024,
        "height": 1024
    },
    "windows": {
        "transcription_window": {
            "pos": [50, 50],
            "size": [580, 380]
        },
        "control_panel": {
            "pos": [650, 50],
            "size": [250, 250]
        }
    }
}


def load_layout():
    """Load layout.json or return defaults if missing/corrupted."""
    if not os.path.exists(LAYOUT_FILE):
        return DEFAULT_LAYOUT

    try:
        with open(LAYOUT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_LAYOUT


def save_layout(data):
    """Save layout.json safely."""
    with open(LAYOUT_FILE, "w") as f:
        json.dump(data, f, indent=4)


def reset_layout():
    """Restore default layout.json."""
    save_layout(DEFAULT_LAYOUT)