# gemini.py
from ai_interface import AIModelInterface
import google.generativeai as genai
from typing import List, Dict, Optional, Union
import PIL.Image

class GeminiModel(AIModelInterface):
    def __init__(self, service_name: str = "google"):
        """Initialize Gemini with API key"""
        super().__init__(service_name)
        print("[DEBUG] Initializing Gemini model")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.chat = None
        self.system_context = """You are a knowledgeable female assistant with expertise in Japanese, 
                English, Chinese, Christianity, and Biblical studies. There are two cameras in the system:
                Camera 1 (front camera) and Camera 2 (rear camera). When asked about 'camera 1' or 'front camera', 
                you'll analyze the front view image. When asked about 'camera 2' or 'rear camera', you'll analyze 
                the rear view image. Please provide helpful and accurate responses for daily life questions and 
                image analysis. Maintain conversation context and provide responses in the same language as the 
                user's query."""
        print("[DEBUG] Gemini model initialized successfully")
        
    def get_model_name(self) -> str:
        return "Gemini"
    
    def format_messages(self, 
                       conversation_history: List[Dict],
                       image_path: Optional[str] = None) -> Union[List[str], List[Union[str, PIL.Image.Image]]]:
        """
        Format messages for Gemini API
        """
        print(f"[DEBUG] Gemini format_messages: Image path = {image_path}")
        
        # Extract the last message
        last_message = conversation_history[-1]
        print(f"[DEBUG] Gemini last message: {last_message}")
        
        # Extract the text content
        if isinstance(last_message["content"], list):
            text_content = last_message["content"][0]["text"]
        else:
            text_content = last_message["content"]
            
        print(f"[DEBUG] Gemini text content: {text_content}")
        
        # If there's an image, handle it with context
        if image_path:
            try:
                print(f"[DEBUG] Gemini opening image: {image_path}")
                image = PIL.Image.open(image_path)
                print(f"[DEBUG] Gemini image loaded successfully: size={image.size}, mode={image.mode}")
                
                # Determine which camera is being used
                camera_context = "front camera (Camera 1)" if "camera1" in image_path else "rear camera (Camera 2)"
                
                # Create a contextual prompt
                prompt = f"{self.system_context}\n\nAnalyzing image from {camera_context}. {text_content}"
                return [prompt, image]
                
            except Exception as e:
                print(f"[DEBUG] Gemini image loading error: {e}")
                raise Exception(f"Error loading image in Gemini: {e}")
        else:
            # For text-only messages, include system context
            return [f"{self.system_context}\n\n{text_content}"]
    
    def generate_response(self,
                         messages: List[Dict],
                         model: str,  # This parameter is ignored for Gemini
                         image_path: Optional[str] = None) -> str:
        """Generate response using Gemini"""
        try:
            print(f"[DEBUG] Gemini generate_response starting: image_path={image_path}")
            formatted_content = self.format_messages(messages, image_path)
            print(f"[DEBUG] Gemini formatted_content length: {len(formatted_content)}")
            
            if image_path:
                print("[DEBUG] Gemini generating response with image")
                try:
                    response = self.model.generate_content(
                        formatted_content,
                        generation_config={
                            "temperature": 0.7,
                            "max_output_tokens": 1000,
                            "candidate_count": 1
                        }
                    )
                    print("[DEBUG] Gemini image response generated successfully")
                    return response.text
                except Exception as e:
                    print(f"[DEBUG] Gemini image generation error: {e}")
                    raise Exception(f"Error generating image response in Gemini: {e}")
            else:
                print("[DEBUG] Gemini generating text-only response")
                if self.chat is None:
                    # Initialize chat with system context
                    self.chat = self.model.start_chat(history=[
                        {"role": "user", "parts": self.system_context},
                        {"role": "model", "parts": "I understand I'm an assistant with access to two cameras and will help analyze images and answer questions accordingly."}
                    ])
                response = self.chat.send_message(
                    formatted_content[0],
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 1000,
                        "candidate_count": 1
                    }
                )
                return response.text
            
        except Exception as e:
            print(f"[DEBUG] Gemini generate_response error: {e}")
            raise Exception(f"Error in Gemini generate_response: {e}")

