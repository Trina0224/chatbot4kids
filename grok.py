# grok.py
from ai_interface import AIModelInterface
from openai import OpenAI
from typing import List, Dict, Optional, Union
import base64

class GrokModel(AIModelInterface):
    def __init__(self, service_name: str = "x"):
        """Initialize Grok with API key"""
        super().__init__(service_name)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        print("[DEBUG] Initialized Grok AI model")
        
    def get_model_name(self) -> str:
        return "Grok"
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error encoding image: {e}")
    
    def format_messages(self, 
                       conversation_history: List[Dict],
                       image_path: Optional[str] = None) -> List[Dict]:
        """
        Format messages for Grok API
        Note: Current implementation handles text only. Image support coming soon.
        """
        formatted_messages = []
        
        # Add system message if present
        if conversation_history and conversation_history[0]["role"] == "system":
            formatted_messages.append({
                "role": "system",
                "content": conversation_history[0]["content"]
            })
        
        # Process conversation messages
        for message in conversation_history[1:]:  # Skip system message if present
            if isinstance(message['content'], str):
                formatted_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
            else:  # Handle messages with images (placeholder for future implementation)
                if image_path and message == conversation_history[-1]:
                    # This is a temporary placeholder - update when X releases image support
                    text_content = message["content"][0]["text"]
                    formatted_messages.append({
                        "role": message["role"],
                        "content": f"{text_content} [Note: Image analysis coming soon in next release]"
                    })
                else:
                    # For non-image messages or previous messages
                    formatted_messages.append({
                        "role": message["role"],
                        "content": message["content"][0]["text"]
                    })
        
        return formatted_messages
    
    def generate_response(self,
                         messages: List[Dict],
                         model: str,  # This parameter is ignored for Grok
                         image_path: Optional[str] = None) -> str:
        """Generate response using Grok"""
        try:
            formatted_messages = self.format_messages(messages, image_path)
            
            # If there's an image but image support isn't ready
            if image_path:
                print("[DEBUG] Image analysis with Grok will be supported in the next release")
            
            response = self.client.chat.completions.create(
                model="grok-beta",
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"Error generating response from Grok: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            raise Exception(error_msg)

