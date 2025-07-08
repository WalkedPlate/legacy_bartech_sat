import subprocess
import uuid
import os
from pathlib import Path
import time

PIPER_EXEC = "/home/edward/piper/piper"
VOICE_PATH = "/home/edward/voices/es_MX-claude-high.onnx" 
ESPEAK_DATA = "/home/edward/espeak-ng-data"

def synthesize_to_wav(text: str) -> str:


    Path("audio_out").mkdir(exist_ok=True)

    output_wav = f"audio_out/{uuid.uuid4()}.wav"

    try:
        command = [
            PIPER_EXEC,
            "--model", VOICE_PATH,
            "--output-file", output_wav,
            "--espeak-ng-data", ESPEAK_DATA
        ]

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(input=text, timeout=10)

        if process.returncode != 0:
            raise RuntimeError(f"Piper falló: {stderr}")

        if not Path(output_wav).exists():
            raise FileNotFoundError(f"Archivo WAV no generado: {output_wav}")

        return output_wav

    except Exception as e:
        raise e


def synthesize(text: str) -> str:
    return synthesize_to_wav(text)
