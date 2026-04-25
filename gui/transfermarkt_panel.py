"""
PES Editor 6 - Python Port
Transfermarkt Panel: scrape a squad + club info from Transfermarkt for any
season and apply directly to the selected club in the Option File.
No CSV intermediary — writes straight to OF binary.

Features:
  • Overflow control  : choose Titulares (11) / First 23 / All (≤32)
  • Auto club info    : club name + crest logo imported automatically
"""
import io
import random
import re
import threading
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

try:
    from PIL import Image as _PILImage
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

import clubs   as Clubs
import emblems as Emblems
import logos   as Logos
import squads  as Squads
import stats  as Stats
import team_quality
from player import Player

# ── HTTP ──────────────────────────────────────────────────────────────────────
_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}

# ── Position tables ───────────────────────────────────────────────────────────
_POS_MAP = {
    "portero": "GK", "goalkeeper": "GK",
    "defensa central": "CBT", "central": "CBT", "centre-back": "CBT",
    "lateral derecho": "SB", "lateral izquierdo": "SB",
    "right-back": "SB", "left-back": "SB",
    "carrilero": "WB", "wing-back": "WB",
    "mediocentro defensivo": "DMF", "defensive midfielder": "DMF", "pivote": "DMF",
    "mediocentro ofensivo": "AMF", "mediapunta": "AMF", "attacking midfielder": "AMF",
    "mediocentro": "CMF", "centrocampista": "CMF", "central midfielder": "CMF",
    "interior": "CMF",
    "right midfielder": "SMF", "left midfielder": "SMF",
    "extremo derecho": "WF", "extremo izquierdo": "WF", "winger": "WF",
    "segundo delantero": "SS", "second striker": "SS",
    "delantero centro": "CF", "delantero": "CF",
    "striker": "CF", "centre-forward": "CF", "forward": "CF",
}

# Baseline used as a last-resort fallback when team_quality data is unavailable
# (e.g. data/position_stats.json missing) and the user kept the default target.
# In normal operation team_quality.stat_block(target_overall, pos) replaces this.
#          Atk Def Bal Stm Spd Acc Res Agi DrA DrS SPA SPS LPA LPS ShA ShP ShT FK  Cur Hea Jmp Tec Agg Men GK  TW
_FALLBACK_STATS = {
    "GK":  [30, 55, 60, 65, 55, 55, 82, 55, 40, 40, 50, 50, 50, 50, 25, 30, 25, 30, 25, 45, 80, 40, 45, 60, 88, 65],
    "CBT": [45, 82, 75, 80, 65, 60, 70, 60, 45, 45, 60, 58, 62, 58, 35, 52, 35, 35, 30, 80, 82, 50, 78, 72, 15, 72],
    "SB":  [62, 75, 70, 78, 76, 74, 68, 74, 62, 62, 68, 65, 62, 62, 48, 52, 48, 45, 42, 58, 68, 62, 65, 66, 15, 72],
    "WB":  [65, 72, 68, 78, 78, 78, 68, 78, 66, 66, 68, 66, 62, 62, 52, 54, 52, 45, 45, 55, 68, 65, 62, 65, 15, 72],
    "DMF": [52, 80, 72, 82, 66, 65, 74, 66, 60, 58, 72, 68, 70, 66, 45, 52, 45, 50, 42, 62, 68, 65, 74, 76, 15, 78],
    "CMF": [68, 65, 72, 78, 68, 68, 72, 70, 68, 66, 75, 72, 70, 68, 60, 62, 60, 60, 55, 60, 65, 72, 62, 72, 15, 78],
    "SMF": [66, 58, 68, 76, 74, 74, 70, 74, 68, 68, 70, 68, 66, 66, 62, 64, 62, 58, 58, 55, 65, 70, 58, 66, 15, 72],
    "AMF": [74, 50, 68, 72, 68, 70, 72, 74, 74, 70, 76, 72, 68, 68, 68, 62, 68, 65, 62, 52, 60, 76, 55, 70, 15, 70],
    "WF":  [70, 48, 68, 72, 82, 82, 70, 80, 78, 76, 68, 66, 62, 62, 66, 62, 66, 58, 60, 52, 65, 74, 55, 65, 15, 68],
    "SS":  [78, 45, 68, 72, 74, 74, 70, 74, 74, 70, 66, 65, 60, 60, 76, 72, 74, 60, 60, 65, 68, 72, 62, 70, 15, 68],
    "CF":  [80, 38, 66, 70, 70, 70, 70, 68, 70, 66, 60, 60, 56, 56, 82, 80, 80, 64, 62, 74, 74, 70, 65, 68, 15, 65],
}


def _resolve_stats(target_overall: int, pos: str):
    """Real stat block scaled to (or interpolated for) target_overall+pos.
    Uses team_quality data when present; falls back to _FALLBACK_STATS scaled
    by target_overall/75 otherwise."""
    if team_quality.is_available():
        return team_quality.stat_block(target_overall, pos)
    base  = _FALLBACK_STATS.get(pos, _FALLBACK_STATS["CMF"])
    scale = target_overall / 75.0
    return [max(1, min(99, round(v * scale))) for v in base]


def _distribute_overall(team_overall: int, rank: int, total: int) -> int:
    """Spread `team_overall` across the squad so starters > bench > reserves.

    Calibrated against the wepesstats scrape: top-11 averages ≈ team avg + 6,
    bench (12-23) ≈ team avg − 2, reserves (24-32) ≈ team avg − 9. Modeled as
    a linear gradient from +13 (best) to −13 (worst), which matches the
    real max/min spread in the data within ~2 points.
    """
    if total <= 1:
        return team_overall
    p = rank / (total - 1)            # 0 = best, 1 = worst
    offset = 13 * (1 - 2 * p)
    return max(20, min(99, round(team_overall + offset)))

#        Drb TDr Pos Rea Ply Pas Scr 1o1 Pst Lin MdS Sid Cen Pen 1T  Out Mrk Sld Cov  DL  PGK 1GK LTh
_DEF_SPEC = {
    "GK":  [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  1,  1,  0],
    "CBT": [0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  1,  0,  0,  0,  1,  1,  1,  1,  0,  0,  0],
    "SB":  [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  1,  1,  1,  0,  0,  0,  0],
    "WB":  [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  1,  1,  1,  0,  0,  0,  0],
    "DMF": [0,  0,  0,  0,  0,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  0,  0,  0],
    "CMF": [0,  1,  1,  0,  1,  1,  0,  0,  0,  1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0],
    "SMF": [1,  0,  0,  0,  1,  1,  0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    "AMF": [1,  1,  1,  0,  1,  1,  1,  0,  0,  0,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0],
    "WF":  [1,  1,  0,  0,  0,  0,  1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    "SS":  [1,  0,  1,  0,  0,  0,  1,  1,  1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    "CF":  [0,  0,  1,  0,  0,  0,  1,  1,  1,  1,  0,  0,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0],
}

_HEIGHT_MAP  = {"GK": 188, "CBT": 184, "SB": 178, "WB": 180, "DMF": 180,
                "CMF": 178, "SMF": 175, "AMF": 175, "WF": 174, "SS": 178, "CF": 182}
_REG_POS_IDX = {"GK": 0, "CWP": 1, "CBT": 2, "SB": 3, "DMF": 4, "WB": 5,
                "CMF": 6, "SMF": 7, "AMF": 8, "WF": 9, "SS": 10, "CF": 11}
_POS_FLAGS   = {"GK": [Stats.gk], "CWP": [Stats.cwp], "CBT": [Stats.cbt],
                "SB": [Stats.sb], "DMF": [Stats.dm],  "WB": [Stats.wb],
                "CMF": [Stats.cm], "SMF": [Stats.sm], "AMF": [Stats.am],
                "WF": [Stats.wg], "SS": [Stats.ss],   "CF": [Stats.cf]}
_POS_ORDER   = {"GK": 0, "CBT": 1, "SB": 2, "WB": 3, "DMF": 4,
                "CMF": 5, "SMF": 6, "AMF": 7, "WF": 8, "SS": 9, "CF": 10}

_NAT_ALIAS = {
    "alemania": "Germany", "germany": "Germany",
    "espana": "Spain", "spain": "Spain",
    "italia": "Italy", "italy": "Italy",
    "francia": "France", "france": "France",
    "suiza": "Switzerland", "switzerland": "Switzerland",
    "brasil": "Brazil", "brazil": "Brazil",
    "suecia": "Sweden", "sweden": "Sweden",
    "republica checa": "Czech Republic", "czech republic": "Czech Republic",
    "bielorrusia": "Belarus", "belarus": "Belarus",
    "paises bajos": "Netherlands", "netherlands": "Netherlands", "holanda": "Netherlands",
    "togo": "Togo", "costa de marfil": "Cote d'Ivoire",
    "camerun": "Cameroon", "cameroon": "Cameroon",
    "argentina": "Argentina", "inglaterra": "England", "england": "England",
    "portugal": "Portugal", "nigeria": "Nigeria", "ghana": "Ghana",
    "senegal": "Senegal", "marruecos": "Morocco",
    "croacia": "Croatia", "croatia": "Croatia",
    "eslovaquia": "Slovakia", "slovakia": "Slovakia",
    "eslovenia": "Slovenia", "slovenia": "Slovenia",
    "belgica": "Belgium", "belgium": "Belgium",
    "dinamarca": "Denmark", "denmark": "Denmark",
    "noruega": "Norway", "norway": "Norway",
    "finlandia": "Finland", "finland": "Finland",
    "grecia": "Greece", "greece": "Greece",
    "turquia": "Turkey", "turkey": "Turkey",
    "rusia": "Russia", "russia": "Russia",
    "ucrania": "Ukraine", "ukraine": "Ukraine",
    "polonia": "Poland", "poland": "Poland",
    "colombia": "Colombia", "chile": "Chile", "uruguay": "Uruguay",
    "ecuador": "Ecuador", "peru": "Peru", "mexico": "Mexico",
    "estados unidos": "United States", "united states": "United States",
    "japon": "Japan", "japan": "Japan",
    "corea del sur": "South Korea", "south korea": "South Korea",
    "australia": "Australia",
    "trinidad y tobago": "Trinidad and Tobago",
    "irlanda": "Ireland", "ireland": "Ireland",
    "irlanda del norte": "Northern Ireland",
    "chipre": "Cyprus", "cyprus": "Cyprus",
    "islandia": "Iceland", "iceland": "Iceland",
    "venezuela": "Venezuela", "rumania": "Romania", "romania": "Romania",
    "serbia": "Serbia and Montenegro",
    "costa rica": "Costa Rica", "jamaica": "Jamaica",
    "austria": "Austria", "bulgaria": "Bulgaria",
    "hungria": "Hungary", "hungary": "Hungary",
    "gales": "Wales", "wales": "Wales",
    "escocia": "Scotland", "scotland": "Scotland",
    "angola": "Angola", "sudafrica": "South Africa", "south africa": "South Africa",
    "tunez": "Tunisia", "tunisia": "Tunisia",
    "iran": "Iran", "arabia saudi": "Saudi Arabia", "saudi arabia": "Saudi Arabia",
    "china": "China", "bosnia": "Bosnia and Herzegovina",
    "israel": "Israel", "estonia": "Estonia",
    "letonia": "Latvia", "latvia": "Latvia",
    "albania": "Albania", "lituania": "Lithuania", "lithuania": "Lithuania",
    "mali": "Mali", "egipto": "Egypt", "egypt": "Egypt",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_squad_url(url: str):
    """
    Accept any Transfermarkt club URL (e.g. /startseite/verein/<id>,
    /kader/verein/<id>, with or without /saison_id/<year>) and rebuild the
    canonical /kader/ squad URL while preserving the regional domain
    (.es / .com / .de / ...). Returns (kader_url, origin).
    """
    pu = urlparse(url.strip())
    if not pu.scheme or not pu.netloc:
        raise ValueError("URL inválida.")
    if "transfermarkt." not in pu.netloc:
        raise ValueError("El dominio no parece de Transfermarkt "
                         "(transfermarkt.com / .es / .de / ...).")
    m = re.search(r"/verein/(\d+)", pu.path)
    if not m:
        raise ValueError("La URL debe ser la de un club: debe contener "
                         "/verein/<id>.")
    verein = m.group(1)
    parts = [p for p in pu.path.split("/") if p]
    slug = parts[0] if parts else "club"
    new_path = f"/{slug}/kader/verein/{verein}"
    saison = re.search(r"/saison_id/(\d+)", pu.path)
    if saison:
        new_path += f"/saison_id/{saison.group(1)}"
    origin = f"{pu.scheme}://{pu.netloc}"
    return origin + new_path, origin


def _strip(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return re.sub(r"\s+", " ",
                  nfkd.encode("ascii", "ignore").decode()).strip()


def _get_pos(pos_text: str) -> str:
    low = pos_text.lower().strip()
    for key, val in _POS_MAP.items():
        if key in low:
            return val
    return "CMF"


def _nat_to_pes(raw: str) -> str:
    key = _strip(raw).lower()
    mapped = _NAT_ALIAS.get(key)
    if mapped:
        return mapped
    for n in Stats.NATION:
        if _strip(n).lower() == key:
            return n
    return _strip(raw).title()


def _sort_key(p):
    order   = _POS_ORDER.get(p["pos"], 99)
    num     = p["number"]
    starter = 0 if 1 <= num <= 11 else (1 if num > 11 else 2)
    return (starter, order, num)


# ── Scraping ──────────────────────────────────────────────────────────────────

def _scrape_page(url: str) -> dict:
    """
    Fetch one Transfermarkt squad page.
    Returns {
        'players': [...],
        'club_name': str,
        'logo_url': str | None,
    }
    """
    pu = urlparse(url)
    origin = f"{pu.scheme}://{pu.netloc}" if pu.scheme and pu.netloc else ""

    r = requests.get(url, headers=_HTTP, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # ── club name ─────────────────────────────────────────────────────
    club_name = ""
    h1 = soup.find("h1", class_=re.compile(r"data-header__headline"))
    if h1:
        club_name = _strip(h1.get_text())
    if not club_name:
        title = soup.find("title")
        if title:
            club_name = _strip(title.get_text().split("|")[0].split("-")[0])

    # ── club logo ─────────────────────────────────────────────────────
    logo_url = None
    logo_img = soup.find("img", class_=re.compile(r"data-header__profile-image"))
    if not logo_img:
        # fallback: any medium-sized crest in the header
        header = soup.find("div", class_=re.compile(r"data-header"))
        if header:
            logo_img = header.find("img")
    if logo_img:
        src = logo_img.get("src") or logo_img.get("data-src") or ""
        if src and not src.endswith("wappen_default.png"):
            logo_url = src if src.startswith("http") else origin + src

    # ── squad table ───────────────────────────────────────────────────
    table = soup.find("table", {"class": "items"})
    if not table:
        raise ValueError(
            "No se encontró la tabla de jugadores en esa página.\n"
            "Asegúrate de pasar una URL de un club Transfermarkt "
            "(con /verein/<id>)."
        )

    players = []
    rows = table.find_all("tr", class_=lambda c: c in ("odd", "even"))
    for row in rows:
        num_div = row.find("div", {"class": "rn_nummer"})
        number  = int(re.sub(r"\D", "",
                             num_div.get_text(strip=True) if num_div else "") or "0")

        inline = row.find("table", {"class": "inline-table"})
        if not inline:
            continue
        name_td = inline.find("td", {"class": "hauptlink"})
        if not name_td:
            continue

        raw_name  = name_td.get_text(strip=True)
        name      = _strip(raw_name)[:15]
        parts     = name.split()
        shirt     = _strip(parts[-1])[:8].upper() if parts else name[:8].upper()

        inline_rows = inline.find_all("tr")
        pos_text    = "centrocampista"
        if len(inline_rows) >= 2:
            pos_text = _strip(inline_rows[1].get_text()).lower()

        # Age sits in the first plain-numeric .zentriert cell to the right of
        # the name column. Anchoring on the inline-table avoids picking up the
        # shirt-number cell (also .zentriert via the rueckennummer class).
        age = 25
        name_outer_td = inline.find_parent("td")
        if name_outer_td:
            for sib in name_outer_td.find_next_siblings("td"):
                cls = sib.get("class") or []
                if "zentriert" not in cls or sib.find("img"):
                    continue
                txt = sib.get_text(strip=True)
                if re.fullmatch(r"\d{1,2}", txt):
                    age = int(txt)
                    break

        nat_raw  = "England"
        flag_img = row.find("img", {"class": "flaggenrahmen"})
        if flag_img:
            nat_raw = flag_img.get("title") or flag_img.get("alt") or "England"

        players.append({
            "number": number,
            "name":   name,
            "shirt":  shirt,
            "pos":    _get_pos(pos_text),
            "age":    age,
            "nat":    _nat_to_pes(nat_raw),
        })

    players.sort(key=_sort_key)
    return {"players": players, "club_name": club_name, "logo_url": logo_url}


def _download_logo_image(url: str, extra_headers: dict = None):
    """Download logo from URL and return (PIL Image, None) or (None, error_str)."""
    if not _PIL_OK:
        return None, "Pillow no instalado"
    try:
        hdrs = {**_HTTP, **(extra_headers or {})}
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "image" not in ct:
            return None, f"content-type inesperado: {ct!r}"
        return _PILImage.open(io.BytesIO(r.content)), None
    except Exception as e:
        return None, str(e)


def _extract_verein_id(url: str):
    """Extract the numeric verein ID from a Transfermarkt URL, e.g. /verein/131/ → '131'."""
    m = re.search(r'/verein/(\d+)', url)
    return m.group(1) if m else None


def _logo_from_wikipedia(club_name: str, log_fn=None):
    """Search Wikipedia for the club article and return its crest thumbnail as PIL Image."""
    def _log(msg, tag="warn"):
        if log_fn:
            log_fn(f"    [S3] {msg}", tag)

    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": f"{club_name} football",
                    "limit": 3, "format": "json"},
            headers=_HTTP, timeout=10)
        r.raise_for_status()
        data = r.json()
        titles = data[1] if len(data) > 1 else []
        if not titles:
            _log("opensearch no devolvió resultados")
            return None, None
        title = titles[0]
        _log(f"artículo encontrado: '{title}'", "")

        r2 = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "titles": title, "prop": "pageimages",
                    "format": "json", "pithumbsize": 500, "pilicense": "any"},
            headers=_HTTP, timeout=10)
        r2.raise_for_status()
        pages = r2.json().get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                _log(f"thumbnail: {thumb}", "")
                img, err = _download_logo_image(thumb)
                if img:
                    return img, f"Wikipedia ('{title}')"
                _log(f"descarga fallida: {err}")
            else:
                _log("la página no tiene thumbnail")
    except Exception as e:
        _log(str(e))
    return None, None


def _find_club_logo(tm_url: str, club_name: str, scraped_logo_url, log_fn=None):
    """
    Try sources in order to obtain a PIL Image for the club crest.
    Returns (PIL.Image, source_label) or (None, None) if all sources fail.

    Source 1 — Transfermarkt CDN  : direct URL built from verein ID (no scraping)
    Source 2 — TheSportsDB API    : free, no API key, JSON search by name
    Source 3 — Wikipedia API      : free, no key, pageimages for the club article
    Source 4 — TM HTML scrape URL : fallback using img src found in page HTML
    """
    def _log(msg, tag="warn"):
        if log_fn:
            log_fn(msg, tag)

    if not _PIL_OK:
        return None, None

    # Source 1: Transfermarkt CDN (try medium → head → big)
    verein_id = _extract_verein_id(tm_url)
    pu = urlparse(tm_url)
    referer = (f"{pu.scheme}://{pu.netloc}/"
               if pu.scheme and pu.netloc
               else "https://www.transfermarkt.com/")
    if verein_id:
        for size in ("medium", "head", "big"):
            cdn_url = f"https://tmssl.akamaized.net/images/wappen/{size}/{verein_id}.png"
            img, err = _download_logo_image(cdn_url, {"Referer": referer})
            if img:
                return img, f"Transfermarkt CDN ({size}, verein/{verein_id})"
            _log(f"    [S1] CDN {size} ✗ {err}")
    else:
        _log("    [S1] ✗ no se pudo extraer verein ID de la URL")

    # Source 2: TheSportsDB free API
    if club_name:
        try:
            r = requests.get(
                "https://www.thesportsdb.com/api/v1/json/3/searchteams.php",
                params={"t": club_name}, headers=_HTTP, timeout=15)
            r.raise_for_status()
            teams = (r.json() or {}).get("teams") or []
            if teams:
                t = teams[0]
                badge_url = t.get("strBadge") or t.get("strTeamBadge")
                if badge_url:
                    img, err = _download_logo_image(badge_url)
                    if img:
                        return img, f"TheSportsDB ('{t.get('strTeam', club_name)}')"
                    _log(f"    [S2] TheSportsDB badge ✗ {err}")
                else:
                    _log(f"    [S2] TheSportsDB: equipo '{t.get('strTeam')}' sin badge URL")
            else:
                _log(f"    [S2] TheSportsDB: sin resultados para '{club_name}'")
        except Exception as e:
            _log(f"    [S2] TheSportsDB ✗ {e}")

    # Source 3: Wikipedia pageimages API
    if club_name:
        img, label = _logo_from_wikipedia(club_name, log_fn)
        if img:
            return img, label

    # Source 4: TM HTML scrape (fragile, last resort)
    if scraped_logo_url:
        img, err = _download_logo_image(scraped_logo_url)
        if img:
            return img, "Transfermarkt HTML scrape"
        _log(f"    [S4] HTML scrape URL ✗ {err}")
    else:
        _log("    [S4] HTML scrape: sin URL de escudo en la página")

    return None, None


# ── Player write ──────────────────────────────────────────────────────────────

def _apply_player(of, player_idx: int, p: dict, player_overall: int):
    pos = p["pos"]

    pl = Player(of, player_idx, 0)
    pl.set_name(p["name"])
    pl.set_shirt_name(p["shirt"])

    base = _resolve_stats(player_overall, pos)
    # Per-player jitter so two squadmates at the same position+overall don't
    # come out as identical clones. Seeded by the OF slot id so the same
    # import produces the same numbers on a re-run.
    rng = random.Random(player_idx * 31 + player_overall)
    for stat, val in zip(Stats.ability99, base):
        Stats.set_value(of, player_idx, stat,
                        max(1, min(99, val + rng.randint(-3, 3))))

    spec = _DEF_SPEC.get(pos, _DEF_SPEC["CMF"])
    for stat, val in zip(Stats.ability_special, spec):
        Stats.set_value(of, player_idx, stat, val)

    for flag in [Stats.gk, Stats.cwp, Stats.cbt, Stats.sb, Stats.dm, Stats.wb,
                 Stats.cm, Stats.sm, Stats.am, Stats.wg, Stats.ss, Stats.cf]:
        Stats.set_value(of, player_idx, flag, 0)
    for flag in _POS_FLAGS.get(pos, [Stats.cm]):
        Stats.set_value(of, player_idx, flag, 1)

    Stats.set_value(of, player_idx, Stats.reg_pos, _REG_POS_IDX.get(pos, 6))
    Stats.set_value_str(of, player_idx, Stats.height, str(_HEIGHT_MAP.get(pos, 178)))
    Stats.set_value_str(of, player_idx, Stats.age,    str(p["age"]))
    Stats.set_value_str(of, player_idx, Stats.weight, "75")
    Stats.set_value_str(of, player_idx, Stats.nationality, p["nat"])
    Stats.set_value_str(of, player_idx, Stats.foot,        "R")
    Stats.set_value_str(of, player_idx, Stats.fav_side,    "R")
    Stats.set_value_str(of, player_idx, Stats.wfa,         "4")
    Stats.set_value_str(of, player_idx, Stats.wff,         "4")
    Stats.set_value_str(of, player_idx, Stats.injury,      "B")
    Stats.set_value_str(of, player_idx, Stats.consistency, "5")
    Stats.set_value_str(of, player_idx, Stats.condition,   "5")


# ── Panel ─────────────────────────────────────────────────────────────────────

class TransfermarktPanel(ttk.Frame):
    def __init__(self, parent, of, refresh_fn=None):
        super().__init__(parent)
        self._of          = of
        self._club_names  = []
        self._busy        = False
        self._refresh_fn  = refresh_fn   # called after a successful import
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        if not _DEPS_OK:
            ttk.Label(self,
                      text="Faltan dependencias:\n"
                           "  pip install requests beautifulsoup4",
                      foreground="red", font=("", 11)).pack(pady=40)
            return

        # config frame
        cfg = ttk.LabelFrame(self, text="Configuración")
        cfg.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(cfg, text="Equipo en OF:").grid(
            row=0, column=0, sticky=tk.W, padx=6, pady=4)
        self._club_var   = tk.StringVar()
        self._club_combo = ttk.Combobox(cfg, textvariable=self._club_var,
                                        state="readonly", width=28)
        self._club_combo.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Label(cfg, text="URL Transfermarkt\n(cualquier página del club):").grid(
            row=1, column=0, sticky=tk.W, padx=6)
        self._url_var = tk.StringVar()
        ttk.Entry(cfg, textvariable=self._url_var, width=54).grid(
            row=1, column=1, columnspan=2, sticky=tk.W+tk.E, padx=4, pady=4)
        ttk.Label(cfg,
                  text="Pega cualquier URL del club (startseite, kader, ...); "
                       "se normaliza a la página de plantilla automáticamente.",
                  foreground="gray").grid(row=2, column=1, columnspan=2,
                                          sticky=tk.W, padx=4, pady=(0, 2))

        # team-overall slider
        ttk.Label(cfg, text="Overall objetivo:").grid(
            row=3, column=0, sticky=tk.W, padx=6)
        sf = ttk.Frame(cfg)
        sf.grid(row=3, column=1, sticky=tk.W, padx=4, pady=4)
        self._overall_var = tk.IntVar(value=75)
        self._overall_scale = ttk.Scale(
            sf, from_=30, to=90, orient=tk.HORIZONTAL,
            variable=self._overall_var, length=200,
            command=lambda v: self._qlabel.config(text=f"{int(float(v))}"))
        self._overall_scale.pack(side=tk.LEFT)
        self._qlabel = ttk.Label(sf, text="75", width=4)
        self._qlabel.pack(side=tk.LEFT)
        hint = ("30 = juvenil   50 = regional   65 = liga menor   "
                "75 = profesional   85 = élite   90 = top mundial")
        ttk.Label(cfg, text=hint,
                  foreground="gray").grid(row=3, column=2, sticky=tk.W)

        # auto-detect overall from club name
        self._auto_var = tk.BooleanVar(value=team_quality.is_available())
        auto_cb = ttk.Checkbutton(
            cfg,
            text="Detectar nivel del equipo automáticamente "
                 "(usa data/team_ratings.json)",
            variable=self._auto_var,
            command=self._on_auto_toggle)
        auto_cb.grid(row=4, column=0, columnspan=3, sticky=tk.W,
                     padx=6, pady=(0, 2))
        if not team_quality.is_available():
            auto_cb.state(["disabled"])
            ttk.Label(cfg,
                      text="  ⚠ data/team_ratings.json ausente — usa el slider "
                           "manual o ejecuta tools/scrape_wepesstats.py",
                      foreground="#BB6600").grid(
                row=5, column=0, columnspan=3, sticky=tk.W, padx=20, pady=(0, 4))
        self._on_auto_toggle()

        # overflow mode
        ttk.Label(cfg, text="Jugadores a importar:").grid(
            row=6, column=0, sticky=tk.W, padx=6, pady=4)
        self._limit_var = tk.StringVar(value="all")
        lf = ttk.Frame(cfg)
        lf.grid(row=6, column=1, sticky=tk.W, padx=4)
        for text, val in [("Solo titulares (11)", "11"),
                          ("Primeros 23",         "23"),
                          ("Todos (hasta 32)",    "all")]:
            ttk.Radiobutton(lf, text=text, variable=self._limit_var,
                            value=val).pack(side=tk.LEFT, padx=4)

        # club info checkbox
        self._info_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg,
                        text="Importar también: nombre del club + escudo (logo)",
                        variable=self._info_var).grid(
            row=7, column=0, columnspan=3, sticky=tk.W, padx=6, pady=(2, 6))
        if not _PIL_OK:
            ttk.Label(cfg,
                      text="  ⚠ Pillow no instalado — el escudo no se importará "
                           "(pip install Pillow)",
                      foreground="#BB6600").grid(
                row=8, column=0, columnspan=3, sticky=tk.W, padx=20, pady=(0, 4))

        # button + status
        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, padx=8, pady=4)
        self._fetch_btn = ttk.Button(btn_row, text="⬇  Fetch & Apply",
                                     command=self._start)
        self._fetch_btn.pack(side=tk.LEFT, padx=4)
        self._status_var = tk.StringVar(value="")
        ttk.Label(btn_row, textvariable=self._status_var,
                  foreground="blue").pack(side=tk.LEFT, padx=8)

        # log
        log_fr = ttk.LabelFrame(self, text="Log")
        log_fr.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        sb = tk.Scrollbar(log_fr)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._log = tk.Text(log_fr, height=16, state=tk.DISABLED,
                            yscrollcommand=sb.set, font=("Courier", 9))
        self._log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        sb.config(command=self._log.yview)
        self._log.tag_config("ok",    foreground="#007700")
        self._log.tag_config("warn",  foreground="#BB6600")
        self._log.tag_config("error", foreground="#CC0000")
        self._log.tag_config("head",  foreground="#000099",
                             font=("Courier", 9, "bold"))

    # ── public ────────────────────────────────────────────────────────────────
    def refresh(self):
        if self._of is None or not _DEPS_OK:
            return
        self._club_names = Clubs.get_names(self._of)
        self._club_combo["values"] = self._club_names
        if self._club_names:
            self._club_combo.current(0)

    # ── log helpers ───────────────────────────────────────────────────────────
    def _log_write(self, msg, tag=""):
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, msg + "\n", tag)
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)

    def _log_clear(self):
        self._log.config(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.config(state=tk.DISABLED)

    def _tlog(self, msg, tag=""):
        self.after(0, lambda m=msg, t=tag: self._log_write(m, t))

    def _tstatus(self, msg):
        self.after(0, lambda m=msg: self._status_var.set(m))

    # ── auto-detect toggle ────────────────────────────────────────────────────
    def _on_auto_toggle(self):
        """Disable the manual slider when auto-detect is on."""
        state = ["disabled"] if self._auto_var.get() else ["!disabled"]
        try:
            self._overall_scale.state(state)
        except tk.TclError:
            pass

    # ── start ─────────────────────────────────────────────────────────────────
    def _start(self):
        if self._busy:
            return
        url = self._url_var.get().strip()
        if not url:
            messagebox.showwarning("URL vacía",
                                   "Ingresa la URL de Transfermarkt.", parent=self)
            return
        try:
            url, _origin = _normalize_squad_url(url)
        except ValueError as e:
            messagebox.showwarning("URL incorrecta", str(e), parent=self)
            return
        club_name = self._club_var.get()
        if not club_name:
            messagebox.showwarning("Sin equipo",
                                   "Selecciona un equipo del OF.", parent=self)
            return

        club_idx  = self._club_names.index(club_name)
        manual_overall = int(self._overall_var.get())
        auto      = bool(self._auto_var.get())
        limit_str = self._limit_var.get()
        limit     = 11 if limit_str == "11" else (23 if limit_str == "23" else 32)
        do_info   = self._info_var.get()

        self._busy = True
        self._fetch_btn.config(state=tk.DISABLED)
        self._log_clear()
        self._tstatus("Descargando...")

        threading.Thread(
            target=self._worker,
            args=(url, club_idx, club_name, manual_overall, auto, limit, do_info),
            daemon=True
        ).start()

    # ── worker (background thread) ────────────────────────────────────────────
    def _worker(self, url, club_idx, club_name, manual_overall, auto, limit, do_info):
        try:
            self._tlog(f"▶ Equipo destino : {club_name}  (idx {club_idx})", "head")
            self._tlog(f"▶ URL            : {url}", "head")
            mode_lbl = "auto-detect" if auto else f"{manual_overall} (manual)"
            self._tlog(f"▶ Overall        : {mode_lbl}   Límite: {limit}", "head")
            self._tlog("")

            # ── get OF squad slots ─────────────────────────────────────
            squad_team   = 73 + club_idx
            player_slots = [
                Squads.get_squad_player(self._of, squad_team, s)
                for s in range(32)
                if Squads.get_squad_player(self._of, squad_team, s) > 0
            ]

            if not player_slots:
                self._tlog(f"✗ El equipo '{club_name}' no tiene jugadores en el OF.",
                           "error")
                self.after(0, self._done)
                return

            self._tlog(f"→ Slots en OF    : {len(player_slots)} jugadores", "ok")

            # ── scrape TM page ─────────────────────────────────────────
            self._tstatus("Scrapeando Transfermarkt...")
            self._tlog("\n[1/3] Descargando página de Transfermarkt...")
            page = _scrape_page(url)
            players   = page["players"]
            tm_name   = page["club_name"]
            logo_url  = page["logo_url"]

            self._tlog(f"→ Jugadores en TM: {len(players)}", "ok")
            if tm_name:
                self._tlog(f"→ Nombre en TM   : {tm_name}", "ok")
            if logo_url:
                self._tlog(f"→ URL escudo     : {logo_url}", "ok")
            else:
                self._tlog("→ Escudo         : no encontrado en la página", "warn")

            # ── overflow ───────────────────────────────────────────────
            scraped     = len(players)
            of_slots    = len(player_slots)
            apply_count = min(scraped, of_slots, limit)

            if scraped > of_slots:
                self._tlog(
                    f"\n⚠ TM tiene {scraped} jugadores pero el OF solo tiene "
                    f"{of_slots} slots disponibles.", "warn")
            if limit < min(scraped, of_slots):
                self._tlog(
                    f"⚠ Límite configurado: se importan solo los primeros {limit}.",
                    "warn")

            players      = players[:apply_count]
            player_slots = player_slots[:apply_count]
            self._tlog(f"→ Se aplicarán   : {apply_count} jugadores\n")

            # ── resolve target overall ─────────────────────────────────
            target_overall = manual_overall
            if auto and team_quality.is_available() and tm_name:
                suggested, matched = team_quality.suggest_overall(tm_name)
                if suggested is not None:
                    target_overall = suggested
                    self._tlog(
                        f"→ Overall detectado: {target_overall}  "
                        f"(match: '{matched}')", "ok")
                    self.after(0, lambda v=target_overall:
                               (self._overall_var.set(v),
                                self._qlabel.config(text=str(v))))
                else:
                    self._tlog(
                        f"→ Sin match en team_ratings.json para '{tm_name}' — "
                        f"usando slider ({manual_overall})", "warn")
            self._tlog(f"→ Overall final  : {target_overall}", "head")

            # ── club info (name + logo) ────────────────────────────────
            if do_info:
                self._tlog("[2/3] Aplicando info del club...")

                if tm_name:
                    old_name = Clubs.get_name(self._of, club_idx)
                    Clubs.set_name(self._of, club_idx, tm_name[:48])
                    self._tlog(f"  Nombre: '{old_name}' → '{tm_name}'", "ok")

                if _PIL_OK:
                    self._tstatus("Buscando escudo...")
                    img, source = _find_club_logo(url, tm_name, logo_url, self._tlog)
                    if img:
                        if Emblems.get_free16(self._of) <= 0:
                            self._tlog("  Escudo: sin slots de emblema libres en OF.", "warn")
                        else:
                            emb_slot  = Emblems.count16(self._of)
                            emb_id    = Emblems.load_from_pil_image(self._of, '16', emb_slot, img)
                            Clubs.set_emblem_int(self._of, club_idx, emb_id)
                            self._tlog(
                                f"  Escudo: importado via {source}"
                                f" → emblema slot {emb_slot} (id={emb_id})"
                                f" ({Emblems.IMG_SIZE}×{Emblems.IMG_SIZE} 16c, "
                                f"vinculado al club)", "ok")
                    else:
                        self._tlog("  Escudo: ninguna fuente retornó imagen.", "warn")
                else:
                    self._tlog("  Escudo: saltado (Pillow no instalado).", "warn")
            else:
                self._tlog("[2/3] Info del club: omitida por configuración.")

            # ── apply players ──────────────────────────────────────────
            self._tstatus("Aplicando jugadores...")
            self._tlog(f"\n[3/3] Aplicando {apply_count} jugadores al OF...")
            self._tlog(
                f"  {'#':>2}  {'Nombre':<16} {'Pos':<5} {'Edad':>4}"
                f"  {'Ovr':>3}  {'Nacionalidad':<22}  {'ID OF':>6}",
                "head")

            for rank, (pid, p) in enumerate(zip(player_slots, players)):
                player_ovr = _distribute_overall(target_overall, rank, apply_count)
                _apply_player(self._of, pid, p, player_ovr)
                label = "TIT" if 1 <= p["number"] <= 11 else "SUP"
                self._tlog(
                    f"  {p['number']:>2}  {p['name']:<16} {p['pos']:<5}"
                    f" {p['age']:>4}  {player_ovr:>3}  {p['nat']:<22}"
                    f"  id={pid}  [{label}]",
                    "ok")

            self._tlog(
                f"\n✔ Hecho. {apply_count} jugadores aplicados a '{club_name}'.\n"
                f"  Guarda con  File › Save.", "ok")
            self._tstatus(f"✔ {apply_count} jugadores aplicados")
            self.after(0, lambda: self._done(success=True))

        except Exception as exc:
            self._tlog(f"\n✗ Error: {exc}", "error")
            self._tstatus("Error — ver log")
            self.after(0, lambda: self._done(success=False))

    def _done(self, success=False):
        self._busy = False
        self._fetch_btn.config(state=tk.NORMAL)
        if success and self._refresh_fn:
            self._refresh_fn()
