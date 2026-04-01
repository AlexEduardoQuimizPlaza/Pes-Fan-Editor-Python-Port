"""
PES Editor 6 - Python Port
Clubs data access.
"""

TOTAL       = 140
START_ADR   = 751472
SIZE        = 88
FIRST_FLAG  = 292
FIRST_DEF_EMBLEM = 115


def get_emblem(of, club: int) -> int:
    a = START_ADR + 60 + SIZE * club
    return (of.data[a + 1] << 8) | of.data[a]


def set_emblem(of, club: int, index: bytes = None):
    edited = True
    if index is None:
        index = of.get_bytes(club + FIRST_DEF_EMBLEM)
        edited = False
    a = START_ADR + 60 + SIZE * club
    of.data[a:a+2]   = index
    of.data[a+4:a+6] = index
    set_emblem_edited(of, club, edited)


def set_emblem_int(of, club: int, emblem_value: int):
    """Set club emblem to integer emblem_value (e.g. slot + FIRST_FLAG)."""
    set_emblem(of, club, of.get_bytes(emblem_value))


def reset_emblem(of, club: int):
    """Reset club emblem to its default (per-club default emblem index)."""
    set_emblem(of, club, None)


def un_ass_emblem(of, emblem: int):
    for i in range(TOTAL):
        if emblem == get_emblem(of, i) - FIRST_FLAG:
            set_emblem(of, i, None)


def get_abbr(of, c: int) -> str:
    """Return 3-letter club abbreviation (offset 49 within each record)."""
    a = START_ADR + 49 + c * SIZE
    try:
        raw = bytes(of.data[a:a + 3])
        return raw.decode("ascii").rstrip('\x00').strip()
    except Exception:
        return "???"


def set_abbr(of, c: int, text: str):
    """Write 3-letter club abbreviation."""
    a = START_ADR + 49 + c * SIZE
    encoded = text[:3].upper().encode("ascii")
    for i in range(3):
        of.data[a + i] = encoded[i] if i < len(encoded) else 0


def get_names(of) -> list:
    return [get_name(of, c) for c in range(TOTAL)]


def get_name(of, c: int) -> str:
    a = START_ADR + c * SIZE
    if of.data[a] == 0:
        return f"<{c}>"
    length = 0
    for i in range(49):
        if of.data[a + i] == 0:
            length = i
            break
    if length == 0:
        return f"<{c}>"
    try:
        return bytes(of.data[a:a+length]).decode("utf-8")
    except Exception:
        return f"<{c}>"


def set_name(of, c: int, name: str):
    a = START_ADR + c * SIZE
    encoded = name.encode("utf-8")[:48]
    for i in range(49):
        of.data[a + i] = 0
    of.data[a:a+len(encoded)] = encoded
    set_name_edited(of, c)


def get_back(of, club: int) -> int:
    """Return the flag background pattern index (0-11)."""
    return of.data[START_ADR + 70 + SIZE * club] & 0xFF


def set_back(of, club: int, back: int):
    of.data[START_ADR + 70 + SIZE * club] = back & 0xFF


def get_color1(of, club: int) -> tuple:
    a = START_ADR + 72 + SIZE * club
    return (of.data[a], of.data[a+1], of.data[a+2])


def set_color1(of, club: int, r: int, g: int, b: int):
    a = START_ADR + 72 + SIZE * club
    of.data[a]   = r & 0xFF
    of.data[a+1] = g & 0xFF
    of.data[a+2] = b & 0xFF


def get_color2(of, club: int) -> tuple:
    a = START_ADR + 76 + SIZE * club
    return (of.data[a], of.data[a+1], of.data[a+2])


def set_color2(of, club: int, r: int, g: int, b: int):
    a = START_ADR + 76 + SIZE * club
    of.data[a]   = r & 0xFF
    of.data[a+1] = g & 0xFF
    of.data[a+2] = b & 0xFF


def get_stadium(of, club: int) -> int:
    a = START_ADR + 80 + SIZE * club
    return of.data[a]


def set_stadium(of, club: int, stadia_idx: int):
    a = START_ADR + 80 + SIZE * club
    of.data[a] = stadia_idx & 0xFF


def import_club(of1, c1: int, of2, c2: int):
    a1 = START_ADR + SIZE * c1
    a2 = START_ADR + SIZE * c2
    t = of1.data[a1 + 54]
    of1.data[a1:a1+SIZE] = of2.data[a2:a2+SIZE]
    of1.data[a1 + 54] = t
    set_name_edited(of1, c1)
    set_emblem_edited(of1, c1, True)
    set_stadium_edited(of1, c1)


def set_name_edited(of, club: int):
    a = START_ADR + 56 + SIZE * club
    of.data[a] |= 0x01


def set_emblem_edited(of, club: int, edited: bool):
    a = START_ADR + 62 + SIZE * club
    if edited:
        of.data[a] |= 0x01
    else:
        of.data[a] &= 0xFE


def set_stadium_edited(of, club: int):
    a = START_ADR + 81 + SIZE * club
    of.data[a] |= 0x01
