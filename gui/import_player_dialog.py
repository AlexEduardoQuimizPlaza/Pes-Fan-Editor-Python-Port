"""
PES Editor 6 - Python Port
Import Player dialog: pick a player from the OF2 file and copy their data
into the currently edited player slot.
"""
import os
import tkinter as tk
from tkinter import ttk

import clubs  as Clubs
import squads as Squads
import stats  as Stats
from player import Player, TOTAL, TOTAL_EDIT, FIRST_EDIT, START_ADR, START_ADR_E

def _valid_pidx(pidx: int) -> bool:
    return (1 <= pidx < TOTAL) or (FIRST_EDIT <= pidx < FIRST_EDIT + TOTAL_EDIT)

# Stats exposed in the Edit Player dialog (copied for mode 1 / restored for mode 2)
_DIALOG_STATS = (
    [Stats.nationality, Stats.age, Stats.height, Stats.weight,
     Stats.foot, Stats.fav_side, Stats.wfa, Stats.wff,
     Stats.consistency, Stats.condition, Stats.injury,
     Stats.drib_sty, Stats.freekick, Stats.pk_style, Stats.dk_sty,
     Stats.reg_pos,
     Stats.gk, Stats.cwp, Stats.cbt, Stats.sb, Stats.dm,
     Stats.wb, Stats.cm, Stats.sm, Stats.am, Stats.wg, Stats.ss, Stats.cf]
    + list(Stats.ability99)
    + list(Stats.ability_special)
)

_MODES = [
    "Import everything (name, appearance, stats, etc.)",
    "Import only the stats editable on the 'Edit Player' dialog",
    "Import everything except stats (name, appearance, etc.)",
]

_REG_POS_NAMES = ["GK", "CWP", "CBT", "SB", "DM", "WB", "CM", "SM", "AM", "WG", "SS", "CF"]

# Extra squad names and their index ranges (mirrors transfer_panel._EXTRA_SQUAD)
_EXTRA_SQUAD = [
    "Classic England", "Classic France", "Classic Germany", "Classic Italy",
    "Classic Netherlands", "Classic Argentina", "Classic Brazil",
    "<Japan 1>", "<Edited> National 1", "<Edited> National 2",
    "<Edited> National 3", "<Edited> National 4", "<Edited> National 5",
    "<Edited> National 6", "<Edited> National 7", "<Edited>",
    "<ML Default>", "<Shop 1>", "<Shop 2>", "<Shop 3>", "<Shop 4>", "<Shop 5>",
]


def _build_squad_list(of):
    """
    Return (display_names, squad_indices) for all squads, prefixed with 'All Players'.
    Mirrors the transfer_panel._build_team_list structure.
    """
    nation_names = list(Stats.NATION[:57])
    club_names   = Clubs.get_names(of)

    names = (["All Players"]
             + nation_names
             + list(_EXTRA_SQUAD[:16])
             + club_names
             + list(_EXTRA_SQUAD[16:]))

    # None = "All Players" special case
    indices = ([None]
               + list(range(57))                              # nations 0-56
               + list(range(57, 73))                          # classic/edited 57-72
               + list(range(73, 73 + len(club_names)))        # clubs 73-212
               + list(range(213, 213 + len(_EXTRA_SQUAD[16:]))))  # ML/shop 213+

    return names, indices


def _block_offset(idx: int) -> int:
    if idx >= FIRST_EDIT:
        return START_ADR_E + (idx - FIRST_EDIT) * 124
    return START_ADR + idx * 124


class ImportPlayerDialog(tk.Toplevel):
    def __init__(self, parent, of, of2, dst_player: Player, on_done):
        super().__init__(parent)
        self.title("Import Player")
        self.resizable(False, False)
        self._of      = of
        self._of2     = of2
        self._dst     = dst_player
        self._on_done = on_done
        self._mode    = tk.IntVar(value=0)
        self._sel_idx = None   # OF2 player index chosen by user
        self._indices = []     # parallel list to listbox entries

        self._squad_names, self._squad_indices = _build_squad_list(of2)

        self._build_ui()
        self.update_idletasks()
        self.grab_set()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        fname = os.path.basename(self._of2.file_name) if self._of2.file_name else "?"
        ttk.Label(self, text=f"From:  {fname}", font=("", 10, "bold")).pack(
            anchor=tk.W, padx=10, pady=(8, 2))

        # Import mode radio buttons
        mode_f = ttk.Frame(self)
        mode_f.pack(fill=tk.X, padx=10, pady=(2, 6))
        for i, text in enumerate(_MODES):
            ttk.Radiobutton(mode_f, text=text, variable=self._mode, value=i).pack(anchor=tk.W)

        # Main area: left list + right preview
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)

        # Left: squad filter + scrolled player list
        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y)

        self._team_var = tk.StringVar(value="All Players")
        team_cb = ttk.Combobox(left, textvariable=self._team_var,
                               values=self._squad_names, width=28, state="readonly")
        team_cb.pack(fill=tk.X, pady=(0, 4))
        team_cb.bind("<<ComboboxSelected>>", lambda _e: self._reload_list())

        sb = ttk.Scrollbar(left, orient=tk.VERTICAL)
        self._lb = tk.Listbox(left, yscrollcommand=sb.set, width=28, height=26,
                              selectmode=tk.SINGLE, activestyle="dotbox")
        sb.config(command=self._lb.yview)
        self._lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self._lb.bind("<<ListboxSelect>>", self._on_select)

        # Right: player preview
        right = ttk.LabelFrame(main, text="Player Info", width=270)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        pv = ttk.Frame(right, padding=8)
        pv.pack(fill=tk.BOTH, expand=True)
        self._pv_vars = {}
        self._build_preview(pv)

        # Bottom buttons
        btn_f = ttk.Frame(self)
        btn_f.pack(fill=tk.X, padx=10, pady=(6, 10))
        self._import_btn = ttk.Button(btn_f, text="Import",
                                      command=self._do_import, state=tk.DISABLED)
        self._import_btn.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_f, text="Cancel", command=self.destroy).pack(side=tk.LEFT)

        self._reload_list()

    def _build_preview(self, parent):
        rows = [
            ("Name",       "name"),
            ("Nationality","nat"),
            ("Age",        "age"),
            ("Height",     "height"),
            ("Weight",     "weight"),
            ("Foot",       "foot"),
            None,
            ("Position",   "pos"),
            ("Reg. Pos.",  "regpos"),
            None,
            ("Attack",     "atk"),
            ("Defence",    "def"),
            ("Speed",      "spd"),
            ("Drib Acc",   "dri"),
            ("Heading",    "hea"),
            ("GK Skills",  "gk"),
        ]
        r = 0
        for item in rows:
            if item is None:
                ttk.Separator(parent, orient=tk.HORIZONTAL).grid(
                    row=r, column=0, columnspan=2, sticky=tk.EW, pady=4)
                r += 1
                continue
            label, key = item
            ttk.Label(parent, text=label + ":", anchor=tk.W).grid(
                row=r, column=0, sticky=tk.W, padx=(0, 8), pady=1)
            var = tk.StringVar(value="—")
            ttk.Label(parent, textvariable=var, anchor=tk.W).grid(
                row=r, column=1, sticky=tk.W, pady=1)
            self._pv_vars[key] = var
            r += 1

    # ------------------------------------------------------------------
    # List population
    # ------------------------------------------------------------------

    def _reload_list(self):
        self._lb.delete(0, tk.END)
        self._indices = []
        self._sel_idx = None
        self._import_btn.config(state=tk.DISABLED)
        self._clear_preview()

        team     = self._team_var.get()
        of2      = self._of2

        try:
            pos = self._squad_names.index(team)
        except ValueError:
            return
        squad_idx = self._squad_indices[pos]

        if squad_idx is None:
            # "All Players": real players first, then edited slots
            for i in range(1, TOTAL):
                p = Player(of2, i, 0)
                if p.name and not p.name.startswith("<"):
                    self._lb.insert(tk.END, p.name)
                    self._indices.append(i)
            for j in range(TOTAL_EDIT):
                i = FIRST_EDIT + j
                p = Player(of2, i, 0)
                self._lb.insert(tk.END, p.name)
                self._indices.append(i)
        else:
            # Specific squad: read squad slots
            size = 23 if squad_idx < 64 else 32
            for slot in range(size):
                pidx = Squads.get_squad_player(of2, squad_idx, slot)
                if not _valid_pidx(pidx):
                    continue
                p = Player(of2, pidx, 0)
                self._lb.insert(tk.END, p.name)
                self._indices.append(pidx)

    # ------------------------------------------------------------------
    # Selection / preview
    # ------------------------------------------------------------------

    def _on_select(self, _event=None):
        sel = self._lb.curselection()
        if not sel:
            return
        idx = self._indices[sel[0]]
        self._sel_idx = idx
        self._import_btn.config(state=tk.NORMAL)
        self._update_preview(idx)

    def _clear_preview(self):
        for var in self._pv_vars.values():
            var.set("—")

    def _update_preview(self, idx: int):
        of2 = self._of2
        p   = Player(of2, idx, 0)
        G   = lambda s: Stats.get_value(of2, idx, s)
        GS  = lambda s: Stats.get_string(of2, idx, s)

        pos_flags = [s.name for s in
                     [Stats.gk, Stats.cwp, Stats.cbt, Stats.sb, Stats.dm,
                      Stats.wb, Stats.cm, Stats.sm, Stats.am, Stats.wg,
                      Stats.ss, Stats.cf]
                     if G(s)]
        reg = G(Stats.reg_pos)
        reg_str = _REG_POS_NAMES[reg] if reg < len(_REG_POS_NAMES) else str(reg)

        self._pv_vars["name"].set(p.name)
        self._pv_vars["nat"].set(GS(Stats.nationality))
        self._pv_vars["age"].set(GS(Stats.age))
        self._pv_vars["height"].set(GS(Stats.height) + " cm")
        self._pv_vars["weight"].set(GS(Stats.weight) + " kg")
        self._pv_vars["foot"].set(GS(Stats.foot))
        self._pv_vars["pos"].set(" ".join(pos_flags) or "—")
        self._pv_vars["regpos"].set(reg_str)
        self._pv_vars["atk"].set(str(G(Stats.attack)))
        self._pv_vars["def"].set(str(G(Stats.defence)))
        self._pv_vars["spd"].set(str(G(Stats.speed)))
        self._pv_vars["dri"].set(str(G(Stats.drib_acc)))
        self._pv_vars["hea"].set(str(G(Stats.heading)))
        self._pv_vars["gk"].set(str(G(Stats.gk_abil)))

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def _do_import(self):
        if self._sel_idx is None:
            return
        mode    = self._mode.get()
        of, of2 = self._of, self._of2
        src     = self._sel_idx
        dst     = self._dst.index

        if mode == 0:
            s_off = _block_offset(src)
            d_off = _block_offset(dst)
            of.data[d_off:d_off + 124] = of2.data[s_off:s_off + 124]

        elif mode == 1:
            for stat in _DIALOG_STATS:
                Stats.set_value(of, dst, stat, Stats.get_value(of2, src, stat))

        elif mode == 2:
            saved = {s: Stats.get_value(of, dst, s) for s in _DIALOG_STATS}
            s_off = _block_offset(src)
            d_off = _block_offset(dst)
            of.data[d_off:d_off + 124] = of2.data[s_off:s_off + 124]
            for stat, val in saved.items():
                Stats.set_value(of, dst, stat, val)

        self._on_done()
        self.destroy()
