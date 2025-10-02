from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from transformers import pipeline
from fastapi.middleware.cors import CORSMiddleware
import speech_recognition as sr
import tempfile

app = FastAPI(title="MoodTune AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Emotion model
emotion_model = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True
)

# Text-based mood analysis
class MoodRequest(BaseModel):
    text: str

@app.post("/analyze-mood")
def analyze_mood(req: MoodRequest):
    result = emotion_model(req.text)[0]
    top_emotion = max(result, key=lambda x: x['score'])
    return {
        "input_text": req.text,
        "mood": top_emotion['label'],
        "confidence": round(top_emotion['score'], 3)
    }

# Audio-based mood analysis
@app.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    file_size = 0
    contents = b""
    
    # Read and validate file size
    while chunk := await file.read(8192):
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            return {"error": "File size too large. Maximum size is 10MB"}
        contents += chunk
    
    # Validate file type
    if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a')):
        return {"error": "Unsupported file format. Please upload WAV, MP3, or M4A file"}

    try:
        # Save audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Convert audio to text using speech_recognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source)
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
            except sr.UnknownValueError:
                return {"error": "Could not understand audio"}
            except sr.RequestError:
                return {"error": "Speech recognition service failed"}

        # Analyze emotion
        result = emotion_model(text)[0]
        top_emotion = max(result, key=lambda x: x['score'])

        return {
            "input_text": text,
            "mood": top_emotion['label'],
            "confidence": round(top_emotion['score'], 3)
        }
    
    finally:
        # Clean up temporary file
        import os
        try:
            os.unlink(tmp_path)
        except:
            pass
