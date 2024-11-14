# camera_utils.py
from picamera2 import Picamera2
from PIL import Image, ImageTk
import datetime
import os
from pathlib import Path
from typing import Optional

class CameraManager:
    """Manages single camera operations"""
    
    @staticmethod
    def detect_camera() -> bool:
        """
        Detect if camera is available
        Returns:
            bool: True if camera is available, False otherwise
        """
        try:
            cam = Picamera2(0)
            cam.close()
            print("[DEBUG] Camera detected")
            return True
        except Exception as e:
            print(f"[DEBUG] Camera not available: {e}")
            return False

    @staticmethod
    def setup_camera() -> Optional[Picamera2]:
        """
        Setup single camera with error handling
        Returns:
            Optional[Picamera2]: Initialized camera object or None if failed
        """
        try:
            camera = Picamera2(0)
            
            # Create preview configuration
            preview_config = camera.create_preview_configuration(
                main={"size": (1536, 864)},
                buffer_count=4
            )
            
            # Configure camera
            camera.configure(preview_config)
            
            # Set camera controls
            camera.set_controls({
                "AfMode": 2,  # Continuous autofocus
                "AwbEnable": 1,  # Auto white balance
                "AeEnable": 1    # Auto exposure
            })
            
            camera.start()
            print("[DEBUG] Camera successfully initialized")
            return camera
            
        except Exception as e:
            print(f"[DEBUG] Error setting up camera: {e}")
            return None

    @staticmethod
    def capture_high_res(camera: Picamera2) -> Optional[str]:
        """
        Capture high resolution image
        Returns:
            Optional[str]: Path to saved image or None if failed
        """
        if not camera:
            print("[DEBUG] No camera provided")
            return None
            
        original_config = None
        try:
            # Store original configuration
            original_config = camera.camera_configuration
            
            # Configure for high-res capture
            camera.stop()
            capture_config = camera.create_still_configuration(
                main={"size": (4608, 2592)}
            )
            camera.configure(capture_config)
            camera.start()
            
            # Set capture controls
            camera.set_controls({
                "AfMode": 2,
                "AwbEnable": 1,
                "AeEnable": 1
            })

            # Create timestamp and filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            pictures_dir = Path.home() / "Pictures"
            pictures_dir.mkdir(exist_ok=True)
            filename = pictures_dir / f"image_{timestamp}.jpg"
            
            # Capture image
            camera.capture_file(str(filename))
            print(f"[DEBUG] High-res image saved: {filename}")
            
            return str(filename)
            
        except Exception as e:
            print(f"[DEBUG] Error capturing high-res image: {e}")
            return None
            
        finally:
            # Restore original configuration
            try:
                if original_config:
                    camera.stop()
                    camera.configure(original_config)
                    camera.start()
            except Exception as e:
                print(f"[DEBUG] Error restoring camera configuration: {e}")

    @staticmethod
    def capture_and_convert(camera: Picamera2) -> Optional[str]:
        """
        Capture and process image for AI analysis
        Returns:
            Optional[str]: Path to processed image or None if failed
        """
        if not camera:
            print("[DEBUG] No camera provided")
            return None
            
        final_path = "camera.jpg"
        
        try:
            # Capture frame
            image_array = camera.capture_array()
            if image_array is None:
                raise ValueError("Captured frame is empty")
                
            # Process image
            img = Image.fromarray(image_array).convert('RGB')
            
            # Calculate resize dimensions
            aspect_ratio = img.width / img.height
            if aspect_ratio > 1:
                resize_width = int(512 * aspect_ratio)
                resize_height = 512
            else:
                resize_width = 512
                resize_height = int(512 / aspect_ratio)
            
            # Resize and crop to 512x512
            img = img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
            left = (resize_width - 512) // 2
            top = (resize_height - 512) // 2
            img = img.crop((left, top, left + 512, top + 512))
            
            # Save processed image
            img.save(final_path, "JPEG", quality=95)
            print(f"[DEBUG] Processed image saved: {final_path}")
            return final_path
            
        except Exception as e:
            print(f"[DEBUG] Error in image processing: {e}")
            return None

