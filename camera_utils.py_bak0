# camera_utils.py
from picamera2 import Picamera2
from PIL import Image
import datetime
import os
from pathlib import Path

class CameraManager:
    @staticmethod
    def detect_cameras() -> list:
        """
        Detect available cameras in the system
        Returns:
            list: List of available camera indices
        """
        available_cameras = []
        try:
            # Try to detect Camera 1
            try:
                cam = Picamera2(0)
                cam.close()
                available_cameras.append(0)
                print("[DEBUG] Camera 1 detected")
            except Exception as e:
                print(f"[DEBUG] Camera 1 not available: {e}")

            # Try to detect Camera 2
            try:
                cam = Picamera2(1)
                cam.close()
                available_cameras.append(1)
                print("[DEBUG] Camera 2 detected")
            except Exception as e:
                print(f"[DEBUG] Camera 2 not available: {e}")

            return available_cameras
        except Exception as e:
            print(f"[DEBUG] Error detecting cameras: {e}")
            return []

    @staticmethod
    def setup_camera(camera_num: int) -> Picamera2:
        """Setup camera with specified number"""
        camera = Picamera2(camera_num)
        
        preview_config = {
            "size": (640, 480),
            "format": "XBGR8888"
        }
        
        still_config = {
            "size": (1640, 1232),
            "format": "XBGR8888"
        }
        
        camera_config = camera.create_preview_configuration(
            main=still_config,
            lores=preview_config
        )
        
        camera.configure(camera_config)
        camera.start()
        return camera


    @staticmethod
    def capture_high_res(camera: Picamera2, camera_num: int) -> str:
        """Capture high resolution image and save to Pictures folder"""
        try:
            # Create high-res configuration
            high_res_config = camera.create_still_configuration(
                main={"size": (3280, 2464), "format": "XBGR8888"}
            )
            
            # Stop current preview to avoid conflicts
            camera.stop()
            
            # Configure for high-res capture
            camera.configure(high_res_config)
            camera.start()
            
            # Take the picture
            image_array = camera.capture_array()
            img = Image.fromarray(image_array, 'RGBA').convert('RGB')
            
            # Create timestamp and filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            pictures_dir = str(Path.home() / "Pictures")
            os.makedirs(pictures_dir, exist_ok=True)
            filename = f"Camera{camera_num}_{timestamp}.jpg"
            filepath = os.path.join(pictures_dir, filename)
            
            # Save image
            img.save(filepath, "JPEG", quality=95)
            
            # Stop camera before reconfiguring
            camera.stop()
            
            # Reconfigure for preview mode
            preview_config = camera.create_preview_configuration(
                main={"size": (1640, 1232), "format": "XBGR8888"},
                lores={"size": (640, 480), "format": "XBGR8888"}
            )
            camera.configure(preview_config)
            camera.start()
            
            return filepath
            
        except Exception as e:
            print(f"Error in high-res capture: {e}")
            # Ensure camera is reconfigured even if there's an error
            try:
                camera.stop()
                preview_config = camera.create_preview_configuration(
                    main={"size": (1640, 1232), "format": "XBGR8888"},
                    lores={"size": (640, 480), "format": "XBGR8888"}
                )
                camera.configure(preview_config)
                camera.start()
            except Exception as config_error:
                print(f"Error reconfiguring camera: {config_error}")
            return None

    @staticmethod
    def capture_and_convert(camera: Picamera2, camera_num: int) -> str:
        """Capture image and convert to 512x512 for GPT usage"""
        final_path = f"camera{camera_num}.jpg"
        
        try:
            # Use main stream for capture (1640x1232)
            image_array = camera.capture_array()
            img = Image.fromarray(image_array, 'RGBA').convert('RGB')
            
            # Calculate aspect ratio preserving resize dimensions
            aspect_ratio = img.width / img.height
            if aspect_ratio > 1:
                resize_width = int(512 * aspect_ratio)
                resize_height = 512
            else:
                resize_width = 512
                resize_height = int(512 / aspect_ratio)
            
            # Resize maintaining aspect ratio
            img = img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
            
            # Crop to center 512x512
            left = (resize_width - 512) // 2
            top = (resize_height - 512) // 2
            img = img.crop((left, top, left + 512, top + 512))
            
            img.save(final_path, "JPEG", quality=90)
            return final_path
            
        except Exception as e:
            print(f"Error in image processing: {e}")
            return None

