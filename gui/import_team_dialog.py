"""
PES Editor 6 - Python Port
Import Team dialog: copy players, squad roster, and club assets (name, kits,
logos, emblem) from a source team in OF2 into a destination team in the primary OF.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox

import clubs   as Clubs
import kits    as Kits
import logos   as Logos
import emblems as Emblems
import squads  as Squads
import stats   as Stats
from player import Player, TOTAL, TOTAL_EDIT, FIRST_EDIT, START_ADR, START_ADR_E
from squads  import NUM23, NUM32, SLOT23, SLOT32

_EXTRA_SQUAD = [
    "Classic England", "Classic France", "Classic Germany", "Classic Italy",
    "Classic Netherlands", "Classic Argentina", "Classic Brazil",
    "<Japan 1>", "<Edited> National 1", "<Edited> National 2",
    "<Edited> National 3", "<Edited> National 4", "<Edited> National 5",
    "<Edited> National 6", "<Edited> National 7", "<Edited>",
    "<ML Default>", "<Shop 1>", "<Shop 2>", "<Shop 3>", "<Shop 4>", "<Shop 5>",
]

_REG_POS = ["GK", "CWP", "CBT", "SB", "DM", "WB", "CM", "SM", "AM", "WG", "SS", "CF"]

# Squad index range for club teams
_CLUB_SQUAD_MIN = 73
_CLUB_SQUAD_MAX = 73 + Clubs.TOTAL - 1   # 212


def _build_squad_list(of):
    nation_names = list(Stats.NATION[:57])
    club_names   = Clubs.get_names(of)
    names   = (nation_names
               + list(_EXTRA_SQUAD[:16])
               + club_names
               + list(_EXTRA_SQUAD[16:]))
    indices = (list(range(57))
               + list(range(57, 73))
               + list(range(73, 73 + len(club_names)))
               + list(range(213, 213 + len(_EXTRA_SQUAD[16:]))))
    return names, indices


def _block_offset(idx: int) -> int:
    if idx >= FIRST_EDIT:
        return START_ADR_E + (idx - FIRST_EDIT) * 124
    return START_ADR + idx * 124


def _squad_size(squad_idx: int) -> int:
    return 23 if squad_idx < 64 else 32


def _squad_addresses(squad_idx: int):
    """Return (slot_start, num_start, size) for raw squad byte access."""
    if squad_idx < 64:
        return SLOT23 + squad_idx * 23 * 2, NUM23 + squad_idx * 23, 23
    else:
        off = squad_idx - 73
        return SLOT32 + off * 32 * 2, NUM32 + off * 32, 32


def _valid_pidx(pidx: int) -> bool:
    return (1 <= pidx < TOTAL) or (FIRST_EDIT <= pidx < FIRST_EDIT + TOTAL_EDIT)


def _is_club_squad(squad_idx: int) -> bool:
    return _CLUB_SQUAD_MIN <= squad_idx <= _CLUB_SQUAD_MAX


def _club_idx(squad_idx: int) -> int:
    """Convert club squad index → club data index (0-139)."""
    return squad_idx - 73


# ------------------------------------------------------------------
# Asset copy helpers
# ------------------------------------------------------------------

def _copy_emblem(of1, club1: int, of2, club2: int):
    """Copy the custom emblem graphic from of2/club2 to of1/club1 (same slot)."""
    val = Clubs.get_emblem(of2, club2)
    slot = val - Clubs.FIRST_FLAG
    if not (0 <= slot < 50):
        return   # national flag or default — no graphic to copy
    src = Emblems.START_ADR + slot * Emblems.SIZE_128
    dst = Emblems.START_ADR + slot * Emblems.SIZE_128
    of1.data[dst:dst + Emblems.SIZE_128] = of2.data[src:src + Emblems.SIZE_128]
    # Update counters if needed
    if slot >= of1.data[Emblems.START_ADR - 160]:
        of1.data[Emblems.START_ADR - 160] = slot + 1


def _copy_logos(of1, club1: int, of2, club2: int):
    """Copy all logo graphics referenced by club2's kit block into of1 (same slots)."""
    for logo_idx in range(Kits.LOGOS_PER_TEAM):
        if not Kits.logo_used(of2, club2, logo_idx):
            continue
        src_slot = Kits.get_logo_slot(of2, club2, logo_idx)
        if src_slot >= Logos.TOTAL:
            continue
        Logos.import_logo(of2, src_slot, of1, src_slot)


class ImportTeamDialog(tk.Toplevel):
    def __init__(self, parent, of, of2, on_done=None):
        super().__init__(parent)
        self.title("Import Full Team from OF2")
        self.resizable(False, False)
        self._of      = of
        self._of2     = of2
        self._on_done = on_done

        self._src_names, self._src_indices = _build_squad_list(of2)
        self._dst_names, self._dst_indices = _build_squad_list(of)

        self._src_squad_idx = None
        self._dst_squad_idx = None
        self._src_players   = []

        # Import options
        self._opt_players = tk.BooleanVar(value=True)
        self._opt_roster  = tk.BooleanVar(value=True)
        self._opt_club    = tk.BooleanVar(value=True)
        self._opt_kits    = tk.BooleanVar(value=True)
        self._opt_logos   = tk.BooleanVar(value=True)
        self._opt_emblem  = tk.BooleanVar(value=True)

        self._build_ui()
        self.update_idletasks()
        self.grab_set()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        fname = os.path.basename(self._of2.file_name) if self._of2.file_name else "?"
        ttk.Label(self, text=f"From:  {fname}", font=("", 10, "bold")).pack(
            anchor=tk.W, padx=12, pady=(10, 4))

        # Two-column: source + destination
        cols = ttk.Frame(self)
        cols.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Left: source (OF2)
        src_f = ttk.LabelFrame(cols, text="Source team  (OF2)")
        src_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self._src_var = tk.StringVar()
        src_cb = ttk.Combobox(src_f, textvariable=self._src_var,
                              values=self._src_names, width=28, state="readonly")
        src_cb.pack(fill=tk.X, padx=6, pady=6)
        src_cb.bind("<<ComboboxSelected>>", lambda _e: self._on_src_select())

        sb1 = ttk.Scrollbar(src_f, orient=tk.VERTICAL)
        self._src_lb = tk.Listbox(src_f, yscrollcommand=sb1.set,
                                  width=30, height=16, activestyle="dotbox")
        sb1.config(command=self._src_lb.yview)
        self._src_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=(0, 4))
        sb1.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 4))

        self._src_count = ttk.Label(src_f, text="")
        self._src_count.pack(pady=(0, 4))

        # Right: destination (OF1)
        dst_f = ttk.LabelFrame(cols, text="Destination team  (primary OF)")
        dst_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._dst_var = tk.StringVar()
        dst_cb = ttk.Combobox(dst_f, textvariable=self._dst_var,
                              values=self._dst_names, width=28, state="readonly")
        dst_cb.pack(fill=tk.X, padx=6, pady=6)
        dst_cb.bind("<<ComboboxSelected>>", lambda _e: self._on_dst_select())

        sb2 = ttk.Scrollbar(dst_f, orient=tk.VERTICAL)
        self._dst_lb = tk.Listbox(dst_f, yscrollcommand=sb2.set,
                                  width=30, height=16, activestyle="dotbox",
                                  foreground="#BB6600")
        sb2.config(command=self._dst_lb.yview)
        self._dst_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=(0, 4))
        sb2.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 4))

        self._dst_count = ttk.Label(dst_f, text="")
        self._dst_count.pack(pady=(0, 4))

        # Options
        opt_f = ttk.LabelFrame(self, text="What to import")
        opt_f.pack(fill=tk.X, padx=12, pady=4)

        left_opts = ttk.Frame(opt_f)
        left_opts.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)
        right_opts = ttk.Frame(opt_f)
        right_opts.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)

        ttk.Checkbutton(left_opts, text="Player data  (stats, name, appearance)",
                        variable=self._opt_players).pack(anchor=tk.W)
        ttk.Checkbutton(left_opts, text="Squad roster  (slots & shirt numbers)",
                        variable=self._opt_roster).pack(anchor=tk.W)
        ttk.Checkbutton(left_opts, text="Club info  (name, colors, back pattern, stadium)",
                        variable=self._opt_club).pack(anchor=tk.W)

        self._opt_kits_cb   = ttk.Checkbutton(right_opts, text="Kit graphics  (home / away / GK)",
                                               variable=self._opt_kits)
        self._opt_kits_cb.pack(anchor=tk.W)
        self._opt_logos_cb  = ttk.Checkbutton(right_opts, text="Kit logos  (sponsor / badge graphics)",
                                               variable=self._opt_logos)
        self._opt_logos_cb.pack(anchor=tk.W)
        self._opt_emblem_cb = ttk.Checkbutton(right_opts, text="Emblem graphic  (custom badge image)",
                                               variable=self._opt_emblem)
        self._opt_emblem_cb.pack(anchor=tk.W)

        self._club_note = ttk.Label(opt_f,
                                    text="⚠ Club info / kits / logos / emblem only available for club teams (not nationals).",
                                    foreground="#888888", font=("", 8))
        self._club_note.pack(anchor=tk.W, padx=8, pady=(0, 4))

        # Warning + buttons
        ttk.Label(self,
                  text="⚠  Existing data will be overwritten in the primary file.",
                  foreground="#BB6600").pack(padx=12, pady=(2, 0))

        btn_f = ttk.Frame(self)
        btn_f.pack(fill=tk.X, padx=12, pady=(8, 12))
        self._import_btn = ttk.Button(btn_f, text="Import Team",
                                      command=self._do_import, state=tk.DISABLED)
        self._import_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_f, text="Cancel", command=self.destroy).pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Source selection
    # ------------------------------------------------------------------

    def _on_src_select(self):
        self._src_lb.delete(0, tk.END)
        self._src_players = []
        self._src_count.config(text="")
        self._update_import_btn()

        name = self._src_var.get()
        try:
            pos = self._src_names.index(name)
        except ValueError:
            return
        squad_idx = self._src_indices[pos]
        self._src_squad_idx = squad_idx

        of2  = self._of2
        size = _squad_size(squad_idx)

        for slot in range(size):
            pidx = Squads.get_squad_player(of2, squad_idx, slot)
            num  = Squads.get_shirt_num(of2, squad_idx, slot)
            if _valid_pidx(pidx):
                p = Player(of2, pidx, 0)
                try:
                    reg = Stats.get_value(of2, pidx, Stats.reg_pos)
                    pos_str = _REG_POS[reg] if reg < len(_REG_POS) else "?"
                except Exception:
                    pos_str = "?"
                self._src_lb.insert(tk.END, f"  #{num:>2}  {pos_str:<4}  {p.name}")
                self._src_players.append(pidx)
            else:
                self._src_lb.insert(tk.END, f"  #{num:>2}  —     <empty>")

        self._src_count.config(text=f"{len(self._src_players)} players")

        # Auto-suggest same team name in destination
        if name in self._dst_names and not self._dst_var.get():
            self._dst_var.set(name)
            self._on_dst_select()

        self._update_club_options()
        self._update_import_btn()

    # ------------------------------------------------------------------
    # Destination selection
    # ------------------------------------------------------------------

    def _on_dst_select(self):
        self._dst_lb.delete(0, tk.END)
        self._dst_count.config(text="")

        name = self._dst_var.get()
        try:
            pos = self._dst_names.index(name)
        except ValueError:
            self._dst_squad_idx = None
            self._update_import_btn()
            return
        squad_idx = self._dst_indices[pos]
        self._dst_squad_idx = squad_idx

        of   = self._of
        size = _squad_size(squad_idx)
        filled = 0

        for slot in range(size):
            pidx = Squads.get_squad_player(of, squad_idx, slot)
            num  = Squads.get_shirt_num(of, squad_idx, slot)
            if _valid_pidx(pidx):
                p = Player(of, pidx, 0)
                try:
                    reg = Stats.get_value(of, pidx, Stats.reg_pos)
                    pos_str = _REG_POS[reg] if reg < len(_REG_POS) else "?"
                except Exception:
                    pos_str = "?"
                self._dst_lb.insert(tk.END, f"  #{num:>2}  {pos_str:<4}  {p.name}")
                filled += 1
            else:
                self._dst_lb.insert(tk.END, f"  #{num:>2}  —     <empty>")

        self._dst_count.config(text=f"{filled} players  (will be replaced)")
        self._update_club_options()
        self._update_import_btn()

    def _update_club_options(self):
        """Enable/disable club-only options based on whether both squads are clubs."""
        src_club = (self._src_squad_idx is not None and _is_club_squad(self._src_squad_idx))
        dst_club = (self._dst_squad_idx is not None and _is_club_squad(self._dst_squad_idx))
        both_clubs = src_club and dst_club
        state = tk.NORMAL if both_clubs else tk.DISABLED
        self._opt_kits_cb.config(state=state)
        self._opt_logos_cb.config(state=state)
        self._opt_emblem_cb.config(state=state)
        if not both_clubs:
            self._opt_kits.set(False)
            self._opt_logos.set(False)
            self._opt_emblem.set(False)

    def _update_import_btn(self):
        ready = (self._src_squad_idx is not None
                 and self._dst_squad_idx is not None
                 and len(self._src_players) > 0)
        self._import_btn.config(state=tk.NORMAL if ready else tk.DISABLED)

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def _do_import(self):
        if self._src_squad_idx is None or self._dst_squad_idx is None:
            return
        if not any([self._opt_players.get(), self._opt_roster.get(),
                    self._opt_club.get(), self._opt_kits.get(),
                    self._opt_logos.get(), self._opt_emblem.get()]):
            messagebox.showwarning("Nothing selected",
                                   "Select at least one import option.", parent=self)
            return

        src_squad = self._src_squad_idx
        dst_squad = self._dst_squad_idx
        of, of2   = self._of, self._of2
        src_name  = self._src_var.get()
        dst_name  = self._dst_var.get()
        n_players = len(self._src_players)
        src_club  = _club_idx(src_squad) if _is_club_squad(src_squad) else None
        dst_club  = _club_idx(dst_squad) if _is_club_squad(dst_squad) else None

        opts = []
        if self._opt_players.get(): opts.append(f"  • {n_players} players")
        if self._opt_roster.get():  opts.append("  • Squad roster")
        if self._opt_club.get():    opts.append("  • Club info (name, colors, back pattern)")
        if self._opt_kits.get():    opts.append("  • Kit graphics")
        if self._opt_logos.get():   opts.append("  • Kit logos")
        if self._opt_emblem.get():  opts.append("  • Emblem graphic")

        if not messagebox.askyesno(
            "Confirm import",
            f"Import  '{src_name}'  →  '{dst_name}'?\n\n"
            + "\n".join(opts)
            + "\n\nThis will overwrite existing data in the primary file.",
            parent=self
        ):
            return

        # ── 1. Player data blocks ──────────────────────────────────────
        if self._opt_players.get():
            src_size = _squad_size(src_squad)
            for slot in range(src_size):
                pidx = Squads.get_squad_player(of2, src_squad, slot)
                if not _valid_pidx(pidx):
                    continue
                off = _block_offset(pidx)
                of.data[off:off + 124] = of2.data[off:off + 124]

        # ── 2. Squad roster (source OF2 → destination OF1) ────────────
        if self._opt_roster.get():
            src_slot, src_num, src_sz = _squad_addresses(src_squad)
            dst_slot, dst_num, dst_sz = _squad_addresses(dst_squad)
            copy_sz = min(src_sz, dst_sz)
            of.data[dst_slot:dst_slot + copy_sz * 2] = of2.data[src_slot:src_slot + copy_sz * 2]
            of.data[dst_num :dst_num  + copy_sz]     = of2.data[src_num :src_num  + copy_sz]
            if dst_sz > copy_sz:
                leftover = dst_sz - copy_sz
                of.data[dst_slot + copy_sz * 2:dst_slot + dst_sz * 2] = bytearray(leftover * 2)
                of.data[dst_num  + copy_sz    :dst_num  + dst_sz]     = bytearray(leftover)

        # ── 3. Club info (name, colors, emblem ref, back, stadium) ────
        if self._opt_club.get() and src_club is not None and dst_club is not None:
            Clubs.import_club(of, dst_club, of2, src_club)

        # ── 4. Kit graphics ───────────────────────────────────────────
        if self._opt_kits.get() and src_club is not None and dst_club is not None:
            Kits.import_kit_block(of, dst_club, of2, src_club)

        # ── 5. Kit logos ──────────────────────────────────────────────
        if self._opt_logos.get() and src_club is not None and dst_club is not None:
            _copy_logos(of, dst_club, of2, src_club)

        # ── 6. Emblem graphic ─────────────────────────────────────────
        if self._opt_emblem.get() and src_club is not None and dst_club is not None:
            _copy_emblem(of, dst_club, of2, src_club)

        if self._on_done:
            self._on_done()

        messagebox.showinfo(
            "Done",
            f"'{src_name}'  imported into  '{dst_name}' successfully.",
            parent=self
        )
        self.destroy()
