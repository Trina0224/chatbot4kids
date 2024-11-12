# chatgpt.py
from ai_interface import AIModelInterface
from openai import OpenAI
import base64
from typing import List, Dict, Optional

class ChatGPTModel(AIModelInterface):
    def __init__(self, service_name: str = "openai"):
        """Initialize ChatGPT with API key"""
        super().__init__(service_name)
        self.client = OpenAI(api_key=self.api_key)
        
    def get_model_name(self) -> str:
        return "ChatGPT"
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def format_messages(self, 
                       conversation_history: List[Dict],
                       image_path: Optional[str] = None) -> List[Dict]:
        """Format messages for ChatGPT API"""
        formatted_messages = []
        
        for message in conversation_history:
            if isinstance(message['content'], str):
                formatted_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
            else:  # Handle messages with images
                formatted_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
        
        # Add image to the last message if provided
        if image_path:
            image_base64 = self.encode_image_to_base64(image_path)
            last_message = formatted_messages[-1]
            if isinstance(last_message['content'], str):
                last_message['content'] = [
                    {"type": "text", "text": last_message['content']},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
        
        return formatted_messages
    
    def generate_response(self,
                         messages: List[Dict],
                         model: str,
                         image_path: Optional[str] = None) -> str:
        """Generate response using ChatGPT"""
        formatted_messages = self.format_messages(messages, image_path)
        
        response = self.client.chat.completions.create(
            model=model,  # "gpt-4o-mini" or "gpt-4o"
            messages=formatted_messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content

