"""
PES Editor 6 - Python Port
Player edit dialog - single-panel layout matching the Java editor.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import stats as Stats
from player import Player


def _stat_bg(stat, v: int):
    """Return (bg, fg) colour for a 1-99 stat value, mirroring Java setStatColour."""
    if stat in (Stats.wfa, Stats.wff, Stats.consistency, Stats.condition):
        if v >= 7:
            return "#FF4040", "black"
        if v >= 6:
            return "#FFA500", "black"
        return None, None
    if v >= 95:
        return "#FF4040", "black"
    if v >= 90:
        return "#FFA500", "black"
    if v >= 80:
        return "#FFFF00", "black"
    if v >= 75:
        return "#B7FF00", "black"
    return None, None


_SIDE_LABELS = ["R side", "L side", "B side"]


class PlayerDialog(tk.Toplevel):
    def __init__(self, parent, of, player: Player):
        super().__init__(parent)
        self.title(f"Edit Player - {player.index} - {player.name}")
        self.resizable(False, False)
        self._of = of
        self._player = player
        self._vars = {}
        self._val_labels = {}
        self._build_ui()
        self.update_idletasks()
        self.grab_set()

    # ── top-level layout ──────────────────────────────────────────────────────
    def _build_ui(self):
        top = ttk.Frame(self, padding=4)
        top.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(top)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))

        mid = ttk.LabelFrame(top, text="1-99 Ability")
        mid.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))

        right = ttk.LabelFrame(top, text="Special Ability")
        right.pack(side=tk.LEFT, fill=tk.Y)

        self._build_general(left)
        self._build_positions(left)
        self._build_ability(mid)
        self._build_special(right)

        # Bottom buttons
        btn = ttk.Frame(self)
        btn.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(btn, text="Accept",         command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn, text="Cancel",         command=self.destroy).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn, text="Paste PSD Stats",command=self._paste_psd).pack(side=tk.LEFT, padx=4)

    # ── General section ───────────────────────────────────────────────────────
    def _build_general(self, parent):
        gen = ttk.LabelFrame(parent, text="General")
        gen.pack(fill=tk.X, pady=(0, 4))

        of   = self._of
        pidx = self._player.index

        def combo_row(row, label, stat, values):
            ttk.Label(gen, text=label).grid(row=row, column=0, sticky=tk.W, padx=4, pady=1)
            var = tk.StringVar(value=Stats.get_string(of, pidx, stat))
            cb  = ttk.Combobox(gen, textvariable=var, values=values,
                               width=18, state="readonly")
            cb.grid(row=row, column=1, sticky=tk.W, padx=4, pady=1)
            self._vars[stat] = var

        def entry_row(row, label, stat):
            ttk.Label(gen, text=label).grid(row=row, column=0, sticky=tk.W, padx=4, pady=1)
            var = tk.StringVar(value=Stats.get_string(of, pidx, stat))
            ttk.Entry(gen, textvariable=var, width=20).grid(
                row=row, column=1, sticky=tk.W, padx=4, pady=1)
            self._vars[stat] = var

        combo_row(0,  "Nationality",        Stats.nationality, list(Stats.NATION))
        entry_row(1,  "Age",                Stats.age)
        entry_row(2,  "Height",             Stats.height)
        entry_row(3,  "Weight",             Stats.weight)
        combo_row(4,  "Foot",               Stats.foot, ["R", "L"])
        combo_row(5,  "Fav Side",           Stats.fav_side, _SIDE_LABELS)
        combo_row(6,  "Weak Foot Accuracy", Stats.wfa,  ["1","2","3","4","5","6","7","8"])
        combo_row(7,  "Weak Foot Frequency",Stats.wff,  ["1","2","3","4","5","6","7","8"])
        combo_row(8,  "Consistency",        Stats.consistency, ["1","2","3","4","5","6","7","8"])
        combo_row(9,  "Condition",          Stats.condition,   ["1","2","3","4","5","6","7","8"])
        combo_row(10, "Injury Tolerancy",   Stats.injury,  ["C","B","A"])
        entry_row(11, "Dribble Style",      Stats.drib_sty)
        entry_row(12, "Free Kick Style",    Stats.freekick)
        entry_row(13, "Penalty Style",      Stats.pk_style)
        entry_row(14, "Drop Kick Style",    Stats.dk_sty)

    # ── Position section ──────────────────────────────────────────────────────
    def _build_positions(self, parent):
        pf   = ttk.LabelFrame(parent, text="Position")
        pf.pack(fill=tk.X)
        of   = self._of
        pidx = self._player.index

        def cb_cell(row, col, stat):
            var = tk.BooleanVar(value=bool(Stats.get_value(of, pidx, stat)))
            ttk.Checkbutton(pf, text=stat.name, variable=var).grid(
                row=row, column=col, sticky=tk.W, padx=2, pady=1)
            self._vars[stat] = var

        # GK on its own
        cb_cell(0, 0, Stats.gk)

        # 3 rows of 4
        others = [Stats.cwp, Stats.cbt, Stats.sb,  Stats.dm,
                  Stats.wb,  Stats.cm,  Stats.sm,  Stats.am,
                  Stats.wg,  Stats.ss,  Stats.cf]
        for i, stat in enumerate(others):
            cb_cell(1 + i // 4, i % 4, stat)

        # Registered position
        ttk.Label(pf, text="Registered Position").grid(
            row=4, column=0, columnspan=2, sticky=tk.W, padx=4, pady=(4, 1))
        reg_var = tk.StringVar(value=Stats.get_string(of, pidx, Stats.reg_pos))
        ttk.Combobox(pf, textvariable=reg_var, width=6, state="readonly",
                     values=["GK","CWP","CBT","SB","DM","WB","CM","SM","AM","WG","SS","CF"]
                     ).grid(row=4, column=2, columnspan=2, sticky=tk.W, padx=4)
        self._vars[Stats.reg_pos] = reg_var

    # ── 1-99 Ability section ──────────────────────────────────────────────────
    def _build_ability(self, parent):
        of   = self._of
        pidx = self._player.index

        # default bg to revert when value drops below threshold
        try:
            _default_bg = parent.winfo_toplevel().cget("bg")
        except Exception:
            _default_bg = "#F0F0F0"

        for i, s in enumerate(Stats.ability99):
            v          = Stats.get_value(of, pidx, s)
            row        = i % 13
            col_offset = (i // 13) * 3

            ttk.Label(parent, text=s.name, anchor=tk.E, width=12).grid(
                row=row, column=col_offset, sticky=tk.E, padx=(6, 1), pady=1)

            var = tk.StringVar(value=str(v))
            self._vars[s] = var

            bg, fg = _stat_bg(s, v)
            lbl = tk.Label(parent, textvariable=var, width=3, anchor=tk.CENTER,
                           relief=tk.RIDGE, font=("TkDefaultFont", 9, "bold"),
                           bg=bg or _default_bg,
                           fg=fg or "black")
            lbl.grid(row=row, column=col_offset + 1, sticky=tk.W, padx=(1, 6), pady=1)
            self._val_labels[s] = (lbl, _default_bg)

            var.trace_add("write",
                lambda *_, stat=s: self._refresh_val_color(stat))

    def _refresh_val_color(self, stat):
        if stat not in self._val_labels:
            return
        lbl, default_bg = self._val_labels[stat]
        try:
            v = int(self._vars[stat].get())
        except (ValueError, tk.TclError):
            return
        bg, fg = _stat_bg(stat, v)
        lbl.config(bg=bg or default_bg, fg=fg or "black")

    # ── Special Ability section ───────────────────────────────────────────────
    def _build_special(self, parent):
        of   = self._of
        pidx = self._player.index
        for i, s in enumerate(Stats.ability_special):
            var = tk.BooleanVar(value=bool(Stats.get_value(of, pidx, s)))
            ttk.Checkbutton(parent, text=s.name, variable=var).grid(
                row=i, column=0, sticky=tk.W, padx=4, pady=1)
            self._vars[s] = var

    # ── save / paste ──────────────────────────────────────────────────────────
    def _paste_psd(self):
        messagebox.showinfo("Paste PSD Stats",
                            "PSD Stats paste is not yet implemented.", parent=self)

    def _save(self):
        of   = self._of
        pidx = self._player.index
        for stat, var in self._vars.items():
            val = var.get()
            if isinstance(var, tk.BooleanVar):
                Stats.set_value(of, pidx, stat, 1 if val else 0)
            else:
                Stats.set_value_str(of, pidx, stat, str(val))
        self.destroy()
