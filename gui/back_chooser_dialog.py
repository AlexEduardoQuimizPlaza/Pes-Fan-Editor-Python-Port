"""
PES Editor 6 - Python Port
BackChooserDialog — equivale a BackChooserDialog.java.
Muestra una cuadrícula 3×4 con los 12 patrones de bandera
(backflag0.png … backflag11.png) renderizados con los dos
colores del equipo. Devuelve el índice elegido (0-11) o -1 si se cancela.
"""
import os
import tkinter as tk
from tkinter import ttk

_COLS    = 4
_ROWS    = 3
_TOTAL   = 12
_CELL_W  = 85
_CELL_H  = 64
_DATA    = os.path.join(os.path.dirname(__file__), '..', 'data')


def render_flag_pattern(back_idx: int,
                        r1: int, g1: int, b1: int,
                        r2: int, g2: int, b2: int,
                        width: int = _CELL_W,
                        height: int = _CELL_H):
    """
    Devuelve una PIL Image RGBA del patrón back_idx recoloreado:
      píxeles oscuros  → color 1  (r1, g1, b1)
      píxeles claros   → color 2  (r2, g2, b2)
    """
    from PIL import Image
    import numpy as np

    path = os.path.join(_DATA, f'backflag{back_idx}.png')
    raw  = Image.open(path).convert('L')          # escala de grises 0-255
    if raw.size != (width, height):
        raw = raw.resize((width, height), Image.NEAREST)

    arr    = np.array(raw, dtype=np.uint8)         # (H, W)
    mask   = arr > 128                             # True = claro = color2
    result = np.zeros((*arr.shape, 4), dtype=np.uint8)
    result[~mask] = [r1, g1, b1, 255]
    result[ mask] = [r2, g2, b2, 255]
    return Image.fromarray(result, 'RGBA')


class BackChooserDialog(tk.Toplevel):
    def __init__(self, parent, r1, g1, b1, r2, g2, b2):
        super().__init__(parent)
        self.title("Choose Background")
        self.resizable(False, False)
        self._result = -1
        self._photos = []
        self._build(r1, g1, b1, r2, g2, b2)
        self.update_idletasks()
        self.grab_set()

    def _build(self, r1, g1, b1, r2, g2, b2):
        grid = ttk.Frame(self)
        grid.pack(padx=4, pady=4)

        for idx in range(_TOTAL):
            row = idx // _COLS
            col = idx % _COLS
            try:
                from PIL import ImageTk
                img  = render_flag_pattern(idx, r1, g1, b1, r2, g2, b2)
                ph   = ImageTk.PhotoImage(img)
            except Exception:
                ph = None

            btn = tk.Button(grid, width=_CELL_W, height=_CELL_H,
                            relief=tk.RAISED, borderwidth=2,
                            command=lambda i=idx: self._select(i))
            if ph is not None:
                btn.config(image=ph)
                self._photos.append(ph)
            btn.grid(row=row, column=col, padx=1, pady=1)

        ttk.Button(self, text="Cancel",
                   command=self._cancel).pack(fill=tk.X, padx=4, pady=(0, 4))

    def _select(self, idx: int):
        self._result = idx
        self.destroy()

    def _cancel(self):
        self._result = -1
        self.destroy()

    @classmethod
    def choose(cls, parent, r1, g1, b1, r2, g2, b2) -> int:
        """Abre el diálogo modal y devuelve el índice elegido o -1."""
        dlg = cls(parent, r1, g1, b1, r2, g2, b2)
        parent.wait_window(dlg)
        return dlg._result
