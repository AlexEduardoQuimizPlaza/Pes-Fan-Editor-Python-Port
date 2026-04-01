"""
PES Editor 6 - Python Port
Stat definition class (renamed from stat.py to avoid conflict with stdlib).
"""


class Stat:
    def __init__(self, stat_type: int, offset: int, shift: int, mask: int, name: str):
        self.type   = stat_type
        self.offset = offset
        self.shift  = shift
        self.mask   = mask
        self.name   = name
