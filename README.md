# PES Fan Editor - Python Port

A Python/tkinter port of the classic **PES Editor 6** (originally written in Java by Compulsion, juce, PeterC10 and lazanet). This version lets you edit your Pro Evolution Soccer 6 option files on any platform that runs Python — no Java required.

---

## Features

| Tab | What you can do |
|-----|----------------|
| **Transfer** | Move players between teams |
| **Team** | Edit team names and attributes |
| **Kits** | Customize kit colors and styles |
| **Emblem** | Import/export team emblems |
| **Logo** | Import/export league logos |
| **League** | Edit league names and settings |
| **Stadium** | Assign stadiums to teams |
| **PES / Shop** | Shop and PES mode settings |
| **Transfermarkt** | Fetch player data online (auto-detects team overall from the PES6 reference DB at `data/team_ratings.json`) |
| **Stat Adjust** | Global stat adjustments |
| **OF2 Import** | Merge data from a second option file |

**Tools menu extras:**
- Export / Import player stats as CSV
- Convert OF2 data → OF1

---

## Requirements

- Python **3.8** or newer
- `tkinter` — bundled with standard Python on Windows/macOS. On Debian/Ubuntu/Mint install it with `sudo apt install python3-tk`.
- `Pillow` (with `ImageTk`) — used for team flags, kits, emblems and logos.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/AlexEduardoQuimizPlaza/Pes-Fan-Editor-Python-Port.git
cd Pes-Fan-Editor-Python-Port
```

### 2. Install dependencies (recommended: virtualenv)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

A virtualenv is recommended because `pip install Pillow` pulls in `ImageTk` automatically. If you prefer to use your distro's system Pillow on Debian/Ubuntu/Mint, install both packages explicitly:

```bash
sudo apt install python3-tk python3-pil python3-pil.imagetk
```

### 3. Run the editor

```bash
python main.py
```

### Optional: rebuild the team-quality reference data

The Transfermarkt importer reads `data/team_ratings.json` (140 PES6 clubs with their average overall rating) and `data/position_stats.json` (per-position stat templates by overall band). Both files are committed to the repo, so you don't need to do anything for normal use. To regenerate them from the upstream source ([wepesstats.rf.gd](https://wepesstats.rf.gd)):

```bash
pip install requests beautifulsoup4 cryptography
python tools/scrape_wepesstats.py            # ~3-5 min, resumable
python tools/scrape_wepesstats.py --aggregate # rebuild JSONs from cache only
```

---

## Supported save file formats

| Format | Extension | Device |
|--------|-----------|--------|
| SharkPort | `.xps` | PS2 |
| PowerSave | `.psu` | PS2 |
| MaxSave | `.max` | PS2 |
| PC Binary | `.bin` | PC |

---

## Usage

1. Launch the editor with `python main.py`
2. Go to **File → Open** and select your PES6 option file
3. Edit using the tabs at the top
4. **File → Save** (or **Save As**) to write your changes back

---

## Credits

Original Java application:
- **Compulsion** — original PES Editor 6 (2006-2007)
- **juce** — CSV import/export (2011-2012)
- **PeterC10** — enhancements (2019)
- **lazanet** — PSD connection (2017-2019)

Python port by **AlexEduardoQuimizPlaza**, based on the original GPL v3 source.

---

## License

This program is free software under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).
