# conversation_manager.py
from openai import OpenAI
import opencc
from typing import List, Dict, Callable
import base64
from tts_manager import TTSManager
import re
from typing import Tuple, Optional
from camera_utils import CameraManager
import datetime
import os
from pathlib import Path
from key_manager import KeyManager
from chatgpt import ChatGPTModel
from typing import Union
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

        # Initialize camera references
        self.camera1 = None
        self.camera2 = None

        self.camera_images = {
            "camera1": "camera1.jpg",
            "camera2": "camera2.jpg"
        }
        
        # Initialize conversation history with system prompt
        self.conversation_history = [
            {
                "role": "system",
                "content": SystemPrompts.get_prompt("ChatGPT")  # Default to ChatGPT prompt
            }
        ]

        #self.conversation_history: List[Dict] = [
        #    {
        #        "role": "system",
        #        "content": """You are a knowledgeable female assistant with expertise in Japanese, 
        #        English, Chinese, Christianity, and Biblical studies. You can also analyze images 
        #        from two cameras. When asked about 'camera 1' or 'front camera', you'll analyze 
        #        the front view image. When asked about 'camera 2' or 'rear camera', you'll analyze 
        #        the rear view image. Please provide helpful and accurate responses for daily life 
        #        questions and image analysis. Maintain conversation context and provide responses 
        #        in the same language as the user's query."""
        #    }
        #]

        # Add command patterns for different languages
        self.photo_commands = {
            'camera1': [
                r'take photo from camera ?1',  # English
                r'camera ?1で写真を撮って',    # Japanese
                r'用camera ?一拍照',           # Traditional Chinese
                r'用camera ?一拍照',           # Traditional Chinese
                r'從camera ?1拍照',           # Traditional Chinese alternative
                r'從camera ?1拍照',           # Traditional Chinese alternative
            ],
            'camera2': [
                r'take photo from camera ?2',  # English
                r'camera ?2で写真を撮って',    # Japanese
                r'用camera ?二拍照',           # Traditional Chinese
                r'用camera ?二拍照',           # Traditional Chinese
                r'從camera ?2拍照',           # Traditional Chinese alternative
                r'從camera ?2拍照',           # Traditional Chinese alternative
            ],
            'what_is_this': [
                r'what is this\??',           # English
                r'これは何\??',               # Japanese
                r'這是什麼\??',               # Traditional Chinese
            ],
            'what_is_that': [
                r'what is that\??',           # English
                r'あれは何\??',               # Japanese
                r'それは何\??',               # Japanese
                r'那是什麼\??',               # Traditional Chinese
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
                print(f"[DEBUG] Created new ChatGPT model instance: {type(self.current_model)}")
            elif model_name == "Claude":
                from claude import ClaudeModel
                self.current_model = ClaudeModel()
                self.clear_history()
                print(f"[DEBUG] Created new Claude model instance: {type(self.current_model)}")
            elif model_name == "Gemini":
                from gemini import GeminiModel
                self.current_model = GeminiModel()
                self.clear_history()
                print(f"[DEBUG] Created new Gemini model instance: {type(self.current_model)}")
            elif model_name == "Grok":
                from grok import GrokModel
                self.current_model = GrokModel()
                self.clear_history()
                print(f"[DEBUG] Created new Grok model instance: {type(self.current_model)}")
            elif model_name == "Perplexity":
                from perplexity import PerplexityModel
                self.current_model = PerplexityModel()
                self.clear_history()
                print(f"[DEBUG] Created new Perplexity model instance: {type(self.current_model)}")
            else:
                raise ValueError(f"Unsupported model: {model_name}")
            
            #self.clear_history()
            print(f"[DEBUG] Current model after switch: {self.current_model.get_model_name()}")
        except Exception as e:
            print(f"[DEBUG] Error during model switch: {str(e)}")
            raise Exception(f"Error switching to {model_name}: {e}")


    def set_cameras(self, camera1: 'Picamera2', camera2: 'Picamera2'):
        """Set camera references from the main app"""
        self.camera1 = camera1
        self.camera2 = camera2

    def parse_command(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Parse the input text to determine command type and camera number
        Returns: (command_type, camera_number or None)
        command_type can be: 'take_photo', 'analyze', 'normal'
        """
        text = text.lower().strip()
        
        # Check for photo commands
        for camera, patterns in self.photo_commands.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                if camera == 'camera1':
                    return 'take_photo', '1'
                elif camera == 'camera2':
                    return 'take_photo', '2'
                elif camera == 'what_is_this':
                    return 'analyze', '2'  # "this" refers to camera 2
                elif camera == 'what_is_that':
                    return 'analyze', '1'  # "that" refers to camera 1
        
        # Check for analysis commands (original camera 1/2 mentions)
        if "camera 1" in text or "front camera" in text:
            return 'analyze', '1'
        elif "camera 2" in text or "rear camera" in text:
            return 'analyze', '2'
        
        return 'normal', None

    def encode_image_to_base64(self, image_path: str) -> str:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            raise Exception(f"Image file not found: {image_path}")

    def add_message(self, role: str, content: Union[str, List], image_path: str = None) -> None:
        if image_path:
            image_base64 = self.encode_image_to_base64(image_path)
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
        else:
            self.conversation_history.append({"role": role, "content": content})

    def clear_history(self) -> None:
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
        Args:
            user_input: The user's input text
            status_callback: Optional callback function to update UI status
        Returns:
            str: The generated response
        """
        try:
            print(f"[DEBUG] Processing input: {user_input}")
            command_type, camera_num = self.parse_command(user_input)
            print(f"[DEBUG] Parsed command: type={command_type}, camera={camera_num}")
            image_path = None

            # Handle user's direct camera commands first
            if command_type == 'take_photo':
                if camera_num == '1' and self.camera1:
                    filepath = CameraManager.capture_high_res(self.camera1, 1)
                elif camera_num == '2' and self.camera2:
                    filepath = CameraManager.capture_high_res(self.camera2, 2)
                else:
                    return "Error: Camera not initialized"

                if filepath:
                    return f"Photo saved to: {filepath}"
                return "Error taking photo"

            elif command_type == 'analyze':
                if camera_num == '1' and self.camera1:
                    image_path = CameraManager.capture_and_convert(self.camera1, 1)
                elif camera_num == '2' and self.camera2:
                    image_path = CameraManager.capture_and_convert(self.camera2, 2)
                else:
                    return "Error: Camera not initialized"

            # Add initial user message to conversation history
            if image_path:
                self.add_message("user", user_input, image_path)
            else:
                self.add_message("user", user_input)

            # Determine model
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

            # Check for AI-initiated camera commands in the response
            camera_pattern = r'{"camera": ?"(\d)"}'
            camera_match = re.search(camera_pattern, initial_response)
            
            if camera_match:
                camera_num = camera_match.group(1)
                print(f"[DEBUG] Found camera command: camera {camera_num}")
                
                if status_callback:
                    status_callback(f"Capturing image from camera {camera_num}...")

                # Handle AI's camera command
                if camera_num == "1" and self.camera1:
                    image_path = CameraManager.capture_and_convert(self.camera1, 1)
                elif camera_num == "2" and self.camera2:
                    image_path = CameraManager.capture_and_convert(self.camera2, 2)
                else:
                    return "Error: Requested camera not initialized"

                if image_path:
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
                return "Error capturing image"

            # Check for search requests in the response
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
                    print(f"[DEBUG] Search result from Perplexity: {search_result}")

                    # Create a new user message with search results
                    combined_input = f"""Original query: {user_input}

Search results for "{search_query}":
{search_result}

Please provide a complete response incorporating this information."""

                    # Add search results to conversation
                    self.add_message("user", combined_input)

                    # Get final response incorporating search results
                    print("[DEBUG] Generating final response with search results")
                    final_response = self.current_model.generate_response(
                        self.conversation_history,
                        model,
                        image_path
                    )

                    # Add final response to history
                    self.add_message("assistant", final_response)

                    # Handle TTS for final response
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

