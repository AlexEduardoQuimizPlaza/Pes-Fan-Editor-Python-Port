"""
PES Editor 6 - Python Port
Entry point.

Requirements:
    - Python 3.8+
    - tkinter (included with standard Python)
    - Pillow (optional, for image import/export): pip install Pillow

Usage:
    python main.py
"""
import sys
import os

# Add project directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
