# بحور الشعر — Arabic Poetic Meters Drum Generator

A command-line tool that synthesizes drum loops matched to the rhythmic character of all 12 major Arabic poetic meters (_buhoor_ — بحور). Driven by a rich JSON metadata registry, the tool produces MP3 files drawn from 44 compatible Arabic percussion cycles, complete with ID3 tags and generation manifests.

---

## Background

Arabic poetry is built on a system of quantitative meters called _buhoor_ (بحور, literally "seas"). Each bahr has a characteristic pattern of long (—) and short (∪) syllables that gives it a distinct rhythmic personality. This tool translates those prosodic patterns into drum grids — kick, snare, ka (doumbek snap), hihat, and crash — so you can hear, and produce with, the rhythmic soul of each meter.

The 12 meters covered represent nearly **100% of the classical Arabic poetic corpus**:

| Bahr         | Arabic   | Corpus share | Time Signature |
| ------------ | -------- | ------------ | -------------- |
| Al-Taweel    | الطويل   | 35.0%        | 4/4            |
| Al-Kamil     | الكامل   | 18.0%        | 3/4            |
| Al-Baseet    | البسيط   | 14.0%        | 4/4            |
| Al-Wafir     | الوافر   | 8.0%         | 6/8            |
| Al-Ramal     | الرمل    | 7.0%         | 4/4            |
| Al-Rajaz     | الرجز    | 5.5%         | 4/4            |
| Al-Khafeef   | الخفيف   | 4.5%         | 10/8           |
| Al-Mutaqarib | المتقارب | 3.5%         | 4/4            |
| Al-Hazaj     | الهزج    | 2.0%         | 4/4            |
| Al-Sari      | السريع   | 1.5%         | 4/4            |
| Al-Mutadarak | المتدارك | 1.0%         | 4/4            |
| Al-Madeed    | المديد   | 0.5%         | 7/8            |

---

## Design Philosophy: Iqaa-First Approach

This tool takes an **iqaa-first (ethnomusicological) approach**: drum patterns are sourced from traditional Arabic percussion cycles (*iqaat*) that musicians have historically performed alongside each meter. These are curated cultural pairings, not mathematical derivations from syllabic structure.

This is a deliberate choice. An alternative **prosody-first (structural) approach** would derive patterns directly from the binary long/short syllable sequence of each meter's prosodic feet. That approach produces structurally accurate patterns but does not reflect what traditional ensembles actually play.

**Al-Sari note:** This project uses the classical theoretical foot sequence for Al-Sari (`مُسْتَفْعِلُنْ مُسْتَفْعِلُنْ مَفْعُولَاتُ`). Other tools may use the ziHaf-collapsed practical form (`مُسْتَفْعِلُنْ مُسْتَفْعِلُنْ فَاعِلُنْ`). Both are scholarly defensible.

---

## Requirements

- Python 3.10+
- `numpy`
- `scipy`
- `pydub`
- `click`
- `ffmpeg` (required by pydub for MP3 export)

Install Python dependencies:

```bash
pip install numpy scipy pydub click
```

Install ffmpeg (if not already present):

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
```

---

## Usage

```bash
# Interactive menu — prompts you to choose a meter
python buhoor_drums.py

# One specific meter by name
python buhoor_drums.py taweel

# Multiple meters at once
python buhoor_drums.py kamil baseet

# All 12 meters (generates ~44 files)
python buhoor_drums.py --all

# List all meters and variants without generating anything
python buhoor_drums.py --list

# View rich metadata for a specific meter/variant pairing
python buhoor_drums.py --info taweel wahda_kabira
```

### Filtering & Metadata

The tool includes a rich metadata registry (`arabic_rhythm_data.json`) that allows you to filter outputs by tradition, region, and instrument context:

```bash
# Generate only traditional pairings (no contemporary experiments)
python buhoor_drums.py --all --traditional-only

# Generate only Egyptian (Masri) rhythms
python buhoor_drums.py --all --region Masri

# Generate only rhythms meant for a full Firqa ensemble
python buhoor_drums.py --all --instrument firqa
```

### Tempo & Humanization

Every variant has its own default tempo chosen to match the prosodic character of its meter. You can override this for any render with `--bpm`. The tool will warn you and clamp the tempo if you exceed the historically accurate `bpm_range` for that rhythm, unless you pass `--no-clamp`.

```bash
# Override tempo (will clamp if outside recommended range)
python buhoor_drums.py taweel -v wahda_kabira --bpm 120

# Override tempo and force it past the recommended range
python buhoor_drums.py taweel -v wahda_kabira --bpm 200 --no-clamp

# Tighter timing, more velocity variation
python buhoor_drums.py --all --jitter 0.003 --velocity-variance 0.2

# Completely mechanical (no humanization)
python buhoor_drums.py --all --jitter 0 --velocity-variance 0
```

---

## Options

```
Usage: buhoor_drums.py [OPTIONS] [BAHR]...

Options:
  --all                           Generate all buhoor.
  -o, --output-dir DIRECTORY      Directory for output MP3 files.
                                  [default: /mnt/user-data/outputs/buhoor]
  -d, --duration FLOAT            Target loop duration in seconds. [default: 10.0]
  -v, --variant TEXT              Render only the named variant(s).
  --traditional-only              Render only is_traditional=True pairings.
  --region [Masri|Shami|Andalusi|Pan-Arab]
                                  Filter by geographic tradition. Repeatable.
  --instrument [doumbek solo|firqa|mixed ensemble|tabl + riq]
                                  Filter by instrument context. Repeatable.
  --seed INTEGER                  Random seed for humanization. [default: 42]
  --jitter FLOAT                  Max ±timing jitter per hit in seconds.
  --velocity-variance FLOAT       Max ±velocity nudge fraction.
  --bpm INTEGER                   Override the tempo for every rendered variant.
  --no-clamp                      Do not clamp BPM to the recommended range.
  --bitrate [128k|192k|256k|320k] MP3 output bitrate. [default: 192k]
  -q, --quiet                     Suppress descriptions and pattern grids.
  -l, --list                      List available buhoor (and their variants) then exit.
  --info BAHR VARIANT             Print full metadata for a specific meter/variant pairing and exit.
  --data FILE                     Path to arabic_rhythm_data.json.
  --validate                      Validate pattern coverage against the JSON registry, then exit.
  -V, --version                   Show the version and exit.
  -h, --help                      Show this message and exit.
```

---

## Output & Manifest

MP3 files are written to the output directory. Each file is named:

```
{meter}_{cycle}_{bpm}bpm.mp3
```

For example: `taweel_mudawwar_masri_80bpm.mp3`

**ID3 Tags:** Files are automatically tagged with rich metadata, including the Arabic meter name, time signature, mood (Genre), geographic tradition (Publisher), and detailed performance notes (Comments).

**Manifest:** After every generation run, a `manifest.json` file is written to the output directory containing the exact metadata, seed, and generation timestamp for every file produced.

---

## Architecture: Adding a New Variant

The tool uses a two-layer, JSON-driven architecture:

1. **`arabic_rhythm_data.json`**: The authoritative source of truth for metadata (BPM ranges, regions, traditions).
2. **`iqaa_patterns.py`**: A registry mapping `(variant_slug, steps_per_bar)` to the actual drum grids.

To add a new rhythm:

1. Add a new record to `arabic_rhythm_data.json`:

```json
{
  "meter_ar": "الطويل",
  "iqaa": "My Custom Rhythm",
  "is_traditional": false,
  "mood_en": "Experimental",
  "geographic_tradition": "Pan-Arab",
  "variant_slug": "my_custom_rhythm",
  "default_bpm": 90,
  "bpm_range": [70, 110],
  "steps_per_bar": 8,
  "instrument_context": "doumbek solo",
  "performance_notes": "DUM on 1, TEK on 4.",
  "syllable_pattern": "∪——∪∪——∪——∪∪——",
  "corpus_pct": 35.0
}
```

2. Add the corresponding drum grid to `IqaaPatternRegistry` in `iqaa_patterns.py`:

```python
("my_custom_rhythm", 8): {
    "kick":  [1, 0, 0, 0, 0, 0, 0, 0],
    "snare": [0, 0, 0, 1, 0, 0, 0, 0],
    "ka":    [0, 0, 1, 0, 1, 0, 1, 0],
    "hihat": [1, 0, 1, 0, 1, 0, 1, 0],
    "crash": [1, 0, 0, 0, 0, 0, 0, 0],
}
```

3. Run `python buhoor_drums.py --validate` to ensure your new pattern is correctly linked.

---

## Technical Notes

**Drum synthesis** is physics-based, using no external samples:

- **Kick** — 808-style pitch sweep from 150 Hz → 50 Hz with exponential decay
- **Snare** — 200 Hz tonal body blended with filtered noise burst
- **Ka** — Light doumbek finger snap; 5 kHz ring with high-pass noise and very short decay
- **Hihat** — White noise passed through a 7 kHz Butterworth high-pass filter
- **Crash** — Broadband noise through a 4 kHz high-pass with slow decay

**Panning** uses a constant-power law (`L = cos(p·π/2)`, `R = sin(p·π/2)`) to maintain equal perceived loudness across the stereo field on headphones.
