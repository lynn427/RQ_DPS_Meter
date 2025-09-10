import time
import tkinter as tk
from PIL import ImageGrab, Image
import pytesseract
import re
import hashlib
import os
import sys

# 🔍 Detect bundled path and load tesseract from 'tesseract-portable'
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

tesseract_path = os.path.join(base_path, 'tesseract-portable', 'tesseract.exe')
pytesseract.pytesseract.tesseract_cmd = tesseract_path


class OCRDPSMeter:
    def __init__(self, root):
        self.root = root
        self.root.title("Royal Quest DPS Meter (OCR)")

        # Internal state
        self.region = (1000, 800, 1300, 1000)
        self.total_damage = 0
        self.last_read_lines = set()
        self.running = False
        self.start_time = None
        self.total_active_time = 0

        # GUI elements
        self.dps_label = tk.Label(root, text="DPS: 0.00", font=("Arial", 16))
        self.dps_label.pack(pady=10)

        self.damage_label = tk.Label(root, text="Total Damage: 0", font=("Arial", 12))
        self.damage_label.pack(pady=5)

        self.region_label = tk.Label(root, text=f"Region: {self.region}", font=("Arial", 10))
        self.region_label.pack(pady=5)

        self.toggle_button = tk.Button(root, text="Start", width=12, command=self.toggle_tracking)
        self.toggle_button.pack(pady=5)

        self.set_region_button = tk.Button(root, text="Set Chat Region", command=self.open_region_selector)
        self.set_region_button.pack(pady=5)

        self.reset_button = tk.Button(root, text="Reset", command=self.reset)
        self.reset_button.pack(pady=10)

        self.update_loop()

    def reset(self):
        self.total_damage = 0
        self.last_read_lines = set()
        self.total_active_time = 0
        self.start_time = time.time() if self.running else None
        self.dps_label.config(text="DPS: 0.00")
        self.damage_label.config(text="Total Damage: 0")

    def toggle_tracking(self):
        if self.running:
            self.running = False
            if self.start_time:
                self.total_active_time += time.time() - self.start_time
            self.toggle_button.config(text="Start")
        else:
            self.running = True
            self.start_time = time.time()
            self.toggle_button.config(text="Stop")

    def read_combat_text(self):
        img = ImageGrab.grab(bbox=self.region)
        gray = img.convert("L")
        text = pytesseract.image_to_string(gray)
        return text

    def extract_damage(self, text):
        lines = text.splitlines()
        damage_this_tick = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_hash = hashlib.md5(line.encode()).hexdigest()
            if line_hash in self.last_read_lines:
                continue

            self.last_read_lines.add(line_hash)

            matches = re.findall(r'\b\d{2,5}\b', line)
            for match in matches:
                dmg = int(match)
                if 10 <= dmg <= 99999:
                    damage_this_tick += dmg

        return damage_this_tick

    def get_elapsed_time(self):
        if self.running and self.start_time:
            return self.total_active_time + (time.time() - self.start_time)
        else:
            return self.total_active_time

    def get_dps(self):
        elapsed = self.get_elapsed_time()
        return self.total_damage / elapsed if elapsed > 0 else 0

    def update_loop(self):
        if self.running:
            try:
                text = self.read_combat_text()
                damage = self.extract_damage(text)
                self.total_damage += damage
            except Exception as e:
                print("OCR Error:", e)

        dps = self.get_dps()
        self.dps_label.config(text=f"DPS: {dps:.2f}")
        self.damage_label.config(text=f"Total Damage: {self.total_damage}")
        self.region_label.config(text=f"Region: {self.region}")

        self.root.after(1000, self.update_loop)

    def open_region_selector(self):
        selector = tk.Toplevel(self.root)
        selector.attributes("-fullscreen", True)
        selector.attributes("-alpha", 0.3)
        selector.configure(bg='black')
        selector.lift()
        selector.attributes("-topmost", True)

        canvas = tk.Canvas(selector, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)

        self.sel_start = None
        self.rect = None

        def on_mouse_down(event):
            self.sel_start = (event.x_root, event.y_root)
            if self.rect:
                canvas.delete(self.rect)

        def on_mouse_drag(event):
            if self.sel_start:
                x0, y0 = self.sel_start
                x1, y1 = event.x_root, event.y_root
                if self.rect:
                    canvas.delete(self.rect)
                self.rect = canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline='red',
                    width=2
                )

        def on_mouse_up(event):
            if self.sel_start:
                x0, y0 = self.sel_start
                x1, y1 = event.x_root, event.y_root
                left = min(x0, x1)
                top = min(y0, y1)
                right = max(x0, x1)
                bottom = max(y0, y1)
                self.region = (left, top, right, bottom)
                self.region_label.config(text=f"Region: {self.region}")
            selector.destroy()

        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)


# --- MAIN ---
if __name__ == "__main__":
    root = tk.Tk()
    app = OCRDPSMeter(root)
    root.mainloop()
