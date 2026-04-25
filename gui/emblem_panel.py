"""
PES Editor 6 - Python Port
Emblem Panel — matches Java EmblemPanel layout:
  Left   : bordered emblem-grid canvas  ("16 Colour Format" / "128 Colour Format" labels)
             + Transparency toggle button
  Center : large preview of the selected emblem
  Right  : stock counts ("16-colour, can stock: N" / "128-colour, can stock: N")
             + Add Emblem button
             + Convert Any Image… button
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import emblems as Emblems
import clubs   as Clubs

# Grid layout: 10 columns × 15 rows = 150 slots
_COLS     = 10
_ROWS_16  = 10   # rows reserved for 16-colour emblems  (100 slots)
_ROWS_128 = 5    # rows reserved for 128-colour emblems (50 slots)
_ROWS     = _ROWS_16 + _ROWS_128   # 15
_CELL     = 40   # px per cell in the grid (was 16)
_PREVIEW  = 256  # px for the large central preview (was 128)


class EmblemPanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of       = of
        self._slot     = 0       # currently selected emblem slot (0-149)
        self._trans    = False   # transparency mode
        self._photos   = []      # PhotoImage cache (prevent GC)
        self._build_ui()

    # ── construction ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Left: emblem grid + labels + Transparency button ──────────────
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, padx=6, pady=6, anchor=tk.N)

        # Bordered area with labels
        border = tk.Frame(left, relief=tk.SOLID, borderwidth=1,
                          bg=self.winfo_toplevel().cget("bg") if self.winfo_toplevel() else "#F0F0F0")
        border.pack()

        lbl16 = ttk.Label(border, text="16 Colour Format")
        lbl16.pack(anchor=tk.W, padx=2, pady=(2, 0))

        self._grid_canvas = tk.Canvas(border,
                                       width =_COLS * _CELL,
                                       height=_ROWS * _CELL,
                                       bg="#606060", cursor="hand2")
        self._grid_canvas.pack(padx=2, pady=1)
        self._grid_canvas.bind("<Button-1>", self._on_grid_click)

        # Separator line between 16-colour and 128-colour areas
        sep_y = _ROWS_16 * _CELL
        self._grid_canvas.create_line(0, sep_y, _COLS * _CELL, sep_y,
                                       fill="#AAAAAA", dash=(4, 2))

        lbl128 = ttk.Label(border, text="128 Colour Format")
        lbl128.pack(anchor=tk.E, padx=2, pady=(0, 2))

        ttk.Button(left, text="Transparency",
                   command=self._toggle_transparency).pack(fill=tk.X, pady=(3, 0))

        # ── Center: large preview ─────────────────────────────────────────
        self._preview = tk.Canvas(self,
                                   width =_PREVIEW,
                                   height=_PREVIEW,
                                   bg="#808080")
        self._preview.pack(side=tk.LEFT, padx=6, pady=6, anchor=tk.N)

        # ── Right: stock counts + buttons ─────────────────────────────────
        right = ttk.Frame(self)
        right.pack(side=tk.LEFT, padx=6, pady=6, anchor=tk.N)

        self._free16_var  = tk.StringVar(value="16-colour, can stock: 0")
        self._free128_var = tk.StringVar(value="128-colour, can stock: 0")
        ttk.Label(right, textvariable=self._free16_var).pack(anchor=tk.W, pady=1)
        ttk.Label(right, textvariable=self._free128_var).pack(anchor=tk.W, pady=1)

        ttk.Button(right, text="Add Emblem",
                   command=self._add_emblem).pack(fill=tk.X, pady=(6, 2))
        ttk.Button(right, text="Convert Any Image…",
                   command=self._convert_image).pack(fill=tk.X, pady=2)

    # ── public API ────────────────────────────────────────────────────────────
    def refresh(self):
        if self._of is None:
            return
        self._free16_var.set(
            f"16-colour, can stock: {Emblems.get_free16(self._of)}")
        self._free128_var.set(
            f"128-colour, can stock: {Emblems.get_free128(self._of)}")
        self._render_grid()
        self._render_preview(self._slot)

    # ── grid rendering ────────────────────────────────────────────────────────
    def _render_grid(self):
        c = self._grid_canvas
        c.delete("emblem")
        self._photos.clear()
        if self._of is None:
            return
        for slot in range(_COLS * _ROWS):
            col  = slot % _COLS
            row  = slot // _COLS
            x0   = col * _CELL
            y0   = row * _CELL
            try:
                ph = self._make_thumbnail(slot)
                self._photos.append(ph)
                c.create_image(x0, y0, anchor=tk.NW, image=ph, tags="emblem")
            except Exception:
                c.create_rectangle(x0, y0, x0 + _CELL, y0 + _CELL,
                                    fill="#404040", outline="", tags="emblem")
        # Highlight current selection
        self._draw_selection()

    def _decode_slot(self, slot: int):
        """Return (r,g,b,a) pixel list for linear slot, or None if empty/unset."""
        c16  = Emblems.count16(self._of)
        c128 = Emblems.count128(self._of)
        opaque = not self._trans
        if slot < _COLS * _ROWS_16:          # 16-colour area  (slots 0..99)
            if slot < c16:
                return Emblems.decode_16(self._of, slot, opaque)
        else:                                 # 128-colour area (slots 100..149)
            es = slot - _COLS * _ROWS_16     # 128-colour slot index
            if es < c128:
                return Emblems.decode_128(self._of, es, opaque)
        return None

    def _make_thumbnail(self, slot: int) -> tk.PhotoImage:
        """Render a _CELL × _CELL thumbnail for an emblem slot."""
        size    = _CELL   # 16
        src     = Emblems.IMG_SIZE  # 64
        bg      = "#606060"
        img     = tk.PhotoImage(width=size, height=size)
        pixels  = self._decode_slot(slot)
        if pixels is None:
            for ty in range(size):
                img.put("{" + " ".join([bg] * size) + "}", to=(0, ty))
            return img
        for ty in range(size):
            row_colors = []
            for tx in range(size):
                sx = min(int(tx * src / size), src - 1)
                sy = min(int(ty * src / size), src - 1)
                r, g, b, a = pixels[sy * src + sx]
                row_colors.append(bg if a < 128 else f"#{r:02x}{g:02x}{b:02x}")
            img.put("{" + " ".join(row_colors) + "}", to=(0, ty))
        return img

    def _draw_selection(self):
        self._grid_canvas.delete("sel_box")
        col = self._slot % _COLS
        row = self._slot // _COLS
        x0  = col * _CELL
        y0  = row * _CELL
        self._grid_canvas.create_rectangle(
            x0, y0, x0 + _CELL, y0 + _CELL,
            outline="#FFFFFF", width=1, tags="sel_box")

    def _on_grid_click(self, event):
        col  = event.x // _CELL
        row  = event.y // _CELL
        slot = row * _COLS + col
        if 0 <= slot < _COLS * _ROWS:
            self._slot = slot
            self._draw_selection()
            self._render_preview(slot)
            if self._of is not None and self._is_occupied(slot):
                self._show_emblem_options(slot)

    def _is_occupied(self, slot: int) -> bool:
        if slot < _COLS * _ROWS_16:
            return slot < Emblems.count16(self._of)
        else:
            return (slot - _COLS * _ROWS_16) < Emblems.count128(self._of)

    def _show_emblem_options(self, slot: int):
        is128     = slot >= _COLS * _ROWS_16
        phys_slot = (slot - _COLS * _ROWS_16) if is128 else slot

        dlg = tk.Toplevel(self)
        dlg.title("Emblem")
        dlg.resizable(False, False)
        dlg.update_idletasks()
        dlg.grab_set()

        # Top: preview + "Options:" label
        top = ttk.Frame(dlg)
        top.pack(padx=10, pady=(10, 5), fill=tk.X)

        preview_canvas = tk.Canvas(top, width=64, height=64, bg="#808080",
                                   highlightthickness=0)
        preview_canvas.pack(side=tk.LEFT, padx=(0, 10))
        pixels = self._decode_slot(slot)
        if pixels is not None:
            img = tk.PhotoImage(width=64, height=64)
            src = Emblems.IMG_SIZE
            for py in range(64):
                row_cols = []
                for px in range(64):
                    r, g, b, a = pixels[py * src + px]
                    row_cols.append("#808080" if a < 128 else f"#{r:02x}{g:02x}{b:02x}")
                img.put("{" + " ".join(row_cols) + "}", to=(0, py))
            preview_canvas.create_image(0, 0, anchor=tk.NW, image=img)
            preview_canvas._img = img
        ttk.Label(top, text="Options:").pack(side=tk.LEFT, anchor=tk.W)

        # Bottom: action buttons
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(padx=10, pady=(5, 10))

        result = [None]

        def _pick(r):
            result[0] = r
            dlg.destroy()

        ttk.Button(btn_frame, text="Delete",
                   command=lambda: _pick('delete')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Import PNG / GIF",
                   command=lambda: _pick('import')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Export as PNG",
                   command=lambda: _pick('export')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Cancel",
                   command=dlg.destroy).pack(side=tk.LEFT, padx=2)

        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - dlg.winfo_width())  // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")
        dlg.wait_window()

        if result[0] == 'delete':
            self._do_delete(is128, phys_slot)
        elif result[0] == 'import':
            self._do_import(is128, phys_slot)
        elif result[0] == 'export':
            self._do_export(is128, phys_slot)

    def _do_delete(self, is128: bool, phys_slot: int):
        try:
            if is128:
                Emblems.delete128(self._of, phys_slot)
            else:
                Emblems.delete16(self._of, phys_slot)
            self._slot = 0
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _do_import(self, is128: bool, phys_slot: int):
        if is128:
            messagebox.showinfo("Not supported",
                "128-colour emblem import not yet implemented.\n"
                "Use a slot in the upper (16-colour) area.", parent=self)
            return
        path = filedialog.askopenfilename(
            title="Import Emblem",
            filetypes=[("Images", "*.png *.gif *.jpg *.bmp"), ("All files", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            Emblems.load_from_image(self._of, '16', phys_slot, path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _do_export(self, is128: bool, phys_slot: int):
        path = filedialog.asksaveasfilename(
            title="Export as PNG",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            parent=self
        )
        if not path:
            return
        try:
            Emblems.export_png(self._of, phys_slot, is128, path)
            messagebox.showinfo("Saved", f"Saved to:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    # ── large preview ─────────────────────────────────────────────────────────
    def _render_preview(self, slot: int):
        c = self._preview
        c.delete("all")
        if self._of is None:
            return
        try:
            pixels = self._decode_slot(slot)
            if pixels is None:
                c.create_text(_PREVIEW // 2, _PREVIEW // 2,
                              text="Empty", fill="#aaaaaa")
                return
            src   = Emblems.IMG_SIZE   # 64
            scale = _PREVIEW // src    # 128 // 64 = 2
            bg    = "#808080"
            img   = tk.PhotoImage(width=_PREVIEW, height=_PREVIEW)
            for py in range(_PREVIEW):
                row_cols = []
                for px in range(_PREVIEW):
                    sx = min(int(px * src / _PREVIEW), src - 1)
                    sy = min(int(py * src / _PREVIEW), src - 1)
                    r, g, b, a = pixels[sy * src + sx]
                    row_cols.append(bg if a < 128 else f"#{r:02x}{g:02x}{b:02x}")
                img.put("{" + " ".join(row_cols) + "}", to=(0, py))
            c.create_image(0, 0, anchor=tk.NW, image=img)
            c._preview_img = img   # prevent GC
        except Exception as e:
            c.create_text(_PREVIEW // 2, _PREVIEW // 2,
                          text=f"Error:\n{e}", fill="red")

    # ── button actions ────────────────────────────────────────────────────────
    def _toggle_transparency(self):
        self._trans = not self._trans
        self._render_grid()
        self._render_preview(self._slot)

    def _add_emblem(self):
        if self._of is None:
            return
        path = filedialog.askopenfilename(
            title="Add Emblem",
            filetypes=[("Images", "*.png *.gif *.jpg *.bmp"), ("All files", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            if self._slot < _COLS * _ROWS_16:
                Emblems.load_from_image(self._of, '16', self._slot, path)
            else:
                messagebox.showinfo(
                    "Not supported",
                    "128-colour emblem import not yet implemented.\n"
                    "Select a slot in the upper (16-colour) grid area.",
                    parent=self)
                return
            self.refresh()
            messagebox.showinfo("Done", "Emblem added.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _convert_image(self):
        if self._of is None:
            return
        from gui.image_converter_dialog import ImageConverterDialog
        ImageConverterDialog(self, self._of, emblem_panel=self)
