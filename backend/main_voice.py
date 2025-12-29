# backend/main.py

import sys
import threading
import schedule
import time
import datetime

# Import configurations and handlers
import config
from utils.logging_config import log_message
from handlers.audio_handler import AudioHandler
from handlers.gemini_handler import GeminiHandler
from handlers.voicevox_handler import VoicevoxHandler
from handlers.database_handler import DatabaseHandler

class SayoApplication:
    def __init__(self):
        log_message("Initializing Sayo...")
        try:
            # Load handlers
            self.audio_handler = AudioHandler(
                whisper_model_name=config.WHISPER_MODEL_NAME,
                sample_rate=config.SAMPLE_RATE,
                channels=config.CHANNELS,
                chunk_size=config.CHUNK_SIZE,
                silence_threshold=config.SILENCE_THRESHOLD,
                silence_duration=config.SILENCE_DURATION,
                max_record_duration=config.MAX_RECORD_DURATION
            )
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
            self.sayo_activated = False

        except (ValueError, ConnectionError) as e:
            log_message(f"Failed to initialize Sayo: {e}")
            sys.exit(1)
        except Exception as e:
            log_message(f"An unexpected error occurred during initialization: {e}")
            sys.exit(1)

    def _announce_time(self):
        """Announces the current time."""
        now = datetime.datetime.now()
        time_text = f"{now.hour}時です"
        log_message(f"Announcing time: {time_text}")
        try:
            # Use a different filename for time to avoid conflicts
            time_audio_path = self.voicevox_handler.synthesize_speech(
                time_text, filename="time.wav"
            )
            self.audio_handler.play_audio(time_audio_path)
        except Exception as e:
            log_message(f"Error during time announcement: {e}")

    def _run_scheduler(self):
        """Runs the scheduler in a loop in a separate thread."""
        schedule.every().hour.at(":00").do(self._announce_time)
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)

    def _handle_spoken_exit(self, text):
        """Checks for spoken exit commands."""
        exit_words = ["exit", "終了", "しゅうりょう", "エグジット", "イグジット"]
        if any(word in text.lower() for word in exit_words):
            log_message("Spoken exit command recognized. Shutting down...")
            self.is_running = False
            return True
        return False

    def run(self):
        """Main application loop."""
        log_message("\nSayo is ready. 話しかけてください。")

        # Start the scheduler in a background thread
        scheduler_thread = threading.Thread(target=self._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()

        while self.is_running:
            recorded_path = self.audio_handler.listen_and_record()

            if recorded_path == "EXIT":
                log_message("Exit command typed. Shutting down...")
                self.is_running = False
                break
            
            if not recorded_path:
                print("######")
                continue

            log_message("\n--- [PROCESS START] ---")
            user_text = self.audio_handler.recognize_speech(recorded_path)
            log_message(f">>> [Whisper] Recognized: {user_text}")

            if not user_text.strip():
                log_message(">>> [LOG] Could not recognize speech.")
                log_message("--- [PROCESS END] ---")
                print("######")
                continue
            
            if self._handle_spoken_exit(user_text):
                break

            response_text = ""
            if self.sayo_activated:
                # If already active, process any speech
                log_message(f">>> [LOG] Processing (active): {user_text}")
                response_text = self.gemini_handler.think(user_text)
            else:
                # Check for hotword to activate
                hotword_detected = "さよ" in user_text.lower() or "さよち" in user_text.lower()
                log_message(f">>> [LOG] Hotword check: {hotword_detected}")
                if hotword_detected:
                    self.sayo_activated = True
                    # Use the full text including the hotword for the first response
                    response_text = self.gemini_handler.think(user_text)
                else:
                    # Not activated, prompt user to call Sayo
                    log_message(">>> [LOG] Hotword not detected. Prompting user.")
                    response_text = "小夜にご用ですか？"

            log_message(f">>> [Gemini] Responded: {response_text}")

            if response_text:
                # Log conversation if it was a meaningful interaction
                if self.sayo_activated:
                     self.db_handler.log_conversation(user_text, response_text)
                
                # Synthesize and play response
                synthesized_path = self.voicevox_handler.synthesize_speech(response_text)
                self.audio_handler.play_audio(synthesized_path)

            log_message("--- [PROCESS END] ---")
            print("######")

        log_message("Sayo is shutting down.")

def main():
    try:
        app = SayoApplication()
        app.run()
    except (KeyboardInterrupt, EOFError):
        log_message("\nInterrupted by user. Shutting down...")
    except Exception as e:
        log_message(f"A critical error occurred: {e}")
        sys.exit(1)
    finally:
        log_message("Sayo is offline.")

if __name__ == "__main__":
    main()
