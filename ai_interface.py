# ai_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from key_manager import KeyManager

class AIModelInterface(ABC):
    """Abstract base class for AI model implementations"""
    
    @abstractmethod
    def __init__(self, service_name: str):
        """
        Initialize the AI model
        Args:
            service_name: Name of the service ('openai', 'anthropic', 'google', 'x')
        """
        self.api_key = KeyManager.load_key(service_name)
    
    @abstractmethod
    def generate_response(self, 
                         messages: List[Dict],
                         model: str,
                         image_path: Optional[str] = None) -> str:
        """
        Generate response from the AI model
        Args:
            messages: List of conversation messages
            model: Model name to use
            image_path: Optional path to image file
        Returns:
            str: Generated response
        """
        pass
    
    @abstractmethod
    def format_messages(self, 
                       conversation_history: List[Dict],
                       image_path: Optional[str] = None) -> List[Dict]:
        """
        Format messages according to specific API requirements
        Args:
            conversation_history: List of conversation messages
            image_path: Optional path to image file
        Returns:
            List[Dict]: Formatted messages for the specific AI model
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the AI model"""
        pass

