"""
PES Editor 6 - Python Port
Kit Panel — visual colour editor.

KITINFO structure (62 bytes per kit slot):
  offsets  0-41  → colour WORDs (16-bit LE): 0x8000 | (B5<<10) | (G5<<5) | R5
  offset   42    → collar byte
  offsets 43-57  → pattern/type/location bytes
  offset   58    → kitType / licensed flag (1 = uses AFS texture)
  offset   60    → model number
"""
import tkinter as tk
from tkinter import ttk, colorchooser

import kits  as Kits
import clubs as Clubs
import logos as Logos
import stats  as Stats

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False


class KitPanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of   = of
        self._ok   = False
        self._team = -1
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Left: team list
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0), pady=6)

        ttk.Label(left, text="Team").pack()
        sb = ttk.Scrollbar(left, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(left, width=26, height=28,
                                   yscrollcommand=sb.set,
                                   exportselection=False)
        sb.config(command=self._listbox.yview)
        self._listbox.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self._listbox.bind("<<ListboxSelect>>",
                           lambda e: self.after_idle(self._on_select))

        # Right: scrollable detail panel
        right_outer = ttk.Frame(self)
        right_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        canvas = tk.Canvas(right_outer, highlightthickness=0)
        vsb = ttk.Scrollbar(right_outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._detail = ttk.Frame(canvas)
        self._detail_win = canvas.create_window((0, 0), window=self._detail,
                                                 anchor=tk.NW)
        self._detail.bind("<Configure>",
                          lambda e: canvas.configure(
                              scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self._detail_win, width=e.width))
        self._canvas = canvas
        self._build_detail()

    def _build_detail(self):
        d = self._detail

        # Top row: licensed checkbox + copy button
        self._lic_var = tk.BooleanVar()
        top_row = ttk.Frame(d)
        top_row.pack(anchor=tk.W, padx=8, pady=(8, 2))
        self._lic_cb = ttk.Checkbutton(
            top_row, text="Licensed kit (uses AFS texture)",
            variable=self._lic_var, command=self._on_lic_change)
        self._lic_cb.pack(side=tk.LEFT)
        self._copy_btn = ttk.Button(top_row, text="Copy kit from…",
                                    command=self._copy_kit_dialog)
        self._copy_btn.pack(side=tk.LEFT, padx=16)

        ttk.Separator(d, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # One LabelFrame per kit slot (Home / Away / 3rd / GK)
        # _kit_data[k] = (model_var, [(offset, btn), ...])
        self._kit_data = []

        for k, kit_name in enumerate(Kits.KIT_NAMES):
            frm = ttk.LabelFrame(d, text=kit_name, padding=6)
            frm.pack(fill=tk.X, padx=8, pady=4)

            # Model spinbox
            model_var = tk.IntVar()
            model_row = ttk.Frame(frm)
            model_row.pack(anchor=tk.W, pady=(0, 6))
            ttk.Label(model_row, text="Model:").pack(side=tk.LEFT)
            spin = ttk.Spinbox(model_row, from_=0, to=255, width=5,
                               textvariable=model_var)
            spin.pack(side=tk.LEFT, padx=4)
            spin.bind("<FocusOut>",
                      lambda e, ki=k, mv=model_var: self._on_model(ki, mv))
            spin.bind("<Return>",
                      lambda e, ki=k, mv=model_var: self._on_model(ki, mv))

            # Colour groups
            color_buttons = []   # list of (kitinfo_offset, tk.Button)
            for _, label, base_off, count in Kits.COLOR_GROUPS:
                row = ttk.Frame(frm)
                row.pack(anchor=tk.W, pady=1)
                ttk.Label(row, text=f"{label}:", width=9,
                          anchor=tk.E).pack(side=tk.LEFT, padx=(0, 4))
                for i in range(count):
                    off = base_off + i * 2
                    btn = tk.Button(row, width=3, height=1,
                                    relief=tk.RAISED, cursor="hand2", bd=1)
                    # Capture kit index, offset and the button itself in the closure
                    btn.config(
                        command=lambda ki=k, o=off, b=btn: self._pick_color(ki, o, b))
                    btn.pack(side=tk.LEFT, padx=1)
                    color_buttons.append((off, btn))

            self._kit_data.append((model_var, color_buttons))

        ttk.Separator(d, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # Logo thumbnails
        logo_frm = ttk.LabelFrame(d, text="Logo slots", padding=4)
        logo_frm.pack(fill=tk.X, padx=8, pady=3)
        self._logo_imgs     = []
        self._logo_labels   = []
        self._logo_img_refs = []
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

    # ── public API ────────────────────────────────────────────────────────────

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

    # ── internal helpers ──────────────────────────────────────────────────────

    def _clear_detail(self):
        self._lic_var.set(False)
        for k in range(Kits.KITS_PER_TEAM):
            model_var, color_buttons = self._kit_data[k]
            model_var.set(0)
            for _, btn in color_buttons:
                btn.config(bg="#cccccc", activebackground="#cccccc")
        self._logo_img_refs = [None] * Kits.LOGOS_PER_TEAM
        for l in range(Kits.LOGOS_PER_TEAM):
            self._logo_imgs[l].config(image="", bg="#cccccc")
            self._logo_labels[l].config(text="-")

    def _on_select(self):
        if not self._ok:
            return
        sel = self._listbox.curselection()
        if not sel:
            return
        t = sel[0]
        self._team = t
        self._ok = False

        self._lic_var.set(Kits.is_licensed(self._of, t))

        for k in range(Kits.KITS_PER_TEAM):
            model_var, color_buttons = self._kit_data[k]
            model_var.set(Kits.get_model(self._of, t, k))
            for off, btn in color_buttons:
                try:
                    r, g, b = Kits.get_color_rgb(self._of, t, k, off)
                    hex_c = f"#{r:02x}{g:02x}{b:02x}"
                    btn.config(bg=hex_c, activebackground=hex_c)
                except Exception:
                    btn.config(bg="#cccccc", activebackground="#cccccc")

        self._logo_img_refs = [None] * Kits.LOGOS_PER_TEAM
        for l in range(Kits.LOGOS_PER_TEAM):
            if Kits.logo_used(self._of, t, l):
                slot = Kits.get_logo_slot(self._of, t, l)
                self._logo_labels[l].config(text=f"#{slot}")
                self._draw_logo(l, slot)
            else:
                self._logo_imgs[l].config(image="", bg="#cccccc")
                self._logo_labels[l].config(text="-")

        self._ok = True

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

    # ── edit handlers ─────────────────────────────────────────────────────────

    def _on_lic_change(self):
        if not self._ok or self._team < 0:
            return
        Kits.set_licensed(self._of, self._team, self._lic_var.get())

    def _on_model(self, kit: int, model_var: tk.IntVar):
        if not self._ok or self._team < 0:
            return
        try:
            v = max(0, min(255, int(model_var.get())))
        except (ValueError, tk.TclError):
            return
        model_var.set(v)
        Kits.set_model(self._of, self._team, kit, v)

    def _pick_color(self, kit: int, offset: int, btn: tk.Button):
        if not self._ok or self._team < 0:
            return
        r, g, b = Kits.get_color_rgb(self._of, self._team, kit, offset)
        result = colorchooser.askcolor(
            color=f"#{r:02x}{g:02x}{b:02x}",
            title="Choose colour",
            parent=self)
        if result and result[0]:
            nr, ng, nb = (int(c) for c in result[0])
            Kits.set_color_rgb(self._of, self._team, kit, offset, nr, ng, nb)
            hex_c = f"#{nr:02x}{ng:02x}{nb:02x}"
            btn.config(bg=hex_c, activebackground=hex_c)

    # ── copy kit dialog ───────────────────────────────────────────────────────

    def _copy_kit_dialog(self):
        if self._team < 0:
            return
        is_club = self._team < Kits.TOTAL_C

        dlg = tk.Toplevel(self)
        dlg.title("Copy kit from…")
        dlg.resizable(False, False)
        dlg.update_idletasks()
        dlg.grab_set()

        ttk.Label(dlg, text="Select source team:").pack(padx=8, pady=(8, 2))

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
            self._ok = False
            t = self._team
            self._team = -1
            self._ok = True
            self._listbox.selection_set(t)
            self._on_select()

        ttk.Button(btn_row, text="Copy",   command=_do_copy).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Cancel",
                   command=dlg.destroy).pack(side=tk.LEFT, padx=4)
        dlg.wait_window()
