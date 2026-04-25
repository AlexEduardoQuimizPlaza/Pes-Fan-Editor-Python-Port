"""
PES Editor 6 - Python Port
Team Panel — matches Java TeamPanel layout:
  Left  : scrollable list  "ABV   Full Name" (clubs) + nations + extras
  Right : detail panel (visible only for club selections)
          • Name text field  (press Return to save)
          • Abbreviation field (3 chars, press Return to save)
          • Emblem preview canvas
          • Flag section: colour 1 / colour 2 buttons + flag preview
          • Stadium dropdown (auto-saves on selection)
          • Team-stats pentagon (ATQ / DF / TEC / VCD / TEQ — averaged from
            the squad, mirrors the in-game team-select pentagon)
"""
import math
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import clubs  as Clubs
import squads as Squads
import stadia as Stadia
import stats  as Stats

# Pentagon vertex order is clockwise from the top, matching the in-game
# team-select view: TEQ (top), DF (upper-right), TEC (lower-right),
# VCD (lower-left), ATQ (upper-left).
_PENTAGON = [
    ("TEQ", "team"),     # Team Work
    ("DF",  "defence"),
    ("TEC", "tech"),
    ("VCD", "speed"),
    ("ATQ", "attack"),
]

_EXTRA_SQUAD = [
    "Classic England", "Classic France", "Classic Germany",
    "Classic Italy", "Classic Netherlands", "Classic Argentina",
    "Classic Brazil",
]


class TeamPanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of       = of
        self._selected = -1   # current club index (-1 = none / nation / extra)
        self._ok       = False  # guard for spurious list-change events
        self._build_ui()

    # ── construction ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Left: list ────────────────────────────────────────────────────
        lf = ttk.Frame(self)
        lf.pack(side=tk.LEFT, fill=tk.Y)

        sb = ttk.Scrollbar(lf)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox = tk.Listbox(lf, yscrollcommand=sb.set,
                                   width=24, height=35,
                                   font=("Courier", 10),
                                   exportselection=False)
        self._listbox.pack(side=tk.LEFT, fill=tk.Y)
        sb.config(command=self._listbox.yview)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # ── Right: detail (hidden until a club is chosen) ─────────────────
        self._detail = ttk.Frame(self)
        self._detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_detail(self._detail)
        self._detail.pack_forget()

    def _build_detail(self, d):
        # Everything centred horizontally (BoxLayout.Y_AXIS equivalent)
        inner = ttk.Frame(d)
        inner.pack(expand=True, fill=tk.BOTH)

        # Name text field
        name_frame = ttk.Frame(inner)
        name_frame.pack(pady=4)
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(name_frame, textvariable=self._name_var,
                                     width=30)
        self._name_entry.pack()
        self._name_entry.bind("<Return>", self._set_name)

        # Abbreviation (3-char)
        abv_frame = ttk.Frame(inner)
        abv_frame.pack(pady=2)
        self._abv_var = tk.StringVar()
        self._abv_entry = ttk.Entry(abv_frame, textvariable=self._abv_var,
                                    width=6, justify=tk.CENTER)
        self._abv_entry.pack()
        self._abv_entry.bind("<Return>", self._set_abv)

        # ── Emblem ────────────────────────────────────────────────────────
        ttk.Label(inner, text="Emblem", anchor=tk.CENTER).pack(fill=tk.X, pady=(10, 2))
        self._emblem_canvas = tk.Canvas(inner, width=72, height=72,
                                         bg="#CCCCCC", relief=tk.RAISED,
                                         borderwidth=2, cursor="hand2")
        self._emblem_canvas.pack()
        # "Default" text placeholder
        self._emblem_canvas.create_text(36, 36, text="Default",
                                         font=("TkDefaultFont", 11, "bold"),
                                         fill="#555555", tags="default_lbl")
        # Left-click → choose emblem,  right-click → reset to default
        self._emblem_canvas.bind("<Button-1>", self._on_emblem_click)
        self._emblem_canvas.bind("<Button-3>", self._on_emblem_reset)

        # ── Flag ──────────────────────────────────────────────────────────
        ttk.Label(inner, text="Flag", anchor=tk.CENTER).pack(fill=tk.X, pady=(10, 2))
        flag_outer = ttk.Frame(inner)
        flag_outer.pack()

        # Fila de controles: [↓Copy]  [color1][color2]  [↑Swap]
        col_row = ttk.Frame(flag_outer)
        col_row.pack()

        self._copy_btn = tk.Button(col_row, text="↓", width=2,
                                    relief=tk.RAISED, command=self._copy_color)
        self._copy_btn.pack(side=tk.LEFT, padx=2)

        colors_frame = ttk.Frame(col_row)
        colors_frame.pack(side=tk.LEFT)
        self._color1_btn = tk.Button(colors_frame, width=3, height=1,
                                      relief=tk.RAISED, bg="#FFFFFF",
                                      command=self._pick_color1)
        self._color1_btn.pack(side=tk.LEFT, padx=1)
        self._color2_btn = tk.Button(colors_frame, width=3, height=1,
                                      relief=tk.RAISED, bg="#000000",
                                      command=self._pick_color2)
        self._color2_btn.pack(side=tk.LEFT, padx=1)

        self._swap_btn = tk.Button(col_row, text="↑", width=2,
                                    relief=tk.RAISED, command=self._swap_colors)
        self._swap_btn.pack(side=tk.LEFT, padx=2)

        # Canvas de bandera — click para elegir patrón
        self._flag_canvas = tk.Canvas(flag_outer, width=85, height=64,
                                       bg="#CCCCCC", relief=tk.RAISED,
                                       borderwidth=2, cursor="hand2")
        self._flag_canvas.pack(pady=2)
        self._flag_canvas.bind("<Button-1>", self._on_flag_click)
        self._flag_photo = None   # referencia PhotoImage (evitar GC)

        # ── Stadium ───────────────────────────────────────────────────────
        ttk.Label(inner, text="Stadium", anchor=tk.CENTER).pack(fill=tk.X, pady=(20, 2))
        self._stad_var   = tk.StringVar()
        self._stad_combo = ttk.Combobox(inner, textvariable=self._stad_var,
                                         width=30, state="readonly")
        self._stad_combo.pack(pady=2)
        self._stad_combo.bind("<<ComboboxSelected>>", self._set_stadium)

        # ── Team stats pentagon ───────────────────────────────────────────
        ttk.Label(inner, text="Team stats", anchor=tk.CENTER).pack(
            fill=tk.X, pady=(16, 2))
        self._pentagon_canvas = tk.Canvas(inner, width=180, height=160,
                                          bg="#2a2e36", highlightthickness=0)
        self._pentagon_canvas.pack(pady=(2, 8))

    # ── public API ────────────────────────────────────────────────────────────
    def refresh(self):
        if self._of is None:
            return
        self._ok = False
        self._listbox.delete(0, tk.END)

        # Clubs:  "ABV   Name"
        for c in range(Clubs.TOTAL):
            abv  = Clubs.get_abbr(self._of, c)
            name = Clubs.get_name(self._of, c)
            self._listbox.insert(tk.END, f"{abv:<3}  {name}")

        # National teams
        for n in Stats.NATION[:57]:
            self._listbox.insert(tk.END, n)

        # Extra squads
        for e in _EXTRA_SQUAD:
            self._listbox.insert(tk.END, e)

        # Stadium dropdown
        self._stad_combo["values"] = Stadia.get_names(self._of)

        # Hide detail panel until a club is picked
        self._detail.pack_forget()
        self._selected = -1
        self._ok = True

    # ── list selection ────────────────────────────────────────────────────────
    def _on_select(self, _event):
        if not self._ok:
            return
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < Clubs.TOTAL:
            self._selected = idx
            self._load_club(idx)
            self._detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        else:
            self._selected = -1
            self._detail.pack_forget()

    def _load_club(self, club: int):
        of = self._of
        self._name_var.set(Clubs.get_name(of, club))
        self._abv_var.set(Clubs.get_abbr(of, club))

        # Emblem
        self._draw_emblem(club)

        # Colors + flag pattern
        r1, g1, b1 = Clubs.get_color1(of, club)
        r2, g2, b2 = Clubs.get_color2(of, club)
        self._color1_btn.config(bg=f"#{r1:02x}{g1:02x}{b1:02x}")
        self._color2_btn.config(bg=f"#{r2:02x}{g2:02x}{b2:02x}")
        self._draw_flag()

        # Stadium
        stad_idx   = Clubs.get_stadium(of, club)
        stad_names = Stadia.get_names(of)
        if stad_idx < len(stad_names):
            self._stad_var.set(stad_names[stad_idx])

        # Pentagon
        self._draw_pentagon(club)

    # ── pentagon ──────────────────────────────────────────────────────────────
    def _compute_pentagon(self, club: int):
        """Average the 5 pentagon stats across the squad. Returns dict or None.

        Some squad slots reference player IDs that fall outside the editable
        range (between TOTAL and FIRST_EDIT, or above 32951) — these are
        in-game placeholder players whose stat block is not in the OF buffer.
        We skip them so we don't read past the end of of.data.
        """
        from player import TOTAL, FIRST_EDIT
        squad_team = 73 + club
        pids = []
        for s in range(32):
            pid = Squads.get_squad_player(self._of, squad_team, s)
            if pid <= 0:
                continue
            if (TOTAL <= pid < FIRST_EDIT) or pid > 32951:
                continue
            pids.append(pid)
        if not pids:
            return None
        sums = {label: 0 for label, _ in _PENTAGON}
        for pid in pids:
            try:
                for label, attr in _PENTAGON:
                    sums[label] += Stats.get_value(self._of, pid,
                                                   getattr(Stats, attr))
            except IndexError:
                # Defensive: skip if the address still falls outside the buffer
                continue
        n = len(pids)
        return {k: round(v / n) for k, v in sums.items()}

    def _draw_pentagon(self, club: int):
        c = self._pentagon_canvas
        c.delete("all")
        W, H = int(c["width"]), int(c["height"])
        cx, cy = W // 2, H // 2 + 4
        R = 50
        values = self._compute_pentagon(club)
        if values is None:
            c.create_text(cx, cy, text="(sin plantel)", fill="#888")
            return

        def vertex(angle, radius):
            return cx + radius * math.cos(angle), cy + radius * math.sin(angle)

        # Concentric reference rings at 25/50/75/100% — feedback for "how full"
        for pct in (0.25, 0.5, 0.75, 1.0):
            pts = []
            for i in range(5):
                ang = -math.pi / 2 + i * 2 * math.pi / 5
                pts.extend(vertex(ang, R * pct))
            c.create_polygon(*pts, outline="#555", fill="",
                             width=1, dash=() if pct == 1.0 else (2, 2))

        # Spokes
        for i in range(5):
            ang = -math.pi / 2 + i * 2 * math.pi / 5
            x, y = vertex(ang, R)
            c.create_line(cx, cy, x, y, fill="#555")

        # Filled value polygon
        pts = []
        for i, (label, _attr) in enumerate(_PENTAGON):
            ratio = max(0.05, min(1.0, values[label] / 99.0))
            ang = -math.pi / 2 + i * 2 * math.pi / 5
            pts.extend(vertex(ang, R * ratio))
        c.create_polygon(*pts, outline="#7fb1ff", fill="#3268c4",
                         stipple="gray50", width=2)

        # Vertex labels with value
        label_R = R + 18
        for i, (label, _attr) in enumerate(_PENTAGON):
            ang = -math.pi / 2 + i * 2 * math.pi / 5
            x, y = vertex(ang, label_R)
            c.create_text(x, y, text=f"{label} {values[label]}",
                          font=("TkDefaultFont", 8, "bold"), fill="#e0e0e0")

    # ── emblem click / reset ──────────────────────────────────────────────────
    def _on_emblem_click(self, _event=None):
        """Left-click: open Choose Emblem dialog."""
        if self._selected < 0 or self._of is None:
            return
        from gui.emblem_chooser_dialog import EmblemChooserDialog
        val = EmblemChooserDialog.choose(self, self._of)
        if val != -1:
            Clubs.set_emblem_int(self._of, self._selected, val)
            self._draw_emblem(self._selected)

    def _on_emblem_reset(self, _event=None):
        """Right-click: reset emblem to default."""
        if self._selected < 0 or self._of is None:
            return
        Clubs.reset_emblem(self._of, self._selected)
        self._draw_emblem(self._selected)

    # ── emblem rendering ──────────────────────────────────────────────────────
    def _draw_emblem(self, club: int):
        import sys
        import emblems as Emblems
        c = self._emblem_canvas
        c.delete("all")
        W = 72

        def _placeholder(text, fg="#555555"):
            c.create_rectangle(0, 0, W, W, fill="#CCCCCC", outline="")
            c.create_text(W // 2, W // 2, text=text,
                          font=("TkDefaultFont", 9, "bold"), fill=fg)

        emblem_idx = Clubs.get_emblem(self._of, club)
        def_idx    = club + Clubs.FIRST_DEF_EMBLEM

        if emblem_idx == def_idx or emblem_idx == 0:
            _placeholder("Default")
            return

        adj_idx = emblem_idx - Clubs.FIRST_FLAG
        if adj_idx < 0:
            # Emblem stored in game data, not in the user-emblem area of the OF.
            # Python can't decode it — show a neutral placeholder.
            _placeholder("Built-in")
            return

        try:
            pixels = Emblems.decode_by_adj(self._of, adj_idx, opaque=False)
        except (IndexError, ValueError) as e:
            # Indirection-table entry pointed outside the OF buffer (corrupted
            # or unsupported emblem variant). Skip rather than break the panel.
            print(f"[draw_emblem] club={club} adj={adj_idx} decode failed: {e}",
                  file=sys.stderr)
            _placeholder("Bad data", "#CC0000")
            return
        if pixels is None:
            _placeholder("Empty")
            return

        try:
            from PIL import Image, ImageTk
            src = Emblems.IMG_SIZE   # 64
            pil = Image.new("RGBA", (src, src))
            pil.putdata(pixels)
            pil = pil.resize((W, W), Image.NEAREST)
            bg  = Image.new("RGBA", (W, W), (204, 204, 204, 255))
            bg.paste(pil, mask=pil)
            ph = ImageTk.PhotoImage(bg)
            c.create_image(0, 0, anchor=tk.NW, image=ph)
            c._emblem_img = ph          # prevent GC
        except Exception as e:
            print(f"[draw_emblem] club={club} adj={adj_idx}: {e}", file=sys.stderr)
            _placeholder("Error", "#CC0000")

    # ── flag click → elegir patrón ────────────────────────────────────────────
    def _on_flag_click(self, _event=None):
        if self._selected < 0 or self._of is None:
            return
        from gui.back_chooser_dialog import BackChooserDialog
        r1, g1, b1 = Clubs.get_color1(self._of, self._selected)
        r2, g2, b2 = Clubs.get_color2(self._of, self._selected)
        result = BackChooserDialog.choose(self, r1, g1, b1, r2, g2, b2)
        if result != -1:
            Clubs.set_back(self._of, self._selected, result)
            self._draw_flag()

    # ── renderizar bandera con patrón real ────────────────────────────────────
    def _draw_flag(self):
        if self._selected < 0 or self._of is None:
            return
        from gui.back_chooser_dialog import render_flag_pattern
        from PIL import ImageTk
        r1, g1, b1 = Clubs.get_color1(self._of, self._selected)
        r2, g2, b2 = Clubs.get_color2(self._of, self._selected)
        back = Clubs.get_back(self._of, self._selected)
        try:
            img = render_flag_pattern(back, r1, g1, b1, r2, g2, b2)
            ph  = ImageTk.PhotoImage(img)
            self._flag_photo = ph
            self._flag_canvas.delete("all")
            self._flag_canvas.create_image(0, 0, anchor=tk.NW, image=ph)
        except Exception:
            # Fallback: dos franjas
            c = self._flag_canvas
            c.delete("all")
            c.create_rectangle(0,  0, 85, 32, fill=f"#{r1:02x}{g1:02x}{b1:02x}", outline="")
            c.create_rectangle(0, 32, 85, 64, fill=f"#{r2:02x}{g2:02x}{b2:02x}", outline="")

    # ── save handlers ─────────────────────────────────────────────────────────
    def _set_name(self, _event=None):
        if self._selected < 0:
            return
        text = self._name_var.get().strip()
        if 0 < len(text) <= 48:
            Clubs.set_name(self._of, self._selected, text)
            self._refresh_list_item(self._selected)

    def _set_abv(self, _event=None):
        if self._selected < 0:
            return
        text = self._abv_var.get().strip().upper()
        if len(text) == 3:
            Clubs.set_abbr(self._of, self._selected, text)
            self._refresh_list_item(self._selected)

    def _refresh_list_item(self, club: int):
        abv  = Clubs.get_abbr(self._of, club)
        name = Clubs.get_name(self._of, club)
        self._listbox.delete(club)
        self._listbox.insert(club, f"{abv:<3}  {name}")
        self._listbox.selection_set(club)

    def _pick_color1(self):
        if self._selected < 0:
            return
        r, g, b = Clubs.get_color1(self._of, self._selected)
        result = colorchooser.askcolor(color=f"#{r:02x}{g:02x}{b:02x}",
                                       title="Colour 1", parent=self)
        if result and result[0]:
            rgb = tuple(int(c) for c in result[0])
            Clubs.set_color1(self._of, self._selected, *rgb)
            self._color1_btn.config(bg=result[1])
            self._draw_flag()

    def _pick_color2(self):
        if self._selected < 0:
            return
        r, g, b = Clubs.get_color2(self._of, self._selected)
        result = colorchooser.askcolor(color=f"#{r:02x}{g:02x}{b:02x}",
                                       title="Colour 2", parent=self)
        if result and result[0]:
            rgb = tuple(int(c) for c in result[0])
            Clubs.set_color2(self._of, self._selected, *rgb)
            self._color2_btn.config(bg=result[1])
            self._draw_flag()

    def _copy_color(self):
        """Copiar color 1 → color 2."""
        if self._selected < 0:
            return
        r, g, b = Clubs.get_color1(self._of, self._selected)
        Clubs.set_color2(self._of, self._selected, r, g, b)
        self._color2_btn.config(bg=f"#{r:02x}{g:02x}{b:02x}")
        self._draw_flag()

    def _swap_colors(self):
        """Intercambiar color 1 ↔ color 2."""
        if self._selected < 0:
            return
        r1, g1, b1 = Clubs.get_color1(self._of, self._selected)
        r2, g2, b2 = Clubs.get_color2(self._of, self._selected)
        Clubs.set_color1(self._of, self._selected, r2, g2, b2)
        Clubs.set_color2(self._of, self._selected, r1, g1, b1)
        self._color1_btn.config(bg=f"#{r2:02x}{g2:02x}{b2:02x}")
        self._color2_btn.config(bg=f"#{r1:02x}{g1:02x}{b1:02x}")
        self._draw_flag()

    def _set_stadium(self, _event=None):
        if self._selected < 0:
            return
        stads = Stadia.get_names(self._of)
        name  = self._stad_var.get()
        if name in stads:
            Clubs.set_stadium(self._of, self._selected, stads.index(name))
