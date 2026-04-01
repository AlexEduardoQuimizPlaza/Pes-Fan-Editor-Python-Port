"""
PES Editor 6 - Python Port
EmblemChooserDialog — matches Java EmblemChooserDialog:
  • 10×10 grid  (100 cells)
  • Cells 0 .. count16-1      → 16-colour emblems  (Python idx = cell + 50)
  • Cells 99 .. 100-count128  → 128-colour emblems (Python idx = 99 - cell)
  • Middle cells are shown as empty (gray)
  • Transparency toggle
  • Cancel button
  Returns the clubs emblem value (adj_idx + FIRST_FLAG) or -1 if cancelled.
"""
import tkinter as tk
from tkinter import ttk
import emblems as Emblems
import clubs   as Clubs

_COLS      = 10
_ROWS      = 10
_CELL      = 20      # px per cell
_W         = _COLS * _CELL
_H         = _ROWS * _CELL


class EmblemChooserDialog(tk.Toplevel):
    def __init__(self, parent, of):
        super().__init__(parent)
        self.title("Choose Emblem")
        self.resizable(False, False)
        self._of      = of
        self._result  = -1       # clubs emblem value (-1 = cancelled)
        self._trans   = True     # start in transparency mode (Java default)
        self._photos  = []       # PhotoImage refs
        self._build()
        self.update_idletasks()
        self.grab_set()

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self):
        ttk.Button(self, text="Transparency",
                   command=self._toggle_trans).pack(fill=tk.X, padx=4, pady=2)

        self._canvas = tk.Canvas(self, width=_W, height=_H,
                                  bg="#404040", cursor="hand2")
        self._canvas.pack(padx=4, pady=2)
        self._canvas.bind("<Button-1>", self._on_click)

        ttk.Button(self, text="Cancel",
                   command=self._cancel).pack(fill=tk.X, padx=4, pady=2)

        self._render()

    # ── rendering ─────────────────────────────────────────────────────────────
    def _render(self):
        c = self._canvas
        c.delete("all")
        self._photos.clear()

        c16  = Emblems.count16(self._of)
        c128 = Emblems.count128(self._of)

        for cell in range(_COLS * _ROWS):
            col = cell % _COLS
            row = cell // _COLS
            x0  = col * _CELL
            y0  = row * _CELL

            emb_idx = self._cell_to_emblem_idx(cell, c16, c128)
            if emb_idx is None:
                # Empty slot — draw a gray square with a subtle border
                c.create_rectangle(x0, y0, x0 + _CELL, y0 + _CELL,
                                    fill="#505050", outline="#666666")
                continue

            try:
                ph = self._make_thumbnail(emb_idx)
                self._photos.append(ph)
                c.create_image(x0, y0, anchor=tk.NW, image=ph)
                # Border to separate cells
                c.create_rectangle(x0, y0, x0 + _CELL, y0 + _CELL,
                                    outline="#888888", fill="")
            except Exception:
                c.create_rectangle(x0, y0, x0 + _CELL, y0 + _CELL,
                                    fill="#505050", outline="#666666")

    def _make_thumbnail(self, adj: int) -> tk.PhotoImage:
        pixels = Emblems.decode_by_adj(self._of, adj, opaque=not self._trans)
        if pixels is None:
            raise ValueError("no emblem data")
        size = _CELL   # 20
        src  = Emblems.IMG_SIZE  # 64
        bg   = "#505050"
        img  = tk.PhotoImage(width=size, height=size)
        for ty in range(size):
            row_cols = []
            for tx in range(size):
                sx = min(int(tx * src / size), src - 1)
                sy = min(int(ty * src / size), src - 1)
                r, g, b, a = pixels[sy * src + sx]
                row_cols.append(bg if a < 128 else f"#{r:02x}{g:02x}{b:02x}")
            img.put("{" + " ".join(row_cols) + "}", to=(0, ty))
        return img

    # ── cell ↔ emblem mapping (mirrors Java EmblemChooserDialog) ──────────────
    @staticmethod
    def _cell_to_emblem_idx(cell: int, c16: int, c128: int):
        """Return Python emblem_idx for a grid cell, or None if empty slot."""
        if cell < c16:
            # 16-colour emblem: Python idx = cell + 50
            return cell + 50
        if cell >= 100 - c128:
            # 128-colour emblem: Python idx = 99 - cell
            return 99 - cell
        return None

    @staticmethod
    def _cell_to_clubs_value(cell: int, c16: int, c128: int) -> int:
        """Return the clubs emblem value for a valid grid cell."""
        if cell < c16:
            # 16-colour: adj_idx = cell + 50  → clubs value = cell + 50 + 292
            return cell + 50 + Clubs.FIRST_FLAG
        if cell >= 100 - c128:
            # 128-colour: adj_idx = 99 - cell → clubs value = 99-cell + 292
            return (99 - cell) + Clubs.FIRST_FLAG
        return -1

    # ── events ────────────────────────────────────────────────────────────────
    def _on_click(self, event):
        col  = event.x // _CELL
        row  = event.y // _CELL
        cell = row * _COLS + col
        if not (0 <= cell < _COLS * _ROWS):
            return
        c16  = Emblems.count16(self._of)
        c128 = Emblems.count128(self._of)
        val  = self._cell_to_clubs_value(cell, c16, c128)
        if val != -1:
            self._result = val
            self.destroy()

    def _toggle_trans(self):
        self._trans = not self._trans
        self._render()

    def _cancel(self):
        self._result = -1
        self.destroy()

    # ── public API ────────────────────────────────────────────────────────────
    @classmethod
    def choose(cls, parent, of) -> int:
        """Open dialog modally; return clubs emblem value or -1 if cancelled."""
        dlg = cls(parent, of)
        parent.wait_window(dlg)
        return dlg._result
