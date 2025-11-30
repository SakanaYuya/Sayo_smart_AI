# backend/handlers/audio_handler.py

import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import queue
import sys
import select
import time
import os
import threading
from utils.logging_config import log_message

class AudioHandler:
    def __init__(self, whisper_model_name, sample_rate, channels, chunk_size, silence_threshold, silence_duration, max_record_duration):
        self.whisper_model = self._load_whisper_model(whisper_model_name)
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_record_duration = max_record_duration
        
        # Thread-safe queue for audio data
        self.audio_queue = queue.Queue()
        self.speaking_event = threading.Event()

    def _load_whisper_model(self, model_name):
        """Loads the specified Whisper model."""
        log_message(f"Loading Whisper model: {model_name}...")
        model = whisper.load_model(model_name)
        log_message("Whisper model loaded.")
        return model

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback function for the audio stream."""
        if status:
            log_message(f"[STDERR] {status}")
        self.audio_queue.put(indata.copy())
        
        # Detect if speaking has started
        if not self.speaking_event.is_set():
            rms = np.sqrt(np.mean(indata**2))
            if rms > self.silence_threshold:
                self.speaking_event.set()
                log_message("話し始めました...")

    def listen_and_record(self, output_filename="recorded_speech.wav"):
        """
        Listens for speech, records it, and stops when silence is detected.
        Returns the path to the recorded file, "EXIT" if 'exit' is typed, or None.
        """
        log_message("話しかけてください... ('exit'と入力して終了)")
        
        frames = []
        self.speaking_event.clear()
        self.audio_queue.queue.clear() # Clear previous data
        silence_start_time = None
        
        with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, 
                              dtype='float32', callback=self._audio_callback, 
                              blocksize=self.chunk_size):
            
            start_time = time.time()
            while True:
                # 1. Check for 'exit' command from stdin
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    line = sys.stdin.readline()
                    if line and line.strip().lower() == 'exit':
                        return "EXIT"

                # 2. Check for recording timeout
                if time.time() - start_time > self.max_record_duration:
                    log_message("最大録音時間に達しました。")
                    break

                try:
                    # 3. Get audio data from queue
                    data = self.audio_queue.get(timeout=1.0)
                    frames.append(data)
                    
                    # 4. Silence detection logic
                    if self.speaking_event.is_set():
                        rms = np.sqrt(np.mean(data**2))
                        if rms < self.silence_threshold:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            elif time.time() - silence_start_time > self.silence_duration:
                                log_message("無音を検出しました。録音を終了します。")
                                break
                        else:
                            silence_start_time = None # Reset timer
                
                except queue.Empty:
                    # Handle cases where the queue is empty
                    if self.speaking_event.is_set() and silence_start_time and (time.time() - silence_start_time > self.silence_duration):
                        log_message("無音を検出しました。録音を終了します。")
                        break
                    # Timeout if no speech is detected for a while
                    elif not self.speaking_event.is_set() and (time.time() - start_time > 10):
                        log_message("10秒間音声が検出されませんでした。")
                        break
                    continue

        if not frames:
            log_message("音声が録音されませんでした。")
            return None

        # Save the recorded audio to a file
        recorded_audio = np.concatenate(frames, axis=0)
        sf.write(output_filename, recorded_audio, self.sample_rate)
        log_message(f"音声を {output_filename} に保存しました。")
        return output_filename

    def recognize_speech(self, audio_path):
        """Transcribes speech from an audio file using Whisper."""
        if not audio_path or not os.path.exists(audio_path):
            return ""
            
        log_message(f"Recognizing speech from {audio_path}...")
        try:
            result = self.whisper_model.transcribe(audio_path, language="ja", task="transcribe")
            text = result.get("text", "")
            log_message(f"Recognized: {text}")
            return text
        except Exception as e:
            log_message(f"Error during speech recognition: {e}")
            return ""

    def play_audio(self, audio_path):
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
