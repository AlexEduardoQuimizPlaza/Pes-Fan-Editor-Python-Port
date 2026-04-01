"""
PES Editor 6 - Python Port
Logo Panel — matches Java LogoPanel:
  • 8×10 grid of logo slots (80 total)
  • Used slots show the logo thumbnail; empty slots are gray
  • Transparency toggle button at the bottom of the grid
  • Clicking any slot opens an options popup:
      Import PNG / GIF  →  load image into slot
      Export as PNG     →  save logo to PNG  (only if slot is used)
      Cancel
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import logos as Logos

_COLS  = 10
_ROWS  = 8
_CELL  = 40   # px per grid cell (logo is 32×32, so 4px padding each side)
_W     = _COLS * _CELL
_H     = _ROWS * _CELL


class LogoPanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of     = of
        self._trans  = True     # start with transparency on (Java default)
        self._photos = []       # PhotoImage references (prevent GC)
        self._build_ui()

    # ── construction ──────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = ttk.Frame(self)
        outer.pack(padx=8, pady=8, anchor=tk.N)

        self._canvas = tk.Canvas(outer, width=_W, height=_H,
                                  bg="#CCCCCC", cursor="hand2")
        self._canvas.pack()
        self._canvas.bind("<Button-1>", self._on_click)

        ttk.Button(outer, text="Transparency",
                   command=self._toggle_trans).pack(fill=tk.X, pady=(2, 0))

    # ── public API ────────────────────────────────────────────────────────────
    def refresh(self):
        if self._of is None:
            return
        self._render_grid()

    # ── grid rendering ────────────────────────────────────────────────────────
    def _render_grid(self):
        c = self._canvas
        c.delete("all")
        self._photos.clear()
        if self._of is None:
            return
        for slot in range(Logos.TOTAL):
            col = slot % _COLS
            row = slot // _COLS
            x0  = col * _CELL
            y0  = row * _CELL
            # Draw cell background
            c.create_rectangle(x0, y0, x0 + _CELL, y0 + _CELL,
                                fill="#CCCCCC", outline="#AAAAAA")
            try:
                ph = self._make_thumbnail(slot)
                if ph is not None:
                    self._photos.append(ph)
                    # Centre the 32×32 image in the 40×40 cell
                    pad = (_CELL - Logos.IMG_SIZE) // 2
                    c.create_image(x0 + pad, y0 + pad, anchor=tk.NW, image=ph)
            except Exception:
                pass

    def _make_thumbnail(self, slot: int):
        """Return a PhotoImage for a used slot, or None if empty."""
        pixels = Logos.decode(self._of, slot, opaque=not self._trans)
        if pixels is None:
            return None
        size = Logos.IMG_SIZE   # 32
        img  = tk.PhotoImage(width=size, height=size)
        bg   = "#CCCCCC"
        for ty in range(size):
            row_cols = []
            for tx in range(size):
                r, g, b, a = pixels[ty * size + tx]
                row_cols.append(bg if a < 128 else f"#{r:02x}{g:02x}{b:02x}")
            img.put("{" + " ".join(row_cols) + "}", to=(0, ty))
        return img

    # ── slot click → options popup ────────────────────────────────────────────
    def _on_click(self, event):
        col  = event.x // _CELL
        row  = event.y // _CELL
        slot = row * _COLS + col
        if 0 <= slot < Logos.TOTAL:
            self._show_options(slot)

    def _show_options(self, slot: int):
        dlg = tk.Toplevel(self)
        dlg.title("Logo")
        dlg.resizable(False, False)

        # Preview of current slot (opaque for clarity in dialog)
        try:
            ph = self._make_thumbnail(slot)
        except Exception:
            ph = None

        # Icon label
        if ph is not None:
            lbl = tk.Label(dlg, image=ph, relief=tk.SUNKEN, borderwidth=1)
            lbl.image = ph   # prevent GC
            lbl.pack(padx=8, pady=(8, 4))

        tk.Label(dlg, text="Options:").pack(padx=8, pady=(4, 2))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(padx=8, pady=(0, 8))

        ttk.Button(btn_frame, text="Import PNG / GIF",
                   command=lambda: self._import(slot, dlg)).pack(
                       side=tk.LEFT, padx=3)

        exp_btn = ttk.Button(btn_frame, text="Export as PNG",
                              command=lambda: self._export(slot, dlg))
        exp_btn.pack(side=tk.LEFT, padx=3)
        if not Logos.is_used(self._of, slot):
            exp_btn.config(state=tk.DISABLED)

        ttk.Button(btn_frame, text="Cancel",
                   command=dlg.destroy).pack(side=tk.LEFT, padx=3)

        # Centre over parent and grab focus
        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - dlg.winfo_width())  // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")
        dlg.grab_set()

    # ── import ────────────────────────────────────────────────────────────────
    def _import(self, slot: int, dlg: tk.Toplevel):
        path = filedialog.askopenfilename(
            title="Import Logo",
            filetypes=[("Images", "*.png *.gif *.jpg *.bmp"), ("All files", "*.*")],
            parent=dlg
        )
        if not path:
            return
        try:
            Logos.load_from_image(self._of, slot, path)
            dlg.destroy()
            self._render_grid()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    # ── export ────────────────────────────────────────────────────────────────
    def _export(self, slot: int, dlg: tk.Toplevel):
        if not Logos.is_used(self._of, slot):
            messagebox.showinfo("Empty", "This slot has no logo.", parent=dlg)
            return
        path = filedialog.asksaveasfilename(
            title="Export Logo",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            parent=dlg
        )
        if not path:
            return
        try:
            Logos.export_to_png(self._of, slot, path)
            dlg.destroy()
            messagebox.showinfo(
                "Saved",
                f"Saved to:\n{path}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    # ── transparency toggle ───────────────────────────────────────────────────
    def _toggle_trans(self):
        self._trans = not self._trans
        self._render_grid()
