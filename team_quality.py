"""
Team quality lookup, backed by data/team_ratings.json and
data/position_stats.json (both produced by tools/scrape_wepesstats.py).

Two services:

    suggest_overall(club_name)          → int | None
        Fuzzy-matches a club name (Transfermarkt-style) against the PES6 club
        ratings and returns the suggested team overall, or None if no good
        match exists.

    stat_block(target_overall, pos)     → list[int] of length 26
        Returns the realistic stat block (Attack, Defense, Balance, ... in the
        same order as Stats.ability99) for a player of the given position at
        the given team-overall target. Linearly interpolates between the
        nearest available bands; falls back to a baked-in CMF fallback when
        a band/position cell is missing.
"""
import difflib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"

# wepesstats column name → index in Stats.ability99
# (Stats.ability99 order is: Atk Def Bal Stm Spd Acc Res Agi DrA DrS SPA SPS
#  LPA LPS ShA ShP ShT FK Cur Hea Jmp Tec Agg Men GK TW)
_STAT_ORDER = [
    "Attack", "Defense", "Balance", "Stamina", "Top speed", "Acceleration",
    "Response", "Agility", "Dribble accuracy", "Dribble speed",
    "Short pass accuracy", "Short pass speed", "Long pass accuracy",
    "Long pass speed", "Shot accuracy", "Shot power", "Shot technique",
    "Free kick accuracy", "Swerve", "Heading", "Jump", "Technique",
    "Aggression", "Mentality", "Goal keeping skills", "Teamwork",
]

# Conservative CMF baseline used when a band/position cell is missing in the
# scraped data (very low or very high overalls have small samples per pos).
_FALLBACK_CMF = [
    68, 65, 72, 78, 68, 68, 72, 70, 68, 66, 75, 72, 70, 68, 60, 62, 60, 60,
    55, 60, 65, 72, 62, 72, 15, 78,
]


# Single-letter / dotted-prefix expansions seen in the wepesstats DB.
# Apply only as standalone tokens — not inside words.
_EXPAND = {
    "r":   "real",
    "rc":  "real club",
    "rcd": "real club deportivo",
    "ca":  "club atletico",
    "ac":  "ac",
    "as":  "as",
    "fc":  "fc",
    "cf":  "cf",
    "sc":  "sc",
    "ud":  "union deportiva",
}
# Tokens that don't carry team identity — drop them from the bag of words used
# for matching (but keep them in the canonical string used for difflib).
_NOISE = {"fc", "cf", "ac", "as", "sc", "cd", "cp", "club", "de", "del", "la",
          "le", "el", "il", "the"}


def _canon(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = []
    for t in s.split():
        toks.append(_EXPAND.get(t, t))
    return " ".join(toks).strip()


def _tokens(s: str) -> set:
    return {t for t in _canon(s).split() if t not in _NOISE and len(t) > 1}


@lru_cache(maxsize=1)
def _load_team_ratings() -> dict:
    fp = _DATA_DIR / "team_ratings.json"
    if not fp.exists():
        return {}
    with open(fp, encoding="utf-8") as f:
        return json.load(f).get("teams", {})


@lru_cache(maxsize=1)
def _load_position_stats() -> dict:
    fp = _DATA_DIR / "position_stats.json"
    if not fp.exists():
        return {}
    with open(fp, encoding="utf-8") as f:
        raw = json.load(f).get("by_band", {})
    return {int(b): v for b, v in raw.items()}


@lru_cache(maxsize=1)
def _team_index():
    """Pre-compute (canonical, tokens) for every team in the DB."""
    out = []
    for name in _load_team_ratings():
        out.append((name, _canon(name), _tokens(name)))
    return out


def suggest_overall(club_name: str):
    """Return (overall:int, matched_name:str) or (None, None).

    Score per candidate = max(jaccard_on_tokens, difflib_ratio_on_canonical).
    Threshold 0.65 — below this we report no match instead of guessing wrong.
    """
    if not club_name:
        return None, None
    teams = _load_team_ratings()
    if not teams:
        return None, None

    target_canon  = _canon(club_name)
    target_tokens = _tokens(club_name)
    if not target_canon:
        return None, None

    best = (0.0, None)
    for name, canon, toks in _team_index():
        if target_tokens and toks:
            inter = len(target_tokens & toks)
            union = len(target_tokens | toks)
            jacc = inter / union if union else 0.0
            cont = inter / min(len(target_tokens), len(toks)) if inter else 0.0
        else:
            jacc = cont = 0.0
        ratio = SequenceMatcher(None, target_canon, canon).ratio()
        # Token-based signals beat raw string ratio: "Celta Vigo" should match
        # "R.C. Celta" (token overlap) rather than "Celtic" (similar string).
        score = max(jacc, ratio * 0.7, cont * 0.85)
        if score > best[0]:
            best = (score, name)

    if best[1] and best[0] >= 0.55:
        return round(teams[best[1]]["avg_top16"]), best[1]
    return None, None


def _bands_for(target: int):
    """Return (lower, upper, weight_upper) for interpolation."""
    bands = sorted(_load_position_stats().keys())
    if not bands:
        return None, None, 0.0
    if target <= bands[0]:
        return bands[0], bands[0], 0.0
    if target >= bands[-1]:
        return bands[-1], bands[-1], 0.0
    for i in range(len(bands) - 1):
        lo, hi = bands[i], bands[i + 1]
        if lo <= target <= hi:
            w = (target - lo) / (hi - lo)
            return lo, hi, w
    return bands[-1], bands[-1], 0.0


def stat_block(target_overall: int, pos: str):
    """
    Return a 26-int list (same order as Stats.ability99) for a player at
    `pos` whose team's overall is `target_overall`. Interpolates between the
    two nearest scraped bands; below the lowest scraped band it linearly
    scales the lowest-band block down so users can model youth/regional
    teams that fall under the wepesstats range.
    """
    by_band = _load_position_stats()
    bands   = sorted(by_band.keys())
    lo, hi, w = _bands_for(target_overall)

    def _row(band):
        cell = by_band.get(band, {}).get(pos) if band is not None else None
        if not cell:
            # graceful fallback: scale CMF baseline by band/75
            scale = (band or target_overall) / 75.0
            return [max(1, min(99, round(v * scale))) for v in _FALLBACK_CMF]
        return [int(cell.get(name, _FALLBACK_CMF[i]))
                for i, name in enumerate(_STAT_ORDER)]

    # Below the lowest scraped band: scale that band's stats down linearly.
    # Above the highest scraped band: same idea, scaling up (capped at 99
    # by the per-stat clamp below).
    if bands and target_overall < bands[0]:
        scale = max(0.3, target_overall / bands[0])
        return [max(1, min(99, round(v * scale))) for v in _row(bands[0])]
    if bands and target_overall > bands[-1]:
        scale = target_overall / bands[-1]
        return [max(1, min(99, round(v * scale))) for v in _row(bands[-1])]

    a = _row(lo)
    if w == 0.0 or hi == lo:
        return [max(1, min(99, v)) for v in a]
    b = _row(hi)
    return [max(1, min(99, round(a[i] * (1 - w) + b[i] * w)))
            for i in range(len(_STAT_ORDER))]


def is_available() -> bool:
    return bool(_load_team_ratings()) and bool(_load_position_stats())
