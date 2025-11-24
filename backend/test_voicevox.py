import requests
import json
import sounddevice as sd
import soundfile as sf
import os
import sys

# --- Configuration ---
VOICEVOX_URL = "http://127.0.0.1:50021"
SPEAKER_ID = 46  # 小夜/Sayo
OUTPUT_FILENAME = "voicevox_test_output.wav"

def synthesize_and_play_voicevox(text, speaker_id=SPEAKER_ID, filename=OUTPUT_FILENAME):
    """VOICEVOXで音声を合成し、再生する。"""
    print(f"VOICEVOXでテキストを合成中: 「{text}」 (スピーカーID: {speaker_id})...")
    
    try:
        # 1. 音声クエリの生成
        response = requests.post(
            f"{VOICEVOX_URL}/audio_query",
            params={"text": text, "speaker": speaker_id}
        )
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        audio_query = response.json()

        # 2. 音声合成
        response = requests.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": speaker_id},
            data=json.dumps(audio_query),
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        
        # 3. 音声ファイルを保存
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"音声を {filename} に保存しました。")

        # 4. 音声ファイルを再生
        data, samplerate = sf.read(filename)
        sd.play(data, samplerate)
        sd.wait()
        print("音声再生が完了しました。")
        return True

    except requests.exceptions.ConnectionError:
        print(f"エラー: VOICEVOXが {VOICEVOX_URL} で起動していません。アプリケーションを起動してください。")
        return False
    except requests.exceptions.RequestException as e:
        print(f"VOICEVOX APIとの通信中にエラーが発生しました: {e}")
        return False
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return False

def main():
    print("--- VOICEVOX単体テストを開始します ---")
    
    test_text = "こんにちは、小夜です。VOICEVOXのテストをしています。"
    success = synthesize_and_play_voicevox(test_text)

    if success:
        print("VOICEVOX単体テスト成功！")
    else:
        print("VOICEVOX単体テスト失敗。")

    print("--- テストを終了します ---")

if __name__ == "__main__":
    main()
