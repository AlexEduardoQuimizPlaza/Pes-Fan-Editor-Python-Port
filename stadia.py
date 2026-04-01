"""
PES Editor 6 - Python Port
Stadia data access.
Ported from Stadia.java (Compulsion 2008-9).
"""

TOTAL      = 36
NAME_ADR   = 9544
MAX_LEN    = 61
SWITCH_ADR = NAME_ADR + MAX_LEN * TOTAL   # 9544 + 61*36 = 11740


def get(of, s: int) -> str:
    a = NAME_ADR + s * MAX_LEN
    if of.data[a] == 0:
        return f"<{s}>"
    length = 0
    for i in range(MAX_LEN):
        if of.data[a + i] == 0:
            length = i
            break
    if length == 0:
        return f"<{s}>"
    try:
        return bytes(of.data[a:a + length]).decode("utf-8")
    except Exception:
        return f"<{s}>"


def get_all(of) -> list:
    return [get(of, s) for s in range(TOTAL)]


def set(of, sn: int, name: str):
    if 0 < len(name) < MAX_LEN:
        a  = NAME_ADR   + sn * MAX_LEN
        sa = SWITCH_ADR + sn
        tb = bytearray(MAX_LEN)
        encoded = name.encode("utf-8")
        copy_len = min(len(encoded), MAX_LEN - 1)
        tb[:copy_len] = encoded[:copy_len]
        of.data[a:a + MAX_LEN] = tb
        of.data[sa] = 1


def import_data(src_of, dst_of):
    from leagues import NAME_ADR as LEAGUES_NAME_ADR
    size = LEAGUES_NAME_ADR - NAME_ADR
    dst_of.data[NAME_ADR:NAME_ADR + size] = src_of.data[NAME_ADR:NAME_ADR + size]


# Legacy aliases used by old stadium_panel
def get_name(of, s: int) -> str:
    return get(of, s)

def get_names(of) -> list:
    return get_all(of)
