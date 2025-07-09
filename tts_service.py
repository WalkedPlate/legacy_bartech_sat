import subprocess
import uuid
import os
import platform
from pathlib import Path
import time


def get_piper_config():
    """Detecta el sistema operativo y configura rutas apropiadas"""

    if platform.system() == "Windows":
        # Configuración para Windows
        piper_dir = Path("C:/piper")

        # Verificar que existe la carpeta
        if not piper_dir.exists():
            raise FileNotFoundError(f"Carpeta Piper no encontrada en {piper_dir}")

        piper_exe = piper_dir / "piper.exe"
        # Usar voz claude como preferida
        voice_file = piper_dir / "voices" / "es_MX-claude-high.onnx"

        # Fallback a otras voces si claude no está disponible
        if not voice_file.exists():
            voice_file = piper_dir / "voices" / "es_ES-sharvard-medium.onnx"
        if not voice_file.exists():
            voice_file = piper_dir / "voices" / "es_ES-davefx-medium.onnx"

        # Verificar archivos críticos
        if not piper_exe.exists():
            raise FileNotFoundError(f"piper.exe no encontrado en {piper_exe}")

        if not voice_file.exists():
            raise FileNotFoundError(f"Modelo de voz no encontrado. Verifica que tengas voces en {piper_dir}/voices/")

        return {
            "PIPER_EXEC": str(piper_exe.absolute()),
            "VOICE_PATH": str(voice_file.absolute()),
            "ESPEAK_DATA": None
        }
    else:
        # Configuración para Linux (Rocky Linux )
        piper_exec = os.getenv("PIPER_EXEC", "/opt/piper/piper/piper")

        # Preferir claude, fallback a sharvard
        voice_path = os.getenv("VOICE_PATH")
        if not voice_path:
            # Buscar claude primero
            claude_voice = "/opt/piper/voices/es_MX-claude-high.onnx"
            sharvard_voice = "/opt/piper/voices/es_ES-sharvard-medium.onnx"

            if os.path.exists(claude_voice):
                voice_path = claude_voice
            elif os.path.exists(sharvard_voice):
                voice_path = sharvard_voice
            else:
                voice_path = claude_voice  # Default para error mensaje

        espeak_data = Path("/usr/share/espeak-ng-data")

        # Verificar archivos críticos
        if not os.path.exists(piper_exec):
            raise FileNotFoundError(f"piper no encontrado en {piper_exec}")

        if not os.path.exists(voice_path):
            raise FileNotFoundError(f"Modelo de voz no encontrado en {voice_path}")

        return {
            "PIPER_EXEC": piper_exec,
            "VOICE_PATH": voice_path,
            "ESPEAK_DATA": str(espeak_data) if espeak_data.exists() else None
        }


# Obtener configuración
try:
    config = get_piper_config()
    PIPER_EXEC = config["PIPER_EXEC"]
    VOICE_PATH = config["VOICE_PATH"]
    ESPEAK_DATA = config["ESPEAK_DATA"]

    # Mostrar configuración detectada
    voice_name = Path(VOICE_PATH).stem
    print(f"Piper configurado para {platform.system()}")
    print(f"Ejecutable: {PIPER_EXEC}")
    print(f"Voz: {voice_name}")
    if ESPEAK_DATA:
        print(f"Espeak data: {ESPEAK_DATA}")

except Exception as e:
    print(f"Error configurando Piper: {e}")
    PIPER_EXEC = None
    VOICE_PATH = None
    ESPEAK_DATA = None


def synthesize_to_wav(text: str) -> str:
    """Síntesis de voz con Piper - multiplataforma"""

    if not PIPER_EXEC or not VOICE_PATH:
        raise RuntimeError("Piper no está configurado correctamente")

    # Crear directorio de salida
    Path("audio_out").mkdir(exist_ok=True)
    output_wav = Path("audio_out") / f"{uuid.uuid4()}.wav"

    try:
        # Comando básico
        command = [
            PIPER_EXEC,
            "--model",
            VOICE_PATH,
            "--output-file",
            str(output_wav.absolute())
        ]

        # Agregar espeak-ng-data solo si existe y estamos en Linux
        if ESPEAK_DATA and os.path.exists(ESPEAK_DATA) and platform.system() != "Windows":
            command.extend(["--espeak-ng-data", ESPEAK_DATA])

        print(f"Ejecutando Piper ({platform.system()})")
        print(f"Texto: '{text[:50]}{'...' if len(text) > 50 else ''}'")

        # Ejecutar proceso
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )

        # Comunicar con timeout
        stdout, stderr = process.communicate(input=text, timeout=30)

        print(f"Return code: {process.returncode}")
        if process.returncode != 0:
            print(f"Stderr: '{stderr}'")

        # Verificar éxito
        if process.returncode != 0:
            raise RuntimeError(f"Piper falló (código {process.returncode}): {stderr}")

        # Verificar archivo de salida
        if not output_wav.exists():
            raise FileNotFoundError(f"Archivo WAV no generado: {output_wav}")

        file_size = output_wav.stat().st_size
        print(f"Audio generado: {output_wav.name} ({file_size} bytes)")

        return str(output_wav)

    except subprocess.TimeoutExpired:
        print("Timeout: Piper tomó más de 30 segundos")
        process.kill()
        raise RuntimeError("Piper timeout después de 30 segundos")
    except Exception as e:
        print(f"Error en synthesize_to_wav: {e}")
        raise e


def synthesize(text: str) -> str:
    """Función principal de síntesis"""
    return synthesize_to_wav(text)


def get_system_info() -> dict:
    """Información del sistema para debugging"""
    return {
        "platform": platform.system(),
        "piper_exec": PIPER_EXEC,
        "voice_path": VOICE_PATH,
        "voice_name": Path(VOICE_PATH).stem if VOICE_PATH else None,
        "espeak_data": ESPEAK_DATA,
        "piper_exists": PIPER_EXEC and os.path.exists(PIPER_EXEC) if PIPER_EXEC else False,
        "voice_exists": VOICE_PATH and os.path.exists(VOICE_PATH) if VOICE_PATH else False,
        "espeak_exists": ESPEAK_DATA and os.path.exists(ESPEAK_DATA) if ESPEAK_DATA else False,
        "is_docker": os.getenv("PIPER_EXEC") is not None
    }


def list_available_voices() -> list:
    """Lista las voces disponibles en el sistema"""
    voices = []

    if platform.system() == "Windows":
        voices_dir = Path("C:/piper/voices")
    else:
        voices_dir = Path("/opt/piper/voices")

    if voices_dir.exists():
        for onnx_file in voices_dir.glob("*.onnx"):
            json_file = voices_dir / f"{onnx_file.stem}.onnx.json"
            voices.append({
                "name": onnx_file.stem,
                "onnx_path": str(onnx_file),
                "json_path": str(json_file) if json_file.exists() else None,
                "size_mb": round(onnx_file.stat().st_size / (1024 * 1024), 1)
            })

    return sorted(voices, key=lambda x: x["name"])


# Test básico al importar
if __name__ == "__main__":
    print("=" * 50)
    print("PIPER TTS - INFORMACIÓN DEL SISTEMA")
    print("=" * 50)

    info = get_system_info()
    for key, value in info.items():
        print(f"   {key}: {value}")

    print("\nVOCES DISPONIBLES:")
    voices = list_available_voices()
    if voices:
        for voice in voices:
            print(f"   • {voice['name']} ({voice['size_mb']} MB)")
    else:
        print("   No se encontraron voces")

    print("\nPRUEBA DE SÍNTESIS:")
    if info["piper_exists"] and info["voice_exists"]:
        try:
            test_file = synthesize("Hola, sistema de síntesis de voz funcionando correctamente")
            print(f"   Prueba exitosa: {test_file}")
        except Exception as e:
            print(f"   Error en prueba: {e}")
    else:
        print("   No se puede probar: faltan archivos de Piper")

    print("=" * 50)