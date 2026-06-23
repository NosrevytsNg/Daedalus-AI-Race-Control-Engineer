# Text-to-Speech System

import platform
import queue
import subprocess
import threading


VOICE_ENABLED = True

# Leave as None to use your default Windows voice.
# Later, you can set this to something like:
# VOICE_NAME = "Microsoft David Desktop"
# VOICE_NAME = "Microsoft Zira Desktop"
VOICE_NAME = None

# Windows SAPI voice rate range is usually -10 to +10.
# 0 = normal speed.
VOICE_RATE = 1

# Volume range: 0 to 100.
VOICE_VOLUME = 100

# Set to True if you want PowerShell / TTS errors printed.
DEBUG_TTS_ERRORS = True


_speech_queue = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def speak_radio_message(text):
    if not VOICE_ENABLED:
        return

    if text is None:
        return

    text = str(text).strip()

    if not text:
        return

    _ensure_worker_started()
    _speech_queue.put(text)


def _ensure_worker_started():
    global _worker_started

    with _worker_lock:
        if _worker_started:
            return

        worker = threading.Thread(
            target=_speech_worker,
            daemon=True
        )
        worker.start()

        _worker_started = True


def _speech_worker():
    while True:
        text = _speech_queue.get()

        try:
            _speak_windows(text)
        except Exception as error:
            if DEBUG_TTS_ERRORS:
                print(f"[TTS ERROR] {error}")
        finally:
            _speech_queue.task_done()


def _speak_windows(text):
    if platform.system() != "Windows":
        if DEBUG_TTS_ERRORS:
            print("[TTS ERROR] Windows TTS is only available on Windows.")
        return

    powershell_command = r"""
Add-Type -AssemblyName System.Speech

$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer

$voiceName = $args[1]

if ($voiceName -ne $null -and $voiceName.Trim().Length -gt 0) {
    $speaker.SelectVoice($voiceName)
}

$speaker.Rate = [int]$args[2]
$speaker.Volume = [int]$args[3]

$speaker.Speak($args[0])

$speaker.Dispose()
"""

    voice_name = VOICE_NAME if VOICE_NAME is not None else ""

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            powershell_command,
            text,
            voice_name,
            str(VOICE_RATE),
            str(VOICE_VOLUME),
        ],
        capture_output=True,
        text=True,
        creationflags=creation_flags,
        timeout=30,
    )

    if result.returncode != 0 and DEBUG_TTS_ERRORS:
        print("[TTS ERROR] PowerShell speech failed.")
        print(result.stderr)