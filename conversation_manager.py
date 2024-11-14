# conversation_manager.py
from openai import OpenAI
import opencc
from typing import List, Dict, Callable, Optional, Union
import base64
from tts_manager import TTSManager
import re
from camera_utils import CameraManager
import datetime
import os
from pathlib import Path
from key_manager import KeyManager
from chatgpt import ChatGPTModel
from system_prompts import SystemPrompts

class ConversationManager:
    def __init__(self, api_key_path: str = "openai_key.txt"):
        self.converter = opencc.OpenCC('s2t')
        # Initialize OpenAI client for speech services
        self.client = OpenAI(api_key=KeyManager.load_key("openai"))
        self.tts_manager = TTSManager(KeyManager.get_key_path("openai"))

        # Initialize current AI model (default to ChatGPT)
        self.current_model = ChatGPTModel()

        # Initialize Perplexity model for searches
        from perplexity import PerplexityModel
        self.search_model = PerplexityModel()

        # Initialize camera reference
        self.camera = None
        
        # Initialize conversation history with system prompt
        self.conversation_history = [
            {
                "role": "system",
                "content": SystemPrompts.get_prompt("ChatGPT")  # Default to ChatGPT prompt
            }
        ]

        # Add command patterns for different languages
        self.photo_commands = {
            'take_photo': [
                r'take photo',           # English
                r'写真を撮って',          # Japanese
                r'拍照',                 # Traditional Chinese
                r'照相'                  # Traditional Chinese alternative
            ],
            'what_is_this': [
                r'what is this\??',      # English
                r'これは何\??',          # Japanese
                r'這是什麼\??',          # Traditional Chinese
            ],
            'analyze_camera': [
                r'camera',               # English
                r'カメラ',               # Japanese
                r'相機'                  # Traditional Chinese
            ]
        }

    def set_ai_model(self, model_name: str) -> None:
        """Change the current AI model"""
        try:
            print(f"[DEBUG] Attempting to switch to {model_name}")
            
            # Update system prompt for new model
            if self.conversation_history:
                self.conversation_history[0]["content"] = SystemPrompts.get_prompt(model_name)
 
            if model_name == "ChatGPT":
                self.current_model = ChatGPTModel()
            elif model_name == "Claude":
                from claude import ClaudeModel
                self.current_model = ClaudeModel()
                self.clear_history()
            elif model_name == "Gemini":
                from gemini import GeminiModel
                self.current_model = GeminiModel()
                self.clear_history()
            elif model_name == "Grok":
                from grok import GrokModel
                self.current_model = GrokModel()
                self.clear_history()
            elif model_name == "Perplexity":
                from perplexity import PerplexityModel
                self.current_model = PerplexityModel()
                self.clear_history()
            else:
                raise ValueError(f"Unsupported model: {model_name}")
            
            print(f"[DEBUG] Current model after switch: {self.current_model.get_model_name()}")
        except Exception as e:
            print(f"[DEBUG] Error during model switch: {str(e)}")
            raise Exception(f"Error switching to {model_name}: {e}")

    def set_camera(self, camera: 'Picamera2'):
        """Set camera reference from the main app"""
        self.camera = camera
        print(f"[DEBUG] Camera reference set: {camera is not None}")

    def parse_command(self, text: str) -> tuple[str, Optional[str]]:
        """
        Parse the input text to determine command type
        Returns: (command_type, None)
        command_type can be: 'take_photo', 'analyze', 'normal'
        """
        text = text.lower().strip()
        
        # Check for photo taking command
        for pattern in self.photo_commands['take_photo']:
            if re.search(pattern, text, re.IGNORECASE):
                return 'take_photo', None

        # Check for "what is this" type questions
        for pattern in self.photo_commands['what_is_this']:
            if re.search(pattern, text, re.IGNORECASE):
                return 'analyze', None

        # Check for general camera analysis commands
        for pattern in self.photo_commands['analyze_camera']:
            if re.search(pattern, text, re.IGNORECASE):
                return 'analyze', None
        
        return 'normal', None

    def add_message(self, role: str, content: Union[str, List], image_path: str = None) -> None:
        if image_path:
            try:
                with open(image_path, "rb") as image_file:
                    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                content_with_image = {
                    "type": "text",
                    "text": content
                }
                image_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
                self.conversation_history.append({
                    "role": role,
                    "content": [content_with_image, image_content]
                })
            except Exception as e:
                print(f"[DEBUG] Error adding message with image: {e}")
                # Fall back to text-only message
                self.conversation_history.append({"role": role, "content": content})
        else:
            self.conversation_history.append({"role": role, "content": content})

    def clear_history(self) -> None:
        """Clear conversation history but keep system prompt"""
        self.conversation_history = [self.conversation_history[0]]
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text.
        Returns 'ja' for Japanese, 'zh' for Chinese, 'en' for English
        """
        # Check for Japanese characters
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return 'ja'
        # Check for Chinese characters
        elif re.search(r'[\u4E00-\u9FFF]', text):
            return 'zh'
        # Default to English
        return 'en'

    def get_response(self, user_input: str, status_callback: Callable[[str], None] = None) -> str:
        """
        Generate a response incorporating camera analysis, online searches, and TTS
        """
        try:
            print(f"[DEBUG] Processing input: {user_input}")
            command_type, _ = self.parse_command(user_input)
            print(f"[DEBUG] Parsed command: type={command_type}")
            image_path = None

            # Handle user's direct camera commands
            if command_type == 'take_photo' and self.camera:
                filepath = CameraManager.capture_high_res(self.camera)
                if filepath:
                    return f"Photo saved to: {filepath}"
                return "Error taking photo"

            elif command_type == 'analyze' and self.camera:
                image_path = CameraManager.capture_and_convert(self.camera)
                if not image_path:
                    return "Error: Failed to capture image"

            # Add initial user message to conversation history
            if image_path:
                self.add_message("user", user_input, image_path)
            else:
                self.add_message("user", user_input)

            # Determine model based on current model type
            if isinstance(self.current_model, ChatGPTModel):
                model = "gpt-4o-mini" if image_path else "gpt-4o"
                print(f"[DEBUG] Using ChatGPT model: {model}")
            else:
                model = None
                print(f"[DEBUG] Using {self.current_model.get_model_name()} with its own model naming")

            # Get initial response from current AI model
            print(f"[DEBUG] Generating initial response using {self.current_model.get_model_name()}")
            initial_response = self.current_model.generate_response(
                self.conversation_history,
                model,
                image_path
            )

            # Check for AI-initiated camera commands
            camera_pattern = r'{"camera": ?"1"}'
            if re.search(camera_pattern, initial_response) and self.camera:
                print("[DEBUG] Found camera command in response")
                
                if status_callback:
                    status_callback("Capturing image...")

                image_path = CameraManager.capture_and_convert(self.camera)
                if not image_path:
                    return "Error: Failed to capture image"

                # Add AI's intermediate response and image to conversation
                self.add_message("assistant", "Let me analyze that image.", None)
                self.add_message("user", "Please analyze this image.", image_path)

                # Get new response with image analysis
                print("[DEBUG] Generating response with image analysis")
                final_response = self.current_model.generate_response(
                    self.conversation_history,
                    model,
                    image_path
                )
                
                # Add final response to history
                self.add_message("assistant", final_response)

                # Handle TTS
                language = self.detect_language(final_response)
                self.tts_manager.text_to_speech(
                    final_response,
                    language,
                    status_callback,
                    model_name=self.current_model.get_model_name()
                )

                if status_callback:
                    status_callback("")

                return final_response

            # Check for search requests
            search_pattern = r'{"Online search": "([^"]+)"}'
            search_match = re.search(search_pattern, initial_response)
            
            if search_match:
                search_query = search_match.group(1)
                print(f"[DEBUG] Found search request: {search_query}")
                
                if status_callback:
                    status_callback(f"Searching for: {search_query}")

                try:
                    # Perform search using Perplexity
                    search_messages = [
                        {
                            "role": "system",
                            "content": "You are a helpful search assistant. Provide accurate and concise information."
                        },
                        {
                            "role": "user",
                            "content": search_query
                        }
                    ]

                    search_result = self.search_model.generate_response(
                        search_messages,
                        "llama-3.1-sonar-large-128k-online",
                        None
                    )

                    # Create a new user message with search results
                    combined_input = f"""Original query: {user_input}

Search results for "{search_query}":
{search_result}

Please provide a complete response incorporating this information."""

                    # Add search results to conversation
                    self.add_message("user", combined_input)

                    # Get final response incorporating search results
                    final_response = self.current_model.generate_response(
                        self.conversation_history,
                        model,
                        image_path
                    )

                    # Add final response to history
                    self.add_message("assistant", final_response)

                    # Handle TTS
                    language = self.detect_language(final_response)
                    self.tts_manager.text_to_speech(
                        final_response,
                        language,
                        status_callback,
                        model_name=self.current_model.get_model_name()
                    )

                    if status_callback:
                        status_callback("")

                    return final_response

                except Exception as e:
                    print(f"[DEBUG] Search error: {e}")
                    error_msg = f"I encountered an error while searching: {str(e)}"
                    if status_callback:
                        status_callback(error_msg)
                    return error_msg

            # No special commands, handle normal response
            print("[DEBUG] No special commands found, processing normal response")
            self.add_message("assistant", initial_response)
            
            # Handle TTS
            language = self.detect_language(initial_response)
            self.tts_manager.text_to_speech(
                initial_response,
                language,
                status_callback,
                model_name=self.current_model.get_model_name()
            )

            if status_callback:
                status_callback("")

            return initial_response

        except Exception as e:
            print(f"[DEBUG] Error in get_response: {str(e)}")
            error_msg = f"Error: {str(e)}"
            if status_callback:
                status_callback(error_msg)
            return error_msg

