import re
import os
import whisper
import subprocess
import logging
from typing import Optional, Tuple
from pathlib import Path
import time

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

try:
    model = whisper.load_model("small", device="cuda" if whisper.torch.cuda.is_available() else "cpu")
except Exception:
    model = whisper.load_model("tiny")

NUM_WORDS = {
    "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3",
    "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
    "ocho": "8", "nueve": "9",
    "zero": "0", "un": "1", "do": "2", "tre": "3",
    "sei": "6", "siet": "7", "och": "8", "nuev": "9",
    "el cero": "0", "el uno": "1", "el dos": "2", "el tres": "3",
    "el cuatro": "4", "el cinco": "5", "el seis": "6", "el siete": "7",
    "el ocho": "8", "el nueve": "9"
}

LETTERS = {
    "a": "A", "be": "B", "ce": "C", "de": "D", "e": "E", "efe": "F",
    "ge": "G", "hache": "H", "i": "I", "jota": "J", "ka": "K", "ele": "L",
    "eme": "M", "ene": "N", "o": "O", "pe": "P", "cu": "Q", "ere": "R",
    "ese": "S", "te": "T", "u": "U", "uve": "V", "ve": "V", "doble ve": "W",
    "equis": "X", "ye": "Y", "zeta": "Z",
    "la a": "A", "la be": "B", "la ce": "C", "la de": "D", "la e": "E",
    "la efe": "F", "la ge": "G", "la hache": "H", "la i": "I", "la jota": "J",
    "la ka": "K", "la ele": "L", "la eme": "M", "la ene": "N", "la o": "O",
    "la pe": "P", "la cu": "Q", "la ere": "R", "la ese": "S", "la te": "T",
    "la u": "U", "la ve": "V", "la uve": "V", "la doble ve": "W", "la equis": "X", 
    "la ye": "Y", "la zeta": "Z"
}
AFFIRMATIVE_KEYWORDS = {"sí", "ok", "de acuerdo", "correcto", "afirmativo", "claro", "vale", "exacto", "es correcto", "es así"}
NEGATIVE_KEYWORDS = {"no", "negativo", "incorrecto", "para nada", "no es así", "no quiero", "nunca", "jamás"}

VALID_ZONES = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


def detect_confirmation(text: str) -> bool | None:
    lowered = text.lower()

    # Normaliza el texto a palabras/frases completas con límites
    for word in AFFIRMATIVE_KEYWORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return True

    for word in NEGATIVE_KEYWORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return False

    return None  # No se pudo determinar


def validate_audio_file(audio_path: str) -> Tuple[bool, str]:
    if not os.path.exists(audio_path):
        return False, "Archivo de audio no encontrado"
    
    file_size = os.path.getsize(audio_path)
    if file_size == 0:
        return False, "El archivo de audio está vacío"
    
    if file_size > MAX_FILE_SIZE:
        return False, "Archivo de audio muy grande (máximo 25MB)"
    
    return True, ""

def convert_to_opus_optimized(input_path: str) -> Optional[str]:
    output_path = f"/tmp/audio_{int(time.time())}.opus"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-c:a", "libopus",
            "-b:a", "64k",
            "-vbr", "on",
            "-application", "voip",
            output_path
        ], capture_output=True, check=True, timeout=10)
        return output_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

def clean_text(text: str) -> str:
    text = re.sub(r'[,.:;\-_]', ' ', text.lower())
    text = re.sub(r'[^\w\s]', '', text).strip()
    return re.sub(r'\s+', ' ', text)

def extract_chars(text: str) -> str:
    words = clean_text(text).split()
    chars = []
    i = 0
    
    while i < len(words):
        word = words[i]
        
        if i + 1 < len(words):
            two_word = f"{word} {words[i+1]}"
            if two_word in LETTERS:
                chars.append(LETTERS[two_word])
                i += 2
                continue
            if two_word in NUM_WORDS:
                chars.append(NUM_WORDS[two_word])
                i += 2
                continue
        
        if word in LETTERS:
            chars.append(LETTERS[word])
        elif word in NUM_WORDS:
            chars.append(NUM_WORDS[word])
        elif word.isdigit() and len(word) <= 4:
            chars.extend(word)
        elif word.isalpha() and len(word) <= 3:
            chars.extend(list(word.upper()))
        
        i += 1
    
    return ''.join(chars)

def is_suspicious_plate(letters: str, numbers: str) -> bool:
    if len(set(letters)) == 1 or len(set(numbers)) == 1:
        return True
    
    if numbers in ['000', '0000']:
        return True
    
    suspicious_combos = ['AAA', 'BBB', 'CCC', 'XXX', 'ZZZ']
    if letters in suspicious_combos:
        return True
    
    return False

def extract_plate(text: str) -> Optional[str]:
    text = text.upper().strip()
    
    patterns = [
        r'\b([A-Z]{3})[-\s]*(\d{3})\b',    # 3L3N
        r'\b([A-Z]{2})[-\s]*(\d{4})\b',    # 2L4N
    ]
    
    for pat in patterns:
        match = re.search(pat, text)
        if match and match.group(1)[0] in VALID_ZONES:
            letters, numbers = match.groups()
            if not is_suspicious_plate(letters, numbers):
                return f"{letters}-{numbers}"
    
    chars = extract_chars(text)
    
    if len(chars) >= 6:
        # Formato 3L3N
        if (len(chars) >= 6 and chars[:3].isalpha() and 
            chars[3:6].isdigit() and chars[0] in VALID_ZONES):
            letters, numbers = chars[:3], chars[3:6]
            if not is_suspicious_plate(letters, numbers):
                return f"{letters}-{numbers}"
        
        # Formato 2L4N
        if (len(chars) >= 6 and chars[:2].isalpha() and 
            chars[2:6].isdigit() and chars[0] in VALID_ZONES):
            letters, numbers = chars[:2], chars[2:6]
            if not is_suspicious_plate(letters, numbers):
                return f"{letters}-{numbers}"
    
    return None

def is_valid_plate(plate: Optional[str]) -> bool:
    if not plate or '-' not in plate:
        return False
    
    try:
        letters, numbers = plate.split('-')
        
        if not (letters.isalpha() and numbers.isdigit()):
            return False
        
        valid_format = ((len(letters) == 3 and len(numbers) == 3) or 
                       (len(letters) == 2 and len(numbers) == 4))
        
        if not valid_format:
            return False
        
        if letters[0] not in VALID_ZONES:
            return False
        
        if is_suspicious_plate(letters, numbers):
            return False
        
        return True
        
    except Exception:
        return False

def transcribe_optimized(audio_path: str) -> dict:
    start_time = time.time()
    opus_path = None
    
    try:
        is_valid, error_msg = validate_audio_file(audio_path)
        if not is_valid:
            return {"success": False, "plate": None, "message": error_msg, "processing_time": 0}
        
        opus_path = convert_to_opus_optimized(audio_path)
        if not opus_path or not os.path.exists(opus_path):
            return {"success": False, "plate": None, 
                   "message": "No se detectó voz clara en el audio", 
                   "processing_time": time.time() - start_time}
        
        result = model.transcribe(
            opus_path,
            language="es",
            fp16=False,
            word_timestamps=False,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0
        )
        
        text = result.get("text", "").strip()
        
        if not text or len(text) < 3:
            return {"success": False, "plate": None, 
                   "message": "No se detectó voz clara en el audio",
                   "processing_time": time.time() - start_time}
        
        plate = extract_plate(text)
        
        if is_valid_plate(plate):
            return {"success": True, "plate": plate, 
                   "message": f"Placa detectada: {plate}",
                   "raw_text": text,
                   "processing_time": time.time() - start_time}
        else:
            return {"success": False, "plate": None, 
                   "message": "No pude determinar la matrícula",
                   "raw_text": text,
                   "processing_time": time.time() - start_time}
    
    except Exception as e:
        logger.error(f"Error en transcripción: {e}")
        return {"success": False, "plate": None, 
               "message": "Error técnico en el procesamiento",
               "processing_time": time.time() - start_time}
    
    finally:
        if opus_path and os.path.exists(opus_path):
            try:
                os.remove(opus_path)
            except Exception:
                pass


def transcribe_general(audio_path: str) -> dict:
    start_time = time.time()
    opus_path = None

    try:
        is_valid, error_msg = validate_audio_file(audio_path)
        if not is_valid:
            return {"success": False, "confirmation": None, "message": error_msg}

        opus_path = convert_to_opus_optimized(audio_path)
        if not opus_path or not os.path.exists(opus_path):
            return {"success": False, "confirmation": None,
                    "message": "No se detectó voz clara en el audio"}

        result = model.transcribe(
            opus_path,
            language="es",
            fp16=False,
            word_timestamps=False,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0
        )

        text = result.get("text", "").strip()

        if not text or len(text) < 3:
            return {"success": False, "confirmation": None,
                    "message": "No se detectó voz clara en el audio",
                    }

        confirmation = detect_confirmation(text)

        return {
            "success": True,
            "raw": text,
            "confirmation": confirmation
        }

    except Exception as e:
        logger.error(f"Error en transcripción: {e}")
        return {
            "success": False, "confirmation": None,
            "message": "Error técnico en el procesamiento",
        }

    finally:
        if opus_path and os.path.exists(opus_path):
            try:
                os.remove(opus_path)
            except Exception:
                pass

def transcribe(audio_path: str) -> dict:
    result = transcribe_optimized(audio_path)
    
    if result["success"]:
        return {"text": result.get("raw_text", ""), "message": result["plate"]}
    else:
        return {"text": result.get("raw_text", ""), "message": result["message"]}
    


