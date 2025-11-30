# backend/handlers/voicevox_handler.py

import requests
import json
import os
from utils.logging_config import log_message

class VoicevoxHandler:
    def __init__(self, base_url, speaker_id):
        self.base_url = base_url
        self.speaker_id = speaker_id
        self._check_voicevox_availability()

    def _check_voicevox_availability(self):
        """Checks if the VOICEVOX engine is running."""
        try:
            response = requests.get(f"{self.base_url}/version")
            response.raise_for_status()
            log_message(f"VOICEVOX is running (version: {response.json()}).")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"VOICEVOX is not running on {self.base_url}. "
                f"Please start the application. Error: {e}"
            )

    def synthesize_speech(self, text, filename="output.wav"):
        """
        Generates speech audio from text using VOICEVOX and saves it to a file.
        Returns the path to the audio file, or None if synthesis fails.
        """
        if not text or not text.strip():
            log_message("No text provided for speech synthesis.")
            return None

        log_message(f"Synthesizing speech for: '{text}'")
        try:
            # 1. Get audio query
            params = {"text": text, "speaker": self.speaker_id}
            response = requests.post(
                f"{self.base_url}/audio_query",
                params=params
            )
            response.raise_for_status()
            audio_query = response.json()

            # 2. Synthesize audio
            response = requests.post(
                f"{self.base_url}/synthesis",
                params={"speaker": self.speaker_id},
                data=json.dumps(audio_query)
            )
            response.raise_for_status()

            # 3. Save audio to file
            with open(filename, "wb") as f:
                f.write(response.content)
            
            log_message(f"Speech synthesized and saved to {filename}")
            return filename
        
        except requests.exceptions.RequestException as e:
            log_message(f"Error during speech synthesis: {e}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            log_message(f"Error processing VOICEVOX response: {e}")
            return None
