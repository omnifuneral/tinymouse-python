import sys
import platform
import threading
import time
import random
import pyautogui
import json
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QLineEdit, QCheckBox, QListWidget, QFileDialog, QRadioButton, QHBoxLayout, QComboBox, QDialog, QTextEdit
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QTimer

# Platform-specific hotkey imports
if platform.system() == "Linux":
    from Xlib import X, display
    from Xlib import XK
else:
    from pynput import keyboard

class TinyMouseApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_data()
        self.init_hotkeys()

    def init_ui(self):
        """Initialize the user interface and layout."""
        self.setWindowTitle("TinyMouse")
        self.setGeometry(100, 100, 600, 500)
        self.setWindowIcon(QIcon("tinymouse_icon.png"))

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Click Coordinates (x, y):"))
        self.coords_input = QLineEdit()
        layout.addWidget(self.coords_input)

        layout.addWidget(QLabel("Delay between clicks (ms):"))
        self.delay_input = QLineEdit()
        layout.addWidget(self.delay_input)

        self.randomize_checkbox = QCheckBox("Randomize delay slightly")
        layout.addWidget(self.randomize_checkbox)

        self.add_click_button = QPushButton("Add Click")
        self.add_click_button.clicked.connect(self.add_click)
        layout.addWidget(self.add_click_button)

        self.select_position_button = QPushButton("Select Position via Click")
        self.select_position_button.clicked.connect(self.select_position)
        layout.addWidget(self.select_position_button)

        self.click_list = QListWidget()
        layout.addWidget(self.click_list)

        self.save_profile_button = QPushButton("Save Profile")
        self.save_profile_button.clicked.connect(self.save_profile)
        layout.addWidget(self.save_profile_button)

        self.load_profile_button = QPushButton("Load Profile")
        self.load_profile_button.clicked.connect(self.load_profile)
        layout.addWidget(self.load_profile_button)

        repeat_layout = QHBoxLayout()
        self.repeat_number_radio = QRadioButton("Repeat by number")
        self.repeat_number_input = QLineEdit()
        repeat_layout.addWidget(self.repeat_number_radio)
        repeat_layout.addWidget(self.repeat_number_input)

        self.repeat_time_radio = QRadioButton("Repeat for time (seconds)")
        self.repeat_time_input = QLineEdit()
        repeat_layout.addWidget(self.repeat_time_radio)
        repeat_layout.addWidget(self.repeat_time_input)
        layout.addLayout(repeat_layout)

        layout.addWidget(QLabel("Theme:"))
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Light", "Dark", "Retro Terminal", "Solarized Dark", "Solarized Light"])
        self.theme_selector.currentIndexChanged.connect(self.change_theme)
        layout.addWidget(self.theme_selector)

        self.start_button = QPushButton("Start Clicking")
        self.start_button.clicked.connect(self.start_clicking)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Clicking")
        self.stop_button.clicked.connect(self.stop_clicking)
        layout.addWidget(self.stop_button)

        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.show_help)
        layout.addWidget(self.help_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def init_data(self):
        """Initialize data structures and variables."""
        self.actions = []
        self.clicking = False
        self.current_repeat = 0
        self.max_repeats = 1
        self.start_time = None
        self.click_thread = None

    def init_hotkeys(self):
        """Initialize hotkey functionality based on the platform."""
        if platform.system() == "Linux":
            self.setup_linux_hotkeys()
        else:
            self.setup_other_hotkeys()

    def setup_linux_hotkeys(self):
        """Set up hotkeys for Linux (X11)."""
        self.hotkey_listener_thread = threading.Thread(target=self.listen_for_linux_hotkeys)
        self.hotkey_listener_thread.do_run = True
        self.hotkey_listener_thread.start()

    def listen_for_linux_hotkeys(self):
        """Listen for hotkey presses on Linux using Xlib."""
        d = display.Display()
        root = d.screen().root
        start_key = (X.ControlMask | X.Mod1Mask, d.keysym_to_keycode(XK.XK_S))
        stop_key = (X.ControlMask | X.Mod1Mask, d.keysym_to_keycode(XK.XK_Q))

        root.grab_key(start_key[1], start_key[0], True, X.GrabModeAsync, X.GrabModeAsync)
        root.grab_key(stop_key[1], stop_key[0], True, X.GrabModeAsync, X.GrabModeAsync)

        while getattr(self.hotkey_listener_thread, "do_run", True):
            if d.pending_events():
                event = root.display.next_event()
                if event.type == X.KeyPress:
                    keycode = event.detail
                    if keycode == start_key[1]:
                        self.start_clicking()
                    elif keycode == stop_key[1]:
                        self.stop_clicking()

            time.sleep(0.1)

        d.close()

    def setup_other_hotkeys(self):
        """Set up hotkeys for Windows and macOS using pynput."""
        def on_press(key):
            try:
                if key == keyboard.HotKey.parse('<ctrl>+<alt>+s'):
                    self.start_clicking()
                elif key == keyboard.HotKey.parse('<ctrl>+<alt>+q'):
                    self.stop_clicking()
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    def add_click(self):
        """Add a click action based on user input."""
        coords = self.coords_input.text().split(',')
        delay = int(self.delay_input.text()) if self.delay_input.text().isdigit() else 1000
        try:
            x, y = int(coords[0].strip()), int(coords[1].strip())
            self.actions.append({"x": x, "y": y, "delay": delay})
            self.click_list.addItem(f"Click at ({x}, {y}) with {delay}ms delay")
            print(f"[INFO] Added click at ({x}, {y}) with delay {delay}ms")
        except (ValueError, IndexError):
            print("[ERROR] Invalid coordinates input.")

    def save_profile(self):
        """Save the current click profile to a .tiny file."""
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Profile", "", "TinyMouse Files (*.tiny)")
        if file_name:
            with open(file_name, 'w') as file:
                json.dump(self.actions, file)
            print(f"[INFO] Profile saved to {file_name}")

    def load_profile(self):
        """Load a click profile from a .tiny file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Profile", "", "TinyMouse Files (*.tiny)")
        if file_name:
            with open(file_name, 'r') as file:
                self.actions = json.load(file)
            self.click_list.clear()
            for action in self.actions:
                self.click_list.addItem(f"Click at ({action['x']}, {action['y']}) with {action['delay']}ms delay")
            print(f"[INFO] Loaded profile from {file_name}")

    def select_position(self):
        """Hide the window, wait for 2 seconds, and capture the mouse position."""
        self.hide()
        time.sleep(2)
        x, y = pyautogui.position()
        self.show()
        self.coords_input.setText(f"{x}, {y}")
        print(f"[INFO] Selected position ({x}, {y})")

    def start_clicking(self):
        """Start the clicking process."""
        if not self.clicking:
            self.clicking = True
            self.current_repeat = 0
            self.max_repeats = int(self.repeat_number_input.text()) if self.repeat_number_radio.isChecked() else None
            self.start_time = time.time() if self.repeat_time_radio.isChecked() else None
            self.hide()
            print("[INFO] Starting clicking...")
            self.click_thread = threading.Thread(target=self.perform_click_cycle)
            self.click_thread.start()

    def perform_click_cycle(self):
        """Perform the click actions in a loop."""
        try:
            while self.clicking and (self.max_repeats is None or self.current_repeat < self.max_repeats):
                for action in self.actions:
                    if not self.clicking:
                        break
                    x, y, delay = action['x'], action['y'], action['delay']
                    if self.randomize_checkbox.isChecked():
                        delay += random.randint(-100, 100)
                    pyautogui.moveTo(x, y)
                    pyautogui.click()
                    print(f"[INFO] Clicked at ({x}, {y}) with {delay}ms delay")
                    time.sleep(delay / 1000)
                self.current_repeat += 1
                if self.repeat_time_radio.isChecked() and time.time() - self.start_time >= int(self.repeat_time_input.text()):
                    break
        finally:
            self.stop_clicking(final=True)

    def stop_clicking(self, final=False):
        """Stop the clicking process and restore the window."""
        self.clicking = False
        if final:
            self.show()
        print("[INFO] Stopped clicking.")

    def change_theme(self):
        """Change the theme based on the user's selection."""
        theme = self.theme_selector.currentText()
        themes = {
            "Light": "background-color: white; color: black;",
            "Dark": "background-color: black; color: white;",
            "Retro Terminal": "background-color: black; color: #00FF00;",
            "Solarized Dark": "background-color: #002b36; color: #839496;",
            "Solarized Light": "background-color: #fdf6e3; color: #657b83;"
        }
        self.setStyleSheet(themes.get(theme, ""))
        print(f"[INFO] Theme changed to {theme}")

    def show_help(self):
        """Show the help dialog."""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.resize(500, 400)
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setFont(QFont("Courier", 10))
        help_text.setText("""
        Welcome to TinyMouse!

        Features:
        - Customize your click locations and delays.
        - Save and load profiles for your click patterns.
        - Choose between repeating by number of cycles or by time.
        - Themes: Select between Light, Dark, Retro Terminal, and Solarized themes.
        - Randomize delay slightly to avoid detection.

        Default Hotkeys:
        - Ctrl+Alt+S: Start clicking
        - Ctrl+Alt+Q: Stop clicking

        To add a click action:
        1. Enter the coordinates (x, y) and delay between clicks in milliseconds.
        2. Click "Add Click" or "Select Position via Click" to capture the coordinates.
        
        Enjoy automating your clicks with TinyMouse!
        """)
        layout = QVBoxLayout()
        layout.addWidget(help_text)
        help_dialog.setLayout(layout)
        help_dialog.exec_()

    def closeEvent(self, event):
        """Handle application close event and clean up threads."""
        self.stop_clicking(final=True)
        if platform.system() == "Linux" and hasattr(self, 'hotkey_listener_thread'):
            self.hotkey_listener_thread.do_run = False
            self.hotkey_listener_thread.join(timeout=2)
        print("[INFO] Exiting TinyMouse...")
        QApplication.quit()
        os._exit(0)

# Main function to run the app
def main():
    app = QApplication(sys.argv)
    window = TinyMouseApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

