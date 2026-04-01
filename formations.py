"""
PES Editor 6 - Python Port
Formations data access.
"""

START_ADR = 677202
SIZE      = 364
ABC_SIZE  = 82


def get_pos(of, squad: int, abc: int, i: int) -> int:
    a = START_ADR + 138 + SIZE * squad + abc * ABC_SIZE + i
    v = of.data[a]
    return v if v < 128 else v - 256


def set_pos(of, squad: int, abc: int, i: int, p: int):
    of.data[START_ADR + 138 + SIZE * squad + abc * ABC_SIZE + i] = p & 0xFF


def get_slot(of, squad: int, i: int) -> int:
    return of.data[START_ADR + 6 + SIZE * squad + i]


def set_slot(of, squad: int, i: int, p: int):
    of.data[START_ADR + 6 + SIZE * squad + i] = p & 0xFF


def get_job(of, squad: int, j: int) -> int:
    return of.data[START_ADR + 111 + SIZE * squad + j]


def set_job(of, squad: int, j: int, i: int):
    of.data[START_ADR + 111 + SIZE * squad + j] = i & 0xFF


def get_x(of, squad: int, abc: int, i: int) -> int:
    v = of.data[START_ADR + 118 + SIZE * squad + abc * ABC_SIZE + 2 * (i - 1)]
    return v if v < 128 else v - 256


def get_y(of, squad: int, abc: int, i: int) -> int:
    v = of.data[START_ADR + 119 + SIZE * squad + abc * ABC_SIZE + 2 * (i - 1)]
    return v if v < 128 else v - 256


def set_x(of, squad: int, abc: int, i: int, x: int):
    of.data[START_ADR + 118 + SIZE * squad + abc * ABC_SIZE + 2 * (i - 1)] = x & 0xFF


def set_y(of, squad: int, abc: int, i: int, y: int):
    of.data[START_ADR + 119 + SIZE * squad + abc * ABC_SIZE + 2 * (i - 1)] = y & 0xFF


def get_atk(of, squad: int, abc: int, i: int, direction: int) -> bool:
    t = of.data[START_ADR + 149 + SIZE * squad + abc * ABC_SIZE + i]
    return ((t >> direction) & 1) == 1


def set_atk(of, squad: int, abc: int, i: int, direction: int):
    if direction < 0:
        return
    a = START_ADR + 149 + SIZE * squad + abc * ABC_SIZE + i
    of.data[a] |= (1 << direction)


def clear_atk(of, squad: int, abc: int, i: int, direction: int):
    if direction < 0:
        return
    a = START_ADR + 149 + SIZE * squad + abc * ABC_SIZE + i
    of.data[a] &= ~(1 << direction) & 0xFF
