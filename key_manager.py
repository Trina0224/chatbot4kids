# key_manager.py
from pathlib import Path
from typing import Dict

class KeyManager:
    """Manages API keys for different services"""
    
    DEFAULT_KEYS = {
        "openai": "openai_key.txt",
        "anthropic": "anthropic_key.txt",
        "google": "google_key.txt",
        "x": "x_key.txt",
        "perplexity": "perplexity_key.txt"
    }
    
    @staticmethod
    def load_key(service: str) -> str:
        """
        Load API key for a specific service
        Args:
            service: Service name ('openai', 'anthropic', 'google', 'x')
        Returns:
            str: API key
        Raises:
            ValueError: If service is unknown
            FileNotFoundError: If key file is missing
        """
        if service not in KeyManager.DEFAULT_KEYS:
            raise ValueError(f"Unknown service: {service}")
            
        key_file = KeyManager.DEFAULT_KEYS[service]
        try:
            with open(key_file, "r") as file:
                return file.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"API key file not found: {key_file}. "
                f"Please ensure you have the {key_file} file in the current directory."
            )

    @staticmethod
    def get_key_path(service: str) -> str:
        """Get the key file path for a service"""
        if service not in KeyManager.DEFAULT_KEYS:
            raise ValueError(f"Unknown service: {service}")
        return KeyManager.DEFAULT_KEYS[service]

