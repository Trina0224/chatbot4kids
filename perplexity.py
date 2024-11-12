# perplexity.py
from ai_interface import AIModelInterface
from openai import OpenAI
from typing import List, Dict, Optional
import base64

class PerplexityModel(AIModelInterface):
    def __init__(self, service_name: str = "perplexity"):
        """Initialize Perplexity with API key"""
        super().__init__(service_name)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.perplexity.ai"
        )
        print("[DEBUG] Initialized Perplexity AI model")
        
    def get_model_name(self) -> str:
        return "Perplexity"
    
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
        Format messages for Perplexity API
        Note: Current implementation handles text only. Image support depends on API capabilities.
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
            else:  # Handle messages with images
                if image_path and message == conversation_history[-1]:
                    # This is a temporary implementation - update when image support is confirmed
                    text_content = message["content"][0]["text"]
                    formatted_messages.append({
                        "role": message["role"],
                        "content": f"{text_content} [Note: Image analysis capabilities subject to API support]"
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
                         model: str,  # This parameter is ignored for Perplexity
                         image_path: Optional[str] = None) -> str:
        """Generate response using Perplexity"""
        try:
            formatted_messages = self.format_messages(messages, image_path)
            
            # If there's an image but image support isn't confirmed
            if image_path:
                print("[DEBUG] Image analysis capabilities subject to Perplexity API support")
            
            response = self.client.chat.completions.create(
                model="llama-3.1-sonar-large-128k-online",  # Default model
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"Error generating response from Perplexity: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            raise Exception(error_msg)

