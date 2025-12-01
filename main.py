import tkinter as tk
from tkinter import ttk
import threading
import time
import webbrowser
from pynput import mouse, keyboard
import pyautogui
import os
import sys  # Added sys for internal path checking

# Configuration for PyAutoGUI
pyautogui.FAILSAFE = True

# --- Resource Path Helper ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class YTCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Playlist Wiper")
        self.root.geometry("280x450")
        self.root.configure(bg="#1f1f1f")
        
        # --- Set App Icon (Fixed for EXE) ---
        try:
            # Use the helper function to find the icon whether in dev or exe
            icon_file = resource_path("app_icon.ico")
            self.root.iconbitmap(icon_file)
        except Exception as e:
            print(f"Icon load error: {e}")

        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)

        # State Variables
        self.recorded_steps = []
        self.is_recording = False
        self.is_running = False
        self.stop_requested = False
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # DONATION LINK
        self.donation_url = "https://www.paypal.com/paypalme/mattchoo2" 

        # Setup UI
        self._setup_styles()
        self._create_widgets()
        
        # Start Global Listener for F2/F3
        self._start_keyboard_listener()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Dark Theme Configuration
        style.configure("TLabel", background="#1f1f1f", foreground="#eee", font=("Segoe UI", 9))
        style.configure("Header.TLabel", background="#222", foreground="#fff", font=("Segoe UI", 10, "bold"))
        style.configure("Warning.TLabel", background="#1f1f1f", foreground="#ffcc00", font=("Segoe UI", 8, "bold"))
        
        style.configure("TButton", background="#333", foreground="white", borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", "#444")])
        
        style.configure("Primary.TButton", background="#3ea6ff")
        style.map("Primary.TButton", background=[("active", "#2c95dd")])
        
        style.configure("Danger.TButton", background="#cc0000")
        style.map("Danger.TButton", background=[("active", "#aa0000")])
        
        # Coffee Button Style
        style.configure("Coffee.TButton", background="#FFDD00", foreground="#000000", font=("Segoe UI", 9, "bold"))
        style.map("Coffee.TButton", background=[("active", "#FFEA00")])

    def _create_widgets(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#222", pady=10)
        header_frame.pack(fill="x")
        ttk.Label(header_frame, text="Playlist Wiper", style="Header.TLabel").pack()

        # Main Body
        body_frame = tk.Frame(self.root, bg="#1f1f1f", padx=15, pady=10)
        body_frame.pack(fill="both", expand=True)

        # Warning Note
        ttk.Label(body_frame, text="⚠️ TIP: Manually sort playlist", style="Warning.TLabel").pack(pady=(0, 2))
        ttk.Label(body_frame, text="\"Oldest to Newest\" before starting!", style="Warning.TLabel").pack(pady=(0, 10))

        # Instructions
        instr_frame = tk.Frame(body_frame, bg="#2a2a2a", padx=5, pady=5)
        instr_frame.pack(fill="x", pady=5)
        ttk.Label(instr_frame, text="1. F2 to Start/Stop Recording", background="#2a2a2a").pack()
        ttk.Label(instr_frame, text="(Click '3 dots' -> 'Remove' -> F2 again)", background="#2a2a2a", foreground="#aaa", font=("Segoe UI", 8)).pack()

        # Status Box
        self.status_var = tk.StringVar(value="Ready. Press F2 to record.")
        self.status_label = tk.Label(body_frame, textvariable=self.status_var, bg="#121212", fg="#888", 
                                     font=("Consolas", 9), padx=5, pady=5, relief="flat", borderwidth=1)
        self.status_label.pack(fill="x", pady=10)

        # Reset Button
        ttk.Button(body_frame, text="Reset Macro", command=self.reset_macro).pack(fill="x", pady=(0, 10))

        # Inputs
        input_frame = tk.Frame(body_frame, bg="#1f1f1f")
        input_frame.pack(fill="x", pady=5)
        
        # Repeats
        tk.Label(input_frame, text="Repeats:", bg="#1f1f1f", fg="#aaa", font=("Segoe UI", 9)).grid(row=0, column=0, padx=5)
        self.repeats_entry = tk.Entry(input_frame, bg="#121212", fg="white", width=5, justify="center")
        self.repeats_entry.insert(0, "10")
        self.repeats_entry.grid(row=0, column=1, padx=5)

        # Gap
        tk.Label(input_frame, text="Gap (s):", bg="#1f1f1f", fg="#aaa", font=("Segoe UI", 9)).grid(row=0, column=2, padx=5)
        self.gap_entry = tk.Entry(input_frame, bg="#121212", fg="white", width=5, justify="center")
        self.gap_entry.insert(0, "2.0")
        self.gap_entry.grid(row=0, column=3, padx=5)

        # Control Buttons
        btn_frame = tk.Frame(body_frame, bg="#1f1f1f")
        btn_frame.pack(fill="x", pady=15)
        
        self.start_btn = ttk.Button(btn_frame, text="Run Loop (F3)", style="Primary.TButton", command=self.start_loop)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop (F3)", style="Danger.TButton", command=self.stop_loop)
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        self.stop_btn.state(['disabled'])

        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(body_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        
        self.progress_label = ttk.Label(body_frame, text="0%", foreground="#888")
        self.progress_label.pack()

        # --- Donation Button ---
        ttk.Separator(body_frame, orient='horizontal').pack(fill='x', pady=(15, 10))
        self.coffee_btn = ttk.Button(body_frame, text="☕ Buy me a Coffee", style="Coffee.TButton", command=self.open_donation)
        self.coffee_btn.pack(fill="x")

    # --- Logic ---

    def open_donation(self):
        webbrowser.open(self.donation_url)

    def _start_keyboard_listener(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

    def on_key_press(self, key):
        if key == keyboard.Key.f2:
            self.root.after(0, self.toggle_recording)
        elif key == keyboard.Key.f3:
            if self.is_running:
                self.root.after(0, self.stop_loop)
            elif self.recorded_steps and not self.is_recording:
                self.root.after(0, self.start_loop)

    def toggle_recording(self):
        if self.is_running: return

        self.is_recording = not self.is_recording
        
        if self.is_recording:
            self.recorded_steps = []
            self.status_var.set("RECORDING... (Click target)")
            self.status_label.config(fg="#ff4e45", bg="#330000")
            self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
            self.mouse_listener.start()
        else:
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
            
            count = len(self.recorded_steps)
            self.status_var.set(f"Saved {count} clicks. Ready.")
            self.status_label.config(fg="#2ba640", bg="#002200")

    def on_mouse_click(self, x, y, button, pressed):
        if not self.is_recording or not pressed:
            return

        win_x = self.root.winfo_x()
        win_y = self.root.winfo_y()
        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()

        if win_x <= x <= win_x + win_w and win_y <= y <= win_y + win_h:
            return 

        self.recorded_steps.append({'x': x, 'y': y, 'button': str(button)})
        self.root.after(0, lambda: self.status_var.set(f"Recorded Step {len(self.recorded_steps)}"))

    def reset_macro(self):
        self.recorded_steps = []
        self.is_recording = False
        self.status_var.set("Macro cleared. Press F2.")
        self.status_label.config(fg="#888", bg="#121212")

    def start_loop(self):
        if not self.recorded_steps:
            self.status_var.set("Error: No steps recorded!")
            return
        
        if self.is_running: return 
        
        try:
            repeats = int(self.repeats_entry.get())
            gap = float(self.gap_entry.get())
        except ValueError:
            self.status_var.set("Error: Invalid inputs")
            return

        self.is_running = True
        self.stop_requested = False
        self.update_ui_state(running=True)
        threading.Thread(target=self.run_automation, args=(repeats, gap), daemon=True).start()

    def stop_loop(self):
        self.stop_requested = True
        self.status_var.set("Stopping...")

    def run_automation(self, repeats, gap):
        for i in range(repeats):
            if self.stop_requested:
                break
            
            percentage = int(((i + 1) / repeats) * 100)
            self.root.after(0, lambda p=percentage, c=i+1: self._update_progress(p, c, repeats))
            
            for step in self.recorded_steps:
                if self.stop_requested: break
                btn = step['button'].replace('Button.', '')
                pyautogui.click(x=step['x'], y=step['y'], button=btn)
                time.sleep(0.5)

            time.sleep(gap)

        self.is_running = False
        self.root.after(0, lambda: self.update_ui_state(running=False))
        self.root.after(0, lambda: self.status_var.set("Finished!"))

    def _update_progress(self, percent, current, total):
        self.progress_var.set(percent)
        self.progress_label.config(text=f"{percent}% ({current}/{total})")
        self.status_var.set(f"Running Loop {current}/{total}...")

    def update_ui_state(self, running):
        if running:
            self.start_btn.state(['disabled'])
            self.stop_btn.state(['!disabled'])
            self.repeats_entry.config(state='disabled')
            self.gap_entry.config(state='disabled')
            self.coffee_btn.state(['disabled'])
        else:
            self.start_btn.state(['!disabled'])
            self.stop_btn.state(['disabled'])
            self.repeats_entry.config(state='normal')
            self.gap_entry.config(state='normal')
            self.coffee_btn.state(['!disabled'])

    def on_close(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = YTCleanerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()