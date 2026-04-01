"""
PES Editor 6 - Python Port
CSV export.
"""
import csv
import stats as Stats
from player import Player, TOTAL, TOTAL_EDIT, FIRST_EDIT


HEADERS = ["ID", "Name", "ShirtName", "Nationality", "Age", "Height", "Weight",
           "Foot", "Fav side", "W Foot Acc", "W Foot Freq", "Injury T",
           "Consistency", "Condition",
           "Attack", "Defense", "Balance", "Stamina", "Speed", "Accel",
           "Response", "Agility", "Drib Acc", "Drib Spe", "S Pass Acc",
           "S Pass Spe", "L Pass Acc", "L Pass Spe", "Shot Acc", "Shot Power",
           "Shot Tech", "FK Acc", "Swerve", "Heading", "Jump", "Tech",
           "Aggression", "Mentality", "GK", "Team Work",
           "Dribbling", "Tactical Drib", "Positioning", "Reaction",
           "Playmaking", "Passing", "Scoring", "1-1 Scoring", "Post",
           "Line Position", "Mid shooting", "Side", "Centre", "Penalties",
           "1-T Pass", "Outside", "Marking", "Sliding", "Cover", "D-L Control",
           "Penalty GK", "1-on-1 GK", "Long Throw",
           "GK flag", "CWP", "CBT", "SB", "DM", "WB", "CM", "SM",
           "AM", "WG", "SS", "CF"]

EXTRA_HEADERS = ["Reg Pos", "Face", "Hair", "Skin", "Face Type"]


def make_file(of, path: str, include_headers: bool = True,
              include_extra: bool = False, include_new: bool = False,
              progress_callback=None) -> bool:
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            hdrs = HEADERS[:]
            if include_extra:
                hdrs.extend(EXTRA_HEADERS)
            if include_headers:
                writer.writerow(hdrs)

            total = TOTAL + TOTAL_EDIT if include_new else TOTAL
            for idx in range(total):
                if progress_callback:
                    progress_callback(idx, total)
                player_idx = idx if idx < TOTAL else FIRST_EDIT + (idx - TOTAL)
                p = Player(of, player_idx, 0)
                if p.name.startswith("<"):
                    continue
                row = _make_row(of, player_idx, p, include_extra)
                writer.writerow(row)
        return True
    except Exception as e:
        print(f"CSV export error: {e}")
        return False


def _make_row(of, player_idx: int, player: Player, extra: bool) -> list:
    row = [
        player_idx,
        player.name,
        player.get_shirt_name(),
        Stats.get_string(of, player_idx, Stats.nationality),
        Stats.get_string(of, player_idx, Stats.age),
        Stats.get_string(of, player_idx, Stats.height),
        Stats.get_string(of, player_idx, Stats.weight),
        Stats.get_string(of, player_idx, Stats.foot),
        Stats.get_string(of, player_idx, Stats.fav_side),
        Stats.get_string(of, player_idx, Stats.wfa),
        Stats.get_string(of, player_idx, Stats.wff),
        Stats.get_string(of, player_idx, Stats.injury),
        Stats.get_string(of, player_idx, Stats.consistency),
        Stats.get_string(of, player_idx, Stats.condition),
    ]
    for s in Stats.ability99:
        row.append(Stats.get_value(of, player_idx, s))
    for s in Stats.ability_special:
        row.append(Stats.get_value(of, player_idx, s))
    for s in Stats.roles[1:]:
        row.append(Stats.get_value(of, player_idx, s))
    if extra:
        row.append(Stats.get_value(of, player_idx, Stats.reg_pos))
        row.append(Stats.get_value(of, player_idx, Stats.face))
        row.append(Stats.get_value(of, player_idx, Stats.hair))
        row.append(Stats.get_value(of, player_idx, Stats.skin))
        row.append(Stats.get_value(of, player_idx, Stats.face_type))
    return row
