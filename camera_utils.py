# camera_utils.py
from picamera2 import Picamera2
from PIL import Image
import datetime
import os
from pathlib import Path
import platform

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
            # Only try Camera 2 if explicitly needed
            if len(available_cameras) > 0:  # Only check for second camera if first one exists
                try:
                    cam = Picamera2(1)
                    cam.close()
                    available_cameras.append(1)
                    print("[DEBUG] Camera 2 detected")
                except Exception:
                    print("[DEBUG] Camera 2 not detected - continuing with single camera")
                    # Not treating this as an error, just information

            return available_cameras
        except Exception as e:
            print(f"[DEBUG] Error in camera detection: {e}")
            return []


    @staticmethod
    def setup_camera(camera_num: int) -> Picamera2:
        """Setup camera with specified number"""
        try:
            camera = Picamera2(camera_num)
            
            # Determine if we're on RPi 4 or 5
            # You can add more sophisticated detection if needed
            try:
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read()
                    is_rpi5 = 'Raspberry Pi 5' in model
                    print(f"[DEBUG] Detected RPi model: {model.strip()}")
            except:
                is_rpi5 = False
                print("[DEBUG] Could not detect RPi model, defaulting to RPi 4 configuration")
            
            # Configure based on RPi version
            if is_rpi5:
                preview_config = {
                    "size": (640, 480),
                    "format": "XBGR8888"  # RPi 5 configuration
                }
            else:
                preview_config = {
                    "size": (640, 480),
                    "format": "YUV420"  # RPi 4 configuration
                }
            
            # Main stream configuration remains the same
            still_config = {
                "size": (1640, 1232),
                "format": "XBGR8888"
            }
            
            print(f"[DEBUG] Camera {camera_num} config - preview: {preview_config}, still: {still_config}")
            
            camera_config = camera.create_preview_configuration(
                main=still_config,
                lores=preview_config
            )
            
            camera.configure(camera_config)
            camera.start()
            print(f"[DEBUG] Camera {camera_num} successfully initialized")
            return camera
            
        except Exception as e:
            print(f"[DEBUG] Error setting up camera {camera_num}: {e}")
            raise


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

