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
| **Transfermarkt** | Fetch player data online |
| **Stat Adjust** | Global stat adjustments |
| **OF2 Import** | Merge data from a second option file |

**Tools menu extras:**
- Export / Import player stats as CSV
- Convert OF2 data → OF1

---

## Requirements

- Python **3.8** or newer
- `tkinter` — included with standard Python installations
- `Pillow` — optional, needed only for emblem/logo image import/export

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/AlexEduardoQuimizPlaza/Pes-Fan-Editor-Python-Port.git
cd Pes-Fan-Editor-Python-Port
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> If you don't need image import/export you can skip this step — the editor will still run.

### 3. Run the editor

```bash
python main.py
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
