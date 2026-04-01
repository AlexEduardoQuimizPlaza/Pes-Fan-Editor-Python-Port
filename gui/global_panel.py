"""
PES Editor 6 - Python Port
Global stat adjustment panel: apply ±delta to a stat across all players.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import stats as Stats
from player import Player, TOTAL, FIRST_EDIT, TOTAL_EDIT


class GlobalPanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of = of
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Global Stat Adjustment", font=("", 12, "bold")).pack(pady=8)
        ttk.Label(self, text="Select a stat and apply a delta to ALL players.").pack()
        ttk.Label(self, text="Values will be clamped to the valid range.").pack(pady=4)

        form = ttk.Frame(self)
        form.pack(padx=8, pady=8)

        ttk.Label(form, text="Stat:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self._stat_var = tk.StringVar()
        stat_names = [s.name for s in Stats.ability99 if s.name]
        self._stat_combo = ttk.Combobox(form, textvariable=self._stat_var, values=stat_names,
                                         width=20, state="readonly")
        self._stat_combo.grid(row=0, column=1, sticky=tk.W, padx=4)
        if stat_names:
            self._stat_combo.current(0)

        ttk.Label(form, text="Delta (+/-):").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self._delta_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self._delta_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=4)

        ttk.Button(form, text="Apply to All Players", command=self._apply).grid(
            row=2, column=0, columnspan=2, pady=8)

        self._result_label = ttk.Label(self, text="")
        self._result_label.pack()

    def refresh(self):
        pass  # nothing to load

    def _apply(self):
        stat_name = self._stat_var.get()
        stat = next((s for s in Stats.ability99 if s.name == stat_name), None)
        if not stat:
            messagebox.showerror("Error", "Select a valid stat.", parent=self)
            return
        try:
            delta = int(self._delta_var.get())
        except ValueError:
            messagebox.showerror("Error", "Delta must be an integer.", parent=self)
            return

        if not messagebox.askyesno("Confirm",
            f"Apply delta {delta:+d} to '{stat_name}' for ALL players?\nThis cannot be undone.",
            parent=self):
            return

        count = 0
        of = self._of
        for i in range(1, TOTAL):
            p = Player(of, i, 0)
            if p.name.startswith("<"):
                continue
            old = Stats.get_value(of, i, stat)
            new = max(0, min(stat.mask, old + delta))
            if new != old:
                Stats.set_value(of, i, stat, new)
                count += 1

        self._result_label.config(text=f"Done. Modified {count} players.")
