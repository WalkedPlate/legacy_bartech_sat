import subprocess
import uuid
import os
from pathlib import Path
import time

import subprocess
import uuid
import os
import platform
from pathlib import Path
import time


# Configuración multiplataforma
def get_piper_config():
    """Detecta el sistema operativo y configura rutas apropiadas"""

    if platform.system() == "Windows":
        # Usar rutas absolutas completas
        piper_dir = Path("C:/piper")

        # Verificar que existe la carpeta
        if not piper_dir.exists():
            raise FileNotFoundError(f"Carpeta Piper no encontrada en {piper_dir}")

        piper_exe = piper_dir / "piper.exe"
        # voice_file = piper_dir / "voices" / "es_ES-davefx-medium.onnx"
        # voice_file = piper_dir / "voices" / "es_MX-claude-high.onnx"  # Voz mexicana
        voice_file = piper_dir / "voices" / "es_ES-sharvard-medium.onnx"

        # Verificar archivos críticos
        if not piper_exe.exists():
            raise FileNotFoundError(f"piper.exe no encontrado en {piper_exe}")

        if not voice_file.exists():
            raise FileNotFoundError(f"Modelo de voz no encontrado en {voice_file}")

        return {
            "PIPER_EXEC": str(piper_exe.absolute()),
            "VOICE_PATH": str(voice_file.absolute()),
            "ESPEAK_DATA": None
        }
    else:
        # (configuración original de Edward)
        return {
            "PIPER_EXEC": "/home/edward/piper/piper",
            "VOICE_PATH": "/home/edward/voices/es_MX-claude-high.onnx",
            "ESPEAK_DATA": "/home/edward/espeak-ng-data"
        }


# Obtener configuración
try:
    config = get_piper_config()
    PIPER_EXEC = config["PIPER_EXEC"]
    VOICE_PATH = config["VOICE_PATH"]
    ESPEAK_DATA = config["ESPEAK_DATA"]
    print(f"Piper configurado: {PIPER_EXEC}")
    print(f"Voz configurada: {VOICE_PATH}")
except Exception as e:
    print(f"Error configurando Piper: {e}")
    PIPER_EXEC = None
    VOICE_PATH = None
    ESPEAK_DATA = None


def synthesize_to_wav(text: str) -> str:
    """Síntesis de voz con Piper - versión corregida para Windows"""

    if not PIPER_EXEC or not VOICE_PATH:
        raise RuntimeError("Piper no está configurado correctamente")

    # Crear directorio de salida
    Path("audio_out").mkdir(exist_ok=True)
    output_wav = Path("audio_out") / f"{uuid.uuid4()}.wav"

    try:
        # Comando con rutas absolutas
        command = [
            PIPER_EXEC,
            "--model",
            VOICE_PATH,
            "--output-file",
            str(output_wav.absolute())
        ]

        # NO agregar espeak-ng-data en Windows
        if ESPEAK_DATA and os.path.exists(ESPEAK_DATA):
            command.extend(["--espeak-ng-data", ESPEAK_DATA])

        print(f"🔧 Ejecutando comando: {' '.join(command)}")
        print(f"📁 Directorio trabajo: {os.getcwd()}")
        print(f"📝 Texto a sintetizar: '{text}'")

        # Ejecutar proceso
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()  # Directorio de trabajo explícito
        )

        # Comunicar con timeout
        stdout, stderr = process.communicate(input=text, timeout=15)

        print(f"🔍 Return code: {process.returncode}")
        print(f"📤 Stdout: '{stdout}'")
        print(f"📤 Stderr: '{stderr}'")

        # Verificar éxito
        if process.returncode != 0:
            raise RuntimeError(f"Piper falló (código {process.returncode}): {stderr}")

        # Verificar archivo de salida
        if not output_wav.exists():
            raise FileNotFoundError(f"Archivo WAV no generado: {output_wav}")

        file_size = output_wav.stat().st_size
        print(f"✅ Audio generado: {output_wav} ({file_size} bytes)")

        return str(output_wav)

    except subprocess.TimeoutExpired:
        print("Timeout: Piper tomó más de 15 segundos")
        process.kill()
        raise RuntimeError("Piper timeout después de 15 segundos")
    except Exception as e:
        print(f"Error en synthesize_to_wav: {e}")
        raise e


def synthesize(text: str) -> str:
    """Función principal de síntesis"""
    return synthesize_to_wav(text)

