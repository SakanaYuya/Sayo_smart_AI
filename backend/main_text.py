# backend/main_text.py

import sys
import threading
import time
import datetime
import os
import sounddevice as sd
import soundfile as sf

# Import configurations and handlers
import config
from utils.logging_config import log_message, print_separator
from handlers.gemini_handler import GeminiHandler
from handlers.voicevox_handler import VoicevoxHandler
from handlers.database_handler import DatabaseHandler

def play_audio(audio_path):
    """Plays an audio file using sounddevice."""
    if not audio_path or not os.path.exists(audio_path):
        log_message("再生する音声ファイルが見つかりません。")
        return
    log_message(f"Playing audio from {audio_path}...")
    try:
        data, samplerate = sf.read(audio_path)
        sd.play(data, samplerate)
        sd.wait()
        log_message("Audio playback finished.")
    except Exception as e:
        log_message(f"Error playing audio: {e}")

class SayoTextApplication:
    def __init__(self):
        log_message("Starting Sayo CLI Prototype (Text-Only Version)...")
        try:
            # Load handlers
            self.gemini_handler = GeminiHandler(
                api_key=config.GEMINI_API_KEY,
                model_name=config.GEMINI_MODEL_NAME,
                system_instruction=config.SYSTEM_INSTRUCTION
            )
            self.voicevox_handler = VoicevoxHandler(
                base_url=config.VOICEVOX_URL,
                speaker_id=config.SPEAKER_ID
            )
            self.db_handler = DatabaseHandler(db_path=config.DB_PATH)
            
            # Application state
            self.is_running = True

        except (ValueError, ConnectionError) as e:
            log_message(f"Failed to initialize Sayo Text Mode: {e}")
            sys.exit(1)
        except Exception as e:
            log_message(f"An unexpected error occurred during initialization: {e}")
            sys.exit(1)

    # Note: Text mode does not use scheduled announcements by default, 
    # but the logic is kept for consistency if needed later.
    # For this reproduction, we will not run a scheduler by default.
    # If scheduling is required, `self._run_scheduler()` should be called in `run()`. 

    def run(self):
        """Main application loop for text mode."""
        log_message("\nSayo is ready. メッセージを入力してください ('exit'で終了)。")

        while self.is_running:
            try:
                # ご主人からの入力を直接表示
                user_input = input("ご主人 > ").strip()
                
                if user_input.lower() == 'exit':
                    log_message("Exit command received. Shutting down...")
                    self.is_running = False
                    break

                if not user_input:
                    continue

                if config.IS_MAKER_MODE:
                    log_message("\n--- [PROCESS START] ---")
                
                gemini_response_text = self.gemini_handler.think(user_input)
                
                # 小夜の応答を直接表示
                print(f"小夜 > {gemini_response_text}")

                # Log the conversation to DB
                self.db_handler.log_conversation(user_input, gemini_response_text)

                if gemini_response_text:
                    log_message(">>> [LOG] VOICEVOX送信中...")
                    synthesized_audio_path = self.voicevox_handler.synthesize_speech(gemini_response_text, filename="output_text.wav")
                    if synthesized_audio_path:
                        log_message(">>> [LOG] 音声再生中...")
                        play_audio(synthesized_audio_path)
                
                if config.IS_MAKER_MODE:
                    log_message("--- [PROCESS END] ---")
                    print_separator()

            except (KeyboardInterrupt, EOFError):
                log_message("\nInterrupted by user. Shutting down...")
                self.is_running = False
            except Exception as e:
                log_message(f"An error occurred in main loop: {e}")
                self.is_running = False

        log_message("Sayo is offline.")

def main():
    try:
        app = SayoTextApplication()
        app.run()
    except Exception as e:
        log_message(f"A critical error occurred: {e}")
        sys.exit(1)
    finally:
        log_message("Sayo is offline.")

if __name__ == "__main__":
    main()