"""
PES Editor 6 - Python Port
Main window (tkinter).
"""
import os
import pickle
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from option_file import OptionFile
import squads as Squads
import csv_maker
import csv_loader

from gui.transfer_panel  import TransferPanel
from gui.team_panel      import TeamPanel
from gui.emblem_panel    import EmblemPanel
from gui.logo_panel      import LogoPanel
from gui.league_panel    import LeaguePanel
from gui.stadium_panel   import StadiumPanel
from gui.global_panel    import GlobalPanel
from gui.import_panel    import ImportPanel
from gui.shop_panel           import ShopPanel
from gui.transfermarkt_panel  import TransfermarktPanel
from gui.kit_panel            import KitPanel
from gui.player_dialog        import PlayerDialog


SETTINGS_FILE = "PFE_settings.dat"
SUPPORTED_EXTS = [
    ("All files", "*"),
    ("PES6 Save Files", "*.xps *.psu *.max *.bin"),
    ("SharkPort XPS", "*.xps"),
    ("PowerSave PSU", "*.psu"),
    ("MaxSave MAX", "*.max"),
    ("PC Binary", "*.bin"),
]


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PES Editor 6")
        self.resizable(False, False)

        self._of   = OptionFile()
        self._of2  = OptionFile()
        self._current_file = None
        self._last_dir = self._load_settings()

        self._build_menu()
        self._build_tabs()
        self._set_file_loaded(False)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_menu(self):
        mb = tk.Menu(self)
        self.config(menu=mb)

        # File menu
        file_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open...",       command=self._open_file)
        self._open2_item = file_menu.add_command
        file_menu.add_command(label="Open OF2...",   command=self._open_of2, state=tk.DISABLED)
        self._open2_item = lambda s: None  # placeholder
        file_menu.add_separator()
        file_menu.add_command(label="Save",          command=self._save,    state=tk.DISABLED)
        file_menu.add_command(label="Save As...",    command=self._save_as, state=tk.DISABLED)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",          command=self.destroy)

        self._file_menu = file_menu

        # Tools menu
        tools_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Export stats to CSV...", command=self._export_csv, state=tk.DISABLED)
        tools_menu.add_command(label="Import stats from CSV...", command=self._import_csv, state=tk.DISABLED)
        tools_menu.add_separator()
        tools_menu.add_command(label="Convert OF2 → OF1", command=self._convert, state=tk.DISABLED)
        self._tools_menu = tools_menu

        # Help menu
        help_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About...", command=self._show_about)

    def _build_tabs(self):
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._transfer_panel = TransferPanel(self._notebook, self._of, self._edit_player)
        self._team_panel     = TeamPanel(self._notebook, self._of)
        self._emblem_panel   = EmblemPanel(self._notebook, self._of)
        self._logo_panel     = LogoPanel(self._notebook, self._of)
        self._league_panel   = LeaguePanel(self._notebook, self._of)
        self._stadium_panel  = StadiumPanel(self._notebook, self._of, self._team_panel)
        self._shop_panel          = ShopPanel(self._notebook, self._of)
        self._transfermarkt_panel = TransfermarktPanel(
            self._notebook, self._of,
            refresh_fn=lambda: (self._emblem_panel.refresh(), self._team_panel.refresh())
        )
        self._global_panel        = GlobalPanel(self._notebook, self._of)
        self._import_panel        = ImportPanel(self._notebook, self._of, self._of2)
        self._kit_panel           = KitPanel(self._notebook, self._of)

        self._notebook.add(self._transfer_panel,      text="Transfer")
        self._notebook.add(self._team_panel,          text="Team")
        self._notebook.add(self._kit_panel,           text="Kits")
        self._notebook.add(self._emblem_panel,        text="Emblem")
        self._notebook.add(self._logo_panel,          text="Logo")
        self._notebook.add(self._league_panel,        text="League")
        self._notebook.add(self._stadium_panel,       text="Stadium")
        self._notebook.add(self._shop_panel,          text="PES / Shop")
        self._notebook.add(self._transfermarkt_panel, text="Transfermarkt")
        self._notebook.add(self._global_panel,        text="Stat Adjust")
        self._notebook.add(self._import_panel,        text="OF2 Import")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open PES6 Option File",
            initialdir=self._last_dir,
            filetypes=SUPPORTED_EXTS,
            parent=self
        )
        if not path:
            return
        self._last_dir = os.path.dirname(path)
        self._save_settings()

        if self._of.read(path):
            self._current_file = path
            Squads.fix_all(self._of)
            self.title(f"PES Editor 6 - {os.path.basename(path)}")
            self._refresh_all()
            self._set_file_loaded(True)
        else:
            messagebox.showerror("Error", "Could not open file.", parent=self)
            self._set_file_loaded(False)

    def _open_of2(self):
        path = filedialog.askopenfilename(
            title="Open Secondary (OF2) File",
            initialdir=self._last_dir,
            filetypes=SUPPORTED_EXTS,
            parent=self
        )
        if not path:
            return
        if self._of2.read(path):
            Squads.fix_all(self._of2)
            self._import_panel.refresh()
            messagebox.showinfo("OF2 Loaded", f"OF2: {os.path.basename(path)}", parent=self)
        else:
            messagebox.showerror("Error", "Could not open OF2 file.", parent=self)

    def _save(self):
        if not self._current_file:
            return
        if os.path.exists(self._current_file):
            os.remove(self._current_file)
        if self._of.save(self._current_file):
            messagebox.showinfo("Saved", f"Saved to:\n{self._current_file}", parent=self)
        else:
            messagebox.showerror("Error", "Save failed.", parent=self)

    def _save_as(self):
        if not self._current_file:
            return
        ext_map = {
            OptionFile.FORMAT_XPS: ("xps", [("SharkPort XPS", "*.xps")]),
            OptionFile.FORMAT_PSU: ("psu", [("PowerSave PSU", "*.psu")]),
            OptionFile.FORMAT_MAX: ("max", [("MaxSave MAX",   "*.max")]),
            OptionFile.FORMAT_BIN: ("bin", [("PC Binary",     "*.bin")]),
        }
        default_ext, filetypes = ext_map.get(self._of.format, ("bin", [("All files", "*.*")]))
        path = filedialog.asksaveasfilename(
            title="Save As",
            initialdir=self._last_dir,
            defaultextension=f".{default_ext}",
            filetypes=filetypes,
            parent=self
        )
        if not path:
            return
        self._save_settings()
        if self._of.save(path):
            self._current_file = path
            self.title(f"PES Editor 6 - {os.path.basename(path)}")
            messagebox.showinfo("Saved", f"Saved to:\n{path}", parent=self)
        else:
            messagebox.showerror("Error", "Save failed.", parent=self)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _export_csv(self):
        if not self._current_file:
            return
        path = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            parent=self
        )
        if not path:
            return
        if csv_maker.make_file(self._of, path):
            messagebox.showinfo("Done", f"CSV exported to:\n{path}", parent=self)
        else:
            messagebox.showerror("Error", "CSV export failed.", parent=self)

    def _import_csv(self):
        if not self._current_file:
            return
        path = filedialog.askopenfilename(
            title="Import CSV",
            filetypes=[("CSV Files", "*.csv"), ("All files", "*.*")],
            parent=self
        )
        if not path:
            return
        changes = []
        if csv_loader.load_file(self._of, path, changes=changes):
            self._transfer_panel.refresh()
            msg = f"Imported from:\n{path}"
            if changes:
                msg += f"\n\nChanges ({len(changes)}):\n" + "\n".join(changes[:15])
                if len(changes) > 15:
                    msg += f"\n... and {len(changes)-15} more"
            messagebox.showinfo("CSV Import Done", msg, parent=self)
        else:
            messagebox.showerror("Error", "CSV import failed.", parent=self)

    def _convert(self):
        from option_file import BLOCK, BLOCK_SIZE
        for i in range(2, 9):
            start = BLOCK[i]
            size  = BLOCK_SIZE[i]
            self._of.data[start:start+size] = self._of2.data[start:start+size]
        self._refresh_all()
        messagebox.showinfo("Converted", "OF2 data copied to OF1.", parent=self)

    # ------------------------------------------------------------------
    # Player editing
    # ------------------------------------------------------------------

    def _edit_player(self, player):
        dlg = PlayerDialog(self, self._of, player)
        self.wait_window(dlg)
        self._transfer_panel.refresh()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_all(self):
        self._transfer_panel.refresh()
        self._team_panel.refresh()
        self._kit_panel.refresh()
        self._emblem_panel.refresh()
        self._logo_panel.refresh()
        self._league_panel.refresh()
        self._stadium_panel.refresh()
        self._shop_panel.refresh()
        self._transfermarkt_panel.refresh()
        self._global_panel.refresh()
        self._import_panel.refresh()

    def _set_file_loaded(self, loaded: bool):
        state = tk.NORMAL if loaded else tk.DISABLED
        self._file_menu.entryconfig("Open OF2...",  state=state)
        self._file_menu.entryconfig("Save",         state=state)
        self._file_menu.entryconfig("Save As...",   state=state)
        self._tools_menu.entryconfig("Export stats to CSV...",   state=state)
        self._tools_menu.entryconfig("Import stats from CSV...", state=state)
        self._tools_menu.entryconfig("Convert OF2 \u2192 OF1",  state=state)

    def _show_about(self):
        messagebox.showinfo(
            "About PES Editor 6",
            "PES Editor 6\nversion 6.1.1 (Python Port)\n\n"
            "Original Java version:\n"
            "© Copyright 2006-7 Compulsion\n"
            "2011, 2012 juce (CSV import)\n"
            "2019 PeterC10 (Enhancements)\n"
            "2017-19 lazanet (PSD connection)\n\n"
            "Python port based on the original GPL v3 source.\n\n"
            "This program is free software under the GNU GPL v3.",
            parent=self
        )

    def _load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "rb") as f:
                    d = pickle.load(f)
                if d and os.path.isdir(d):
                    return d
        except Exception:
            pass
        return None

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "wb") as f:
                pickle.dump(self._last_dir, f)
        except Exception:
            pass
