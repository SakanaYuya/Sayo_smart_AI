# backend/handlers/gemini_handler.py

import google.generativeai as genai
from utils.logging_config import log_message

class GeminiHandler:
    def __init__(self, api_key, model_name, system_instruction):
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            system_instruction=system_instruction
        )
        log_message("Gemini API configured.")

    def think(self, prompt):
        """
        Sends a prompt to the Gemini model and returns its response.
        Returns an empty string if the prompt is empty or only whitespace.
        """
        if not prompt or not prompt.strip():
            return ""
        
        log_message(f"Sending to Gemini: {prompt}")
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            log_message(f"Gemini responded: {text}")
            return text
        except Exception as e:
            log_message(f"Error communicating with Gemini: {e}")
            return "すみません、ご主人。少し考えごとをしていました。もう一度お願いできますか？"

