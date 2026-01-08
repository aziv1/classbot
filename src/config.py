# GLOBAL VARS, WILL BE BETTER INTEGRATED LATER

"""
When choosing the model. please note the following - Taken from https://huggingface.co/openai/whisper-tiny

Size    	Parameters 	English-only 	Multilingual
tiny    	39 M 	    ✓ 	            ✓
base 	    74 M 	    ✓ 	            ✓
small 	    244 M       ✓ 	            ✓
medium 	    769 M    	✓ 	            ✓
large 	    1550 M 	    x 	            ✓
large-v2 	1550 M  	x 	            ✓
"""

#MODEL AND INPUT STREAMING
FS = 16000
CHUNK_DURATION = 5           
SILENCE_THRESHOLD = 0.3
MODEL_NAME = "small" # Note that this is whisper from open-ai, all run locally. 
LANGUAGE = "en"
BEAM_SIZE = 5
TEMPERATURE = 0.0

# LLM
CHUNK_LEN = 2048
SERVER_URL = "ws://172.16.100.99:8765"

streaming_active = False

#GUI AND MENUS

## Viewport size
viewport_width = 1024
viewport_height = 1024

## Window positions & sizes
window_settings = {
    "transcription_window": {
        "pos": (50, 50),
        "size": (580, 380)
    },
    "control_panel": {
        "pos": (650, 50),
        "size": (250, 250)
    }
}

#USER SETTINGS
## Not Implemented