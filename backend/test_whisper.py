import os
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import sys

# Ensure the script can find the whisper model
# This might be necessary if running outside the venv activation context
# For simplicity, we assume the venv is activated or python path is set correctly.

WHISPER_MODEL_NAME = "small"
TEST_AUDIO_FILE = "test_input.wav"
RECORD_DURATION = 5 # seconds

def record_audio(filename=TEST_AUDIO_FILE, duration=RECORD_DURATION, samplerate=16000):
    """Records audio from the microphone."""
    print(f"Recording for {duration} seconds...")
    try:
        sd.default.samplerate = samplerate
        sd.default.channels = 1
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        sf.write(filename, recording, samplerate)
        print(f"Audio recorded to {filename}")
        return filename
    except Exception as e:
        print(f"Error recording audio: {e}")
        print("Please ensure your microphone is connected and accessible.")
        print("On macOS, you might need to grant microphone access to your terminal application in System Settings > Privacy & Security > Microphone.")
        sys.exit(1)

def recognize_speech(whisper_model, audio_path):
    """Recognizes speech from an audio file using Whisper."""
    print(f"Recognizing speech from {audio_path}...")
    try:
        result = whisper_model.transcribe(audio_path, language="ja", task="transcribe")
        text = result["text"]
        print(f"Recognized: {text}")
        return text
    except Exception as e:
        print(f"Error recognizing speech: {e}")
        sys.exit(1)

def main():
    print("Starting Whisper test...")
    
    # Load Whisper model
    try:
        print(f"Loading Whisper model: {WHISPER_MODEL_NAME}...")
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
        print("Whisper model loaded.")
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        print("Please ensure the Whisper model files are downloaded and accessible.")
        print("You might need to run 'whisper --model small --task transcribe --language en' once to download the model.")
        sys.exit(1)

    # Record audio
    recorded_audio_path = record_audio()

    # Recognize speech
    recognize_speech(whisper_model, recorded_audio_path)

    print("\nWhisper test finished.")

if __name__ == "__main__":
    main()
