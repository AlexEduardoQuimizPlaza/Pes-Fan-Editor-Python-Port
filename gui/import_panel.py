"""
PES Editor 6 - Python Port
OF2 Import Panel: copy data blocks from a secondary option file.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from option_file import BLOCK, BLOCK_SIZE


class ImportPanel(ttk.Frame):
    def __init__(self, parent, of, of2):
        super().__init__(parent)
        self._of  = of
        self._of2 = of2
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="OF2 Import", font=("", 12, "bold")).pack(pady=8)
        ttk.Label(self, text="Copy data blocks from the secondary (OF2) file to the primary file.").pack()
        ttk.Label(self, text="Open OF2 via File > Open OF2...", font=("", 9, "italic")).pack()

        frame = ttk.LabelFrame(self, text="Select Blocks to Import")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        BLOCK_NAMES = [
            "Block 0: Header",
            "Block 1: General Player Data",
            "Block 2: Edit Player Data",
            "Block 3: Extended Player Data",
            "Block 4: Player Stats",
            "Block 5: Clubs Data",
            "Block 6: Kits Data",
            "Block 7: Formations",
            "Block 8: Squads",
            "Block 9: Unknown",
        ]

        self._block_vars = []
        for i, name in enumerate(BLOCK_NAMES):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(frame, text=name, variable=var)
            cb.pack(anchor=tk.W, padx=8, pady=2)
            self._block_vars.append(var)

        ttk.Button(self, text="Import Selected Blocks", command=self._import).pack(pady=8)
        self._status_label = ttk.Label(self, text="")
        self._status_label.pack()

    def refresh(self):
        of2_loaded = self._of2.file_name is not None
        status = f"OF2: {self._of2.file_name}" if of2_loaded else "OF2: not loaded"
        self._status_label.config(text=status)

    def _import(self):
        if self._of2.file_name is None:
            messagebox.showerror("Error", "No OF2 file loaded. Use File > Open OF2...", parent=self)
            return
        selected = [i for i, v in enumerate(self._block_vars) if v.get()]
        if not selected:
            messagebox.showwarning("Warning", "No blocks selected.", parent=self)
            return
        if not messagebox.askyesno("Confirm",
            f"Import {len(selected)} block(s) from OF2?\nThis will overwrite data in the primary file.",
            parent=self):
            return
        for i in selected:
            start = BLOCK[i]
            size  = BLOCK_SIZE[i]
            self._of.data[start:start+size] = self._of2.data[start:start+size]
        messagebox.showinfo("Done", f"Imported {len(selected)} block(s) from OF2.", parent=self)
