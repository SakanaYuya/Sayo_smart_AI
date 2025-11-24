import os
import whisper
import google.generativeai as genai
import requests
import json
import sounddevice as sd
import soundfile as sf
import numpy as np

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VOICEVOX_PORT = 50021
VOICEVOX_BASE_URL = f"http://localhost:{VOICEVOX_PORT}"
WHISPER_MODEL_NAME = "small"
AUDIO_FILE_PATH = "input.wav" # Temporary file for recording

def initialize_sayo():
    """Initializes Sayo's components."""
    # Initialize Whisper model
    print(f"Loading Whisper model: {WHISPER_MODEL_NAME}...")
    whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
    print("Whisper model loaded.")

    # Configure Gemini API
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini API configured.")

    # Check VOICEVOX availability
    try:
        response = requests.get(f"{VOICEVOX_BASE_URL}/version")
        response.raise_for_status()
        print(f"VOICEVOX is running (version: {response.json()}).")
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"VOICEVOX is not running on port {VOICEVOX_PORT}. Please start the application.")
    except Exception as e:
        print(f"Error checking VOICEVOX: {e}")
        raise

    return whisper_model, gemini_model

def record_audio(filename=AUDIO_FILE_PATH, duration=5, samplerate=16000):
    """Records audio from the microphone."""
    print(f"Recording for {duration} seconds...")
    sd.default.samplerate = samplerate
    sd.default.channels = 1
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    sf.write(filename, recording, samplerate)
    print(f"Audio recorded to {filename}")
    return filename

def recognize_speech(whisper_model, audio_path):
    """Recognizes speech from an audio file using Whisper."""
    print(f"Recognizing speech from {audio_path}...")
    result = whisper_model.transcribe(audio_path)
    text = result["text"]
    print(f"Recognized: {text}")
    return text

def think_with_gemini(gemini_model, prompt):
    """Gets a response from Gemini API."""
    print(f"Sending to Gemini: {prompt}")
    response = gemini_model.generate_content(prompt)
    text = response.text
    print(f"Gemini responded: {text}")
    return text

def synthesize_speech(text, speaker_id=0):
    """Synthesizes speech using VOICEVOX."""
    print(f"Synthesizing speech for: {text}")
    params = {
        "text": text,
        "speaker": speaker_id,
    }
    headers = {"Content-Type": "application/json"}

    # Get audio query
    response = requests.post(
        f"{VOICEVOX_BASE_URL}/audio_query",
        headers=headers,
        params={"text": text, "speaker": speaker_id}
    )
    response.raise_for_status()
    audio_query = response.json()

    # Synthesize audio
    response = requests.post(
        f"{VOICEVOX_BASE_URL}/synthesis",
        headers=headers,
        params={"speaker": speaker_id},
        data=json.dumps(audio_query)
    )
    response.raise_for_status()
    
    # Save audio to a file (e.g., output.wav)
    output_audio_path = "output.wav"
    with open(output_audio_path, "wb") as f:
        f.write(response.content)
    print(f"Speech synthesized and saved to {output_audio_path}")
    return output_audio_path

def play_audio(audio_path):
    """Plays an audio file."""
    print(f"Playing audio from {audio_path}...")
    data, samplerate = sf.read(audio_path)
    sd.play(data, samplerate)
    sd.wait()
    print("Audio playback finished.")

def main():
    print("Starting Sayo CLI Prototype...")
    try:
        whisper_model, gemini_model = initialize_sayo()

        print("
Sayo is ready. Press Enter to speak, type 'exit' to quit.")
        while True:
            input("Press Enter to speak...")
            
            recorded_audio_path = record_audio()
            user_speech_text = recognize_speech(whisper_model, recorded_audio_path)

            if user_speech_text.lower() == 'exit':
                break

            gemini_response_text = think_with_gemini(gemini_model, user_speech_text)
            synthesized_audio_path = synthesize_speech(gemini_response_text)
            play_audio(synthesized_audio_path)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
