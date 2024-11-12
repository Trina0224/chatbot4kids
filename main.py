# main.py
from dual_camera_gpt_app import DualCameraGPTApp
import tkinter as tk

def main():
    root = tk.Tk()
    app = DualCameraGPTApp(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_program)
    root.mainloop()

if __name__ == "__main__":
    main()

