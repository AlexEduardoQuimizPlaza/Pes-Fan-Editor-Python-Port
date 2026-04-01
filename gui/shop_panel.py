"""
PES Editor 6 - Python Port
Shop Panel: PES Points editor + Shop Items unlock.
Ported from WENPanel.java + ShopPanel.java + WENShopPanel.java (Compulsion 2008-9).
"""
import tkinter as tk
from tkinter import ttk, messagebox


class ShopPanel(ttk.Frame):
    def __init__(self, parent, of):
        super().__init__(parent)
        self._of = of
        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(padx=8, pady=8, fill=tk.BOTH)

        # --- PES Points (WENPanel) ---
        wen_frame = ttk.LabelFrame(container, text="PES Points")
        wen_frame.pack(fill=tk.X, padx=4, pady=4)

        self._wen_entry = ttk.Entry(wen_frame, width=10)
        self._wen_entry.pack(padx=6, pady=(6, 2))
        self._wen_entry.bind("<Return>", self._on_wen_enter)

        ttk.Label(wen_frame, text="Enter an amount (0-99999) and press Return",
                  foreground="gray").pack(padx=6, pady=(0, 2))

        self._wen_current = ttk.Label(wen_frame, text="Current:  0")
        self._wen_current.pack(padx=6, pady=(0, 6))

        # --- Shop Items (ShopPanel) ---
        shop_frame = ttk.LabelFrame(container, text="Shop Items")
        shop_frame.pack(fill=tk.X, padx=4, pady=4)

        self._unlock_status = ttk.Label(shop_frame, text="")
        ttk.Button(shop_frame, text="Unlock", command=self._unlock_shop).pack(
            padx=6, pady=(6, 2))
        self._unlock_status.pack(padx=6, pady=(0, 6))

    # ------------------------------------------------------------------
    # PES Points
    # ------------------------------------------------------------------

    def refresh(self):
        if self._of is None or not self._of.data:
            return
        wen = (self._to_int(self._of.data[50]) << 16) \
            | (self._to_int(self._of.data[49]) << 8) \
            |  self._to_int(self._of.data[48])
        self._wen_current.config(text=f"Current:  {wen}")
        self._wen_entry.delete(0, tk.END)
        self._unlock_status.config(text="")

    def _on_wen_enter(self, event):
        try:
            value = int(self._wen_entry.get())
        except ValueError:
            return
        self._set_wen(value)

    def _set_wen(self, new_wen: int):
        if 0 <= new_wen <= 99999:
            self._of.data[48] = self._to_byte(new_wen & 0xFF)
            self._of.data[49] = self._to_byte((new_wen & 0xFF00) >> 8)
            self._of.data[50] = self._to_byte((new_wen & 0xFF0000) >> 16)
            self._of.data[5208] = self._to_byte(new_wen & 0xFF)
            self._of.data[5209] = self._to_byte((new_wen & 0xFF00) >> 8)
            self._of.data[5210] = self._to_byte((new_wen & 0xFF0000) >> 16)
            self.refresh()
        else:
            self._wen_entry.delete(0, tk.END)
            messagebox.showerror(
                "Error", "Amount must be in the range 0-99999", parent=self)

    # ------------------------------------------------------------------
    # Shop Items
    # ------------------------------------------------------------------

    def _unlock_shop(self):
        for i in range(20):
            self._of.data[5144 + i] = self._to_byte(0xFF)   # -1 as signed byte
        self._of.data[5164] = self._to_byte(0xFA)   # -6
        self._of.data[5165] = 11
        self._of.data[5166] = self._to_byte(0xFE)   # -2
        self._of.data[5167] = self._to_byte(0xFF)   # -1
        self._of.data[5168] = self._to_byte(0xEF)   # -17
        self._of.data[5169] = 127
        self._of.data[52]   = 100
        self._unlock_status.config(text="Unlocked")

    # ------------------------------------------------------------------
    # Helpers (mirror Java OptionFile.toInt / toByte)
    # ------------------------------------------------------------------

    @staticmethod
    def _to_int(b: int) -> int:
        """Unsigned byte value (mirrors Java's Byte.toUnsignedInt)."""
        return b & 0xFF

    @staticmethod
    def _to_byte(i: int) -> int:
        """Truncate to one unsigned byte (bytearray stores 0-255)."""
        return i & 0xFF
