# tts_manager.py
from pathlib import Path
from openai import OpenAI
import pygame
import threading
import os
from typing import Callable
import time

class TTSManager:
    def __init__(self, api_key_path: str = "openai_key.txt"):
        """
        Initialize the TTS Manager.
        Args:
            api_key_path (str): Path to the file containing the OpenAI API key
        """
        self.client = OpenAI(api_key=self._load_api_key(api_key_path))
        pygame.mixer.init()
        self.is_playing = False
        self.current_thread = None
        self.current_audio_path = None
        self._lock = threading.Lock()
   
        # Define voice mapping for different AI models
        self.voice_mapping = {
            'ChatGPT': 'nova',      # Default friendly voice
            'Claude': 'alloy',      # More professional, balanced voice
            'Gemini': 'onyx',    # Deep, resonant voice 
            'Grok': 'shimmer',         # Bright, energetic voice
            'Perplexity': 'echo',  # Or any other appropriate voice
            'default': 'nova'       # Fallback voice
        }

    def _load_api_key(self, filepath: str) -> str:
        """
        Load the OpenAI API key from file.
        Args:
            filepath (str): Path to the API key file
        Returns:
            str: The API key
        """
        try:
            with open(filepath, "r") as file:
                return file.read().strip()
        except FileNotFoundError:
            raise Exception(f"API key file not found at {filepath}")
    
    def text_to_speech(self, 
                      text: str, 
                      language: str = "en",
                      status_callback: Callable[[str], None] = None,
                      model_name: str = "ChatGPT") -> None:
        """
        Convert text to speech using model-specific voice.
        Args:
            text (str): Text to convert to speech
            language (str): Language code ('en', 'ja', 'zh')
            status_callback: Callback function to update status
            model_name (str): Name of the AI model for voice selection
        """
        if status_callback:
            status_callback("Generating speech...")
        
        # Stop any existing playback
        self.stop_playback()
        
        # Create a unique filename
        output_path = Path("/tmp") / f"tts_{os.getpid()}_{int(time.time()*1000)}.mp3"
        
        try:
            # Select voice based on model and language
            voice = self.voice_mapping.get(model_name, self.voice_mapping['default'])
            
            # Generate speech
            with self.client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice=voice,
                input=text
            ) as response:
                response.stream_to_file(str(output_path))
            
            if status_callback:
                status_callback("Playing audio...")
            
            with self._lock:
                self.current_audio_path = output_path
                self.current_thread = threading.Thread(
                    target=self._play_audio,
                    args=(output_path, status_callback)
                )
                self.current_thread.daemon = True
                self.current_thread.start()
            
        except Exception as e:
            print(f"Error in text to speech conversion: {e}")
            if status_callback:
                status_callback(f"Error: {str(e)}")
            if output_path.exists():
                try:
                    os.remove(output_path)
                except Exception as e:
                    print(f"Error removing temporary file: {e}")


    
    def _play_audio(self, audio_path: Path, 
                    status_callback: Callable[[str], None] = None) -> None:
        """
        Play the audio file and clean up afterwards.
        Args:
            audio_path (Path): Path to the audio file to play
            status_callback: Callback function to update status
        """
        try:
            with self._lock:
                if not self.is_playing:
                    pygame.mixer.music.load(str(audio_path))
                    self.is_playing = True
                    pygame.mixer.music.play()
            
            # Wait for playback to finish or stop command
            while self.is_playing and pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
        except Exception as e:
            print(f"Error playing audio: {e}")
            if status_callback:
                status_callback(f"Error playing audio: {str(e)}")
        
        finally:
            # Cleanup
            with self._lock:
                self.is_playing = False
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                except Exception as e:
                    print(f"Error stopping audio: {e}")
                
                if audio_path.exists():
                    try:
                        os.remove(audio_path)
                    except Exception as e:
                        print(f"Error removing audio file: {e}")
                
                if status_callback:
                    status_callback("")
                
                self.current_audio_path = None
    
    def stop_playback(self):
        """
        Safely stop the current audio playback.
        """
        with self._lock:
            if self.is_playing:
                self.is_playing = False
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                except Exception as e:
                    print(f"Error stopping playback: {e}")
                
                # Clean up current audio file
                if self.current_audio_path and self.current_audio_path.exists():
                    try:
                        os.remove(self.current_audio_path)
                    except Exception as e:
                        print(f"Error removing current audio file: {e}")
                
                self.current_audio_path = None

