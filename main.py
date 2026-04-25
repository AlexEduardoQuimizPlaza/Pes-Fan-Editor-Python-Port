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
    _frozen = getattr(sys, 'frozen', False)
    missing = []

    try:
        import tkinter  # noqa: F401
    except ImportError:
        if _frozen:
            missing.append("tkinter no está disponible. Descarga de nuevo el ejecutable.")
        else:
            missing.append(
                "tkinter is missing.\n"
                "  Debian/Ubuntu/Mint: sudo apt install python3-tk\n"
                "  Fedora:             sudo dnf install python3-tkinter"
            )

    try:
        from PIL import Image, ImageTk  # noqa: F401
    except ImportError:
        if _frozen:
            missing.append("Pillow no está disponible. Descarga de nuevo el ejecutable.")
        else:
            missing.append(
                "Pillow with ImageTk is missing.\n"
                "  pip install -r requirements.txt"
            )

    if missing:
        msg = "No se puede iniciar PES Editor:\n\n" + "\n\n".join(missing)
        print(msg, file=sys.stderr)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("PES Editor — error al iniciar", msg)
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
