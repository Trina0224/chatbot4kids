# dual_camera_gpt_app.py
import tkinter as tk
from tkinter import ttk, scrolledtext, font
from PIL import Image, ImageTk
import threading
import queue
from collections import deque
import datetime
import os
import sounddevice as sd
import numpy as np
from pydub import AudioSegment
from conversation_manager import ConversationManager
from camera_utils import CameraManager
import time
from pathlib import Path
import opencc

class DualCameraGPTApp:
    def __init__(self, master):
        self.master = master
        master.title("Camera GPT Interface")
        
        self.input_focus_timer = None
        self.is_input_focused = False

        # Initialize converter before other components
        self.converter = opencc.OpenCC('s2t')


        # Initialize recording state
        self.is_recording = False
        self.recording_thread = None
        self.audio_data = []
        self.sample_rate = 44100

        # Initialize command history
        self.command_history = deque(maxlen=10)
        self.history_index = 0
        
        # Set default font size for chat areas
        self.current_font_size = 12
        self.chat_font = font.Font(size=self.current_font_size)
        
        # Define color schemes for different participants
        self.chat_colors = {
            'human': '#666666',      # Subtle gray for human
            'ChatGPT': '#10a37f',    # OpenAI green
            'Claude': '#7C3AED',     # Purple for Claude
            'Gemini': '#1A73E8',     # Google blue
            'Grok': '#1DA1F2'        # Twitter/X blue
        }
        
        # Configure text tags for colors
        #self.setup_text_tags()

        # Initialize preview update flags
        self.running = True
        
        ## Initialize cameras
        self.setup_camera()
        
        # Initialize the GPT conversation manager
        self.conversation_manager = ConversationManager()

        # Initialize cameras
        #self.setup_camera()
        
        # Pass camera references to conversation manager
        self.conversation_manager.set_camera(self.camera)

        # Bind Escape key
        self.master.bind('<Escape>', self.stop_audio)
        
        # Create main UI
        self.create_ui()
        
        # Now we can setup text tags after chat_display is created
        self.setup_text_tags()
        
        # Start the preview loops in separate threads
        self.start_preview_thread()
        
        # Display welcome message
        self.display_welcome_message()

    
    def setup_camera(self):
        """Setup single camera"""
        print("[DEBUG] Attempting to initialize camera")
        self.camera = None
        
        try:
            if CameraManager.detect_camera():
                self.camera = CameraManager.setup_camera()
                print("[DEBUG] Camera initialized successfully")
            else:
                print("[DEBUG] No camera detected")
        except Exception as e:
            print(f"[DEBUG] Error setting up camera: {e}")

    
    def create_ui(self):
        # Create horizontal container for main content and model selection
        self.horizontal_container = ttk.Frame(self.master)
        self.horizontal_container.pack(fill=tk.BOTH, expand=True)

        # Create main container
        self.main_container = ttk.Frame(self.horizontal_container)
        self.main_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create right side control panel
        self.control_panel = ttk.Frame(self.horizontal_container)
        self.control_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Create model selection frame in control panel
        self.model_frame = ttk.LabelFrame(self.control_panel, text="AI Model")
        self.model_frame.pack(fill=tk.X, padx=5, pady=5)

        # Add radio buttons for model selection
        self.model_var = tk.StringVar(value="ChatGPT")  # Default selection
        models = ["ChatGPT", "Claude", "Gemini", "Grok", "Perplexity"]

        for model in models:
            radio = ttk.Radiobutton(
                self.model_frame,
                text=model,
                variable=self.model_var,
                value=model,
                command=self.on_model_change
            )
            radio.pack(padx=5, pady=2, anchor=tk.W)

        # Add control buttons under the model selection
        self.button_frame = ttk.LabelFrame(self.control_panel, text="Controls")
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)

        # Style for the buttons
        button_style = ttk.Style()
        button_style.configure('Tall.TButton', padding=(5, 10))

        # Record button (keeping as tk.Button for color support)
        self.record_button = tk.Button(
            self.button_frame,
            text="Say Something (`)",
            command=self.toggle_recording,
            relief=tk.RAISED,
            bg='light gray',
            activebackground='gray'
        )
        self.record_button.pack(fill=tk.X, padx=5, pady=5, ipady=10)

        # Send button
        self.send_button = ttk.Button(
            self.button_frame,
            text="Stop",
            #command=self.handle_input,
            command=self.stop_audio,
            style='Tall.TButton'
        )
        self.send_button.pack(fill=tk.X, padx=5, pady=5, ipady=10)

        # Exit button
        self.exit_button = ttk.Button(
            self.button_frame,
            text="Exit (ctrl+Q)",
            command=self.exit_program,
            style='Tall.TButton'
        )
        self.exit_button.pack(fill=tk.X, padx=5, pady=5, ipady=10)

        # Create font size control frame
        self.create_font_control()
        

        # Create camera frame if camera is available
        if self.camera:
            self.camera_frame = ttk.Frame(self.main_container)
            self.camera_frame.pack(side=tk.TOP, fill=tk.X)
            
            self.preview_canvas = tk.Canvas(
                self.camera_frame, 
                width=426,  # 16:9 aspect ratio
                height=240
            )
            self.preview_canvas.pack(padx=5, expand=True)
        else:
            # No camera message
            no_camera_label = ttk.Label(
                self.main_container,
                text="No camera detected. Voice and text chat only.",
                font=('Arial', 12, 'italic')
            )
            no_camera_label.pack(side=tk.TOP, pady=10)



        # Create chat frame
        self.chat_frame = ttk.Frame(self.main_container)
        self.chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Status label for processing feedback
        self.status_label = ttk.Label(
            self.main_container,
            text="",
            font=('Arial', 10, 'bold')
        )
        self.status_label.pack(fill=tk.X, padx=5)

        # Create chat container
        chat_container = ttk.Frame(self.chat_frame)
        chat_container.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for chat container
        chat_container.grid_columnconfigure(0, weight=1)
        chat_container.grid_rowconfigure(0, weight=1)
        chat_container.grid_rowconfigure(1, weight=0)

        # Chat display with reduced height
        self.chat_display = scrolledtext.ScrolledText(
            chat_container,
            wrap=tk.WORD,
            font=self.chat_font,
            height=10  # Shows approximately 10 lines
        )
        self.chat_display.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        # Input frame
        self.input_frame = ttk.Frame(chat_container)
        self.input_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=5)

        # Configure input frame grid
        self.input_frame.grid_columnconfigure(0, weight=1)

        # Chat input
        self.chat_input = ttk.Entry(
            self.input_frame,
            font=self.chat_font
        )
        self.chat_input.grid(row=0, column=0, sticky='ew')

        # Bind keys
        self.chat_input.bind("<Return>", lambda e: self.handle_input())
        self.chat_input.bind("<Up>", self.handle_up_key)
        self.chat_input.bind("<Down>", self.handle_down_key)
        
        # Add focus and unfocus bindings to chat input
        self.chat_input.bind("<FocusIn>", self.on_input_focus)
        self.chat_input.bind("<FocusOut>", self.on_input_unfocus)
        self.chat_input.bind("<Key>", self.reset_focus_timer)

        # Keyboard shortcuts
        for widget in (self.master, self.chat_input):
            widget.bind('`', lambda e: self.toggle_recording())
            widget.bind('<Control-q>', lambda e: self.exit_program())


    def on_input_focus(self, event=None):
        """Handle input focus event"""
        self.is_input_focused = True
        self.start_focus_timer()
        print("[DEBUG] Input focused")

    def on_input_unfocus(self, event=None):
        """Handle input unfocus event"""
        self.is_input_focused = False
        if self.input_focus_timer:
            self.master.after_cancel(self.input_focus_timer)
            self.input_focus_timer = None
        print("[DEBUG] Input unfocused")

    def reset_focus_timer(self, event=None):
        """Reset the focus timer when user types or clicks buttons"""
        if event.keysym != 'grave':  # Don't reset for backtick key
            self.start_focus_timer()

    def start_focus_timer(self):
        """Start or restart the focus timer"""
        if self.input_focus_timer:
            self.master.after_cancel(self.input_focus_timer)
        self.input_focus_timer = self.master.after(3000, self.auto_unfocus)
        print("[DEBUG] Focus timer started/reset")

    def auto_unfocus(self):
        """Automatically unfocus the input after timer expires"""
        self.is_input_focused = False
        self.input_focus_timer = None
        self.master.focus_set()  # Move focus to main window
        print("[DEBUG] Auto unfocused due to timer")

    def handle_backtick(self, event):
        """Handle backtick key press"""
        if not self.is_input_focused:
            self.toggle_recording()
            return "break"  # Prevent the backtick from appearing in input
        return None  # Allow backtick in input when focused

    def handle_input(self):
        """Modified handle_input method"""
        user_input = self.chat_input.get().strip()
        if not user_input:
            return
        
        # Reset focus after sending message
        self.is_input_focused = False
        if self.input_focus_timer:
            self.master.after_cancel(self.input_focus_timer)
            self.input_focus_timer = None

    def on_model_change(self):
        """Handle AI model selection change"""
        selected_model = self.model_var.get()
        print(f"[DEBUG] Model selection changed in UI to: {selected_model}")
        try:
            self.conversation_manager.set_ai_model(selected_model)
            self.update_status(f"Switched to {selected_model}")
            print(f"[DEBUG] Successfully switched conversation manager to {selected_model}")
        except Exception as e:
            print(f"[DEBUG] Error switching model in UI: {str(e)}")
            self.update_status(f"Error switching to {selected_model}: {str(e)}")

    def create_font_control(self):
        # Create frame for font size control
        font_control_frame = ttk.Frame(self.main_container)
        font_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Label for the slider
        font_label = ttk.Label(
            font_control_frame,
            text="Chat Text Size:"
        )
        font_label.pack(side=tk.LEFT, padx=5)
        
        # Create the slider
        self.font_size_var = tk.IntVar(value=self.current_font_size)
        self.font_slider = ttk.Scale(
            font_control_frame,
            from_=12,
            to=24,
            orient=tk.HORIZONTAL,
            variable=self.font_size_var,
            command=self.update_font_size
        )
        self.font_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Display current font size
        self.font_size_label = ttk.Label(
            font_control_frame,
            text=str(self.current_font_size)
        )
        self.font_size_label.pack(side=tk.LEFT, padx=5)

    def update_font_size(self, *args):
        new_size = self.font_size_var.get()
        self.current_font_size = new_size
        self.chat_font.configure(size=new_size)
        self.font_size_label.configure(text=str(new_size))
        
        # Update text tags with new font size
        self.setup_text_tags()
        
        # Update font for both chat display and input area
        self.chat_display.configure(font=self.chat_font)
        self.chat_input.configure(font=self.chat_font)
        
        
        # Adjust chat display height - maintain about 10 lines of text
        # As font gets bigger, reduce number of lines to maintain reasonable height
        if new_size <= 12:
            display_height = 10
        elif new_size <= 16:
            display_height = 8
        elif new_size <= 20:
            display_height = 6
        else:
            display_height = 5
  

        # Adjust chat display height based on font size
        # This helps maintain the input area visibility
        #base_height = 20  # Base height for font size 12
        #adjusted_height = max(10, int(base_height * (12 / new_size)))  # Minimum height of 10
        
        #self.chat_display.configure(height=adjusted_height)
        self.chat_display.configure(height=display_height)

        # Force update of the display
        self.master.update_idletasks()


    def handle_up_key(self, event):
        if len(self.command_history) > 0:
            if self.history_index < len(self.command_history):
                self.history_index += 1
                self.chat_input.delete(0, tk.END)
                self.chat_input.insert(0, self.command_history[-self.history_index])

    def handle_down_key(self, event):
        if self.history_index > 0:
            self.history_index -= 1
            self.chat_input.delete(0, tk.END)
            if self.history_index > 0:
                self.chat_input.insert(0, self.command_history[-self.history_index])
    
    def display_welcome_message(self):
        welcome_message = """Welcome! I'm your AI assistant. I can help you with questions in English, Japanese, Chinese, 
and particularly with topics related to Sciense, Math, Medical, Engineering, Christianity and the Bible.

Camera Commands:
- "what is this?" or "what is that?" - Analyze the current camera view
- "camera 1" or "take photo" - Capture and analyze the camera view
- "take photo" - Take a high-resolution photo (saves to Pictures folder)

Other Commands:
Type 'quit', 'exit', or 'bye' to end the program, or use the Exit button.

Keyboard shortcuts:
` (Backtick) - Toggle Recording
Enter/Return - Send Message
Ctrl+Q  - Exit Program
Esc - Stop AI's talking

How can I help you today?
"""
        self.chat_display.insert(tk.END, welcome_message)
        self.chat_display.see(tk.END)

    
    def start_preview_thread(self):
        """Start preview thread for the camera"""
        if self.camera:
            self.preview_queue = queue.Queue()
            threading.Thread(
                target=self.capture_preview_loop,
                args=(self.camera, self.preview_queue),
                daemon=True
            ).start()
            
            self.update_preview_canvas()



    def capture_preview_loop(self, camera, preview_queue):
        while self.running:
            try:
                frame = camera.capture_array()
                if frame is not None:
                    image = Image.fromarray(frame)
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                    image = image.resize((426, 240), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image=image)
                    preview_queue.put(photo)
                else:
                    print("[DEBUG] Empty frame from camera")
                
            except Exception as e:
                print(f"[DEBUG] Error capturing preview: {e}")
                time.sleep(0.1)
        
            time.sleep(0.033)  # ~30 FPS


    def update_preview_canvas(self):
        """Update preview canvas for camera"""
        try:
            if hasattr(self, 'preview_queue') and not self.preview_queue.empty():
                photo = self.preview_queue.get_nowait()
                if photo:
                    self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                    self.preview_canvas.image = photo
                    
        except Exception as e:
            print(f"[DEBUG] Error updating preview canvas: {e}")
    
        if self.running:
            self.master.after(33, self.update_preview_canvas)



    def update_status(self, message):
        self.status_label.config(text=message)
        if message in ("---",
                       "Switched to ChatGPT", 
                       "Switched to Claude", 
                       "Switched to Gemini", 
                       "Switched to Grok", 
                       "Switched to Perplexity", 
                       "Recording audio...", "Generating speech"): # "Processing audio...", "Playing audio..."):
            self.record_button.configure(state=tk.NORMAL)#DISABLED)
        else:
            self.record_button.configure(state=tk.DISABLED)#NORMAL) # This enables the button
        self.master.update_idletasks()

    def handle_input(self):
        user_input = self.chat_input.get().strip()
        if not user_input:
            return
        
        # Add to command history
        self.command_history.append(user_input)
        self.history_index = 0
        
        # Clear input field
        self.chat_input.delete(0, tk.END)
        
        # Display user input
        #self.chat_display.insert(tk.END, f"\nYou: {user_input}\n")
        #self.chat_display.see(tk.END)
        # Display user input with color
        self.insert_colored_message("human", user_input)

        # Check for exit commands
        if user_input.lower() in ['quit', 'exit', 'bye']:
            self.exit_program()
            return
    
        # Get current model name
        current_model = self.conversation_manager.current_model.get_model_name()
        
        image_path = None
        if ("camera" in user_input.lower() or
            "what is this" in user_input.lower() or
            "what is that" in user_input.lower()) and self.camera:
            self.update_status("Processing image... Please wait.")
            image_path = CameraManager.capture_and_convert(self.camera)
            if not image_path:
                self.insert_colored_message("system", "Error capturing image.")
                return


        # Get response from GPT
        response = self.conversation_manager.get_response(
            user_input,
            status_callback=self.update_status
        )
        
        # Display AI response with appropriate color
        self.insert_colored_message(current_model, response)

        
        # Clear status
        self.update_status("")

   
    def cleanup(self):
        """Safely cleanup resources"""
        print("[DEBUG] Starting cleanup...")
        self.running = False
    
        if self.camera:
            try:
                print("[DEBUG] Stopping camera...")
                self.camera.stop()
                self.camera.close()
                print("[DEBUG] Camera stopped")
            except Exception as e:
                print(f"[DEBUG] Error stopping camera: {e}")
    
        print("[DEBUG] Cleanup completed")



    def exit_program(self):
        """Safely exit the program"""
        print("[DEBUG] Exiting program...")
        try:
            self.cleanup()
        except Exception as e:
            print(f"[DEBUG] Error during cleanup: {e}")
        finally:
            self.master.quit()
            self.master.destroy()
    

    def toggle_recording(self):
        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.record_button.configure(bg='red', activebackground='dark red')
            self.update_status("Recording audio...")
            self.audio_data = []
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()
        else:
            # Stop recording
            self.is_recording = False
            self.record_button.configure(bg='light gray', activebackground='gray')
            self.update_status("Processing audio...")
            if self.recording_thread:
                self.recording_thread.join()
            self.save_and_transcribe_audio()

    def record_audio(self):
        """Record audio in chunks while is_recording is True."""
        try:
            with sd.InputStream(channels=1, samplerate=self.sample_rate, dtype='float32') as stream:
                while self.is_recording:
                    audio_chunk, _ = stream.read(self.sample_rate)
                    self.audio_data.append(audio_chunk)
        except Exception as e:
            print(f"Error recording audio: {e}")
            self.update_status(f"Error recording audio: {e}")
            self.is_recording = False
            self.master.after(0, lambda: self.record_button.configure(
                bg='light gray', 
                activebackground='gray'
            ))

    def save_and_transcribe_audio(self):
        """Save recorded audio to MP3 and transcribe it."""
        try:
            if not self.audio_data:
                self.update_status("No audio recorded")
                return

            # Combine all audio chunks
            combined_audio = np.concatenate(self.audio_data)
            
            # Convert to AudioSegment
            audio_segment = AudioSegment(
                (combined_audio * 32767).astype(np.int16).tobytes(),
                frame_rate=self.sample_rate,
                sample_width=2,
                channels=1
            )
            
            # Save as MP3
            output_path = Path("/tmp") / f"recording_{int(time.time())}.mp3"
            audio_segment.export(str(output_path), format="mp3")
            
            # Transcribe audio
            self.update_status("Transcribing audio...")
            with open(output_path, "rb") as audio_file:
                transcription = self.conversation_manager.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Convert to traditional Chinese if needed and display
            transcribed_text = self.converter.convert(transcription.text)
            self.chat_input.insert(0, transcribed_text)
            self.update_status("")
            
            # Clean up
            if output_path.exists():
                os.remove(output_path)

            # Automatically trigger send after a short delay (to ensure UI is updated)
            self.master.after(100, self.handle_input) #delay 100ms to trigger the Send button

            
        except Exception as e:
            print(f"Error processing audio: {e}")
            self.update_status(f"Error processing audio: {e}")


    def stop_audio(self, event=None):
        """
        Stop audio playback when Escape is pressed.
        """
        try:
            self.conversation_manager.tts_manager.stop_playback()
            self.update_status("")
        except Exception as e:
            print(f"Error stopping audio: {e}")
            self.update_status("Error stopping audio")
    
        # Ensure the UI remains responsive
        self.master.update()

    def setup_text_tags(self):
        """Configure text tags for color coding messages"""
        for participant, color in self.chat_colors.items():
            self.chat_display.tag_configure(
                participant,
                foreground=color,
                font=(self.chat_font.actual('family'),
                      self.chat_font.actual('size'),
                      'bold')  # Make speaker names bold
            )
            # Add a tag for the message text itself (not bold)
            self.chat_display.tag_configure(
                f"{participant}_text",
                foreground=color,
                font=(self.chat_font.actual('family'),
                      self.chat_font.actual('size'))
            )

    def insert_colored_message(self, speaker: str, message: str):
        """Insert a color-coded message into the chat display"""
        # Get the appropriate color tag
        tag = speaker if speaker in self.chat_colors else 'human'

        # Insert speaker label with bold colored font
        if speaker == "human":
            speaker_text = "You: "
        else:
            speaker_text = f"{speaker}: "

        self.chat_display.insert(tk.END, f"\n{speaker_text}", tag)

        # Insert message with colored but not bold font
        self.chat_display.insert(tk.END, f"{message}\n", f"{tag}_text")

        # Ensure the latest message is visible
        self.chat_display.see(tk.END)

