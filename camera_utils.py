from picamera2 import Picamera2
from PIL import Image, ImageTk
import datetime
import os
from pathlib import Path

class CameraManager:
    @staticmethod
    def detect_cameras() -> list:
        """Detect available camera"""
        try:
            # Try to detect Camera
            try:
                cam = Picamera2(0)
                cam.close()
                print("[DEBUG] Camera detected")
                return [0]
            except Exception as e:
                print(f"[DEBUG] Camera not available: {e}")
                return []
        except Exception as e:
            print(f"[DEBUG] Error in camera detection: {e}")
            return []

    @staticmethod
    def setup_camera(camera_num: int) -> Picamera2:
        """Setup camera with specified configuration"""
        try:
            camera = Picamera2(camera_num)
            
            # Create preview configuration (matching autoFcamera.py)
            preview_config = camera.create_preview_configuration(
                main={"size": (1536, 864)},
                buffer_count=4
            )
            
            # Configure camera
            camera.configure(preview_config)
            
            # Enable continuous autofocus
            camera.set_controls({
                "AfMode": 2  # 0:Manual 1:Auto 2:Continuous
                #"HFlip": True
            })

            camera.start()
            print(f"[DEBUG] Camera successfully initialized")
            return camera
            
        except Exception as e:
            print(f"[DEBUG] Error setting up camera: {e}")
            raise

    @staticmethod
    def capture_high_res(camera: Picamera2, camera_num: int) -> str:
        """Capture high resolution image and save to Pictures folder"""
        try:
            # Stop preview
            camera.stop()
            
            # Configure for high-res capture
            capture_config = camera.create_still_configuration(
                main={"size": (4608, 2592)}
            )
            camera.configure(capture_config)
            camera.start()
            camera.set_controls({
                "AfMode": 2
                #"HFlip": True
            })

            # Capture image
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            pictures_dir = str(Path.home() / "Pictures")
            os.makedirs(pictures_dir, exist_ok=True)
            filename = os.path.join(pictures_dir, f"image_{timestamp}.jpg")
            camera.capture_file(filename)
            
            print(f"Image saved: {filename}")
            
            # Return to preview configuration
            camera.stop()
            preview_config = camera.create_preview_configuration(
                main={"size": (1536, 864)},
                buffer_count=4
            )
            camera.configure(preview_config)
            camera.start()
            
            # Re-enable continuous autofocus
            camera.set_controls({
                "AfMode": 2
                #"HFlip": True
            })
            
            return filename
            
        except Exception as e:
            print(f"Error capturing image: {e}")
            # Ensure camera is reconfigured even after error
            try:
                camera.stop()
                preview_config = camera.create_preview_configuration(
                    main={"size": (1536, 864)},
                    buffer_count=4
                )
                camera.configure(preview_config)
                camera.start()
                camera.set_controls({
                    "AfMode": 2
                    #"HFlip": True
                })
            except Exception as config_error:
                print(f"Error reconfiguring camera: {config_error}")
            return None

    @staticmethod
    def capture_and_convert(camera: Picamera2, camera_num: int) -> str:
        """Capture image and convert to 512x512 for AI processing"""
        final_path = f"camera{camera_num}.jpg"
        
        try:
            # Capture frame
            image_array = camera.capture_array()
            img = Image.fromarray(image_array).convert('RGB')
            
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
            
            # Center crop to 512x512
            left = (resize_width - 512) // 2
            top = (resize_height - 512) // 2
            img = img.crop((left, top, left + 512, top + 512))
            
            img.save(final_path, "JPEG", quality=95)
            return final_path
            
        except Exception as e:
            print(f"Error in image processing: {e}")
            return None

