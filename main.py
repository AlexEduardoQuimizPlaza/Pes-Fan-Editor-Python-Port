"""
PES Editor 6 - Python Port
Entry point.

Requirements:
    - Python 3.8+
    - tkinter (bundled with standard Python; on Debian/Ubuntu/Mint:
      sudo apt install python3-tk)
    - Pillow with ImageTk (pip install -r requirements.txt, ideally in a venv;
      on Debian/Ubuntu/Mint system Python: sudo apt install python3-pil python3-pil.imagetk)

Usage:
    python main.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _check_dependencies():
    """Fail fast with an actionable message if a required dep is missing."""
    missing = []
    try:
        import tkinter  # noqa: F401
    except ImportError:
        missing.append(
            "tkinter is missing.\n"
            "  Debian/Ubuntu/Mint: sudo apt install python3-tk\n"
            "  Fedora:             sudo dnf install python3-tkinter"
        )

    try:
        from PIL import Image, ImageTk  # noqa: F401
    except ImportError:
        missing.append(
            "Pillow with ImageTk is missing.\n"
            "  Recommended (any OS): python -m venv .venv && "
            "source .venv/bin/activate && pip install -r requirements.txt\n"
            "  Debian/Ubuntu/Mint system Python: "
            "sudo apt install python3-pil python3-pil.imagetk"
        )

    if missing:
        msg = "Cannot start PES Editor — missing dependencies:\n\n" + "\n\n".join(missing)
        print(msg, file=sys.stderr)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("PES Editor — missing dependencies", msg)
            root.destroy()
        except Exception:
            pass
        sys.exit(1)


def main():
    _check_dependencies()
    from gui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
