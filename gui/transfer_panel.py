"""
PES Editor 6 – Python Port
Transfer Panel – three-column layout matching the Java editor:
  Left column  : Squad A  (team dropdown + pos / name / shirt-num listboxes)
  Centre column: Free players (nation filter + alpha-sort + player list)
  Right column : Squad B  (same structure as Squad A)
  Bottom       : shirt-num / name / shirt-name editors, checkboxes, info panel
"""
import tkinter as tk
from tkinter import ttk, simpledialog

import stats      as Stats
import squads     as Squads
import clubs      as Clubs
import formations as Formations
from player import (Player, TOTAL, FIRST_EDIT, TOTAL_EDIT,
                    FIRST_CLASSIC, FIRST_CLUB, FIRST_ML,
                    FIRST_YOUNG, FIRST_OLD, FIRST_UNUSED)

# ── constants ──────────────────────────────────────────────────────────────────
_EXTRA_SQUAD = [
    "Classic England", "Classic France", "Classic Germany", "Classic Italy",
    "Classic Netherlands", "Classic Argentina", "Classic Brazil",
    "<Japan 1>", "<Edited> National 1", "<Edited> National 2",
    "<Edited> National 3", "<Edited> National 4", "<Edited> National 5",
    "<Edited> National 6", "<Edited> National 7", "<Edited>",
    "<ML Default>", "<Shop 1>", "<Shop 2>", "<Shop 3>", "<Shop 4>", "<Shop 5>",
]

# Map formation position code → label  (mirrors PositionList.java)
_POS_MAP = {
    0: "GK",  1: "CBT", 2: "CBT", 3: "CBT", 4: "CWP", 5: "ASW",
    6: "CBT", 7: "CBT", 8: "LB",  9: "RB",
    10: "DM", 11: "DM", 12: "DM", 13: "DM", 14: "DM",
    15: "LWB", 16: "RWB",
    17: "CM",  18: "CM",  19: "CM",  20: "CM",  21: "CM",
    22: "LM",  23: "RM",
    24: "AM",  25: "AM",  26: "AM",  27: "AM",  28: "AM",
    29: "LW",  30: "RW",
    31: "SS",  32: "SS",  33: "SS",  34: "SS",  35: "SS",
    36: "CF",  37: "CF",  38: "CF",  39: "CF",  40: "CF",
}

_NATION_SPECIAL = ["Unused", "ML Old", "ML Young", "Duplicates?",
                   "Free Agents", "All Players"]

# Stat colour thresholds matching Java InfoPanel.setStatColour
_COL_99 = [
    (95, "stat_red"),
    (90, "stat_orange"),
    (80, "stat_yellow"),
    (75, "stat_lime"),
]

def _stat_tag(stat, v: int) -> str:
    """Return colour tag for a stat value (mirrors Java setStatColour)."""
    from stats import wfa, wff, consistency, condition
    if stat in (wfa, wff, consistency, condition):
        if v >= 7: return "stat_red"
        if v >= 6: return "stat_orange"
        return "stat_white"
    for threshold, tag in _COL_99:
        if v >= threshold:
            return tag
    return "stat_white"


def _find_player_squads(of, player_idx: int) -> list:
    """Return list of squad name strings containing this player."""
    names, indices = _build_team_list(of)
    idx_to_name = {v: names[i] for i, v in enumerate(indices) if v is not None}
    result = []
    for sq in range(64):
        for slot in range(23):
            if Squads.get_squad_player(of, sq, slot) == player_idx:
                result.append(idx_to_name.get(sq, f"<squad {sq}>"))
                break
    for sq in range(73, 73 + Clubs.TOTAL):
        for slot in range(32):
            if Squads.get_squad_player(of, sq, slot) == player_idx:
                result.append(idx_to_name.get(sq, f"<squad {sq}>"))
                break
    return result


# ── helpers ────────────────────────────────────────────────────────────────────
def _unicode_font(size: int = 10):
    import tkinter.font as tkfont
    available = set(tkfont.families())
    for name in ("Noto Sans", "DejaVu Sans", "FreeSans",
                 "Arial Unicode MS", "Segoe UI"):
        if name in available:
            return (name, size)
    return ("TkDefaultFont", size)


def _is_real(name: str) -> bool:
    if not name or name.startswith("<"):
        return False
    return all(ch.isprintable() and ch not in "\x7f\xa0" for ch in name)


def _pos_label(of, squad_t: int, slot: int) -> str:
    """Position abbreviation for a formation slot (mirrors PositionList.java)."""
    if slot == 0:
        return "GK"
    if slot >= 11:
        return ""
    try:
        p = Formations.get_pos(of, squad_t, 0, slot)
    except Exception:
        return ""
    if p > 40:
        return str(p)
    return _POS_MAP.get(p, "")


def _squad_t(squad_idx: int) -> int:
    """Convert squad_idx to formation table index (mirrors Java t calculation)."""
    if squad_idx < 64:
        return squad_idx
    if squad_idx >= 73:
        return squad_idx - 9
    return squad_idx


def _squad_size(squad_idx: int) -> int:
    return 32 if squad_idx >= 73 else 23


def _build_team_list(of):
    """Return (names, indices) for the team combo (combo_index == squad_index + 1 offset)."""
    nation_names = list(Stats.NATION[:57])
    club_names   = Clubs.get_names(of)
    names = (["– select –"]
             + nation_names
             + list(_EXTRA_SQUAD[:16])
             + club_names
             + list(_EXTRA_SQUAD[16:]))
    indices = ([None]
               + list(range(57))
               + list(range(57, 73))
               + list(range(73, 73 + len(club_names)))
               + list(range(213, 213 + len(_EXTRA_SQUAD[16:]))))
    return names, indices


# ── SquadPane ──────────────────────────────────────────────────────────────────
class SquadPane(ttk.Frame):
    """One team column: dropdown + pos / name / shirt-number parallel listboxes."""

    def __init__(self, parent, of, label: str, on_select_cb=None, on_edit_cb=None):
        super().__init__(parent, relief=tk.RIDGE, borderwidth=1)
        self._of          = of
        self._label       = label
        self._on_select   = on_select_cb   # (player, squad_idx, slot)
        self._on_edit     = on_edit_cb     # (player)
        self._squad_idx   = None
        self._slots       = []             # [(player_or_None, slot_int), ...]
        self._team_names  = []
        self._team_indices= []
        self._font        = _unicode_font()
        self._active      = False          # is this the "target" squad?
        self._build()

    # ── construction ──────────────────────────────────────────────────────────
    def _build(self):
        ttk.Label(self, text=self._label, font=_unicode_font(9)).pack(
            fill=tk.X, padx=2)

        # Team dropdown
        self._team_var = tk.StringVar(value="– select –")
        self._team_combo = ttk.Combobox(self, textvariable=self._team_var,
                                         width=22, state="readonly",
                                         font=self._font)
        self._team_combo.pack(fill=tk.X, padx=2, pady=(0, 2))
        self._team_combo.bind("<<ComboboxSelected>>", self._on_team_sel)

        # Three parallel listboxes inside a shared frame
        lf = ttk.Frame(self)
        lf.pack(fill=tk.BOTH, expand=True, padx=2)

        self._sb = ttk.Scrollbar(lf, orient=tk.VERTICAL)
        self._sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._lb_pos = tk.Listbox(lf, width=4, height=26,
                                  font=self._font, background="#FFFFDF",
                                  selectmode=tk.EXTENDED,
                                  exportselection=False,
                                  activestyle="none")
        self._lb_pos.pack(side=tk.LEFT, fill=tk.Y)

        self._lb_num = tk.Listbox(lf, width=3, height=26,
                                  font=self._font,
                                  exportselection=False,
                                  activestyle="none")
        self._lb_num.pack(side=tk.RIGHT, fill=tk.Y)

        self._lb_name = tk.Listbox(lf, width=16, height=26,
                                   font=self._font,
                                   exportselection=False,
                                   selectmode=tk.SINGLE,
                                   activestyle="dotbox")
        self._lb_name.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._sb.config(command=self._yview_all)

        for lb in (self._lb_pos, self._lb_name, self._lb_num):
            lb.config(yscrollcommand=self._sb.set)
            lb.bind("<MouseWheel>", self._on_wheel)
            lb.bind("<Button-4>",   self._on_wheel)
            lb.bind("<Button-5>",   self._on_wheel)

        self._lb_name.bind("<<ListboxSelect>>", self._on_sel)
        self._lb_name.bind("<Double-Button-1>", self._on_dbl)

    # ── scrolling sync ─────────────────────────────────────────────────────────
    def _yview_all(self, *args):
        self._lb_pos.yview(*args)
        self._lb_name.yview(*args)
        self._lb_num.yview(*args)

    def _on_wheel(self, event):
        d = -1 if (event.num == 4 or event.delta > 0) else 1
        for lb in (self._lb_pos, self._lb_name, self._lb_num):
            lb.yview_scroll(d, "units")

    # ── events ─────────────────────────────────────────────────────────────────
    def _on_team_sel(self, _event):
        idx = self._team_combo.current()
        if 0 <= idx < len(self._team_indices):
            self.load_squad(self._team_indices[idx])

    def _on_sel(self, _event):
        self._active = True
        sel = self._lb_name.curselection()
        if sel and sel[0] < len(self._slots):
            player, slot = self._slots[sel[0]]
            if self._on_select and player:
                self._on_select(player, self._squad_idx, slot)

    def _on_dbl(self, _event):
        sel = self._lb_name.curselection()
        if sel and sel[0] < len(self._slots):
            player, _slot = self._slots[sel[0]]
            if self._on_edit and player:
                self._on_edit(player)

    # ── public API ─────────────────────────────────────────────────────────────
    def refresh_combos(self):
        names, indices = _build_team_list(self._of)
        self._team_names   = names
        self._team_indices = indices
        self._team_combo["values"] = names

    def load_squad(self, squad_idx):
        self._squad_idx = squad_idx
        self._slots = []
        for lb in (self._lb_pos, self._lb_name, self._lb_num):
            lb.delete(0, tk.END)
        if squad_idx is None:
            self._team_var.set("– select –")
            return
        st   = _squad_t(squad_idx)
        size = _squad_size(squad_idx)
        for slot in range(size):
            pidx  = Squads.get_squad_player(self._of, squad_idx, slot)
            shirt = Squads.get_shirt_num(self._of, squad_idx, slot)
            pos   = _pos_label(self._of, st, slot)
            if pidx > 0:
                p = Player(self._of, pidx, 0)
                self._lb_pos.insert(tk.END, pos)
                self._lb_name.insert(tk.END, p.name)
                self._lb_num.insert(tk.END, str(shirt) if shirt > 0 else "·")
                self._slots.append((p, slot))
            else:
                self._lb_pos.insert(tk.END, pos)
                self._lb_name.insert(tk.END, "")
                self._lb_num.insert(tk.END, "·")
                self._slots.append((None, slot))

    def select_squad_by_idx(self, squad_idx: int):
        """Select combo and load squad by squad_idx value."""
        try:
            combo_pos = self._team_indices.index(squad_idx)
            self._team_combo.current(combo_pos)
            self._team_var.set(self._team_names[combo_pos])
        except (ValueError, IndexError):
            pass
        self.load_squad(squad_idx)

    def reload(self):
        self.load_squad(self._squad_idx)

    def get_selected(self):
        """Return (player, squad_idx, slot) or (None,None,None)."""
        sel = self._lb_name.curselection()
        if not sel or sel[0] >= len(self._slots):
            return None, None, None
        player, slot = self._slots[sel[0]]
        return player, self._squad_idx, slot

    def get_selected_slot_index(self):
        sel = self._lb_name.curselection()
        return sel[0] if sel else -1

    def find_free_slot(self):
        """Return index of first empty slot, or -1."""
        for i, (p, _slot) in enumerate(self._slots):
            if p is None:
                return i
        return -1

    @property
    def squad_idx(self):
        return self._squad_idx


# ── FreePane ──────────────────────────────────────────────────────────────────
class FreePane(ttk.Frame):
    """Centre column: nationality filter + alpha-sort + free-player list."""

    def __init__(self, parent, of, on_select_cb=None, on_edit_cb=None):
        super().__init__(parent, relief=tk.RIDGE, borderwidth=1)
        self._of        = of
        self._on_select = on_select_cb  # (player)
        self._on_edit   = on_edit_cb    # (player)
        self._players   = []
        self._alpha     = True
        self._font      = _unicode_font()
        self._build()

    def _build(self):
        ttk.Label(self, text="Free Players", font=_unicode_font(9)).pack(
            fill=tk.X, padx=2)

        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=2, pady=(0, 2))

        all_nations = list(Stats.NATION) + _NATION_SPECIAL
        self._nation_var = tk.StringVar(value="All Players")
        self._nation_combo = ttk.Combobox(top, textvariable=self._nation_var,
                                           values=all_nations, state="readonly",
                                           width=16, font=self._font)
        self._nation_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._nation_combo.bind("<<ComboboxSelected>>", lambda _: self._load())

        self._sort_btn = ttk.Button(top, text="Alpha", width=6,
                                    command=self._toggle_sort)
        self._sort_btn.pack(side=tk.LEFT, padx=(2, 0))

        lf = ttk.Frame(self)
        lf.pack(fill=tk.BOTH, expand=True, padx=2)
        sb = ttk.Scrollbar(lf)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._lb = tk.Listbox(lf, width=18, height=26,
                              font=self._font, exportselection=False,
                              yscrollcommand=sb.set)
        self._lb.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self._lb.yview)
        self._lb.bind("<<ListboxSelect>>", self._on_sel)
        self._lb.bind("<Double-Button-1>",  self._on_dbl)

    def _toggle_sort(self):
        self._alpha = not self._alpha
        self._sort_btn.config(text="Alpha" if self._alpha else "Index")
        self._load()

    def _on_sel(self, _event):
        sel = self._lb.curselection()
        if sel and sel[0] < len(self._players):
            if self._on_select:
                self._on_select(self._players[sel[0]])

    def _on_dbl(self, _event):
        sel = self._lb.curselection()
        if sel and sel[0] < len(self._players):
            if self._on_edit:
                self._on_edit(self._players[sel[0]])

    def _load(self):
        nation_name = self._nation_var.get()
        nation_idx  = self._nation_combo.current()
        total_nations = len(Stats.NATION)

        players = []
        special_offset = nation_idx - total_nations

        if nation_name == "All Players":
            for i in range(1, TOTAL):
                p = Player(self._of, i, 0)
                if _is_real(p.name):
                    players.append(p)
            for i in range(TOTAL_EDIT):
                p = Player(self._of, FIRST_EDIT + i, 0)
                if _is_real(p.name):
                    players.append(p)
        elif nation_name == "Unused":
            for i in range(FIRST_UNUSED, TOTAL):
                players.append(Player(self._of, i, 0))
        elif nation_name == "ML Old":
            for i in range(FIRST_OLD, FIRST_UNUSED):
                players.append(Player(self._of, i, 0))
        elif nation_name == "ML Young":
            for i in range(FIRST_YOUNG, FIRST_OLD):
                players.append(Player(self._of, i, 0))
        elif nation_name == "Free Agents":
            assigned = set()
            # scan all club squad slots
            for t in range(73, 73 + Clubs.TOTAL):
                for slot in range(32):
                    pidx = Squads.get_squad_player(self._of, t, slot)
                    if pidx > 0:
                        assigned.add(pidx)
            for i in range(1, FIRST_CLASSIC):
                if i not in assigned:
                    p = Player(self._of, i, 0)
                    if _is_real(p.name):
                        players.append(p)
            for i in range(FIRST_CLUB, FIRST_ML):
                if i not in assigned:
                    p = Player(self._of, i, 0)
                    if _is_real(p.name):
                        players.append(p)
        elif 0 <= nation_idx < total_nations:
            for i in range(1, TOTAL):
                if Stats.get_value(self._of, i, Stats.nationality) == nation_idx:
                    players.append(Player(self._of, i, 0))
            for i in range(FIRST_EDIT, FIRST_EDIT + TOTAL_EDIT):
                if Stats.get_value(self._of, i, Stats.nationality) == nation_idx:
                    players.append(Player(self._of, i, 0))
        else:
            # Duplicates or fallback
            for i in range(1, TOTAL):
                p = Player(self._of, i, 0)
                if _is_real(p.name):
                    players.append(p)

        if self._alpha:
            players.sort()

        self._players = players
        self._lb.delete(0, tk.END)
        for p in players:
            self._lb.insert(tk.END, p.name)

    def refresh(self):
        self._load()

    def get_selected(self):
        sel = self._lb.curselection()
        if sel and sel[0] < len(self._players):
            return self._players[sel[0]]
        return None


# ── TransferPanel ──────────────────────────────────────────────────────────────
class TransferPanel(ttk.Frame):
    """Main Transfer tab – three columns + bottom editor/info section."""

    def __init__(self, parent, of, on_player_edit=None):
        super().__init__(parent)
        self._of             = of
        self._on_player_edit = on_player_edit
        self._font           = _unicode_font()
        self._last_player    = None
        self._last_squad_pane = None  # which squad pane was last active
        self._build()

    # ── UI construction ────────────────────────────────────────────────────────
    def _build(self):
        # Main horizontal split: [3-column lists] | [right panel]
        # Mirrors Java: listPan(GridLayout 3) + editOptInfoPan(BorderLayout)
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        # ── Right panel: editors / checkboxes / info / compare ─────────────
        right = ttk.Frame(main, relief=tk.GROOVE, borderwidth=1)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(2, 2), pady=2)

        # Editors
        ed = ttk.Frame(right)
        ed.pack(fill=tk.X, padx=4, pady=(4, 2))
        ttk.Label(ed, text="#:").grid(row=0, column=0, sticky=tk.W)
        self._num_var = tk.StringVar()
        self._num_entry = ttk.Entry(ed, textvariable=self._num_var, width=5)
        self._num_entry.grid(row=0, column=1, sticky=tk.W, padx=(2, 0))
        self._num_entry.bind("<Return>", self._apply_num)

        ttk.Label(ed, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(ed, textvariable=self._name_var,
                                     width=16, font=self._font)
        self._name_entry.grid(row=1, column=1, sticky=tk.W, padx=(2, 0))
        self._name_entry.bind("<Return>", self._apply_name)

        ttk.Label(ed, text="Shirt:").grid(row=2, column=0, sticky=tk.W)
        self._shirt_var = tk.StringVar()
        self._shirt_entry = ttk.Entry(ed, textvariable=self._shirt_var,
                                      width=16, font=self._font)
        self._shirt_entry.grid(row=2, column=1, sticky=tk.W, padx=(2, 0))
        self._shirt_entry.bind("<Return>", self._apply_shirt)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=4)

        # Checkboxes
        self._auto_rel = tk.BooleanVar(value=True)
        self._auto_sub = tk.BooleanVar(value=True)
        self._safe     = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="Auto Release",
                        variable=self._auto_rel).pack(anchor=tk.W, padx=6)
        ttk.Checkbutton(right, text="Auto Sub",
                        variable=self._auto_sub).pack(anchor=tk.W, padx=6)
        ttk.Checkbutton(right, text="Safe Mode",
                        variable=self._safe).pack(anchor=tk.W, padx=6)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=4)

        # Info panel (black bg, coloured text — mirrors Java InfoPanel)
        info_sb = ttk.Scrollbar(right, orient=tk.VERTICAL)
        info_sb.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        self._info = tk.Text(right, width=24, state=tk.DISABLED,
                             font=self._font, background="black",
                             foreground="white", insertbackground="white",
                             yscrollcommand=info_sb.set)
        self._info.pack(fill=tk.BOTH, expand=True, padx=(4, 0), pady=2)
        info_sb.config(command=self._info.yview)
        # colour tags matching Java InfoPanel
        self._info.tag_configure("stat_white",  foreground="white")
        self._info.tag_configure("stat_red",    foreground="#FF4040")
        self._info.tag_configure("stat_orange", foreground="#FFA500")
        self._info.tag_configure("stat_yellow", foreground="#FFFF00")
        self._info.tag_configure("stat_lime",   foreground="#B7FF00")
        self._info.tag_configure("stat_green",  foreground="#00FF00")
        self._info.tag_configure("pos_tag",     foreground="#80FFFF")

        ttk.Button(right, text="Compare Stats",
                   command=self._compare).pack(fill=tk.X, padx=4, pady=4)

        # ── Three-column list area (fills remaining space) ──────────────────
        # Layout mirrors Java GridLayout(0,3): Free Players | Squad A | Squad B
        cols = tk.Frame(main)
        cols.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.columnconfigure(2, weight=1)
        cols.rowconfigure(0, weight=1)

        self._free = FreePane(cols, self._of,
                              on_select_cb=self._on_free_select,
                              on_edit_cb=self._open_editor)
        self._free.grid(row=0, column=0, sticky=tk.NSEW, padx=1, pady=2)

        self._squad_l = SquadPane(cols, self._of, "Squad A",
                                  on_select_cb=self._on_squad_select,
                                  on_edit_cb=self._open_editor)
        self._squad_l.grid(row=0, column=1, sticky=tk.NSEW, padx=1, pady=2)

        self._squad_r = SquadPane(cols, self._of, "Squad B",
                                  on_select_cb=self._on_squad_select,
                                  on_edit_cb=self._open_editor)
        self._squad_r.grid(row=0, column=2, sticky=tk.NSEW, padx=1, pady=2)

        # ── Wire up drag-and-drop AFTER all panels exist ───────────────────
        self._setup_dnd()

    # ── callbacks ──────────────────────────────────────────────────────────────
    def _on_squad_select(self, player, squad_idx, slot):
        if player:
            self._last_player = player
            self._show_info(player, squad_idx, slot)
            self._name_entry.config(state=tk.NORMAL)
            self._name_var.set(player.name)
            self._shirt_var.set(player.get_shirt_name())
            shirt_num = Squads.get_shirt_num(self._of, squad_idx, slot)
            self._num_var.set(str(shirt_num) if shirt_num > 0 else "")

    def _on_free_select(self, player):
        if player:
            self._last_player = player
            self._show_info(player, None, None)
            self._name_var.set(player.name)
            self._shirt_var.set(player.get_shirt_name())
            self._num_var.set("")

    def _open_editor(self, player):
        if self._on_player_edit and player:
            self._on_player_edit(player)

    def _compare(self):
        """Select all players of same position in both squads (stub)."""
        pass

    # ── info display ───────────────────────────────────────────────────────────
    def _show_info(self, player, squad_idx, slot):
        """Mirrors Java InfoPanel single-player mode."""
        of   = self._of
        pidx = player.index

        t = self._info
        t.config(state=tk.NORMAL)
        t.delete("1.0", tk.END)

        def w(text, tag="stat_white"):
            t.insert(tk.END, text, tag)

        # ── ID + name ──────────────────────────────────────────────────────
        w(f"ID: {pidx}  ")
        w(f"{player.name}\n")

        # ── Squads (shown first so always visible) ─────────────────────────
        squads = _find_player_squads(of, pidx)
        if squads:
            w("Teams: ", "stat_yellow")
            w(", ".join(squads) + "\n", "stat_white")
        else:
            w("Teams: Free Agent\n", "stat_yellow")

        # ── Nationality + age ──────────────────────────────────────────────
        nat = Stats.get_string(of, pidx, Stats.nationality)
        age = Stats.get_string(of, pidx, Stats.age)
        w(f"{nat}  Age: {age}\n")

        # ── Foot / side / height / weight ──────────────────────────────────
        foot_v = Stats.get_value(of, pidx, Stats.foot)
        side_v = Stats.get_value(of, pidx, Stats.fav_side)
        foot_s = "LF" if foot_v == 1 else "RF"
        if foot_v == 1:   # left foot: 0=LS, 1=RS, 2=BS
            side_s = {0: "LS", 1: "RS", 2: "BS"}.get(side_v, "?")
        else:             # right foot: 0=RS, 1=LS, 2=BS
            side_s = {0: "RS", 1: "LS", 2: "BS"}.get(side_v, "?")
        h = Stats.get_string(of, pidx, Stats.height)
        wt = Stats.get_string(of, pidx, Stats.weight)
        w(f"{foot_s}/{side_s}  {h}cm  {wt}Kg\n")

        # ── Positions ──────────────────────────────────────────────────────
        pos_pairs = [
            (Stats.gk,  "GK"),
            (Stats.cwp, "CWP"), (Stats.cbt, "CB"),
            (Stats.sb,  "SB"),  (Stats.wb,  "WB"),  (Stats.dm, "DM"),
            (Stats.cm,  "CM"),  (Stats.sm,  "SM"),  (Stats.am, "AM"),
            (Stats.ss,  "SS"),  (Stats.cf,  "CF"),  (Stats.wg, "WG"),
        ]
        active = [abbr for st, abbr in pos_pairs
                  if Stats.get_value(of, pidx, st) == 1]
        if active:
            w("  ".join(active) + "\n", "pos_tag")

        # ── All ability99 stats ────────────────────────────────────────────
        w("\n")
        for st in Stats.ability99:
            if not st.name:
                continue
            v = Stats.get_value(of, pidx, st)
            w(f"{st.name:<12}", "stat_white")
            w(f"{v:3d}\n", _stat_tag(st, v))

        # ── Special abilities ──────────────────────────────────────────────
        specials = [s.name for s in Stats.ability_special
                    if s.name and Stats.get_value(of, pidx, s) == 1]
        if specials:
            w("\n")
            for i, sp in enumerate(specials):
                tag = "stat_red" if (i & 1) else "stat_green"
                w(f"  {sp}\n", tag)

        t.config(state=tk.DISABLED)
        t.see("1.0")

    # ── transfer operations ────────────────────────────────────────────────────
    def _add_to_squad(self, player, squad_pane: SquadPane):
        """Add a free player to a squad pane."""
        sq = squad_pane.squad_idx
        if sq is None:
            return
        size = _squad_size(sq)
        # find first empty slot
        for slot in range(size):
            pidx = Squads.get_squad_player(self._of, sq, slot)
            if pidx == 0:
                Squads.set_squad_player(self._of, sq, slot, player.index)
                # assign next free shirt number
                used = {Squads.get_shirt_num(self._of, sq, s)
                        for s in range(size) if Squads.get_squad_player(self._of, sq, s)}
                for n in range(1, 100):
                    if n not in used:
                        Squads.set_shirt_num(self._of, sq, slot, n)
                        break
                if self._auto_rel.get():
                    self._release_from_other_clubs(player.index, sq)
                squad_pane.reload()
                return

    def _release_from_squad(self, squad_pane: SquadPane):
        """Remove the selected player from a squad, returning to free pool."""
        player, sq, slot = squad_pane.get_selected()
        if player is None or sq is None:
            return
        Squads.set_squad_player(self._of, sq, slot, 0)
        Squads.set_shirt_num(self._of, sq, slot, 0)
        Squads.tidy(self._of, sq)
        squad_pane.reload()
        self._free.refresh()

    def _release_from_other_clubs(self, player_idx: int, keep_squad: int):
        """Auto-release: remove player from all other club squads."""
        for t in range(73, 73 + Clubs.TOTAL):
            if t == keep_squad:
                continue
            for slot in range(32):
                if Squads.get_squad_player(self._of, t, slot) == player_idx:
                    Squads.set_squad_player(self._of, t, slot, 0)
                    Squads.set_shirt_num(self._of, t, slot, 0)
                    Squads.tidy(self._of, t)

    def _transfer_between(self, src_pane: SquadPane, dst_pane: SquadPane):
        """Move selected player from src squad to dst squad."""
        player, src_sq, src_slot = src_pane.get_selected()
        if player is None or src_sq is None or dst_pane.squad_idx is None:
            return
        # remove from source
        Squads.set_squad_player(self._of, src_sq, src_slot, 0)
        Squads.set_shirt_num(self._of, src_sq, src_slot, 0)
        Squads.tidy(self._of, src_sq)
        # add to destination
        dst_sq = dst_pane.squad_idx
        size   = _squad_size(dst_sq)
        for slot in range(size):
            if Squads.get_squad_player(self._of, dst_sq, slot) == 0:
                Squads.set_squad_player(self._of, dst_sq, slot, player.index)
                used = {Squads.get_shirt_num(self._of, dst_sq, s)
                        for s in range(size)
                        if Squads.get_squad_player(self._of, dst_sq, s)}
                for n in range(1, 100):
                    if n not in used:
                        Squads.set_shirt_num(self._of, dst_sq, slot, n)
                        break
                break
        src_pane.reload()
        dst_pane.reload()

    # ── drag-and-drop ──────────────────────────────────────────────────────────
    def _setup_dnd(self):
        """Bind mouse drag events to all listboxes for DnD transfers."""
        self._dnd_source  = None   # panel (SquadPane | FreePane)
        self._dnd_origin  = None   # (x_root, y_root) at press
        self._dnd_active  = False  # True once drag threshold crossed

        # Map every listbox tk-name → owning panel
        self._dnd_map = {}
        for lb in (self._squad_l._lb_name,
                   self._squad_l._lb_pos,
                   self._squad_l._lb_num):
            self._dnd_map[str(lb)] = self._squad_l
        for lb in (self._squad_r._lb_name,
                   self._squad_r._lb_pos,
                   self._squad_r._lb_num):
            self._dnd_map[str(lb)] = self._squad_r
        self._dnd_map[str(self._free._lb)] = self._free

        for lb in self._dnd_map:
            w = self.nametowidget(lb)
            w.bind("<ButtonPress-1>",   self._dnd_press,   add="+")
            w.bind("<B1-Motion>",       self._dnd_motion,  add="+")
            w.bind("<ButtonRelease-1>", self._dnd_release, add="+")

    def _dnd_press(self, event):
        self._dnd_origin = (event.x_root, event.y_root)
        self._dnd_active = False
        self._dnd_source = self._dnd_map.get(str(event.widget))

    def _dnd_motion(self, event):
        if not self._dnd_origin:
            return
        dx = abs(event.x_root - self._dnd_origin[0])
        dy = abs(event.y_root - self._dnd_origin[1])
        if dx + dy >= 6 and not self._dnd_active:
            self._dnd_active = True
            try:
                event.widget.config(cursor="fleur")
            except Exception:
                pass

    def _dnd_release(self, event):
        try:
            event.widget.config(cursor="")
        except Exception:
            pass

        active = self._dnd_active
        src    = self._dnd_source
        self._dnd_active = False
        self._dnd_source = None
        self._dnd_origin = None

        if not active or src is None:
            return

        # Identify drop target
        target_widget = self.winfo_containing(event.x_root, event.y_root)
        dst = self._dnd_map.get(str(target_widget))
        if dst is None or dst is src:
            return

        # Perform the appropriate transfer
        if isinstance(src, FreePane) and isinstance(dst, SquadPane):
            p = src.get_selected()
            if p:
                self._add_to_squad(p, dst)
                self._free.refresh()
        elif isinstance(src, SquadPane) and isinstance(dst, FreePane):
            self._release_from_squad(src)
        elif isinstance(src, SquadPane) and isinstance(dst, SquadPane):
            self._transfer_between(src, dst)

    # Button handlers
    def _free_to_left(self):
        p = self._free.get_selected()
        if p:
            self._add_to_squad(p, self._squad_l)

    def _free_to_right(self):
        p = self._free.get_selected()
        if p:
            self._add_to_squad(p, self._squad_r)

    def _release_left(self):
        self._release_from_squad(self._squad_l)

    def _release_right(self):
        self._release_from_squad(self._squad_r)

    def _transfer_l_to_r(self):
        self._transfer_between(self._squad_l, self._squad_r)

    def _transfer_r_to_l(self):
        self._transfer_between(self._squad_r, self._squad_l)

    # ── editors ────────────────────────────────────────────────────────────────
    def _apply_name(self, _event=None):
        if not self._last_player:
            return
        new_name = self._name_var.get().strip()
        if new_name and len(new_name) <= 15:
            self._last_player.set_name(new_name)
            self._squad_l.reload()
            self._squad_r.reload()
            self._free.refresh()

    def _apply_shirt(self, _event=None):
        if not self._last_player:
            return
        self._last_player.set_shirt_name(self._shirt_var.get().strip())

    def _apply_num(self, _event=None):
        if not self._last_player:
            return
        try:
            n = int(self._num_var.get())
            if not (1 <= n <= 99):
                return
        except ValueError:
            return
        # find the player in the active squads and update shirt number
        for pane in (self._squad_l, self._squad_r):
            sq = pane.squad_idx
            if sq is None:
                continue
            size = _squad_size(sq)
            for slot in range(size):
                if Squads.get_squad_player(self._of, sq, slot) == self._last_player.index:
                    Squads.set_shirt_num(self._of, sq, slot, n)
                    pane.reload()
                    return

    # ── public API ─────────────────────────────────────────────────────────────
    def refresh(self):
        self._squad_l.refresh_combos()
        self._squad_r.refresh_combos()
        # Default Squad A to first club (squad 73), Squad B empty — mirrors Java
        self._squad_l.select_squad_by_idx(73)
        self._squad_r.load_squad(None)
        self._free.refresh()
