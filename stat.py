"""
PES Editor 6 - Python Port
Stat class: defines a bit-packed attribute within player data.
"""


class Stat:
    def __init__(self, stat_type: int, offset: int, shift: int, mask: int, name: str):
        """
        stat_type: encoding type (0=raw, 1=height offset, 2=age offset, 3=nationality, 4=foot, 5=1-based, 6=injury, 7=freekick)
        offset:    byte offset within the 124-byte player stats block (relative to stats start)
        shift:     bit shift within a 16-bit word
        mask:      bitmask after shifting
        name:      display label
        """
        self.type = stat_type
        self.offset = offset
        self.shift = shift
        self.mask = mask
        self.name = name
