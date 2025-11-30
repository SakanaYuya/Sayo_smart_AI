# backend/main_text.py

import sys
import threading
import schedule
import time
import datetime

# Import configurations and handlers
import config
from utils.logging_config import log_message
from handlers.gemini_handler import GeminiHandler
from handlers.voicevox_handler import VoicevoxHandler
from handlers.database_handler import DatabaseHandler

class SayoTextApplication:
    def __init__(self):
        log_message("Initializing Sayo Text Mode...")
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

    def _announce_time(self):
        """Announces the current time."""
        now = datetime.datetime.now()
        time_text = f"{now.hour}時です"
        log_message(f"Announcing time: {time_text}")
        try:
            time_audio_path = self.voicevox_handler.synthesize_speech(
                time_text, filename="time_text_mode.wav"
            )
            # In text mode, we'll just log that audio was synthesized, not play automatically
            # If automatic playback is desired, an audio play function would be needed here.
            log_message("Time announcement audio synthesized (not auto-played in text mode).")
        except Exception as e:
            log_message(f"Error during time announcement: {e}")

    def _run_scheduler(self):
        """Runs the scheduler in a loop in a separate thread."""
        schedule.every().hour.at(":00").do(self._announce_time)
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)

    def run(self):
        """Main application loop for text mode."""
        log_message("\nSayo Text Mode is ready. 何か話しかけてください (終了するには 'exit' と入力):")

        # Start the scheduler in a background thread
        scheduler_thread = threading.Thread(target=self._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()

        while self.is_running:
            try:
                user_input = input("ご主人: ").strip()
                
                if user_input.lower() == 'exit':
                    log_message("Exit command received. Shutting down...")
                    self.is_running = False
                    break

                if not user_input:
                    continue

                log_message("\n--- [PROCESS START] ---")
                log_message(f">>> [User] Input: {user_input}")

                response_text = self.gemini_handler.think(user_input)
                log_message(f">>> [Gemini] Responded: {response_text}")

                if response_text:
                    self.db_handler.log_conversation(user_input, response_text)
                    
                    # Synthesize and play response (text mode often plays it)
                    synthesized_path = self.voicevox_handler.synthesize_speech(response_text, filename="output_text.wav")
                    if synthesized_path:
                        # For text mode, we assume a simple playback if a play_audio function is available
                        # or just rely on the voicevox_handler to save the file.
                        # As there's no AudioHandler in text mode, we omit direct playback here.
                        log_message("Synthesized response saved for playback (manual playback if needed).")
                    
                print(f"Sayo: {response_text}")
                log_message("--- [PROCESS END] ---")
                print("######")

            except (KeyboardInterrupt, EOFError):
                log_message("\nInterrupted by user. Shutting down...")
                self.is_running = False
            except Exception as e:
                log_message(f"An error occurred in main loop: {e}")
                self.is_running = False

        log_message("Sayo Text Mode is shutting down.")

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
