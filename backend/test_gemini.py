import os
import google.generativeai as genai
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def list_gemini_models():
    """Lists available Gemini models."""
    print("Listing available Gemini models...")
    try:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"  Model: {m.name}, Description: {m.description}")
    except Exception as e:
        print(f"Error listing models: {e}")
        sys.exit(1)

def test_gemini_api():
    """Tests the Gemini API connection and response."""
    print("Starting Gemini API test...")

    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please ensure your .env file in the backend directory contains GEMINI_API_KEY=\"YOUR_API_KEY\"")
        sys.exit(1)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Gemini API configured.")

        # First, try to list models to find a suitable one
        list_gemini_models()

        # Attempt to use gemini-1.5-flash, or a suitable alternative if found
        # You might need to manually update this based on the list_gemini_models output
        model_name = 'gemini-flash-latest' # Default, will try to find an alternative if this fails
        
        # Example of how you might select an alternative if 'gemini-1.5-flash' is not available
        # For now, we'll just try the specified model and let the error guide us if it's still not found.
        # In a real application, you'd have more robust model selection logic.

        gemini_model = genai.GenerativeModel(model_name)
        print(f"Using Gemini model: {model_name}")

        test_prompt = "今日は何月何日ですか"
        print(f"Sending prompt to Gemini: '{test_prompt}'")
        response = gemini_model.generate_content(test_prompt)
        
        response_text = response.text
        print(f"Gemini responded: {response_text}")
        print("Gemini API test successful!")

    except Exception as e:
        print(f"An error occurred during Gemini API test: {e}")
        print("Please check your GEMINI_API_KEY and network connection.")
        sys.exit(1)

if __name__ == "__main__":
    test_gemini_api()
