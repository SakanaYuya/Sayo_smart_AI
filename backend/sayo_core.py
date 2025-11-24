import os
import time
import threading
import queue
import json
import datetime
import requests
import numpy as np
import google.generativeai as genai
import schedule
import sounddevice as sd
import soundfile as sf
import whisper
import warnings
import sys
import sqlite3
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VOICEVOX_URL = "http://127.0.0.1:50021"
SPEAKER_ID = 46  # 小夜/Sayo
SAMPLE_RATE = 16000 # Whisperは16k推奨
SILENCE_THRESHOLD = 0.02 # マイクの無音判定閾値 (RMS値)
SILENCE_DURATION = 1.0 # 無音と判断する継続時間（秒）
CHUNK_SIZE = 1024 # sounddeviceのバッファサイズ
CHANNELS = 1 # モノラル録音
MAX_RECORD_DURATION = 30 # 最大録音時間（秒）
DB_PATH = "sayo_log.db"
WHISPER_MODEL_NAME = "small"
GEMINI_MODEL_NAME = "gemini-flash-latest"

# --- Database Functions ---
def init_db():
    """Initializes the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_text TEXT,
        sayo_text TEXT
    )
    """)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def log_conversation(user_text, sayo_text):
    """Logs the conversation to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversation_logs (user_text, sayo_text) VALUES (?, ?)",
        (user_text, sayo_text)
    )
    conn.commit()
    conn.close()
    print("Conversation logged.")

# --- Time Signal Function ---
def announce_time():
    """Announces the current time."""
    now = datetime.datetime.now()
    time_text = f"{now.hour}時です"
    print(f"Announcing time: {time_text}")
    try:
        # Use a different file for time announcement to avoid conflicts
        time_audio_path = synthesize_speech(time_text, speaker_id=SPEAKER_ID, filename="time.wav")
        play_audio(time_audio_path)
    except Exception as e:
        print(f"Error during time announcement: {e}")

def run_scheduler():
    """Runs the scheduler in a loop."""
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- Audio Recording Functions (New) ---
audio_queue = queue.Queue()
recording_event = threading.Event()
speaking_event = threading.Event()

def audio_callback(indata, frames, time_info, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(indata.copy())
    if not speaking_event.is_set():
        # Check for speech start
        rms = np.sqrt(np.mean(indata**2))
        if rms > SILENCE_THRESHOLD:
            speaking_event.set()
            print("話し始めました...")
    
def listen_and_record_speech(output_filename="recorded_speech.wav"):
    """Listens for speech, records it, and stops when silence is detected."""
    print("話しかけてください...")
    frames = []
    speaking_event.clear()
    recording_event.clear()
    silence_start_time = None
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32', callback=audio_callback, blocksize=CHUNK_SIZE):
        start_time = time.time()
        while True:
            if time.time() - start_time > MAX_RECORD_DURATION:
                print("最大録音時間に達しました。")
                break

            try:
                data = audio_queue.get(timeout=1.0) # 1秒待機
                frames.append(data)
                
                # Check for silence if speaking has started
                if speaking_event.is_set():
                    rms = np.sqrt(np.mean(data**2))
                    if rms < SILENCE_THRESHOLD:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time > SILENCE_DURATION:
                            print("無音を検出しました。録音を終了します。")
                            break
                    else:
                        silence_start_time = None # Reset silence timer if speech detected
            except queue.Empty:
                if speaking_event.is_set() and silence_start_time is not None and (time.time() - silence_start_time > SILENCE_DURATION):
                    print("無音を検出しました。録音を終了します。")
                    break
                elif not speaking_event.is_set() and (time.time() - start_time > 5): # 5秒間話さない場合はタイムアウト
                    print("5秒間音声が検出されませんでした。")
                    break
                pass # キューが空でもループは継続

    if frames:
        recorded_audio = np.concatenate(frames)
        sf.write(output_filename, recorded_audio, SAMPLE_RATE)
        print(f"音声を {output_filename} に保存しました。")
        return output_filename
    else:
        print("音声が録音されませんでした。")
        return None

# --- Core Sayo Functions ---
def initialize_sayo():
    """Initializes Sayo's components."""
    # Initialize Database
    init_db()

    # Initialize Whisper model
    print(f"Loading Whisper model: {WHISPER_MODEL_NAME}...")
    whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
    print("Whisper model loaded.")

    # Configure Gemini API
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print("Gemini API configured.")

    # Check VOICEVOX availability
    try:
        response = requests.get(f"{VOICEVOX_URL}/version")
        response.raise_for_status()
        print(f"VOICEVOX is running (version: {response.json()}).")
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"VOICEVOX is not running on {VOICEVOX_URL}. Please start the application.")
    except Exception as e:
        print(f"Error checking VOICEVOX: {e}")
        raise

    return whisper_model, gemini_model

def recognize_speech(whisper_model, audio_path):
    """Recognizes speech from an audio file using Whisper."""
    if not audio_path:
        return ""
    print(f"Recognizing speech from {audio_path}...")
    # warnings.filterwarnings("ignore", category=UserWarning, module='whisper.transcribe') # FP16警告を無視
    result = whisper_model.transcribe(audio_path, language="ja", task="transcribe")
    text = result["text"]
    print(f"Recognized: {text}")
    return text

def think_with_gemini(gemini_model, prompt):
    """Gets a response from Gemini API."""
    if not prompt.strip():
        return ""
    print(f"Sending to Gemini: {prompt}")
    response = gemini_model.generate_content(prompt)
    text = response.text
    print(f"Gemini responded: {text}")
    return text

def synthesize_speech(text, speaker_id=SPEAKER_ID, filename="output.wav"):
    """Synthesizes speech using VOICEVOX."""
    if not text.strip():
        print("合成するテキストがありません。")
        return None
    print(f"Synthesizing speech for: {text}")
    params = {
        "text": text,
        "speaker": speaker_id,
    }
    headers = {"Content-Type": "application/json"}

    # Get audio query
    response = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        headers=headers,
        params={"text": text, "speaker": speaker_id}
    )
    response.raise_for_status()
    audio_query = response.json()

    # Synthesize audio
    response = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        headers=headers,
        params={"speaker": speaker_id},
        data=json.dumps(audio_query)
    )
    response.raise_for_status()
    
    # Save audio to a file
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"Speech synthesized and saved to {filename}")
    return filename

def play_audio(audio_path):
    """Plays an audio file."""
    if not audio_path or not os.path.exists(audio_path):
        print("再生する音声ファイルが見つかりません。")
        return
    print(f"Playing audio from {audio_path}...")
    data, samplerate = sf.read(audio_path)
    sd.play(data, samplerate)
    sd.wait()
    print("Audio playback finished.")

def main():
    print("Starting Sayo CLI Prototype...")
    try:
        whisper_model, gemini_model = initialize_sayo()

        # Setup and start scheduler for time announcement
        schedule.every().hour.at(":00").do(announce_time)
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()

        print("\nSayo is ready. 話しかけてください (または 'exit' と入力して終了)。")
        while True:
            # ユーザーからの入力を待つ代わりに、音声入力を監視
            recorded_audio_path = listen_and_record_speech()

            if recorded_audio_path is None:
                print("音声入力がありませんでした。")
                continue

            user_speech_text = recognize_speech(whisper_model, recorded_audio_path)

            if not user_speech_text.strip():
                print("音声を認識できませんでした。もう一度お話しください。")
                continue

            gemini_response_text = think_with_gemini(gemini_model, user_speech_text)
            
            # Log the conversation
            log_conversation(user_speech_text, gemini_response_text)

            synthesized_audio_path = synthesize_speech(gemini_response_text)
            play_audio(synthesized_audio_path)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
