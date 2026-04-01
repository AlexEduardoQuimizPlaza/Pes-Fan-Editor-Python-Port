"""
PES Editor 6 - Python Port
League Panel: list of league names, click to select, type and press Enter to rename.
Ported from LeaguePanel.java (Compulsion 2008-9).
"""
import tkinter as tk
from tkinter import ttk
import leagues as Leagues


class LeaguePanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of = of
        self._build_ui()

    def _build_ui(self):
        pan = ttk.LabelFrame(self, text="League Names")
        pan.pack(padx=8, pady=8)

        self._listbox = tk.Listbox(pan, width=30, height=20)
        self._listbox.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)
        # defer to after_idle so we get the final selection state,
        # mirroring Java's e.getValueIsAdjusting() == false check
        self._listbox.bind("<<ListboxSelect>>",
                           lambda e: self.after_idle(self._load_selection))

        self._editor = ttk.Entry(pan, width=20)
        self._editor.pack(side=tk.LEFT, padx=4, pady=4, anchor=tk.N)
        self._editor.bind("<Return>", self._on_enter)

    def refresh(self):
        if self._of is None:
            return
        self._listbox.delete(0, tk.END)
        for name in Leagues.get_all(self._of):
            self._listbox.insert(tk.END, name)

    def _load_selection(self):
        """Called after_idle so the listbox selection is stable."""
        sel = self._listbox.curselection()
        if not sel:
            self._editor.delete(0, tk.END)
            return
        i = sel[0]
        self._editor.delete(0, tk.END)
        self._editor.insert(0, Leagues.get(self._of, i))

    def _on_enter(self, event):
        sel = self._listbox.curselection()
        if not sel:
            return
        sn = sel[0]
        text = self._editor.get().strip()
        if not text or len(text) > Leagues.MAX_LEN:
            return
        if text != Leagues.get(self._of, sn):
            Leagues.set(self._of, sn, text)
            self._listbox.delete(sn)
            self._listbox.insert(sn, text)
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(sn)
        # advance to next item
        if sn < Leagues.TOTAL - 1:
            next_i = sn + 1
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(next_i)
            self._listbox.see(next_i)
            self._editor.delete(0, tk.END)
            self._editor.insert(0, Leagues.get(self._of, next_i))
