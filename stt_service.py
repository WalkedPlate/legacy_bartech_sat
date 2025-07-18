import re
import os
import subprocess
import logging
from typing import Optional, Tuple
from pathlib import Path
import time
from faster_whisper import WhisperModel
import difflib

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
# Cargar modelo de Faster-Whisper
try:
    model = WhisperModel("medium", device="cpu", compute_type="int8")
except Exception as e:
    logger.error(f"No se pudo cargar el modelo: {e}")
    raise
NUM_WORDS = {
    "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3",
    "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
    "ocho": "8", "nueve": "9",
    "zero": "0", "un": "1", "do": "2", "tre": "3",
    "sei": "6", "siet": "7", "och": "8", "nuev": "9",
    "el cero": "0", "el uno": "1", "el dos": "2", "el tres": "3",
    "el cuatro": "4", "el cinco": "5", "el seis": "6", "el siete": "7",
    "el ocho": "8", "el nueve": "9",
    "uno a": "1A", "dos a": "2A", "tres a": "3A",
    "cuatro a": "4A", "cinco a": "5A", "seis a": "6A",
    "siete a": "7A", "ocho a": "8A",

    "sero": "0", "huno": "1", "dose": "2", "trez": "3", "quattro": "4",
    "sinco": "5", "zinco": "5", "seys": "6", "ceiz": "6", "ciete": "7",
    "syete": "7", "hoche": "8", "nuebe": "9", "nuevé": "9",

    "la cero": "0", "el zero": "0", "la zero": "0", "la uno": "1",
    "el una": "1", "la una": "1", "la dos": "2", "el dose": "2",
    "la dose": "2", "la tres": "3", "el trez": "3", "la trez": "3",
    "la cuatro": "4", "el quattro": "4", "la quattro": "4", "la cinco": "5",
    "el sinco": "5", "la sinco": "5", "la seis": "6", "el seys": "6",
    "la seys": "6", "la siete": "7", "el ciete": "7", "la ciete": "7",
    "la ocho": "8", "el hoche": "8", "la hoche": "8", "la nueve": "9",
    "el nuebe": "9", "la nuebe": "9",

    "diez": "10", "dies": "10", "diés": "10", "once": "11", "onse": "11",
    "honse": "11", "doce": "12", "doze": "12"
}
LETTERS = {
    "a": "A", "be": "B", "ce": "C", "de": "D", "e": "E", "efe": "F",
    "ge": "G", "hache": "H", "i": "I","y":"I", "jota": "J", "ka": "K", "ele": "L",
    "eme": "M", "ene": "N", "o": "O", "pe": "P", "cu": "Q", "ere": "R",
    "ese": "S", "te": "T", "u": "U", "uve": "V", "ve": "V", "doble ve": "W",
    "equis": "X", "ye": "Y", "zeta": "Z",

    "la a": "A", "la be": "B", "la ce": "C", "la de": "D", "la e": "E",
    "la efe": "F", "la ge": "G", "la hache": "H", "la i": "I", "la jota": "J",
    "la ka": "K", "la ele": "L", "la eme": "M", "la ene": "N", "la o": "O",
    "la pe": "P", "la cu": "Q", "la ere": "R", "la ese": "S", "la te": "T",
    "la u": "U", "la ve": "V", "la uve": "V", "la doble ve": "W", "la equis": "X",
    "la ye": "Y", "la zeta": "Z",
    "i griega": "Y", "la i griega": "Y",
    "doble u": "W", "uve doble": "W",
    "be grande": "B", "be larga": "B",
    "ve corta": "V", "ve chica": "V", "ve pequeña": "V",

    "ha": "A", "ah": "A", "se": "C", "ze": "C", "dé": "D", "dhe": "D",
    "he": "E", "eh": "E", "hefe": "F", "eph": "F", "gue": "G", "je": "G",
    "ache": "H", "hace": "H", "ash": "H", "hi": "I","hota": "J", "jotta": "J",
    "yota": "J", "ca": "K", "kha": "K", "elle": "L", "el": "L", "em": "M",
    "emme": "M", "en": "N", "enne": "N", "ho": "O", "oh": "O", "pé": "P",
    "phe": "P", "que": "Q", "khu": "Q", "erre": "R", "rre": "R", "er": "R",
    "sse": "S", "té": "T", "the": "T", "hu": "U", "uh": "U", "ube": "V",
    "doble uve": "W", "uve doble": "W", "ekis": "X", "ex": "X", "equys": "X",
    "yé": "Y", "greek i": "Y", "seta": "Z", "zetta": "Z", "zet": "Z",

    "la ha": "A", "el ha": "A", "la ah": "A", "la se": "C", "el se": "C",
    "la ze": "C", "la dé": "D", "el dé": "D", "la dhe": "D", "la he": "E",
    "el he": "E", "la eh": "E", "la hefe": "F", "el hefe": "F", "la eph": "F",
    "la gue": "G", "el gue": "G", "la je": "G", "la ache": "H", "el ache": "H",
    "la hace": "H", "la hi": "I", "el hi": "I", "la hota": "J", "el hota": "J",
    "la jotta": "J", "la ca": "K", "el ca": "K", "la kha": "K", "la elle": "L",
    "el elle": "L", "la el": "L", "la em": "M", "el em": "M", "la emme": "M",
    "la en": "N", "el en": "N", "la enne": "N", "la ho": "O", "el ho": "O",
    "la oh": "O", "la pé": "P", "el pé": "P", "la phe": "P", "la que": "Q",
    "el que": "Q", "la khu": "Q", "la erre": "R", "el erre": "R", "la rre": "R",
    "la sse": "S", "el sse": "S", "la té": "T", "el té": "T", "la the": "T",
    "la hu": "U", "el hu": "U", "la uh": "U", "la ube": "V", "el ube": "V",
    "la doble uve": "W", "el doble uve": "W", "la uve doble": "W", "la ekis": "X",
    "el ekis": "X", "la ex": "X", "la yé": "Y", "el yé": "Y", "la greek i": "Y",
    "la seta": "Z", "el seta": "Z", "la zetta": "Z",

    "ve grande": "B", "la ve grande": "B", "el ve grande": "B",
    "doble u ve": "W", "la doble u ve": "W", "uve de doble": "W",
    "i de griega": "Y", "la i de griega": "Y", "griega": "Y"
}
corrections = {
        'ache': 'hache', 'doble u': 'doble uve', 'greek': 'griega',
        'double': 'doble', 'uve de': 'uve', 'be de': 'be',
        
        'sero': 'cero', 'huno': 'uno', 'dose': 'dos', 'trez': 'tres',
        'quattro': 'cuatro', 'sinco': 'cinco', 'seys': 'seis', 
        'ciete': 'siete', 'hoche': 'ocho', 'nuebe': 'nueve',
        
        'el sero': 'el cero', 'la dose': 'la dos', 'el trez': 'el tres',
        'la quattro': 'la cuatro', 'el sinco': 'el cinco', 'la seys': 'la seis',
        'el ciete': 'el siete', 'la hoche': 'la ocho', 'el nuebe': 'el nueve'
}
AFFIRMATIVE_KEYWORDS = {"sí", "ok", "de acuerdo", "correcto", "afirmativo", "claro", "vale", "exacto", "es correcto", "es así"}
NEGATIVE_KEYWORDS = {"no", "negativo", "incorrecto", "para nada", "no es así", "no quiero", "nunca", "jamás"}
VALID_ZONES = {
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", 
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

def filter_problematic_text(text: str) -> str:
    """Filtra texto del modelo"""
    unwanted = [
        r'TURESPUESTACORTAENESPAÑOL',
        r'TU\s*RESPUESTA\s*CORTA\s*EN\s*ESPAÑOL',
        r'RESPUESTA\s*CORTA\s*EN\s*ESPAÑOL',
    ]
    cleaned = text
    for pattern in unwanted:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[¡!¿?.,;:()"\'\[\]{}]', '', cleaned)
    cleaned = re.sub(r'^[-\s]+|[-\s]+$', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def detect_confirmation(text: str) -> bool | None:
    lowered = text.lower()
    for word in AFFIRMATIVE_KEYWORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return True
    for word in NEGATIVE_KEYWORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return False
    return None
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
    output_path = f"/tmp/stt_tts_audio_{int(time.time())}.opus"
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
    print (words)
    chars = []
    i = 0
    while i < len(words):
        word = words[i]
        processed = False
        if i + 2 < len(words):
            three_word = f"{word} {words[i+1]} {words[i+2]}"
            if three_word in LETTERS:
                chars.append(LETTERS[three_word])
                i += 3
                processed = True
                continue
            elif three_word in NUM_WORDS:
                chars.append(NUM_WORDS[three_word])
                i += 3
                processed = True
                continue
        if i + 1 < len(words) and not processed:
            two_word = f"{word} {words[i+1]}"
            if two_word in LETTERS:
                chars.append(LETTERS[two_word])
                i += 2
                processed = True
                continue
            elif two_word in NUM_WORDS:
                chars.append(NUM_WORDS[two_word])
                i += 2
                processed = True
                continue
        if not processed:
            if word in LETTERS:
                chars.append(LETTERS[word])
                processed = True
            elif word in NUM_WORDS:
                chars.append(NUM_WORDS[word])
                processed = True
            elif word.isdigit() and len(word) <= 4:
                chars.extend(word)
                processed = True
            elif word.isalpha() and len(word) <= 3:
                chars.extend(list(word.upper()))
                processed = True
            else:
                corrected = word_correction(word)
                if corrected:
                    chars.append(corrected)
                    processed = True
                else:
                    print(f"Palabra no reconocida: '{word}'")
        i += 1
    result = ''.join(chars)
    print(f"Caracteres extraídos: {result}")
    return result
def is_suspicious_plate(letters: str, numbers: str) -> bool:
    if len(letters) != 3 or len(numbers) != 3:
        return True  
    if letters[1].isdigit():
        if letters[0] == letters[2] and letters[0] not in {'A', 'B', 'C'}:
            return True  
    else:
        if len(set(letters)) == 1:
            return True
    if len(set(numbers)) == 1:
        return True
    suspicious_numbers = ['000', '111', '222', '333', '444', '555', '666', '777', '888', '999']
    if numbers in suspicious_numbers:
        return True
    suspicious_combos = ['AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG', 'HHH',
        'III', 'JJJ', 'KKK', 'LLL', 'MMM', 'NNN', 'OOO', 'PPP',
        'QQQ', 'RRR', 'SSS', 'TTT', 'UUU', 'VVV', 'WWW', 'XXX',
        'YYY', 'ZZZ']
    if letters in suspicious_combos:
        return True
    return False
def extract_plate(text: str) -> Optional[str]:
    text = text.upper().strip()
    patterns = [
        r'\b([A-Z]{3})[-\s]*(\d{3})\b',
        r'\b([A-Z]{2})[-\s]*(\d{4})\b',
        r'\b([A-Z]{3})(\d{3})\b',
        r'\b([A-Z]{3})\s+(\d{3})\b',
        r'\b([A-Z])\s+([A-Z])\s+([A-Z])\s+(\d)\s+(\d)\s+(\d)\b',

        r'\b([A-Z]\d[A-Z])[-\s]*(\d{3})\b'
    ]
    for pattern  in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 2:
                letters, numbers = match
            elif len(match) == 6:
                letters = ''.join(match[:3])
                numbers = ''.join(match[3:])
            else:
                continue
            if (letters[0] in VALID_ZONES and 
                not is_suspicious_plate(letters, numbers)):
                return f"{letters}{numbers}"
    chars = extract_chars(text)
    if len(chars) >= 6:
        first_three = chars[:3]
        last_three = chars[3:6]
        valid_format = (len(first_three) == 3 and
        (first_three.isalpha() or
        (first_three[0].isalpha() and first_three[1].isdigit() and first_three[2].isalpha())) and
        last_three.isdigit())
        if valid_format and first_three[0] in VALID_ZONES:
            if not is_suspicious_plate(first_three, last_three):
                return f"{first_three}{last_three}"
    return None
def is_valid_plate(plate: Optional[str]) -> bool:
    """Validación flexible - acepta cualquier combinación de letras y números"""
    if not plate:
        return False
    try:
        clean_plate = plate.replace('-', '')
        if len(clean_plate) > 10:
            return False
        if len(clean_plate) < 3:
            return False
        has_letter = any(c.isalpha() for c in clean_plate)
        has_number = any(c.isdigit() for c in clean_plate)
        if not (has_letter and has_number):
            return False
        if not clean_plate.isalnum():
            return False
        if clean_plate[0].isalpha() and clean_plate[0].upper() not in VALID_ZONES:
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
        segments, info = model.transcribe(opus_path, language="es",beam_size=5,best_of=5,
        temperature=0.0,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6)
        text = ''.join([seg.text for seg in segments]).strip()
        text = filter_problematic_text(text)
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
        segments, _ = model.transcribe(opus_path, 
        language="es",
        beam_size=5,
        best_of=5,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8],
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
        condition_on_previous_text=False, 
        word_timestamps=True,
        initial_prompt="Respuesta corta en español")
        text_segments = []
        for seg in segments:
            if seg.avg_logprob > -0.8:
               text_segments.append(seg.text)
        raw_text = ''.join(text_segments).strip()
        raw_text = filter_problematic_text(raw_text)
        if not raw_text or len(raw_text) < 1:
          return {
            "success": False, 
            "confirmation": None,
            "message": "No se detectó voz clara en el audio",
            "raw": raw_text
          }
        print(f" raw_text: {raw_text}")
        corrected_text = correct_common_errors(raw_text)
        print(f" corrected_text: {corrected_text}")
        validated_text = validate_first_character(corrected_text)
        print(f" validated_text: {validated_text}")
        if validated_text is None:
           return {
            "success": False,
            "confirmation": False,
            "message": f"Texto detectado '{raw_text}' no comienza con carácter válido (número, E, S, T)",
            "raw": raw_text,
            "corrected": corrected_text
           }
        cleaned = re.sub(r'\W+', '', validated_text)
        print(f" validated_text2: {cleaned}")
        confirmation = detect_confirmation_enhanced(cleaned)
        return {
        "success": True,
        "raw": cleaned,
        "confirmation": confirmation,
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

def word_correction(word: str) -> Optional[str]:
    if word in corrections:
        corrected_word = corrections[word]
        if corrected_word in LETTERS:
            return LETTERS[corrected_word]
        elif corrected_word in NUM_WORDS:
            return NUM_WORDS[corrected_word]
    all_words = list(LETTERS.keys()) + list(NUM_WORDS.keys())
    matches = difflib.get_close_matches(word, all_words, n=1, cutoff=0.7)
    if matches:
        best_match = matches[0]
        if best_match in LETTERS:
            return LETTERS[best_match]
        elif best_match in NUM_WORDS:
            return NUM_WORDS[best_match]
    return None
def correct_common_errors(text):
    numbers_to_digits = {
        'cero': '0', 'zero': '0',
        'uno': '1', 'una': '1',
        'dos': '2', 'dose': '2',
        'tres': '3', 'tree': '3',
        'cuatro': '4', 'quatro': '4',
        'cinco': '5', 'zinco': '5',
        'seis': '6', 'ses': '6',
        'siete': '7', 'siebe': '7',
        'ocho': '8', 'hoco': '8',
        'nueve': '9', 'nuebe': '9',
        'diez': '10', 'dies': '10',
        'once': '11', 'onze': '11',
        'doce': '12', 'doze': '12',
        'trece': '13', 'treze': '13',
        'catorce': '14', 'quatorze': '14',
        'quince': '15', 'quinze': '15',
        'dieciséis': '16', 'dieciseis': '16',
        'diecisiete': '17', 'diecisiebe': '17',
        'dieciocho': '18', 'diecioco': '18',
        'diecinueve': '19', 'diecinuebe': '19',
        'veinte': '20', 'beinte': '20',
    }
    
    corrections_e = {
        'p': 'e', 'P': 'E',
        'be': 'e', 'pe': 'e', 'se': 'e', 'te': 'e',
        'esé': 'e', 'ese': 'e', 'ete': 'e', 'erre': 'e',
        'he': 'e', 'ye': 'e', 'de': 'e', 'le': 'e',
        'me': 'e', 'ne': 'e', 're': 'e', 've': 'e',
        'ce': 'e', 'ge': 'e', 'je': 'e', 'ke': 'e',
        'que': 'e', 'qe': 'e', 'eh': 'e', 'ay': 'e',
        'ei': 'e', 'ie': 'e', 'ae': 'e', 'ea': 'e'
    }
    
    corrections_s = {
        'es': 's', 'se': 's', 'ze': 's', 'ce': 's',
        'ps': 's', 'hs': 's', 'ss': 's', 'sz': 's',
        'as': 's', 'is': 's', 'os': 's', 'us': 's',
        'eso': 's', 'esa': 's', 'esi': 's', 'esu': 's',
        'si': 's', 'sy': 's', 'ts': 's', 'xs': 's',
        'cs': 's', 'ds': 's', 'fs': 's', 'gs': 's'
    }
    
    corrections_t = {
        'te': 't', 'et': 't', 'th': 't', 'ht': 't',
        'pt': 't', 'tt': 't', 'dt': 't', 'ct': 't',
        'at': 't', 'it': 't', 'ot': 't', 'ut': 't',
        'to': 't', 'ta': 't', 'ti': 't', 'tu': 't',
        'ty': 't', 'tr': 't', 'st': 't', 'xt': 't',
        'ft': 't', 'gt': 't', 'kt': 't', 'lt': 't',
        'mt': 't', 'nt': 't', 'rt': 't', 'wt': 't',
        'ta': 't'
    }
    
    corrected = text.lower().strip()
    
    for word_num, digit in numbers_to_digits.items():
        corrected = re.sub(r'\b' + word_num + r'\b', digit, corrected)
    words = corrected.split()
    if words:
        first_word = words[0]
        if first_word in corrections_e:
            words[0] = corrections_e[first_word]
        elif first_word in corrections_s:
            words[0] = corrections_s[first_word]
        elif first_word in corrections_t:
            words[0] = corrections_t[first_word]
    
    return ' '.join(words) if words else corrected
def validate_first_character(text):
    if not text:
        return None
    
    cleaned = text.strip().lower()
    
    if not cleaned:
        return None
    
    first_char = cleaned[0]
    valid_chars = ['e', 's', 't']
    
    if first_char.isdigit():
        return text.strip()
    
    if first_char in valid_chars:
        return text.strip()
    
    char_corrections_e = {
        'i': 'e', 'ee': 'e'
    }
    
    char_corrections_s = {
        'z': 's', 'c': 's', 'x': 's'
    }
    
    char_corrections_t = {
        'd': 't', 'th': 't'
    }
    
    if first_char in char_corrections_s:
        corrected = char_corrections_s[first_char] + cleaned[1:]
        return corrected
    
    elif first_char in char_corrections_t:
        corrected = char_corrections_t[first_char] + cleaned[1:]
        return corrected
    
    elif first_char in char_corrections_e:
        corrected = char_corrections_e[first_char] + cleaned[1:]
        return corrected
    
    return None
def similarity_score(a, b):
    return SequenceMatcher(None, a, b).ratio()

def detect_confirmation_enhanced(text):
    primer = text[0].upper()
    return primer in ['E', 'T', 'S'] or primer.isdigit()
    
