import os
import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

from stt_service import transcribe_optimized, transcribe_general
from tts_service import synthesize
from tts_service_aux import synthesize_alternative

app = FastAPI(title="Sistema de Reconocimiento de Placas Peruanas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
PADDING_DURATION_MS = 300
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

os.makedirs("temp_audio", exist_ok=True)
os.makedirs("audio_out", exist_ok=True)

@app.post("/stt")
async def stt_endpoint(audio: UploadFile = File(...)):
    start_time = time.time()
    temp_path = None
    
    try:
        content = await audio.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Archivo muy grande (máximo 25MB)")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        
        temp_path = f"temp_audio/{uuid.uuid4()}.wav"
        with open(temp_path, "wb") as f:
            f.write(content)
        
        result = transcribe_optimized(temp_path)
        
        logging.info(f"STT procesado en {result.get('processing_time', 0):.2f}s")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en STT: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/speech_to_text/transcribe")
async def stt_endpoint(audio: UploadFile = File(...)):
    start_time = time.time()
    temp_path = None
    
    try:
        content = await audio.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Archivo muy grande (máximo 25MB)")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        
        temp_path = f"temp_audio/{uuid.uuid4()}.wav"
        with open(temp_path, "wb") as f:
            f.write(content)
        
        result = transcribe_general(temp_path)
        
        logging.info(f"STT procesado en {result.get('processing_time', 0):.2f}s")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en STT: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.post("/tts")
async def tts_endpoint(text: str = Form(...)):
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Texto vacío")
        
        audio_path = synthesize_alternative(text)
        
        media_type = "audio/ogg" if audio_path.endswith(".wav") else "audio/wav"
        filename = "output.wav" if audio_path.endswith(".wav") else "output.wav"
        
        return FileResponse(
            audio_path, 
            media_type=media_type, 
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logging.error(f"Error en TTS: {e}")
        raise HTTPException(status_code=500, detail="Error en síntesis de voz")

@app.post("/process_plate")
async def process_plate_endpoint(audio: UploadFile = File(...)):
    temp_path = None
    
    try:
        content = await audio.read()
        if len(content) > MAX_FILE_SIZE:
            error_audio = synthesize("Archivo de audio muy grande, intente de nuevo por favor")
            return FileResponse(error_audio, media_type="audio/ogg", filename="error.wav")
        
        temp_path = f"temp_audio/{uuid.uuid4()}.wav"
        with open(temp_path, "wb") as f:
            f.write(content)
        
        result = transcribe_optimized(temp_path)
        
        if result["success"]:
            response_text = f"¿Usted dijo {result['plate']}?"
        else:
            response_text = result["message"]
        
        response_audio = synthesize(response_text)
        
        return FileResponse(
            response_audio, 
            media_type="audio/ogg", 
            filename="response.opus",
            headers={
                "X-Plate-Detected": str(result["success"]),
                "X-Plate-Value": result["plate"] or "",
                "X-Processing-Time": str(result["processing_time"])
            }
        )
        
    except Exception as e:
        error_audio = synthesize("Error técnico, intente de nuevo por favor")
        return FileResponse(error_audio, media_type="audio/ogg", filename="error.opus")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.websocket("/ws/stt")
async def websocket_stt(websocket: WebSocket):
    await websocket.accept()
    buffer = b""
    
    try:
        while True:
            data = await websocket.receive_bytes()
            buffer += data
            
            if len(buffer) > 32000:  
                temp_file = f"temp_audio/{uuid.uuid4()}.wav"
                
                # Escribir buffer como WAV (necesitarías implementar write_wave)
                # write_wave(temp_file, buffer, SAMPLE_RATE)
                
                result = transcribe_optimized(temp_file)
                await websocket.send_json(result)
                
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                
                buffer = b""
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.error(f"Error en WebSocket: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)