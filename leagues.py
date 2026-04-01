"""
PES Editor 6 - Python Port
Leagues data access.
Ported from Leagues.java (Compulsion 2008-9).
"""

TOTAL     = 29
NAME_ADR  = 11859
MAX_LEN   = 61
FIELD_LEN = 84

_DEF = [
    "ISS", "England", "French", "German", "Italian",
    "Netherlands", "Spanish", "International", "European", "African",
    "American", "Asia-Oceanian", "Konami", "D2", "D1", "European Masters",
    "European Championship", "Product Placement Cup",
]


def get(of, l: int) -> str:
    a = NAME_ADR + l * FIELD_LEN
    if of.data[a] != 0:
        length = 0
        for i in range(MAX_LEN + 1):
            if of.data[a + i] == 0:
                length = i
                break
        if length == 0:
            return f"<{l}>"
        try:
            return bytes(of.data[a:a + length]).decode("utf-8")
        except Exception:
            return f"<{l}>"
    else:
        if l > 10:
            name = _DEF[l - 11]
            if l < 27:
                name = name + " Cup"
        else:
            name = f"<{l}>"
        return name


def get_all(of) -> list:
    return [get(of, l) for l in range(TOTAL)]


def set(of, ln: int, name: str):
    if 0 < len(name) <= MAX_LEN:
        a = NAME_ADR + ln * FIELD_LEN
        encoded = name.encode("utf-8")
        tb = bytearray(MAX_LEN + 2)
        copy_len = min(len(encoded), MAX_LEN)
        tb[:copy_len] = encoded[:copy_len]
        tb[MAX_LEN + 1] = 1
        of.data[a:a + MAX_LEN + 2] = tb


def import_data(src_of, dst_of):
    start = NAME_ADR
    size  = FIELD_LEN * TOTAL
    dst_of.data[start:start + size] = src_of.data[start:start + size]
