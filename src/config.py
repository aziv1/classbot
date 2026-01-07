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
SILENCE_THRESHOLD = 0.01
MODEL_NAME = "small" # Note that this is whisper from open-ai, all run locally. 
LANGUAGE = "en"
BEAM_SIZE = 5
TEMPERATURE = 0.0

#GUI AND MENUS
## Not Implemented

#USER SETTINGS
## Not Implemented