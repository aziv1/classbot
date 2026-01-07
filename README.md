# ClassBot

## Preface
- At the time of writing 07/01/25, I currently have a broken shoulder and am largely unable to write. THis aims to turn the teachers speech into organised and easy to understand transcriptions seeing as I will be unable to write for the next 4-6 weeks (minimum).
- Hopefully in a future version, a super lightweight language model can be used to automatically parse all of the transcriptions into nicely dot-pointed notes and a light OCR can be used to take a photo of the board and transcribe what is seen into text. However it is probable that equations and the somewhat questionalble writing of the teachers will make this a far fetched hope.

## Personal Notes
### File Tree
~~~raw
├───src
│   |   config.py
│   |   main.py
│   ├───backends
│   │   └───__pycache__
│   ├───gui
│   │   main_window.py
│   │   __init__.py */ Note that this is empty and only exists for behaviour
│   │   └───__pycache__
│   ├───models
│   │   ├───hub
│   │   │   └───models--Systran--faster-whisper-small
│   │   └───xet
│   ├───modules
│   │   └───__pycache__
│   │   file_streamer.py
│   │   mic_streamer.py
│   │   utils.py
│   └───__pycache__
└───venv
    ├───Include
    ├───Lib
    |───Scripts
    |___ ... */ You get it. 
~~~

### To-Do
- [ ] Core Functionality
  - [ ] Transcription interrupt
  - [ ] Microphone Selection with native integration to utils script (I like it and don't want to change it)
  - [ ] Run Flags and Pausing (Dont compromise captured data)
- [ ] Better config integration
- [ ] UI Improvements
  - [ ] User settings menu
  - [ ] Colours ?????
  - [ ] Layout Memory ?
  - [ ] Auto-Scaling
  - [ ] Time Stampting using time lib (Can just use system time)
  - [ ] Possible grid system
- [ ] OCR -> Possibly Over Network
- [ ] GPT -> Possibly Over Network
- [ ] Remote Control - ESP32-CYD B)