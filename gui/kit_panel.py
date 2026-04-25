"""
PES Editor 6 - Python Port
Kit Panel — visual kit editor with 2D preview.
"""
import tkinter as tk
from tkinter import ttk, colorchooser
from pathlib import Path

import kits  as Kits
import clubs as Clubs
import logos as Logos
import stats  as Stats

try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

# ── Asset paths ───────────────────────────────────────────────────────────────
_ASSETS = Path(__file__).parent.parent / "assets" / "kits"

# ── Template grid: pantstemplate.png (8 cols × 8 rows, each cell 25×27 px) ──
_PANTS_COL  = [3, 35, 67, 99, 131, 163, 195, 227]
_PANTS_ROW  = [2, 34, 66, 98, 130, 162, 194, 226]
_PANTS_CW, _PANTS_CH = 25, 27

# ── Template grid: sleevestemplate.png (8 cols × 4 rows, each cell 18×34 px)
_SOCK_COL  = [7, 39, 71, 103, 135, 167, 199, 231]
_SOCK_ROW  = [3, 43, 83, 123]
_SOCK_CW, _SOCK_CH = 18, 34

# ── Shirt cells in kitstemplate.png (rows 161-198, 3 collar types) ──────────
_SHIRT_CELLS = [
    (96,  161, 144, 199),   # round collar
    (144, 161, 192, 199),   # V-neck / zipped collar
    (192, 161, 240, 199),   # standard collar
]

# ── GK shirt cells in kitsgoalkeepertemplate.png (2 types, long sleeves) ────
_GK_SHIRT_CELLS = [
    (96,  161, 144, 199),   # GK type 0
    (144, 161, 192, 199),   # GK type 1
]

# ── Placeholder colors in template images ────────────────────────────────────
# Each sprite uses these as stand-in colors that we replace at render time.
_WHITE  = (255, 255, 255)   # → colors[0]  primary
_CYAN   = (32,  232, 224)   # → colors[1]  secondary
_BLUE   = (80,  96,  248)   # → colors[2]  tertiary
_PURPLE = (175, 0,   183)   # → colors[3]  quaternary

_COLOR_MAP = {_WHITE: 0, _CYAN: 1, _BLUE: 2, _PURPLE: 3}

_PREVIEW_SCALE = 4          # pixel scale for sprites (nearest-neighbour)
_PW, _PH = 220, 430         # preview canvas size in pixels

# ── Pattern layer thumbnails ──────────────────────────────────────────────────
TW, TH = 64, 52             # thumbnail pixel size
TCOLS  = 3                  # columns in the pattern grid
TPAD   = 4                  # padding between thumbnails

# (layer_idx, button_label, kitinfo_offset, num_options)
_LAYERS = [
    (0, "Base",      42,  3),
    (1, "Pequeñas",  43, 31),   # collar accents (1 OFF + 30 sprites)
    (2, "Medias",    44, 31),   # sleeve / shoulder designs
    (3, "Grandes 1", 45, 31),   # body pattern (front)
    (4, "Grandes 2", 46, 31),   # body pattern (alt / back)
]
# Full in-game header titles displayed above the grid
_LAYER_TITLES = [
    "Base",
    "Partes pequeñas",
    "Partes medias",
    "Partes grandes 1",
    "Partes grandes 2",
]

# (template filename, cell_w, cell_h, n_cols, n_rows)
_LAYER_GRID = {
    1: ("cuellotemplate.png",                 48, 40, 5, 6),
    2: ("MangasTemplate.png",                 48, 40, 5, 6),
    3: ("Camisetaenfrenteatrastemplate.png",  48, 40, 5, 6),
    4: ("Camisetaenfrenteatrastemplate3.png", 48, 40, 5, 6),
}

# Accent colour used when tinting WHITE pixels of a layer sprite (matches the
# in-game thumbnail palette: magenta for cuello, blue for mangas, etc.)
_LAYER_ACCENT = {
    1: (220, 60, 200),
    2: (50,  60, 180),
    3: (60, 100, 220),
    4: (110, 175, 240),
}


# ── Template loader (singleton images) ───────────────────────────────────────
_tmpl_shirt: "Image.Image | None" = None
_tmpl_gk:    "Image.Image | None" = None
_tmpl_pants: "Image.Image | None" = None
_tmpl_socks: "Image.Image | None" = None
_tmpl_layer: dict = {}            # layer_idx → loaded template image (or None)
_tmpl_outline: "Image.Image | None" = None  # cached light-grey shirt outline
_tmpl_loaded = False


def _ensure_templates():
    global _tmpl_shirt, _tmpl_gk, _tmpl_pants, _tmpl_socks, _tmpl_loaded
    global _tmpl_outline
    if _tmpl_loaded or not _PIL:
        return
    _tmpl_loaded = True
    try:
        _tmpl_shirt = Image.open(_ASSETS / 'kitstemplate.png').convert('RGBA')
        _tmpl_gk    = Image.open(_ASSETS / 'kitsgoalkeepertemplate.png').convert('RGBA')
        _tmpl_pants = Image.open(_ASSETS / 'pantstemplate.png').convert('RGBA')
        _tmpl_socks = Image.open(_ASSETS / 'sleevestemplate.png').convert('RGBA')
    except Exception:
        pass

    # Layer templates (cuello / mangas / camiseta-frente-atras)
    for li, (fname, _cw, _ch, _nc, _nr) in _LAYER_GRID.items():
        try:
            _tmpl_layer[li] = Image.open(_ASSETS / fname).convert('RGBA')
        except Exception:
            _tmpl_layer[li] = None

    # Cache a light-grey shirt silhouette for use as a thumbnail backdrop
    if _tmpl_shirt is not None:
        sx0, sy0, sx1, sy1 = _SHIRT_CELLS[0]    # round collar
        base = _tmpl_shirt.crop((sx0, sy0, sx1, sy1)).convert('RGBA')
        data = list(base.getdata())
        out = []
        for r, g, b, a in data:
            if a == 0:
                out.append((r, g, b, 0))
            elif (r, g, b) == (0, 0, 0):
                out.append((150, 150, 150, a))   # outline → mid-grey
            else:
                out.append((245, 245, 245, a))   # interior → near-white
        base.putdata(out)
        _tmpl_outline = base


def _tint_layer_sprite(sprite: "Image.Image",
                       accent: tuple) -> "Image.Image":
    """Replace WHITE pixels with the layer's accent colour, preserve outlines."""
    result = sprite.copy().convert('RGBA')
    data = list(result.getdata())
    out = []
    ar, ag, ab = accent
    for r, g, b, a in data:
        if a == 0:
            out.append((r, g, b, 0))
        elif (r, g, b) == (255, 255, 255):
            out.append((ar, ag, ab, a))
        elif (r, g, b) == (0, 0, 0):
            out.append((50, 50, 50, a))
        else:
            out.append((r, g, b, a))
    result.putdata(out)
    return result


def _tint_sprite(sprite: "Image.Image", colors: list) -> "Image.Image":
    """
    Replace template placeholder colors with actual kit colors.
    Transparent pixels and black outlines are preserved.
    """
    result = sprite.copy().convert('RGBA')
    data   = list(result.getdata())
    out    = []
    for r, g, b, a in data:
        if a == 0:
            out.append((r, g, b, 0))
            continue
        idx = _COLOR_MAP.get((r, g, b))
        if idx is not None and idx < len(colors):
            cr, cg, cb = colors[idx]
            out.append((cr, cg, cb, a))
        else:
            out.append((r, g, b, a))
    result.putdata(out)
    return result


def _extract_cell(template: "Image.Image",
                  col_starts: list, row_starts: list,
                  cw: int, ch: int,
                  col: int, row: int) -> "Image.Image":
    x0 = col_starts[col % len(col_starts)]
    y0 = row_starts[row % len(row_starts)]
    return template.crop((x0, y0, x0 + cw, y0 + ch)).convert('RGBA')


def _collar_thumb(collar_idx: int, colors: list) -> "Image.Image":
    """TW×TH thumbnail for Base layer using real shirt sprite."""
    bg = Image.new('RGBA', (TW, TH), (60, 60, 60, 255))
    if _tmpl_shirt is not None and collar_idx < len(_SHIRT_CELLS):
        sx0, sy0, sx1, sy1 = _SHIRT_CELLS[collar_idx]
        sprite = _tmpl_shirt.crop((sx0, sy0, sx1, sy1)).convert('RGBA')
        tinted = _tint_sprite(sprite, colors if colors else [(180, 180, 180)])
        sw, sh = sprite.size
        scale = min(TW / sw, TH / sh) * 0.88
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        scaled = tinted.resize((nw, nh), Image.NEAREST)
        ox, oy = (TW - nw) // 2, (TH - nh) // 2
        bg.paste(scaled, (ox, oy), scaled)
    else:
        draw = ImageDraw.Draw(bg)
        draw.text((TW // 2 - 4, TH // 2 - 6), str(collar_idx),
                  fill=(200, 200, 200))
    return bg.convert('RGB')


def _paste_outline(bg: "Image.Image") -> tuple:
    """Paste the cached shirt outline onto bg, return (off_x, off_y, w, h)."""
    if _tmpl_outline is None:
        return (TPAD, TPAD, TW - 2 * TPAD, TH - 2 * TPAD)
    sw, sh = _tmpl_outline.size
    scale = min((TW - 4) / sw, (TH - 4) / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    scaled = _tmpl_outline.resize((nw, nh), Image.NEAREST)
    ox, oy = (TW - nw) // 2, (TH - nh) // 2
    bg.paste(scaled, (ox, oy), scaled)
    return (ox, oy, nw, nh)


def _layer_thumb(layer_idx: int, option_idx: int) -> "Image.Image":
    """
    TW×TH thumbnail for a Partes pequeñas / medias / grandes option.
    option_idx == 0  → "OFF" (no design)
    option_idx >= 1  → sprite cell (option_idx - 1) from the layer's template
    """
    bg = Image.new('RGBA', (TW, TH), (235, 235, 235, 255))
    ox, oy, nw, nh = _paste_outline(bg)

    if option_idx == 0:
        draw = ImageDraw.Draw(bg)
        # Faint dark band so the OFF text stays readable on the white shirt
        draw.rectangle([ox + 4, oy + nh // 2 - 7, ox + nw - 4, oy + nh // 2 + 7],
                       fill=(95, 95, 95, 200))
        draw.text((TW // 2 - 9, TH // 2 - 6), "OFF", fill=(255, 255, 255))
        return bg.convert('RGB')

    grid = _LAYER_GRID.get(layer_idx)
    tmpl = _tmpl_layer.get(layer_idx)
    if grid is None or tmpl is None:
        # No template available — fall back to a numbered tag
        draw = ImageDraw.Draw(bg)
        txt = str(option_idx)
        draw.text((TW // 2 - len(txt) * 3, TH // 2 - 6), txt, fill=(50, 50, 50))
        return bg.convert('RGB')

    _fname, cw, ch, n_cols, n_rows = grid
    sprite_idx = option_idx - 1
    col = sprite_idx % n_cols
    row = sprite_idx // n_cols
    if row >= n_rows:
        return bg.convert('RGB')

    x0, y0 = col * cw, row * ch
    cell = tmpl.crop((x0, y0, x0 + cw, y0 + ch))
    accent = _LAYER_ACCENT.get(layer_idx, (180, 100, 200))
    tinted = _tint_layer_sprite(cell, accent)

    # Scale the layer sprite to roughly match the shirt outline area
    if nw > 0 and nh > 0:
        scaled = tinted.resize((nw, nh), Image.NEAREST)
        bg.paste(scaled, (ox, oy), scaled)
    return bg.convert('RGB')


class KitPanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of   = of
        self._ok   = False
        self._team = -1
        self._kit  = 0      # 0=Home 1=Away 2=3rd 3=GK

        self._cur_layer  = 0
        self._cur_pat    = [0] * len(_LAYERS)
        self._grid_thumbs: list = []

        _ensure_templates()
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Left column: team list ────────────────────────────────────────────
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0), pady=6)

        ttk.Label(left, text="Equipo").pack()
        sb = ttk.Scrollbar(left, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(left, width=26, height=28,
                                   yscrollcommand=sb.set, exportselection=False)
        sb.config(command=self._listbox.yview)
        self._listbox.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self._listbox.bind("<<ListboxSelect>>",
                           lambda e: self.after_idle(self._on_select))

        # ── Right column ──────────────────────────────────────────────────────
        right = ttk.Frame(self)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Kit slot tab buttons (Home / Away / 3rd / GK)
        tab_row = ttk.Frame(right)
        tab_row.pack(fill=tk.X, pady=(0, 6))
        self._kit_btns = []
        for i, name in enumerate(Kits.KIT_NAMES):
            btn = ttk.Button(tab_row, text=name, width=10,
                             command=lambda ki=i: self._on_kit_tab(ki))
            btn.pack(side=tk.LEFT, padx=2)
            self._kit_btns.append(btn)

        # Content area: preview on left, scrollable editor on right
        content = ttk.Frame(right)
        content.pack(fill=tk.BOTH, expand=True)

        # ── Preview canvas ────────────────────────────────────────────────────
        preview_frame = ttk.LabelFrame(content, text="Vista previa", padding=4)
        preview_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self._preview_canvas = tk.Canvas(preview_frame, width=_PW, height=_PH,
                                         bg='#d0d0d0', highlightthickness=0)
        self._preview_canvas.pack()
        self._preview_ref = None

        # ── Scrollable color/logo editor ──────────────────────────────────────
        editor_outer = ttk.Frame(content)
        editor_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ed_canvas = tk.Canvas(editor_outer, highlightthickness=0)
        vsb = ttk.Scrollbar(editor_outer, orient=tk.VERTICAL, command=ed_canvas.yview)
        ed_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        ed_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._detail = ttk.Frame(ed_canvas)
        self._detail_win = ed_canvas.create_window((0, 0), window=self._detail,
                                                    anchor=tk.NW)
        self._detail.bind("<Configure>",
                          lambda e: ed_canvas.configure(
                              scrollregion=ed_canvas.bbox("all")))
        ed_canvas.bind("<Configure>",
                       lambda e: ed_canvas.itemconfig(self._detail_win,
                                                       width=e.width))
        self._ed_canvas = ed_canvas
        self._build_detail()

    def _build_detail(self):
        d = self._detail

        # Licensed checkbox
        top = ttk.Frame(d)
        top.pack(anchor=tk.W, padx=8, pady=(8, 2))
        self._lic_var = tk.BooleanVar()
        ttk.Checkbutton(top, text="Licensed (usa textura AFS)",
                        variable=self._lic_var,
                        command=self._on_lic_change).pack(side=tk.LEFT)

        ttk.Separator(d, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # Model row + copy button
        model_row = ttk.Frame(d)
        model_row.pack(anchor=tk.W, padx=8, pady=2)
        ttk.Label(model_row, text="Modelo:").pack(side=tk.LEFT)
        self._model_var = tk.IntVar()
        spin = ttk.Spinbox(model_row, from_=0, to=255, width=5,
                           textvariable=self._model_var)
        spin.pack(side=tk.LEFT, padx=4)
        spin.bind("<FocusOut>", lambda e: self._on_model())
        spin.bind("<Return>",   lambda e: self._on_model())
        ttk.Button(model_row, text="Copiar kit de…",
                   command=self._copy_kit_dialog).pack(side=tk.LEFT, padx=12)

        ttk.Separator(d, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # Color groups
        # _color_buttons maps kitinfo_offset → tk.Button
        self._color_buttons: dict[int, tk.Button] = {}
        for key, label, base_off, count in Kits.COLOR_GROUPS:
            row = ttk.Frame(d)
            row.pack(anchor=tk.W, padx=8, pady=2)
            ttk.Label(row, text=f"{label}:", width=10,
                      anchor=tk.E).pack(side=tk.LEFT, padx=(0, 4))
            for i in range(count):
                off = base_off + i * 2
                btn = tk.Button(row, width=3, height=1,
                                relief=tk.RAISED, cursor="hand2", bd=1)
                btn.config(command=lambda o=off, b=btn: self._pick_color(o, b))
                btn.pack(side=tk.LEFT, padx=1)
                self._color_buttons[off] = btn

        ttk.Separator(d, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=6)

        # ── Pattern layer editor ──────────────────────────────────────────────
        pat_lf = ttk.LabelFrame(d, text="Patrones de camiseta", padding=4)
        pat_lf.pack(fill=tk.X, padx=8, pady=4)

        layer_row = ttk.Frame(pat_lf)
        layer_row.pack(fill=tk.X, pady=(0, 4))
        self._layer_btns: list[ttk.Button] = []
        for i, (_, lname, _, _) in enumerate(_LAYERS):
            btn = ttk.Button(layer_row, text=lname, width=10,
                             command=lambda li=i: self._on_layer_btn(li))
            btn.pack(side=tk.LEFT, padx=1)
            self._layer_btns.append(btn)

        self._layer_title = ttk.Label(pat_lf, text=_LAYER_TITLES[0],
                                       anchor=tk.CENTER,
                                       font=("TkDefaultFont", 10, "bold"))
        self._layer_title.pack(fill=tk.X, pady=(2, 2))

        grid_h = (TH + TPAD) * 3 + TPAD   # show ~3 rows by default
        grid_wrap = ttk.Frame(pat_lf)
        grid_wrap.pack(fill=tk.X)
        self._grid_canvas = tk.Canvas(grid_wrap, height=grid_h,
                                      bg="#404040", highlightthickness=0)
        grid_sb = ttk.Scrollbar(grid_wrap, orient=tk.VERTICAL,
                                 command=self._grid_canvas.yview)
        self._grid_canvas.configure(yscrollcommand=grid_sb.set)
        grid_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._grid_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._grid_canvas.bind("<Button-1>", self._on_grid_click)
        self._grid_canvas.bind("<Button-4>",
            lambda e: self._grid_canvas.yview_scroll(-1, "units"))
        self._grid_canvas.bind("<Button-5>",
            lambda e: self._grid_canvas.yview_scroll(1, "units"))

        self._update_layer_btns()
        if _PIL:
            self.after_idle(self._redraw_grid)

        ttk.Separator(d, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=6)

        # Logo slots
        logo_frm = ttk.LabelFrame(d, text="Logos del equipo", padding=4)
        logo_frm.pack(fill=tk.X, padx=8, pady=4)
        self._logo_imgs:     list[tk.Label]  = []
        self._logo_labels:   list[ttk.Label] = []
        self._logo_img_refs: list            = []
        for _ in range(Kits.LOGOS_PER_TEAM):
            cell = ttk.Frame(logo_frm)
            cell.pack(side=tk.LEFT, padx=6)
            img_lbl = tk.Label(cell, width=34, height=34,
                               bg="#cccccc", relief=tk.SUNKEN)
            img_lbl.pack()
            slot_lbl = ttk.Label(cell, text="-", anchor=tk.CENTER, width=6)
            slot_lbl.pack()
            self._logo_imgs.append(img_lbl)
            self._logo_labels.append(slot_lbl)

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh(self):
        self._ok = False
        self._listbox.delete(0, tk.END)
        if self._of is None or not hasattr(self._of, 'data') or not self._of.data:
            return
        for c in range(Clubs.TOTAL):
            self._listbox.insert(tk.END, Clubs.get_name(self._of, c))
        for n in range(Kits.TOTAL_N):
            label = Stats.NATION[n] if n < len(Stats.NATION) else f"Squad {n}"
            self._listbox.insert(tk.END, f"[N] {label}")
        self._ok = True
        self._team = -1
        self._clear_detail()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _clear_detail(self):
        self._lic_var.set(False)
        self._model_var.set(0)
        for btn in self._color_buttons.values():
            btn.config(bg="#cccccc", activebackground="#cccccc")
        self._cur_pat = [0] * len(_LAYERS)
        if hasattr(self, '_grid_canvas'):
            self._grid_canvas.delete("all")
            self._grid_thumbs = []
        self._logo_img_refs = [None] * Kits.LOGOS_PER_TEAM
        for l in range(Kits.LOGOS_PER_TEAM):
            self._logo_imgs[l].config(image="", bg="#cccccc")
            self._logo_labels[l].config(text="-")
        self._preview_canvas.delete("all")
        self._preview_ref = None
        self._update_tab_style()

    def _update_tab_style(self):
        for i, btn in enumerate(self._kit_btns):
            # ttk buttons don't reliably support 'pressed' on all themes;
            # use text decoration instead
            btn.config(text=(f"[{Kits.KIT_NAMES[i]}]"
                             if i == self._kit
                             else Kits.KIT_NAMES[i]))

    def _on_kit_tab(self, kit_idx: int):
        self._kit = kit_idx
        self._update_tab_style()
        if self._team >= 0 and self._ok:
            self._ok = False
            self._load_kit_data()
            self._ok = True

    def _on_select(self):
        if not self._ok:
            return
        sel = self._listbox.curselection()
        if not sel:
            return
        self._team = sel[0]
        self._ok = False

        self._lic_var.set(Kits.is_licensed(self._of, self._team))
        self._load_kit_data()

        # Refresh logos
        self._logo_img_refs = [None] * Kits.LOGOS_PER_TEAM
        for l in range(Kits.LOGOS_PER_TEAM):
            if Kits.logo_used(self._of, self._team, l):
                slot = Kits.get_logo_slot(self._of, self._team, l)
                self._logo_labels[l].config(text=f"#{slot}")
                self._draw_logo(l, slot)
            else:
                self._logo_imgs[l].config(image="", bg="#cccccc")
                self._logo_labels[l].config(text="-")

        self._ok = True

    def _load_kit_data(self):
        """Populate model spinbox + color buttons + patterns from current team/kit slot."""
        k, t = self._kit, self._team
        self._model_var.set(Kits.get_model(self._of, t, k))
        for off, btn in self._color_buttons.items():
            try:
                r, g, b = Kits.get_color_rgb(self._of, t, k, off)
                hx = f"#{r:02x}{g:02x}{b:02x}"
                btn.config(bg=hx, activebackground=hx)
            except Exception:
                btn.config(bg="#cccccc", activebackground="#cccccc")
        for li, (_, _, off, n_opts) in enumerate(_LAYERS):
            try:
                v = Kits.get_pattern_byte(self._of, t, k, off) % n_opts
            except Exception:
                v = 0
            self._cur_pat[li] = v
        self._redraw_preview()
        if _PIL and hasattr(self, '_grid_canvas'):
            self._redraw_grid()

    def _draw_logo(self, l: int, slot: int):
        lbl = self._logo_imgs[l]
        try:
            pixels = Logos.decode(self._of, slot, opaque=False)
            if _PIL and pixels is not None:
                img = Image.new("RGBA", (32, 32))
                img.putdata(pixels)
                bg = Image.new("RGBA", (34, 34), (204, 204, 204, 255))
                bg.paste(img, (1, 1), mask=img)
                ph = ImageTk.PhotoImage(bg)
                self._logo_img_refs[l] = ph
                lbl.config(image=ph, bg="#cccccc")
            else:
                lbl.config(image="", bg="#888888")
        except Exception:
            lbl.config(image="", bg="#888888")

    # ── Preview rendering ─────────────────────────────────────────────────────

    def _group_colors(self, group_key: str) -> list:
        """Return list of (r, g, b) for the named COLOR_GROUP in current kit."""
        for key, _label, base_off, count in Kits.COLOR_GROUPS:
            if key == group_key:
                out = []
                for i in range(count):
                    try:
                        out.append(Kits.get_color_rgb(
                            self._of, self._team, self._kit,
                            base_off + i * 2))
                    except Exception:
                        out.append((180, 180, 180))
                return out
        return [(180, 180, 180)]

    def _redraw_preview(self):
        if not _PIL or self._team < 0:
            return
        if _tmpl_shirt is None or _tmpl_pants is None or _tmpl_socks is None:
            return

        shirt_colors  = self._group_colors("shirt")
        shorts_colors = self._group_colors("shorts")
        socks_colors  = self._group_colors("socks")

        model  = self._model_var.get()
        is_gk  = (self._kit >= 2)   # tabs 2 and 3 are GK Home / GK Away
        scale  = _PREVIEW_SCALE

        # ── Shirt sprite ──────────────────────────────────────────────────────
        collar_type = self._cur_pat[0]
        if is_gk and _tmpl_gk is not None:
            shirt_cells = _GK_SHIRT_CELLS
            tmpl_s = _tmpl_gk
        else:
            shirt_cells = _SHIRT_CELLS
            tmpl_s = _tmpl_shirt

        sx0, sy0, sx1, sy1 = shirt_cells[collar_type % len(shirt_cells)]
        shirt_raw    = tmpl_s.crop((sx0, sy0, sx1, sy1)).convert('RGBA')
        shirt_tinted = _tint_sprite(shirt_raw, shirt_colors)
        shirt_big    = shirt_tinted.resize(
            (shirt_raw.width * scale, shirt_raw.height * scale), Image.NEAREST)

        # ── Shorts sprite ─────────────────────────────────────────────────────
        # Use model to select which pants pattern (8×8 grid = 64 patterns)
        pants_col = model % 8
        pants_row = (model // 8) % 8
        pants_raw    = _extract_cell(_tmpl_pants,
                                     _PANTS_COL, _PANTS_ROW,
                                     _PANTS_CW, _PANTS_CH,
                                     pants_col, pants_row)
        pants_tinted = _tint_sprite(pants_raw, shorts_colors)
        pants_big    = pants_tinted.resize(
            (pants_raw.width * scale, pants_raw.height * scale), Image.NEAREST)

        # ── Sock sprite ───────────────────────────────────────────────────────
        sock_col = (model // 2) % 8
        sock_row = (model // 16) % 4
        sock_raw    = _extract_cell(_tmpl_socks,
                                    _SOCK_COL, _SOCK_ROW,
                                    _SOCK_CW, _SOCK_CH,
                                    sock_col, sock_row)
        sock_tinted = _tint_sprite(sock_raw, socks_colors)
        sock_big    = sock_tinted.resize(
            (sock_raw.width * scale, sock_raw.height * scale), Image.NEAREST)

        # ── Composite ─────────────────────────────────────────────────────────
        bg_color = (208, 208, 208, 255)
        canvas_img = Image.new('RGBA', (_PW, _PH), bg_color)

        # Shirt — centered horizontally, near top
        sh_x = (_PW - shirt_big.width) // 2
        sh_y = 10
        canvas_img.paste(shirt_big, (sh_x, sh_y), shirt_big)

        # Shorts — centered, just below shirt
        pt_x = (_PW - pants_big.width) // 2
        pt_y = sh_y + shirt_big.height + 6
        canvas_img.paste(pants_big, (pt_x, pt_y), pants_big)

        # Socks — two side by side, centred below shorts
        gap       = 10
        total_sw  = sock_big.width * 2 + gap
        sk_xl     = (_PW - total_sw) // 2
        sk_xr     = sk_xl + sock_big.width + gap
        sk_y      = pt_y + pants_big.height + 6
        canvas_img.paste(sock_big, (sk_xl, sk_y), sock_big)
        canvas_img.paste(sock_big, (sk_xr, sk_y), sock_big)

        photo = ImageTk.PhotoImage(canvas_img)
        self._preview_ref = photo
        self._preview_canvas.delete("all")
        self._preview_canvas.create_image(0, 0, image=photo, anchor=tk.NW)

    # ── Pattern layer editor ──────────────────────────────────────────────────

    def _on_layer_btn(self, li: int):
        self._cur_layer = li
        self._update_layer_btns()
        if _PIL and hasattr(self, '_grid_canvas'):
            self._redraw_grid()

    def _update_layer_btns(self):
        for i, btn in enumerate(self._layer_btns):
            lname = _LAYERS[i][1]
            btn.config(text=f"[{lname}]" if i == self._cur_layer else lname)
        if hasattr(self, '_layer_title'):
            self._layer_title.config(text=_LAYER_TITLES[self._cur_layer])

    def _redraw_grid(self):
        if not _PIL or not hasattr(self, '_grid_canvas'):
            return
        canvas = self._grid_canvas
        canvas.delete("all")
        self._grid_thumbs = []

        li = self._cur_layer
        _, _, _, n_opts = _LAYERS[li]
        sel = self._cur_pat[li]

        if li == 0:
            colors = self._group_colors("shirt") if self._team >= 0 else [(180, 180, 180)]
            thumbs = [_collar_thumb(i, colors) for i in range(n_opts)]
        else:
            thumbs = [_layer_thumb(li, i) for i in range(n_opts)]

        row = col = 0
        for idx, img in enumerate(thumbs):
            x0 = TPAD + col * (TW + TPAD)
            y0 = TPAD + row * (TH + TPAD)
            ph = ImageTk.PhotoImage(img)
            self._grid_thumbs.append(ph)
            canvas.create_image(x0, y0, image=ph, anchor=tk.NW)
            border = "#ffff00" if idx == sel else "#666666"
            canvas.create_rectangle(x0 - 1, y0 - 1, x0 + TW, y0 + TH,
                                    outline=border, width=2)
            col += 1
            if col >= TCOLS:
                col = 0
                row += 1

        n_rows = (n_opts + TCOLS - 1) // TCOLS
        total_h = TPAD + n_rows * (TH + TPAD)
        total_w = TPAD + TCOLS * (TW + TPAD)
        canvas.configure(scrollregion=(0, 0, total_w, total_h))

    def _on_grid_click(self, event):
        cx = self._grid_canvas.canvasx(event.x)
        cy = self._grid_canvas.canvasy(event.y)
        col = int(cx - TPAD) // (TW + TPAD)
        row = int(cy - TPAD) // (TH + TPAD)
        if col < 0 or col >= TCOLS:
            return
        idx = row * TCOLS + col
        li = self._cur_layer
        _, _, off, n_opts = _LAYERS[li]
        if not (0 <= idx < n_opts):
            return
        x0 = TPAD + col * (TW + TPAD)
        y0 = TPAD + row * (TH + TPAD)
        if cx < x0 or cx >= x0 + TW or cy < y0 or cy >= y0 + TH:
            return
        self._cur_pat[li] = idx
        if self._ok and self._team >= 0:
            Kits.set_pattern_byte(self._of, self._team, self._kit, off, idx)
        self._redraw_grid()
        if li == 0:
            self._redraw_preview()

    # ── Edit handlers ─────────────────────────────────────────────────────────

    def _on_lic_change(self):
        if not self._ok or self._team < 0:
            return
        Kits.set_licensed(self._of, self._team, self._lic_var.get())

    def _on_model(self):
        if not self._ok or self._team < 0:
            return
        try:
            v = max(0, min(255, int(self._model_var.get())))
        except (ValueError, tk.TclError):
            return
        self._model_var.set(v)
        Kits.set_model(self._of, self._team, self._kit, v)
        self._redraw_preview()

    def _pick_color(self, offset: int, btn: tk.Button):
        if not self._ok or self._team < 0:
            return
        r, g, b = Kits.get_color_rgb(self._of, self._team, self._kit, offset)
        result = colorchooser.askcolor(
            color=f"#{r:02x}{g:02x}{b:02x}",
            title="Elegir color",
            parent=self)
        if result and result[0]:
            nr, ng, nb = (int(c) for c in result[0])
            Kits.set_color_rgb(self._of, self._team, self._kit, offset, nr, ng, nb)
            hx = f"#{nr:02x}{ng:02x}{nb:02x}"
            btn.config(bg=hx, activebackground=hx)
            self._redraw_preview()

    # ── Copy kit dialog ───────────────────────────────────────────────────────

    def _copy_kit_dialog(self):
        if self._team < 0:
            return
        is_club = self._team < Kits.TOTAL_C

        dlg = tk.Toplevel(self)
        dlg.title("Copiar kit de…")
        dlg.resizable(False, False)
        dlg.grab_set()

        ttk.Label(dlg, text="Seleccionar equipo fuente:").pack(padx=8, pady=(8, 2))
        sb = ttk.Scrollbar(dlg, orient=tk.VERTICAL)
        lb = tk.Listbox(dlg, width=30, height=20,
                        yscrollcommand=sb.set, exportselection=False)
        sb.config(command=lb.yview)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 8))

        teams = []
        if is_club:
            for c in range(Clubs.TOTAL):
                if c != self._team and not Kits.is_licensed(self._of, c):
                    lb.insert(tk.END, Clubs.get_name(self._of, c))
                    teams.append(c)
        else:
            for n in range(Kits.TOTAL_N):
                t = n + Kits.TOTAL_C
                if t != self._team and not Kits.is_licensed(self._of, t):
                    label = Stats.NATION[n] if n < len(Stats.NATION) else f"Squad {n}"
                    lb.insert(tk.END, f"[N] {label}")
                    teams.append(t)

        btn_row = ttk.Frame(dlg)
        btn_row.pack(fill=tk.X, padx=8, pady=(0, 8))

        def _do_copy():
            sel = lb.curselection()
            if not sel:
                return
            src = teams[sel[0]]
            Kits.import_kit_block(self._of, self._team, self._of, src)
            dlg.destroy()
            # Reload current team display
            self._ok = False
            t = self._team
            self._team = -1
            self._ok = True
            self._listbox.selection_set(t)
            self._on_select()

        ttk.Button(btn_row, text="Copiar",
                   command=_do_copy).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Cancelar",
                   command=dlg.destroy).pack(side=tk.LEFT, padx=4)
        dlg.wait_window()
