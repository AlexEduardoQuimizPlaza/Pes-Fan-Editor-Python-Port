"""
PES Editor 6 - Python Port
Kit data access.  Addresses ported from Kits.java (Compulsion 2008-9).

Layout per team block
─────────────────────
Club teams  : startAdrC = 786332, sizeC = 544, total = 140
National    : startAdrN = 763804, sizeN = 352, total = 64

Within each team's SIZE-byte block:
  offset  58        : licensed flag (1 = licensed)
  offset  60        : GK Home kit  (62 bytes: model + 61 colour bytes)
  offset 122        : Home kit     (62 bytes)
  offset 184        : GK Away kit  (62 bytes)
  offset 246        : Away kit     (62 bytes)
  offset 256+l*24   : logo entry l (0-3), each 24 bytes
                        +2  = used flag (1 = logo assigned)
                        +3  = logo slot number

The original Compulsion Java port labelled these "Home / Away / 3rd / GK"
which does not match the actual PES 6 layout — verified against the in-game
"Editar equipo" preview where slot 0 holds the GK kit, slot 1 the Home kit,
slot 2 the alternate GK and slot 3 the Away kit.  KIT_SLOT_MAP below remaps
the user-facing tab order (Home, Away, GK Home, GK Away) onto the on-disk
slots so the panel shows the right kit per tab.
"""

# Club kit constants (matches Java's Kits.java)
START_ADR_C = 786332
SIZE_C       = 544
TOTAL_C      = 140       # == Clubs.total

# National team kit constants
START_ADR_N  = 763804
SIZE_N       = 352
TOTAL_N      = 64

# Per-team block offsets
LIC_OFFSET   = 58        # licensed flag
KIT_OFFSET   = 60        # first kit base
KIT_SIZE     = 62        # bytes per kit (1 model + 61 colour bytes)
KITS_PER_TEAM = 4        # Home / Away / GK Home / GK Away
LOGO_OFFSET  = 256       # logo table base within team block
LOGO_SIZE    = 24        # bytes per logo entry
LOGOS_PER_TEAM = 4

KIT_NAMES    = ["Home", "Away", "GK Home", "GK Away"]

# UI tab index → physical slot index in the OF block.
# OF stores kits in order (GK Home, Home, GK Away, Away) at offsets
# 60 / 122 / 184 / 246, but the panel exposes them as (Home, Away,
# GK Home, GK Away) which is the order players expect.
KIT_SLOT_MAP = (1, 3, 0, 2)

# WE→PES model number remapping (from Convert.java)
_MODEL_MAP = {149: 22, 150: 83, 151: 84}   # Java bytes -107,-106,-105 unsigned = 149,150,151

# ── KITINFO colour field layout ───────────────────────────────────────────────
# Each colour field is a 16-bit LE WORD: 0x8000 | (B5<<10) | (G5<<5) | R5
# Offsets are relative to the START of the KITINFO record (= _kitinfo_base).
#
# (field_key, display_label, kitinfo_offset, count)
COLOR_GROUPS = [
    ("shirt",   "Shirt",    0,  5),   # shirtColors[0..4]
    ("shorts",  "Shorts",  10,  4),   # shortsColors[0..3]
    ("socks",   "Socks",   18,  3),   # socksColors[0..2]
    ("captain", "Armband", 24,  3),   # captainColors[0..2]
    ("nameBC",  "Name BC", 30,  1),
    ("nameC",   "Name",    32,  1),
    ("numBC",   "Num BC",  34,  1),
    ("numC",    "Number",  36,  1),
    ("shnBC",   "Sh# BC",  38,  1),
    ("shnC",    "Sh#",     40,  1),
]


# ── internal address helpers ──────────────────────────────────────────────────

def _base(team: int) -> int:
    """Absolute OF offset for the start of team's kit block."""
    if team < TOTAL_C:
        return START_ADR_C + SIZE_C * team
    return START_ADR_N + SIZE_N * (team - TOTAL_C)


def _kitinfo_base(team: int, kit: int) -> int:
    """Absolute offset of the start of KITINFO record for kit slot k.

    `kit` is the user-facing tab index (0=Home, 1=Away, 2=GK Home, 3=GK Away);
    KIT_SLOT_MAP translates it to the physical slot used on disk.
    """
    physical = KIT_SLOT_MAP[kit]
    return _base(team) + KIT_SIZE * physical


def _kit_addr(team: int, kit: int) -> int:
    """Address of the model byte within KITINFO (= _kitinfo_base + 60)."""
    return _kitinfo_base(team, kit) + KIT_OFFSET


def _logo_addr(team: int, logo: int) -> int:
    return _base(team) + LOGO_OFFSET + LOGO_SIZE * logo


# ── licensed flag ─────────────────────────────────────────────────────────────

def is_licensed(of, team: int) -> bool:
    return of.data[_base(team) + LIC_OFFSET] == 1


def set_licensed(of, team: int, value: bool):
    of.data[_base(team) + LIC_OFFSET] = 1 if value else 0


# ── kit model ─────────────────────────────────────────────────────────────────

def get_model(of, team: int, kit: int) -> int:
    return of.data[_kit_addr(team, kit)] & 0xFF


def set_model(of, team: int, kit: int, model: int):
    of.data[_kit_addr(team, kit)] = model & 0xFF


# ── colour WORD encode / decode ───────────────────────────────────────────────
# Format: 0x8000 | (B5 << 10) | (G5 << 5) | R5   (5 bits per channel, 0-31)

def word_to_rgb(word: int) -> tuple:
    """Decode a PES6 15-bit colour WORD to (r, g, b) in 0-255 range."""
    r5 = (word)       & 0x1F
    g5 = (word >> 5)  & 0x1F
    b5 = (word >> 10) & 0x1F
    return (round(r5 * 255 / 31), round(g5 * 255 / 31), round(b5 * 255 / 31))


def rgb_to_word(r: int, g: int, b: int) -> int:
    """Encode (r, g, b) 0-255 to a PES6 15-bit colour WORD."""
    return 0x8000 | (round(b * 31 / 255) << 10) | (round(g * 31 / 255) << 5) | round(r * 31 / 255)


def get_color_word(of, team: int, kit: int, offset: int) -> int:
    """Read the 16-bit LE colour WORD at kitinfo_offset from the KITINFO start."""
    a = _kitinfo_base(team, kit) + offset
    return of.data[a] | (of.data[a + 1] << 8)


def set_color_word(of, team: int, kit: int, offset: int, word: int):
    a = _kitinfo_base(team, kit) + offset
    of.data[a]     = word & 0xFF
    of.data[a + 1] = (word >> 8) & 0xFF


def get_color_rgb(of, team: int, kit: int, offset: int) -> tuple:
    """Return (r, g, b) 0-255 for the colour WORD at kitinfo_offset."""
    return word_to_rgb(get_color_word(of, team, kit, offset))


def set_color_rgb(of, team: int, kit: int, offset: int, r: int, g: int, b: int):
    set_color_word(of, team, kit, offset, rgb_to_word(r, g, b))


# ── kit colour bytes ──────────────────────────────────────────────────────────

def get_kit_bytes(of, team: int, kit: int) -> bytes:
    """Return the full KIT_SIZE (62) bytes for the given kit."""
    a = _kit_addr(team, kit)
    return bytes(of.data[a: a + KIT_SIZE])


def set_kit_bytes(of, team: int, kit: int, data: bytes):
    a = _kit_addr(team, kit)
    of.data[a: a + KIT_SIZE] = data[:KIT_SIZE]


# ── logo entries ──────────────────────────────────────────────────────────────

def logo_used(of, team: int, logo: int) -> bool:
    return of.data[_logo_addr(team, logo) + 2] == 1


def get_logo_slot(of, team: int, logo: int) -> int:
    return of.data[_logo_addr(team, logo) + 3] & 0xFF


def set_logo(of, team: int, logo: int, slot: int):
    a = _logo_addr(team, logo)
    of.data[a + 2] = 1
    of.data[a + 3] = slot & 0xFF


def clear_logo(of, team: int, logo: int):
    a = _logo_addr(team, logo)
    of.data[a + 2] = 0
    of.data[a + 3] = 88   # Java: setLogoUnused writes 88 at +3


# ── copy entire kit block between teams/files ─────────────────────────────────

def import_kit_block(of1, team1: int, of2, team2: int):
    """
    Copy the complete kit block for team2 in of2 into team1's slot in of1.
    Both teams must be the same type (both clubs or both nationals).
    """
    size = SIZE_C if team1 < TOTAL_C else SIZE_N
    a1 = _base(team1)
    a2 = _base(team2)
    of1.data[a1: a1 + size] = of2.data[a2: a2 + size]


# ── pattern bytes (collar type + design layers) ───────────────────────────────
# Offsets are relative to _kitinfo_base(team, kit), same as colour offsets.
# offset 42 = collar/base type (0-2)
# offset 43 = cuello design, 44 = mangas, 45 = frente, 46 = espalda

def get_pattern_byte(of, team: int, kit: int, offset: int) -> int:
    return of.data[_kitinfo_base(team, kit) + offset] & 0xFF


def set_pattern_byte(of, team: int, kit: int, offset: int, value: int):
    of.data[_kitinfo_base(team, kit) + offset] = value & 0xFF


# ── WE → PES model conversion ─────────────────────────────────────────────────

def convert_models(of, team: int):
    """Remap WE-specific model bytes to PES equivalents (Convert.kitModel)."""
    for k in range(KITS_PER_TEAM):
        m = get_model(of, team, k)
        if m in _MODEL_MAP:
            set_model(of, team, k, _MODEL_MAP[m])
