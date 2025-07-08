import os
import uuid
import time
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Configuración global
SHERPA_MODELS_DIR = Path("/opt/sherpa_models")
DEFAULT_MODEL = "es_ES-davefx-medium"

# Variables globales para mantener el modelo cargado
_sherpa_tts = None
_current_model = None


def load_sherpa_model(model_id: str = DEFAULT_MODEL):
    """Cargar modelo Sherpa-ONNX (solo se carga una vez)"""
    global _sherpa_tts, _current_model

    if _sherpa_tts is not None and _current_model == model_id:
        return _sherpa_tts

    try:
        import sherpa_onnx

        # Usar estructura de carpetas real
        model_dir = SHERPA_MODELS_DIR / "vits-piper-es_ES-davefx-medium"
        model_file = model_dir / f"{model_id}.onnx"
        tokens_file = model_dir / "tokens.txt"
        data_dir = model_dir / "espeak-ng-data"

        # Verificar archivos
        if not model_file.exists():
            raise FileNotFoundError(f"Modelo Sherpa no encontrado: {model_file}")

        print(f"🔧 Cargando modelo Sherpa: {model_id}")
        print(f"📁 Ruta: {model_file}")
        start_time = time.time()

        # Configuración optimizada para el servidor del SAT
        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=str(model_file),
                    lexicon="",
                    tokens=str(tokens_file) if tokens_file.exists() else "",
                    data_dir=str(data_dir) if data_dir.exists() else "",
                    length_scale=1.0,
                    noise_scale=0.667,
                    noise_scale_w=0.8,
                ),
                provider="cpu",
                debug=False,
                num_threads=4,
            ),
            rule_fsts="",
            max_num_sentences=1,
        )

        _sherpa_tts = sherpa_onnx.OfflineTts(config)
        _current_model = model_id

        load_time = time.time() - start_time
        print(f"✅ Sherpa cargado en {load_time:.2f}s")

        return _sherpa_tts

    except ImportError:
        raise RuntimeError("sherpa-onnx no está instalado. Ejecuta: pip install sherpa-onnx")
    except Exception as e:
        logger.error(f"Error cargando Sherpa: {e}")
        raise RuntimeError(f"Error cargando modelo Sherpa: {e}")


def synthesize_sherpa(text: str, model_id: str = DEFAULT_MODEL, speaker_id: int = 0, speed: float = 1.0) -> str:
    """
    Síntesis de voz con Sherpa-ONNX
    """
    start_time = time.time()

    try:
        # Cargar modelo (lazy loading)
        tts = load_sherpa_model(model_id)

        # Crear directorio de salida
        Path("audio_out").mkdir(exist_ok=True)
        output_wav = Path("audio_out") / f"sherpa_{uuid.uuid4()}.wav"

        print(f"🎵 Sherpa TTS: '{text[:50]}...'")

        # Generar audio - CORREGIDO
        synthesis_start = time.time()
        audio = tts.generate(text, sid=speaker_id, speed=speed)  # ← USAR 'sid' no 'speaker_id'
        synthesis_time = time.time() - synthesis_start

        # Guardar como WAV
        import soundfile as sf
        sf.write(str(output_wav), audio.samples, samplerate=audio.sample_rate)

        # Verificar archivo
        if not output_wav.exists():
            raise FileNotFoundError(f"Archivo no generado: {output_wav}")

        file_size = output_wav.stat().st_size
        duration = len(audio.samples) / audio.sample_rate
        total_time = time.time() - start_time

        print(f"✅ Sherpa: {total_time:.2f}s total, {synthesis_time:.2f}s síntesis")
        print(f"   Archivo: {file_size} bytes, {duration:.2f}s duración")

        return str(output_wav)

    except Exception as e:
        logger.error(f"Error en Sherpa TTS: {e}")
        raise RuntimeError(f"Sherpa TTS falló: {e}")


def get_available_models() -> list:
    """Obtener lista de modelos Sherpa instalados"""
    if not SHERPA_MODELS_DIR.exists():
        return []

    models = []
    for model_dir in SHERPA_MODELS_DIR.iterdir():
        if model_dir.is_dir():
            model_file = model_dir / f"{model_dir.name}.onnx"
            if model_file.exists():
                # Leer info del modelo si existe
                config_file = model_dir / "config.json"
                if config_file.exists():
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        models.append({
                            "id": model_dir.name,
                            "description": config.get("description", model_dir.name),
                            "path": str(model_file)
                        })
                    except:
                        models.append({
                            "id": model_dir.name,
                            "description": model_dir.name,
                            "path": str(model_file)
                        })
                else:
                    models.append({
                        "id": model_dir.name,
                        "description": model_dir.name,
                        "path": str(model_file)
                    })

    return models


def switch_model(model_id: str):
    """Cambiar modelo activo"""
    global _sherpa_tts, _current_model

    model_dir = SHERPA_MODELS_DIR / model_id
    if not (model_dir / f"{model_id}.onnx").exists():
        raise FileNotFoundError(f"Modelo {model_id} no está instalado")

    # Forzar recarga
    _sherpa_tts = None
    _current_model = None

    # Cargar nuevo modelo
    load_sherpa_model(model_id)
    print(f"Cambiado a modelo: {model_id}")


def get_sherpa_info() -> dict:
    """Información del estado actual de Sherpa"""
    return {
        "model_loaded": _sherpa_tts is not None,
        "current_model": _current_model,
        "available_models": get_available_models(),
        "models_directory": str(SHERPA_MODELS_DIR)
    }


# Función principal compatible con tu sistema actual
def synthesize_alternative_sherpa(text: str) -> str:
    """Función compatible con tu sistema actual"""
    return synthesize_sherpa(text)


# Pre-cargar modelo al importar (opcional)
try:
    if (SHERPA_MODELS_DIR / DEFAULT_MODEL).exists():
        load_sherpa_model(DEFAULT_MODEL)
        print(f"Sherpa pre-cargado: {DEFAULT_MODEL}")
except Exception as e:
    print(f"Sherpa no pre-cargado: {e}")