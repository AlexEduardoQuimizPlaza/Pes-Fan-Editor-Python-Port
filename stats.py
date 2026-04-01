"""
PES Editor 6 - Python Port
Stats: all stat definitions and get/set helpers.
"""
import os
from stat_def import Stat  # noqa: F401 - re-exported for convenience

# -- Physical / identity stats --
hair       = Stat(0, 45, 0,  0x7FF, "")
face_type  = Stat(0, 55, 0,  0x3,   "")
skin       = Stat(0, 41, 6,  0x3,   "")
face       = Stat(0, 53, 5,  0x1FF, "")
name_edited    = Stat(0, 3,  0, 0x1,    "")
call_edited    = Stat(0, 3,  2, 0x1,    "")
shirt_edited   = Stat(0, 3,  1, 0x1,    "")
ability_edited = Stat(0, 40, 4, 0x1,    "")
call_name  = Stat(0, 1,  0, 0xFFFF, "")

height     = Stat(1, 41, 0, 0x3F,   "Height")
foot       = Stat(4, 5,  0, 0x01,   "Foot")
fav_side   = Stat(0, 33, 14, 0x03,  "Fav side")
wfa        = Stat(5, 33, 11, 0x07,  "W Foot Acc")
wff        = Stat(5, 33,  3, 0x07,  "W Foot Freq")
injury     = Stat(6, 33,  6, 0x03,  "Injury T")
drib_sty   = Stat(5,  6,  0, 0x03,  "")
freekick   = Stat(5,  5,  1, 0x0F,  "")
pk_style   = Stat(5,  5,  5, 0x07,  "")
dk_sty     = Stat(5,  6,  2, 0x03,  "")
age        = Stat(2, 65,  9, 0x1F,  "Age")
weight     = Stat(0, 41,  8, 0x7F,  "Weight")
nationality = Stat(3, 65, 0, 0x7F,  "Nationality")
consistency = Stat(5, 33, 0, 0x07,  "Consistency")
condition   = Stat(5, 33, 8, 0x07,  "Condition")
reg_pos    = Stat(0,  6,  4, 0xF,   "")

# -- Position flags --
gk  = Stat(0,  7,  7, 1, "GK")
cwp = Stat(0,  7, 15, 1, "CWP")
cbt = Stat(0,  9,  7, 1, "CBT")
sb  = Stat(0,  9, 15, 1, "SB")
dm  = Stat(0, 11,  7, 1, "DM")
wb  = Stat(0, 11, 15, 1, "WB")
cm  = Stat(0, 13,  7, 1, "CM")
sm  = Stat(0, 13, 15, 1, "SM")
am  = Stat(0, 15,  7, 1, "AM")
wg  = Stat(0, 15, 15, 1, "WG")
ss  = Stat(0, 17,  7, 1, "SS")
cf  = Stat(0, 17, 15, 1, "CF")
roles = [gk, Stat(0, 7, 15, 1, "?"), cwp, cbt, sb, dm, wb, cm, sm, am, wg, ss, cf]

# -- Ability 99 stats --
attack   = Stat(0,  7, 0, 0x7F, "Attack")
defence  = Stat(0,  8, 0, 0x7F, "Defense")
balance  = Stat(0,  9, 0, 0x7F, "Balance")
stamina  = Stat(0, 10, 0, 0x7F, "Stamina")
speed    = Stat(0, 11, 0, 0x7F, "Speed")
accel    = Stat(0, 12, 0, 0x7F, "Accel")
response = Stat(0, 13, 0, 0x7F, "Response")
agility  = Stat(0, 14, 0, 0x7F, "Agility")
drib_acc = Stat(0, 15, 0, 0x7F, "Drib Acc")
drib_spe = Stat(0, 16, 0, 0x7F, "Drib Spe")
s_pass_acc = Stat(0, 17, 0, 0x7F, "S Pass Acc")
s_pass_spe = Stat(0, 18, 0, 0x7F, "S Pass Spe")
l_pass_acc = Stat(0, 19, 0, 0x7F, "L Pass Acc")
l_pass_spe = Stat(0, 20, 0, 0x7F, "L Pass Spe")
shot_acc   = Stat(0, 21, 0, 0x7F, "Shot Acc")
shot_pow   = Stat(0, 22, 0, 0x7F, "Shot Power")
shot_tec   = Stat(0, 23, 0, 0x7F, "Shot Tech")
fk         = Stat(0, 24, 0, 0x7F, "FK Acc")
curling    = Stat(0, 25, 0, 0x7F, "Swerve")
heading    = Stat(0, 26, 0, 0x7F, "Heading")
jump       = Stat(0, 27, 0, 0x7F, "Jump")
tech       = Stat(0, 29, 0, 0x7F, "Tech")
aggress    = Stat(0, 30, 0, 0x7F, "Aggression")
mental     = Stat(0, 31, 0, 0x7F, "Mentality")
gk_abil    = Stat(0, 32, 0, 0x7F, "GK")
team       = Stat(0, 28, 0, 0x7F, "Team Work")

ability99 = [
    attack, defence, balance, stamina, speed, accel, response, agility,
    drib_acc, drib_spe, s_pass_acc, s_pass_spe, l_pass_acc, l_pass_spe,
    shot_acc, shot_pow, shot_tec, fk, curling, heading, jump,
    tech, aggress, mental, gk_abil, team,
]

ability_special = [
    Stat(0, 21,  7, 1, "Dribbling"),
    Stat(0, 21, 15, 1, "Tactical Drib"),
    Stat(0, 23,  7, 1, "Positioning"),
    Stat(0, 23, 15, 1, "Reaction"),
    Stat(0, 25,  7, 1, "Playmaking"),
    Stat(0, 25, 15, 1, "Passing"),
    Stat(0, 27,  7, 1, "Scoring"),
    Stat(0, 27, 15, 1, "1-1 Scoring"),
    Stat(0, 29,  7, 1, "Post"),
    Stat(0, 29, 15, 1, "Line Position"),
    Stat(0, 31,  7, 1, "Mid shooting"),
    Stat(0, 31, 15, 1, "Side"),
    Stat(0, 19, 15, 1, "Centre"),
    Stat(0, 19,  7, 1, "Penalties"),
    Stat(0, 35,  0, 1, "1-T Pass"),
    Stat(0, 35,  1, 1, "Outside"),
    Stat(0, 35,  2, 1, "Marking"),
    Stat(0, 35,  3, 1, "Sliding"),
    Stat(0, 35,  4, 1, "Cover"),
    Stat(0, 35,  5, 1, "D-L Control"),
    Stat(0, 35,  6, 1, "Penalty GK"),
    Stat(0, 35,  7, 1, "1-on-1 GK"),
    Stat(0, 37,  7, 1, "Long Throw"),
]

# -- String lookup arrays --
mod_foot   = ["R", "L"]
mod_injury = ["C", "B", "A"]
mod_fk     = ["A", "B", "C", "D", "E", "F", "G", "H"]
mod_18     = ["1", "2", "3", "4", "5", "6", "7", "8"]

DEFAULT_NATION = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Czech Republic", "Denmark",
    "England", "Finland", "France", "Germany", "Greece", "Hungary", "Ireland",
    "Italy", "Latvia", "Netherlands", "Northern Ireland", "Norway", "Poland",
    "Portugal", "Romania", "Russia", "Scotland", "Serbia and Montenegro",
    "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland", "Turkey",
    "Ukraine", "Wales", "Angola", "Cameroon", "Cote d'Ivoire", "Ghana",
    "Nigeria", "South Africa", "Togo", "Tunisia", "Costa Rica", "Mexico",
    "Trinidad and Tobago", "United States", "Argentina", "Brazil", "Chile",
    "Colombia", "Ecuador", "Paraguay", "Peru", "Uruguay", "Iran", "Japan",
    "Saudi Arabia", "South Korea", "Australia", "Bosnia and Herzegovina",
    "Estonia", "Israel", "Honduras", "Jamaica", "Panama", "Bolivia",
    "Venezuela", "China", "Uzbekistan", "Albania", "Cyprus", "Iceland",
    "Macedonia", "Armenia", "Belarus", "Georgia", "Liechtenstein", "Lithuania",
    "Algeria", "Benin", "Burkina Faso", "Cape Verde", "Congo", "DR Congo",
    "Egypt", "Equatorial Guinea", "Gabon", "Gambia", "Guinea", "Guinea-Bissau",
    "Kenya", "Liberia", "Libya", "Mali", "Morocco", "Mozambique", "Senegal",
    "Sierra Leone", "Zambia", "Zimbabwe", "Canada", "Grenada", "Guadeloupe",
    "Martinique", "Netherlands Antilles", "Oman", "New Zealand",
    "Free Nationality",
]


def _load_nations():
    try:
        with open("nationality.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        if lines:
            return lines
    except Exception:
        pass
    return DEFAULT_NATION


NATION = _load_nations()
NATION_FREE = next((i for i, n in enumerate(NATION) if n.lower().startswith("free ")), 0)


# ------------------------------------------------------------------
# get / set value
# ------------------------------------------------------------------

def _player_stat_address(player_idx: int, stat: Stat) -> int:
    from player import START_ADR, START_ADR_E, FIRST_EDIT
    if player_idx >= FIRST_EDIT:
        base = START_ADR_E + 48 + (player_idx - FIRST_EDIT) * 124
    else:
        base = START_ADR + 48 + player_idx * 124
    return base + stat.offset


def get_value(of, player_idx: int, stat: Stat) -> int:
    a = _player_stat_address(player_idx, stat)
    val = (of.data[a] << 8) | of.data[a - 1]
    val = (val >> stat.shift) & stat.mask
    return val


def set_value(of, player_idx: int, stat: Stat, v: int):
    a = _player_stat_address(player_idx, stat)
    old = (of.data[a] << 8) | of.data[a - 1]
    old_mask = 0xFFFF & (~(stat.mask << stat.shift))
    old = old & old_mask
    v = (v & stat.mask) << stat.shift
    v = old | v
    of.data[a - 1] = v & 0xFF
    of.data[a]     = (v >> 8) & 0xFF


def set_value_str(of, player_idx: int, stat: Stat, s: str):
    try:
        if stat.type == 0:
            v = int(s)
        elif stat.type == 1:
            v = int(s) - 148
        elif stat.type == 2:
            v = int(s) - 15
        elif stat.type == 3:
            v = NATION_FREE
            for i, n in enumerate(NATION):
                if s == n:
                    v = i
                    break
        elif stat.type == 4:
            v = mod_foot.index(s) if s in mod_foot else 0
        elif stat.type == 5:
            v = int(s) - 1
        elif stat.type == 6:
            v = mod_injury.index(s) if s in mod_injury else 0
        elif stat.type == 7:
            v = mod_fk.index(s) if s in mod_fk else 0
        else:
            v = int(s)
        set_value(of, player_idx, stat, v)
    except (ValueError, TypeError):
        pass


def get_string(of, player_idx: int, stat: Stat) -> str:
    val = get_value(of, player_idx, stat)
    if stat.type == 0:
        return str(val)
    elif stat.type == 1:
        return str(val + 148)
    elif stat.type == 2:
        return str(val + 15)
    elif stat.type == 3:
        return NATION[val] if val < len(NATION) else str(val)
    elif stat.type == 4:
        return mod_foot[val] if val < len(mod_foot) else str(val)
    elif stat.type == 5:
        return str(val + 1)
    elif stat.type == 6:
        return mod_injury[val] if val < len(mod_injury) else str(val)
    elif stat.type == 7:
        return mod_fk[val] if val < len(mod_fk) else str(val)
    return str(val)
