# claude.py
from ai_interface import AIModelInterface
from anthropic import Anthropic
from typing import List, Dict, Optional, Tuple
import base64
from pathlib import Path

class ClaudeModel(AIModelInterface):
    def __init__(self, service_name: str = "anthropic"):
        """Initialize Claude with API key"""
        super().__init__(service_name)
        self.client = Anthropic(api_key=self.api_key)
        self.model_name = "claude-3-5-sonnet-20241022"
        
    def get_model_name(self) -> str:
        return "Claude"
    
    def format_messages(self, 
                       conversation_history: List[Dict],
                       image_path: Optional[str] = None) -> Tuple[str, List[Dict]]:
        """
        Format messages for Claude API
        Returns:
            Tuple[str, List[Dict]]: (system_message, formatted_messages)
        """
        # Extract system prompt
        system_message = ""
        if conversation_history and conversation_history[0]["role"] == "system":
            system_message = conversation_history[0]["content"]

        # Format conversation messages
        formatted_messages = []
        for message in conversation_history[1:]:  # Skip system message
            if message["role"] in ["user", "assistant"]:
                if isinstance(message['content'], str):
                    formatted_messages.append({
                        "role": message["role"],
                        "content": [
                            {
                                "type": "text",
                                "text": message["content"]
                            }
                        ]
                    })
                else:  # Handle list type content (for messages with images)
                    # For image messages, we need special handling
                    if message["role"] == "user" and image_path and message == conversation_history[-1]:
                        # This is the latest message with an image
                        try:
                            with open(image_path, "rb") as img_file:
                                image_data = base64.b64encode(img_file.read()).decode('utf-8')
                                formatted_messages.append({
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": "image/jpeg",
                                                "data": image_data
                                            }
                                        },
                                        {
                                            "type": "text",
                                            "text": message["content"][0]["text"]
                                        }
                                    ]
                                })
                        except Exception as e:
                            raise Exception(f"Error processing image: {e}")
                    else:
                        # Regular message with non-string content
                        formatted_messages.append({
                            "role": message["role"],
                            "content": [
                                {
                                    "type": "text",
                                    "text": message["content"][0]["text"]
                                }
                            ]
                        })

        return system_message, formatted_messages
    
    def generate_response(self,
                         messages: List[Dict],
                         model: str,  # This parameter is ignored for Claude
                         image_path: Optional[str] = None) -> str:
        """Generate response using Claude"""
        try:
            system_message, formatted_messages = self.format_messages(messages, image_path)
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=1000,
                temperature=0.7,
                system=system_message,
                messages=formatted_messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Error generating response from Claude: {e}")

