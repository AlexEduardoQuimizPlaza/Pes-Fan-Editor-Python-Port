"""
PES Editor 6 - Python Port
Squad slot management.
"""
import formations as Formations

NUM23   = 657956
NUM32   = 659635
SLOT23  = 664372
SLOT32  = 667730


def fix_form(of, s: int, fix_jobs: bool):
    if not ((0 <= s < 64) or (73 <= s < 213)):
        return
    t = s if s <= 72 else s - 9
    if s < 64:
        size       = 23
        first_adr  = SLOT23 + s * size * 2
        first_adr_num = NUM23 + s * size
    else:
        size       = 32
        first_adr  = SLOT32 + (s - 73) * size * 2
        first_adr_num = NUM32 + (s - 73) * size

    temp     = bytearray(64)
    temp_num = bytearray(32)
    temp[:size * 2]  = of.data[first_adr:first_adr + size * 2]
    temp_num[:size]  = of.data[first_adr_num:first_adr_num + size]

    for p in range(size):
        slot = Formations.get_slot(of, t, p)
        if slot >= 32:
            # Java signed bytes: values like 0xFF=-1 are invalid indices.
            # Java would throw ArrayIndexOutOfBoundsException (silently swallowed
            # by the AWT event dispatcher). We just skip these positions.
            continue
        of.data[first_adr + p * 2: first_adr + p * 2 + 2] = temp[slot * 2: slot * 2 + 2]
        of.data[first_adr_num + p] = temp_num[slot]

    if fix_jobs:
        for j in range(6):
            for i in range(32):
                if Formations.get_slot(of, t, i) == Formations.get_job(of, t, j):
                    Formations.set_job(of, t, j, i)
                    break

    for i in range(32):
        Formations.set_slot(of, t, i, i)


def fix_all(of):
    for i in range(213):
        fix_form(of, i, True)
    # Java's fixAll also processes squads 64-72 (which Python skips).
    # Normalize their slot bytes so Java doesn't read values > 127 as negative indices.
    for gap in range(64, 73):
        for i in range(32):
            Formations.set_slot(of, gap, i, i)


def tidy(of, team: int):
    if not ((0 <= team < 64) or (73 <= team < 213)):
        return
    if team < 64:
        size      = 23
        first_adr = SLOT23 + team * size * 2
        first_adr_num = NUM23 + team * size
    else:
        size      = 32
        first_adr = SLOT32 + (team - 73) * size * 2
        first_adr_num = NUM32 + (team - 73) * size

    # Remove duplicate / zero player entries
    seen = set()
    for p in range(size):
        idx = (of.data[first_adr + p * 2 + 1] << 8) | of.data[first_adr + p * 2]
        if idx in seen or idx == 0:
            of.data[first_adr + p * 2]     = 0
            of.data[first_adr + p * 2 + 1] = 0
            of.data[first_adr_num + p]      = 0
        else:
            seen.add(idx)


def get_squad_player(of, team: int, slot: int) -> int:
    """Return player index for squad slot, or 0 if empty."""
    if team < 64:
        first_adr = SLOT23 + team * 23 * 2
    else:
        first_adr = SLOT32 + (team - 73) * 32 * 2
    lo = of.data[first_adr + slot * 2]
    hi = of.data[first_adr + slot * 2 + 1]
    return (hi << 8) | lo


def set_squad_player(of, team: int, slot: int, player_idx: int):
    if team < 64:
        first_adr = SLOT23 + team * 23 * 2
    else:
        first_adr = SLOT32 + (team - 73) * 32 * 2
    of.data[first_adr + slot * 2]     = player_idx & 0xFF
    of.data[first_adr + slot * 2 + 1] = (player_idx >> 8) & 0xFF


def get_shirt_num(of, team: int, slot: int) -> int:
    if team < 64:
        first_adr_num = NUM23 + team * 23
    else:
        first_adr_num = NUM32 + (team - 73) * 32
    return of.data[first_adr_num + slot]


def set_shirt_num(of, team: int, slot: int, num: int):
    if team < 64:
        first_adr_num = NUM23 + team * 23
    else:
        first_adr_num = NUM32 + (team - 73) * 32
    of.data[first_adr_num + slot] = num & 0xFF
