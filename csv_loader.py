"""
PES Editor 6 - Python Port
CSV import.
"""
import csv
import stats as Stats
from player import Player, TOTAL, FIRST_EDIT
from csv_maker import HEADERS


def load_file(of, path: str,
              update_club_teams: bool = True,
              update_national_teams: bool = True,
              update_classic_teams: bool = False,
              changes: list = None,
              progress_callback=None) -> bool:
    if changes is None:
        changes = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return False

        # Detect header row
        header = rows[0]
        if header[0].strip().upper() == "ID":
            rows = rows[1:]  # skip header

        total = len(rows)
        for i, row in enumerate(rows):
            if progress_callback:
                progress_callback(i, total)
            if len(row) < 2:
                continue
            try:
                player_idx = int(row[0])
            except ValueError:
                continue
            if player_idx <= 0 or (player_idx >= TOTAL and player_idx < FIRST_EDIT) or player_idx > 32951:
                continue
            p = Player(of, player_idx, 0)
            if p.name.startswith("<ERROR>"):
                continue
            _apply_row(of, player_idx, row, changes)
        return True
    except Exception as e:
        print(f"CSV import error: {e}")
        return False


def _apply_row(of, player_idx: int, row: list, changes: list):
    col = 2  # skip ID and Name
    if len(row) > col:
        old_shirt = Player(of, player_idx, 0).get_shirt_name()
        new_shirt = row[col].strip()
        if new_shirt and new_shirt != old_shirt:
            Player(of, player_idx, 0).set_shirt_name(new_shirt)
    col += 1

    stat_list = [
        Stats.nationality, Stats.age, Stats.height, Stats.weight,
        Stats.foot, Stats.fav_side, Stats.wfa, Stats.wff,
        Stats.injury, Stats.consistency, Stats.condition,
    ]
    for s in stat_list:
        if len(row) > col:
            try:
                Stats.set_value_str(of, player_idx, s, row[col].strip())
            except Exception:
                pass
        col += 1

    for s in Stats.ability99:
        if len(row) > col:
            try:
                v = int(row[col])
                Stats.set_value(of, player_idx, s, v)
            except Exception:
                pass
        col += 1

    for s in Stats.ability_special:
        if len(row) > col:
            try:
                v = int(row[col])
                Stats.set_value(of, player_idx, s, v)
            except Exception:
                pass
        col += 1
