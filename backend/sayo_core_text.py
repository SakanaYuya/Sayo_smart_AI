import os
import time
import threading
import queue
import json
import datetime
import requests
import google.generativeai as genai
import sys
import sqlite3
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VOICEVOX_URL = "http://127.0.0.1:50021"
SPEAKER_ID = 46  # 小夜/Sayo
DB_PATH = "sayo_log.db"
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

# --- Core Sayo Functions ---
def initialize_sayo():
    """Initializes Sayo's components."""
    # Initialize Database
    init_db()

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

    return gemini_model

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
    """Synthesizes speech using VOICEVOX and saves it."""
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

def main():
    log_message("Starting Sayo CLI Prototype (Text-Only Version)...")
    try:
        gemini_model = initialize_sayo()

        log_message("\nSayo is ready. メッセージを入力してください ('exit'で終了)。")
        
        while True:
            try:
                user_input = input("ご主人 > ")
            except (KeyboardInterrupt, EOFError):
                log_message("\nInterrupted by user. Shutting down...")
                break

            if user_input.lower() == 'exit':
                log_message("Exit command received. Shutting down...")
                break

            if not user_input.strip():
                continue

            log_message("\n--- [PROCESS START] ---")
            
            gemini_response_text = think_with_gemini(gemini_model, user_input)
            
            print(f"小夜 > {gemini_response_text}") # Display Sayo's response text

            # Log the conversation to DB
            log_conversation(user_input, gemini_response_text)

            if gemini_response_text:
                log_message(">>> [LOG] VOICEVOX送信中...")
                synthesized_audio_path = synthesize_speech(gemini_response_text)
                if synthesized_audio_path:
                    log_message(">>> [LOG] 音声再生中...")
                    play_audio(synthesized_audio_path)
            
            log_message("--- [PROCESS END] ---")
            print("######") # 区切り線

    except Exception as e:
        log_message(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        log_message("Sayo is offline.")

if __name__ == "__main__":
    main()
