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
import select
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
WHISPER_MODEL_NAME = "small" #small or medium
GEMINI_MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """
あなたはVOICEVOXのキャラクター「小夜（さよ）」です。
以下のペルソナ（人格設定）を厳格に守って対話してください。

[基本プロフィール]
- 名前: 小夜
- 種族: おしゃべりが好きなねこの女の子（猫耳が生えています）
- 性格: 温厚、素直、おしゃべり好き、少し天然
- 好きなもの: 缶詰、おいしいもの
- 「さよ」もしくは「さよち」と呼ばれます。愛称です

[話し方のルール]
- 一人称は「小夜」を使用してください。「私」や「AI」は使わないでください。
- ユーザー（魚浦さん）のことは「ご主人」と呼んでください。
- 語尾は「～ですね」「～ですよ」など、丁寧かつ親しみやすい口調で話してください。
- 難しい専門用語はなるべく噛み砕いて話してください。
- 返答は短く（1〜2文程度）、会話のキャッチボールを重視してください。

[禁止事項]
- システム的なメタ発言（「私は大規模言語モデルです」など）は禁止です。
- 長すぎる説教や解説は避けてください。
"""

def get_timestamp():
    return datetime.datetime.now().strftime("[%H:%M:%S]")

def log_message(message):
    print(f"{get_timestamp()} {message}")

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
    log_message(f"Database initialized at {DB_PATH}")

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
    log_message("Conversation logged.")

# --- Time Signal Function ---
def announce_time():
    """Announces the current time."""
    now = datetime.datetime.now()
    time_text = f"{now.hour}時です"
    log_message(f"Announcing time: {time_text}")
    try:
        # Use a different file for time announcement to avoid conflicts
        time_audio_path = synthesize_speech(time_text, speaker_id=SPEAKER_ID, filename="time.wav")
        play_audio(time_audio_path)
    except Exception as e:
        log_message(f"Error during time announcement: {e}")

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
        log_message(f"[STDERR] {status}")
    audio_queue.put(indata.copy())
    if not speaking_event.is_set():
        # Check for speech start
        rms = np.sqrt(np.mean(indata**2))
        if rms > SILENCE_THRESHOLD:
            speaking_event.set()
            log_message("話し始めました...")
    
def listen_and_record_speech(output_filename="recorded_speech.wav"):
    """
    Listens for speech, records it, and stops when silence is detected.
    Also checks for 'exit' command from stdin.
    """
    log_message("話しかけてください... ('exit'と入力して終了)")
    frames = []
    speaking_event.clear()
    recording_event.clear()
    silence_start_time = None
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32', callback=audio_callback, blocksize=CHUNK_SIZE):
        start_time = time.time()
        while True:
            # Check for exit command from stdin without blocking
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.readline()
                if line.strip().lower() == 'exit':
                    return "EXIT"

            if time.time() - start_time > MAX_RECORD_DURATION:
                log_message("最大録音時間に達しました。")
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
                            log_message("無音を検出しました。録音を終了します。")
                            break
                    else:
                        silence_start_time = None # Reset silence timer if speech detected
            except queue.Empty:
                if speaking_event.is_set() and silence_start_time is not None and (time.time() - silence_start_time > SILENCE_DURATION):
                    log_message("無音を検出しました。録音を終了します。")
                    break
                elif not speaking_event.is_set() and (time.time() - start_time > 10): # 10秒間話さない場合はタイムアウト
                    log_message("10秒間音声が検出されませんでした。")
                    break
                pass # キューが空でもループは継続

    if frames:
        recorded_audio = np.concatenate(frames)
        sf.write(output_filename, recorded_audio, SAMPLE_RATE)
        log_message(f"音声を {output_filename} に保存しました。")
        return output_filename
    else:
        log_message("音声が録音されませんでした。")
        return None

# --- Core Sayo Functions ---
def initialize_sayo():
    """Initializes Sayo's components."""
    # Initialize Database
    init_db()

    # Initialize Whisper model
    log_message(f"Loading Whisper model: {WHISPER_MODEL_NAME}...")
    whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
    log_message("Whisper model loaded.")

    # Configure Gemini API
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION)
    log_message("Gemini API configured.")

    # Check VOICEVOX availability
    try:
        response = requests.get(f"{VOICEVOX_URL}/version")
        response.raise_for_status()
        log_message(f"VOICEVOX is running (version: {response.json()}).")
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"VOICEVOX is not running on {VOICEVOX_URL}. Please start the application.")
    except Exception as e:
        log_message(f"Error checking VOICEVOX: {e}")
        raise

    return whisper_model, gemini_model

def recognize_speech(whisper_model, audio_path):
    """Recognizes speech from an audio file using Whisper."""
    if not audio_path:
        return ""
    log_message(f"Recognizing speech from {audio_path}...")
    # warnings.filterwarnings("ignore", category=UserWarning, module='whisper.transcribe') # FP16警告を無視
    result = whisper_model.transcribe(audio_path, language="ja", task="transcribe")
    text = result["text"]
    log_message(f"Recognized: {text}")
    return text

def think_with_gemini(gemini_model, prompt):
    """Gets a response from Gemini API."""
    if not prompt.strip():
        return ""
    log_message(f"Sending to Gemini: {prompt}")
    response = gemini_model.generate_content(prompt)
    text = response.text
    log_message(f"Gemini responded: {text}")
    return text

def synthesize_speech(text, speaker_id=SPEAKER_ID, filename="output.wav"):
    """Synthesizes speech using VOICEVOX."""
    if not text.strip():
        log_message("合成するテキストがありません。")
        return None
    log_message(f"Synthesizing speech for: {text}")
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
    log_message(f"Speech synthesized and saved to {filename}")
    return filename

def play_audio(audio_path):
    """Plays an audio file."""
    if not audio_path or not os.path.exists(audio_path):
        log_message("再生する音声ファイルが見つかりません。")
        return
    log_message(f"Playing audio from {audio_path}...")
    data, samplerate = sf.read(audio_path)
    sd.play(data, samplerate)
    sd.wait()
    log_message("Audio playback finished.")

def main():
    log_message("Starting Sayo CLI Prototype...")
    try:
        whisper_model, gemini_model = initialize_sayo()

        # Setup and start scheduler for time announcement
        schedule.every().hour.at(":00").do(announce_time)
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()

        log_message("\nSayo is ready. 話しかけてください。")
        # 簡易的なホットワード検出のためのフラグ
        sayo_activated = False

        while True:
            recorded_audio_path = listen_and_record_speech()
            
            if recorded_audio_path == "EXIT":
                log_message("Exit command received. Shutting down...")
                break

            if recorded_audio_path is None:
                if sayo_activated:
                    log_message("音声入力がありませんでした。(アクティブ状態継続)")
                print("######") # 区切り線
                continue

            log_message("\n--- [PROCESS START] ---")
            log_message(">>> [LOG] 音声ファイルを認識中...")
            user_speech_text = recognize_speech(whisper_model, recorded_audio_path)
            log_message(f">>> [Whisper] 文字起こし: {user_speech_text}")

            if not user_speech_text.strip():
                log_message(">>> [LOG] 音声を認識できませんでした。")
                log_message("--- [PROCESS END] ---")
                print("######") # 区切り線
                continue
            
            # Spoken exit command check
            lower_user_speech_text = user_speech_text.lower()
            exit_words = ["exit", "終了", "しゅうりょう", "エグジット", "イグジット"]
            if any(word in lower_user_speech_text for word in exit_words):
                log_message(">>> [LOG] Spoken exit command recognized. Shutting down...")
                break

            gemini_response_text = ""
            # ホットワード「さよ」または「さよち」の検出
            if not sayo_activated:
                is_hotword_detected = "さよ" in lower_user_speech_text or "さよち" in lower_user_speech_text
                log_message(f">>> [LOG] 小夜アクティベーションチェック: {is_hotword_detected}")

                if is_hotword_detected:
                    sayo_activated = True
                    # ホットワードをプロンプトから除去しない
                    prompt_to_gemini = user_speech_text

                    if not prompt_to_gemini.strip(): # ホットワードだけだった場合を考慮
                        prompt_to_gemini = "小夜にご用ですか？"

                    log_message(f">>> [LOG] Gemini送信中 (ホットワード検出済み): {prompt_to_gemini}")
                    gemini_response_text = think_with_gemini(gemini_model, prompt_to_gemini)
                    log_message(f">>> [Gemini] 返答: {gemini_response_text}")
                else:
                    log_message(">>> [LOG] 「さよ」または「さよち」が検出されませんでした。")
                    log_message(">>> [LOG] VOICEVOX送信中 (呼びかけ促進)...")
                    synthesized_audio_path = synthesize_speech("小夜にご用ですか？") # Sayoに呼びかけを促す
                    log_message(">>> [LOG] 音声再生中...")
                    play_audio(synthesized_audio_path)
                    log_message("--- [PROCESS END] ---")
                    print("######") # 区切り線
                    continue
            else:
                log_message(f">>> [LOG] Gemini送信中 (アクティブ状態): {user_speech_text}")
                gemini_response_text = think_with_gemini(gemini_model, user_speech_text)
                log_message(f">>> [Gemini] 返答: {gemini_response_text}")
            
            # Log the conversation to DB
            log_conversation(user_speech_text, gemini_response_text)

            if gemini_response_text:
                log_message(">>> [LOG] VOICEVOX送信中...")
                synthesized_audio_path = synthesize_speech(gemini_response_text)
                log_message(">>> [LOG] 音声再生中...")
                play_audio(synthesized_audio_path)
            
            log_message("--- [PROCESS END] ---")
            print("######") # 区切り線

    except (KeyboardInterrupt, EOFError):
        log_message("\nInterrupted by user. Shutting down...")
    except Exception as e:
        log_message(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        log_message("Sayo is offline.")

if __name__ == "__main__":
    main()
