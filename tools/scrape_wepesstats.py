"""
One-shot scraper for https://wepesstats.rf.gd — extracts the full PES6 player
database (≈ 4800 players × 150 pages) and aggregates two reference datasets
that the editor uses to generate realistic squads when importing from
Transfermarkt:

    data/team_ratings.json     — overall-rating profile per club
    data/position_stats.json   — average stat block per (overall band, position)

The site protects itself with a JavaScript AES challenge from InfinityFree
(slowAES.decrypt). We solve that handshake once with `cryptography`, store the
resulting __test cookie, and reuse it for every page.

Usage:
    python tools/scrape_wepesstats.py              # full run, resumable
    python tools/scrape_wepesstats.py --aggregate  # skip download, just rebuild JSONs
"""
import argparse
import collections
import gzip
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT       = Path(__file__).resolve().parent.parent
CACHE_DIR  = ROOT / ".cache" / "wepesstats"
DATA_DIR   = ROOT / "data"
PAGES      = 150
BASE       = "https://wepesstats.rf.gd/pes6.php"
UA         = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# AES challenge constants pulled from the site's interstitial JS.
# These look stable per-IP/session window; if the script ever starts returning
# the JS-redirect page again, re-extract them from a fresh interstitial.
_AES_KEY = bytes.fromhex("f655ba9d09a112d4968c63579db590b4")
_AES_IV  = bytes.fromhex("98344c2eee86c3994890592585b49f80")
_AES_CT  = bytes.fromhex("af1bfeff9fe9c56bbfdaa9d4c93cef8e")


def _solve_cookie() -> str:
    dec = Cipher(algorithms.AES(_AES_KEY), modes.CBC(_AES_IV),
                 backend=default_backend()).decryptor()
    return (dec.update(_AES_CT) + dec.finalize()).hex()


def _fetch(page: int, cookie: str, retries: int = 3) -> bytes:
    url = f"{BASE}?page={page}&i=1"
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Cookie": f"__test={cookie}",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return data
        except (urllib.error.URLError, TimeoutError) as e:
            wait = 2 ** attempt
            print(f"  retry {attempt + 1}/{retries} after {wait}s ({e})",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"failed to fetch page {page}")


def download_all(force: bool = False) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cookie = _solve_cookie()
    print(f"cookie = {cookie}")
    print(f"caching {PAGES} pages into {CACHE_DIR}/ ...")
    for p in range(1, PAGES + 1):
        out = CACHE_DIR / f"p{p:03d}.html"
        if out.exists() and not force and out.stat().st_size > 1024:
            continue
        data = _fetch(p, cookie)
        out.write_bytes(data)
        print(f"  page {p:3d}: {len(data):>7d} bytes")
        time.sleep(0.6)  # be polite to a free host


# ── parsing ──────────────────────────────────────────────────────────────────

def _read_pages():
    rows = []
    cols = None
    for p in range(1, PAGES + 1):
        fp = CACHE_DIR / f"p{p:03d}.html"
        if not fp.exists():
            print(f"missing page {p} — run without --aggregate first")
            sys.exit(2)
        soup = BeautifulSoup(fp.read_bytes(), "html.parser",
                             from_encoding="latin-1")
        tables = soup.find_all("table")
        # results table is the one with > 5 rows and an Overall Rating header
        result_tbl = next(
            (t for t in tables
             if any("Overall" in c.get_text()
                    for c in (t.find("tr") or []).find_all(["th", "td"]))),
            None
        )
        if result_tbl is None:
            continue
        trs = result_tbl.find_all("tr")
        if cols is None:
            cols = [c.get_text(" ", strip=True)
                       .replace(" ⇩", "").replace(" ⇧", "")
                    for c in trs[0].find_all(["th", "td"])]
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
            if len(cells) >= len(cols):
                rows.append(dict(zip(cols, cells)))
    return rows


_INT_FIELDS = (
    "Overall Rating", "Attack", "Defense", "Balance", "Stamina", "Top speed",
    "Acceleration", "Response", "Agility", "Dribble accuracy", "Dribble speed",
    "Short pass accuracy", "Short pass speed", "Long pass accuracy",
    "Long pass speed", "Shot accuracy", "Shot power", "Shot technique",
    "Free kick accuracy", "Swerve", "Heading", "Jump", "Technique", "Mentality",
    "Goal keeping skills", "Teamwork", "Aggression",
)


def _coerce(rows):
    out = []
    for r in rows:
        try:
            o = int(r["Overall Rating"])
        except (KeyError, ValueError):
            continue
        rec = {"name": r["Name"], "team": r["Team"], "pos": r["Position"],
               "overall": o}
        for k in _INT_FIELDS:
            try:
                rec[k] = int(r[k])
            except (KeyError, ValueError):
                pass
        out.append(rec)
    return out


def _build_team_ratings(players):
    by_team = collections.defaultdict(list)
    for p in players:
        if p["team"]:
            by_team[p["team"]].append(p["overall"])

    teams = {}
    for name, ovrs in by_team.items():
        if name == "Without Team":
            continue
        ovrs_sorted = sorted(ovrs, reverse=True)
        top = ovrs_sorted[:16]
        teams[name] = {
            "avg_top16": round(statistics.mean(top), 1) if top else 0,
            "avg_all":   round(statistics.mean(ovrs_sorted), 1),
            "max":       max(ovrs_sorted),
            "n_players": len(ovrs_sorted),
        }
    return teams


# Maps wepesstats positions to PES editor position codes used by the panel.
_POS_NORMALIZE = {"GK": "GK", "CBT": "CBT", "SB": "SB", "WB": "WB",
                  "DMF": "DMF", "CMF": "CMF", "SMF": "SMF", "AMF": "AMF",
                  "WF": "WF", "SS": "SS", "CF": "CF", "CWP": "CBT"}


def _build_position_stats(players):
    """For each (overall band, position) compute the mean of every stat — gives
    us realistic stat blocks to use when generating players for a target team."""
    bands = [60, 65, 70, 75, 80, 85, 90]
    width = 4

    def _band(o):
        for b in bands:
            if b - width // 2 <= o <= b + width // 2 - 1:
                return b
        return None

    bucket = collections.defaultdict(list)
    for p in players:
        pos = _POS_NORMALIZE.get(p["pos"])
        if pos is None:
            continue
        b = _band(p["overall"])
        if b is None:
            continue
        bucket[(b, pos)].append(p)

    out = collections.defaultdict(dict)
    for (b, pos), ps in bucket.items():
        if len(ps) < 3:
            continue
        agg = {}
        for k in _INT_FIELDS:
            vals = [p[k] for p in ps if k in p]
            if vals:
                agg[k] = round(statistics.mean(vals))
        agg["_sample"] = len(ps)
        out[str(b)][pos] = agg
    return out


def aggregate() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("parsing cached pages...")
    rows = _read_pages()
    players = _coerce(rows)
    print(f"  {len(players)} players parsed")

    teams = _build_team_ratings(players)
    (DATA_DIR / "team_ratings.json").write_text(
        json.dumps({"source": "wepesstats.rf.gd", "teams": teams},
                   ensure_ascii=False, indent=2))
    print(f"  wrote team_ratings.json ({len(teams)} teams)")

    pos_stats = _build_position_stats(players)
    (DATA_DIR / "position_stats.json").write_text(
        json.dumps({"source": "wepesstats.rf.gd",
                    "bands": sorted(int(b) for b in pos_stats),
                    "by_band": pos_stats},
                   ensure_ascii=False, indent=2))
    print(f"  wrote position_stats.json "
          f"({sum(len(v) for v in pos_stats.values())} band×pos cells)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregate", action="store_true",
                    help="skip download, only rebuild JSONs from cache")
    ap.add_argument("--force", action="store_true",
                    help="redownload pages even if cached")
    args = ap.parse_args()

    if not args.aggregate:
        download_all(force=args.force)
    aggregate()


if __name__ == "__main__":
    main()
