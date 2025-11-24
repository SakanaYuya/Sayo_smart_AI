import os
import sys
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. 設定 ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHISPER_MODEL_NAME = "small"
GEMINI_MODEL_NAME = "gemini-flash-latest"
TEST_AUDIO_FILE = "test_input.wav"
RECORD_DURATION = 5 # seconds

# --- 2. 各機能の関数 ---

def record_audio(filename=TEST_AUDIO_FILE, duration=RECORD_DURATION, samplerate=16000):
    """マイクから音声を録音する"""
    print(f"{duration}秒間、録音を開始します...")
    try:
        sd.default.samplerate = samplerate
        sd.default.channels = 1
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        sf.write(filename, recording, samplerate)
        print(f"音声を {filename} に保存しました。")
        return filename
    except Exception as e:
        print(f"録音中にエラーが発生しました: {e}")
        sys.exit(1)

def recognize_speech(whisper_model, audio_path):
    """Whisperで音声をテキストに変換する"""
    print(f"{audio_path} から文字起こしをしています...")
    try:
        result = whisper_model.transcribe(audio_path, language="ja", task="transcribe")
        text = result["text"]
        print(f"Whisper認識結果: 「{text}」")
        return text
    except Exception as e:
        print(f"文字起こし中にエラーが発生しました: {e}")
        sys.exit(1)

def think_with_gemini(gemini_model, prompt):
    """Gemini APIに応答を生成させる"""
    if not prompt.strip():
        print("Whisperがテキストを認識できなかったため、Geminiへの送信をスキップします。")
        return None
        
    print(f"Geminiにプロンプトを送信中: 「{prompt}」")
    try:
        response = gemini_model.generate_content(prompt)
        text = response.text
        print(f"Geminiの応答: 「{text}」")
        return text
    except Exception as e:
        print(f"Gemini APIとの通信中にエラーが発生しました: {e}")
        sys.exit(1)

# --- 3. メインの実行フロー ---

def main():
    """全体の処理を実行する"""
    print("--- Whisper -> Gemini 連携テストを開始します ---")

    # モデルの初期化
    try:
        print(f"Whisperモデル ({WHISPER_MODEL_NAME}) をロード中...")
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
        print("Whisperモデルのロード完了。")

        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEYが.envファイルに設定されていません。")
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        print(f"Geminiモデル ({GEMINI_MODEL_NAME}) の準備完了。")

    except Exception as e:
        print(f"モデルの初期化中にエラー: {e}")
        sys.exit(1)

    # 実行
    audio_path = record_audio()
    recognized_text = recognize_speech(whisper_model, audio_path)
    think_with_gemini(gemini_model, recognized_text)

    print("\n--- テストを終了します ---")

if __name__ == "__main__":
    main()
