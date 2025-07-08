import os
import uuid
from pathlib import Path
from TTS.api import TTS
from num2words import num2words
import re

# Configuración del modelo
MODEL_NAME = "tts_models/es/css10/vits"

tts = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=False)

def convertir_numeros_a_texto(texto: str) -> str:
    """Convierte todos los números en el texto a su forma escrita en español."""
    def reemplazar(match):
        num = int(match.group(0))
        return num2words(num, lang='es')
    return re.sub(r'\d+', reemplazar, texto)

def synthesize_alternative(text: str) -> str:
    """
    Convierte texto a audio WAV usando Coqui TTS.
    Convierte números a texto para mejor pronunciación.
    Retorna la ruta del archivo generado.
    """
    # Convertir números a texto
    texto_convertido = convertir_numeros_a_texto(text)
    
    # Asegura el directorio
    Path("audio_out").mkdir(exist_ok=True)
    
    # Genera archivo con UUID
    output_wav = f"audio_out/{uuid.uuid4()}.wav"
    
    # Ejecuta TTS con el texto convertido
    tts.tts_to_file(text=texto_convertido, file_path=output_wav)
    
    return output_wav
