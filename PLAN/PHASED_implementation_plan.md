# بحور الشعر — Implementation Plan: JSON-Driven Expansion

## Executive Summary

| | |
|---|---|
| **Current State** | Single-file Python CLI; 4 hardcoded meters; patterns embedded in a `BUHOOR` dict; no external data loading |
| **Goal** | Expand to all 13 Arabic poetic meters in `arabic_rhythm_data.json`, driven by the JSON as the authoritative source of truth, with a shared iqaa pattern registry and new filter/metadata features |
| **Key Architectural Decision** | Separate **data** (JSON metadata) from **patterns** (drum grids) via a two-layer registry — `MeterRegistry` wraps the JSON; `IqaaPatternRegistry` maps `(variant_slug, steps_per_bar) → patterns dict` — so each iqaa is crafted once and reused across every meter that cites it |
| **Estimated Time** | 8–14 days across 4-6 coding sessions |

---

## Gap Analysis: JSON vs. Current Script

### New meters in JSON not yet in script

| Meter | Arabic | Corpus % | Iqaa count |
|-------|--------|----------|------------|
| Al-Ramal | الرمل | 7.0% | 4 |
| Al-Rajaz | الرجز | 5.5% | 4 |
| Al-Khafeef | الخفيف | 4.5% | 3 |
| Al-Mutaqarib | المتقارب | 3.5% | 4 |
| Al-Hazaj | الهزج | 2.0% | 3 |
| Al-Sari | السريع | 1.5% | 4 |
| Al-Mutadarak | المتدارك | 1.0% | 4 |
| Al-Madeed | المديد | 0.5% | 3 |

### New iqaa step-counts not yet handled

| Steps | Iqaa examples | Current support |
|-------|---------------|-----------------|
| 4 | Maqsum, Wahda, Malfuf, Ayyub, Wahda Saghira, Fallahi, Baladi | ❌ (script uses min 12) |
| 6 | Yuruk Semai, Sudasi | ❌ |
| 7 | Nawakht, Dawr Hindi | ❌ |
| 8 | Wahda Kabira, Masmudi Kabir (8-step) | ❌ |
| 10 | Sama'i Thaqil, Jurjina, Mudawwar Shami | ❌ |
| 12 | Mudawwar Masri | ✅ |
| 21 | Sama'i Darij, Sama'i Saraband | ✅ (kamil/wafir only) |
| 32 | Warshan 'Arabi | ❌ |

### Metadata fields in JSON not yet used

`is_traditional`, `bpm_range`, `geographic_tradition`, `instrument_context`, `performance_notes`, `corpus_pct`

---

## Phase 1: Data Layer Separation (2–3 days)

### Goal
**Replace the monolithic `BUHOOR` dict with a two-layer registry loaded from JSON, while keeping all existing audio output bit-for-bit identical.**

### Tasks

**1.1: Extract patterns into `iqaa_patterns.py`** (half day)

Create a standalone module with a registry of `(variant_slug, steps_per_bar) → patterns dict`. Migrate all existing patterns from `BUHOOR["taweel"]["variants"]`, `"kamil"`, `"baseet"`, and `"wafir"` into it.

```python
# iqaa_patterns.py

IqaaPatternRegistry: dict[tuple[str, int], dict[str, list[int]]] = {
    ("wahda", 12): {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    # ... migrate all existing variants here
}

def get_pattern(variant_slug: str, steps: int) -> dict[str, list[int]] | None:
    """Return pattern for (slug, steps), fallback to nearest steps if exact miss.
    Implementation details: handle during coding session."""
    pass
```

**1.2: Build `MeterRegistry` JSON loader** (half day)

```python
# meter_registry.py

import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class IqaaRecord:
    meter_ar: str
    iqaa: str
    is_traditional: bool
    mood_en: str
    geographic_tradition: str
    variant_slug: str
    default_bpm: int
    bpm_range: tuple[int, int]
    steps_per_bar: int
    instrument_context: str
    performance_notes: str
    syllable_pattern: str
    corpus_pct: float

def load_registry(json_path: Path) -> dict[str, list[IqaaRecord]]:
    """Load JSON, group by meter slug, return meter_slug → [IqaaRecord].
    Key decision: meter slug derived from meter_ar via a known mapping dict.
    Implementation details: handle during coding session."""
    pass

def validate_registry(registry: dict, pattern_registry: dict) -> list[str]:
    """Return list of (meter, variant_slug, steps_per_bar) combos missing patterns.
    Implementation details: handle during coding session."""
    pass
```

**1.3: Wire registries into `buhoor_drums.py`** (1 day)

- Replace direct `BUHOOR` lookups with registry calls
- Add `--data PATH` CLI option (default: `arabic_rhythm_data.json` co-located with script)
- Add `--validate` flag that runs `validate_registry()` and prints gaps, then exits
- Keep `BUHOOR` dict as fallback if JSON not found (backward compatibility)

**1.4: Regression test** (half day)

Generate all 4 original meters with old and new code paths. Compare file sizes and MD5 checksums. Zero diff = success.

```bash
# Before refactor
python buhoor_drums.py --all -o /tmp/before -q --seed 42

# After refactor
python buhoor_drums_v2.py --all -o /tmp/after -q --seed 42

md5sum /tmp/before/*.mp3 /tmp/after/*.mp3
```

### Success Criteria
- ✅ All existing 11 MP3 files reproduce with identical MD5 checksums
- ✅ `--validate` reports 0 missing patterns for current 4 meters
- ✅ `--data missing.json` exits with a clear error message, not a traceback
- ✅ `IqaaPatternRegistry` and `MeterRegistry` importable as standalone modules

### Deliverables
- [ ] `iqaa_patterns.py` — all existing patterns migrated
- [ ] `meter_registry.py` — JSON loader + dataclass + validator
- [ ] `buhoor_drums.py` — wired to new registries, `--data` and `--validate` flags added
- [ ] MD5 regression report (paste into commit message)

### Rollback Plan
**If** checksum diff appears after wiring: revert `buhoor_drums.py` to the `BUHOOR` dict, keep `iqaa_patterns.py` and `meter_registry.py` as dead files. Both new modules are additive.

---

## Phase 2: New Iqaa Drum Patterns (3–4 days)

### Goal
**Craft and validate drum patterns for every iqaa step-count not currently supported, using `performance_notes` as the primary specification.**

### Tasks

**2.1: Add `ka` (doumbek finger-snap) voice** (half day)

The JSON performance notes describe three articulations: DUM (low resonant), TEK (rim snap), KA (light snap). Currently the script only has kick/snare/hihat/crash. Add:

```python
def synth_ka(duration: float = 0.06) -> np.ndarray:
    """Light doumbek finger snap — higher pitched than snare TEK.
    Spec: ~5000 Hz ring + high-pass noise, very short decay.
    Implementation details: handle during coding session."""
    pass

SYNTH_MAP = {
    "kick":  synth_kick,
    "snare": synth_snare,
    "hihat": synth_hihat,
    "crash": synth_crash,
    "ka":    synth_ka,   # new
}
```

**2.2: Pattern crafting by step-count group** (2 days)

Work through each step-count group. For each iqaa, extract the DUM/TEK/KA beat placements from `performance_notes` and encode as step arrays. Commit each group as a separate git commit so failures are isolated.

*Group A — 4-step iiqaat* (Maqsum, Wahda, Malfuf, Ayyub, Wahda Saghira, Fallahi, Baladi):
```python
# Example: Maqsum 4-step — "DUM on 1 and 3; tek on 2 and 4"
("maqsum", 4): {
    "kick":  [1, 0, 1, 0],  # DUM beats 1, 3
    "snare": [0, 1, 0, 1],  # TEK beats 2, 4
    "hihat": [1, 1, 1, 1],
    "crash": [1, 0, 0, 0],
}
```

*Group B — 6-step* (Yuruk Semai, Sudasi): `[1, 0, 0, 1, 0, 0]` style compound pulse patterns

*Group C — 7-step* (Nawakht 4+3, Dawr Hindi): asymmetric — kick on 1, snare on 4, ka on 5 or 6

*Group D — 8-step* (Wahda Kabira, Masmudi Kabir 8-step, Ciftetelli)

*Group E — 10-step* (Sama'i Thaqil, Jurjina, Mudawwar Shami): "DUM on 1; tek on 3; second DUM on 7"

*Group F — 32-step* (Warshan 'Arabi): constructed as 4× an 8-step base with sparse ornamentation

**Key Decision — 4-step timing model**: The current timing formula is `step_dur = beats_per_bar × 60 / (bpm × steps_per_bar)`. For 4-step iiqaat, treat each step as one full beat (quarter note at that bpm), i.e. `beats_per_bar=4`, `steps_per_bar=4`. Verify this matches the "felt" pulse before committing to all 4-step patterns.

**2.3: Validate patterns audibly** (half day)

Generate one MP3 per new iqaa type and listen. Document pass/fail in a `PATTERN_AUDIT.md` file committed alongside the code.

```bash
# Quick validation — generate one 10-s loop per new iqaa
python buhoor_drums.py baseet -v maqsum    # 4-step
python buhoor_drums.py kamil -v yuruk_semai  # 6-step
python buhoor_drums.py baseet -v nawakht   # 7-step
```

### Success Criteria
- ✅ `--validate` reports 0 missing patterns for all 40 JSON records
- ✅ All 7 step-count groups render without `IndexError` or `ValueError`
- ✅ `ka` voice audibly distinct from `snare` in generated audio
- ✅ `PATTERN_AUDIT.md` documents listen-check for at least one pattern per step group

### Deliverables
- [ ] `iqaa_patterns.py` — all 40 (slug, steps) combos populated
- [ ] `synth_ka()` in `buhoor_drums.py`
- [ ] `PATTERN_AUDIT.md` — pass/fail log per step group
- [ ] Timing model tested and documented for 4-step group

### Rollback Plan
**If** a step-count group produces garbled audio: comment out that group in `IqaaPatternRegistry` and skip in `generate_bahr()` with a `# TODO: pattern pending` warning. Other groups are unaffected.

---

## Phase 3: Add Remaining 8 Meters (2–3 days)

### Goal
**Register all 8 missing meters from the JSON so the CLI can render them, adding the complete poetic corpus coverage the JSON was designed for.**

### Tasks

**3.1: Add `meter_ar → slug` mapping and BUHOOR entries** (1 day)

```python
# Arabic meter name → CLI slug (add to meter_registry.py)
METER_SLUG_MAP: dict[str, str] = {
    "الطويل":   "taweel",
    "الكامل":   "kamil",
    "البسيط":   "baseet",
    "الوافر":   "wafir",
    "الرمل":    "ramal",    # new
    "الرجز":    "rajaz",    # new
    "الخفيف":   "khafeef",  # new
    "المتقارب": "mutaqarib",# new
    "الهزج":    "hazaj",    # new
    "السريع":   "sari",     # new
    "المتدارك": "mutadarak",# new
    "المديد":   "madeed",   # new
}
```

For each new meter, add a minimal BUHOOR-style entry (arabic name, taf'eela, syllable pattern, description, time_signature, beats_per_bar, steps_per_bar). Pull `steps_per_bar` from the JSON record — do not guess. The `variants` list is now sourced from the registry, not hardcoded.

**3.2: Handle heterogeneous `steps_per_bar` per meter** (half day)

Some meters (Al-Ramal, Al-Rajaz) have multiple iqaa pairings with *different* step counts. The current `generate_bahr()` assumes a single `steps_per_bar` per meter. Refactor the loop to use the record's `steps_per_bar` per variant, not the meter-level value.

```python
def generate_bahr(key: str, records: list[IqaaRecord], ...) -> list[str]:
    """Generate one MP3 per IqaaRecord.
    Each record carries its own steps_per_bar — do not assume meter-wide uniformity.
    Implementation details: handle during coding session."""
    pass
```

**3.3: Update CLI help text and `--list` output** (half day)

`--list` should now group by meter and show corpus %, traditional flag, and region:

```
الرمل  ramal    7.0%
    • wahda        (traditional, Pan-Arab)   80 BPM  Romantic, delicate
    • maqsum       (traditional, Pan-Arab)  100 BPM  Romantic, delicate
    • sama3i_darij (traditional, Pan-Arab)   96 BPM  Romantic, delicate
    • sama3i_thaqil(traditional, Pan-Arab)   60 BPM  Romantic, delicate
```

### Success Criteria
- ✅ `python buhoor_drums.py --all` renders at least one MP3 per new meter without error
- ✅ `python buhoor_drums.py --list` shows all 13 meters with corpus %
- ✅ `python buhoor_drums.py ramal -v sama3i_thaqil` renders correctly at 10 steps/bar
- ✅ No regression on original 4 meters (re-run MD5 comparison)

### Deliverables
- [ ] `METER_SLUG_MAP` in `meter_registry.py`
- [ ] BUHOOR entries for all 8 new meters
- [ ] `generate_bahr()` refactored for per-variant `steps_per_bar`
- [ ] Updated CLI help strings and `--list` output
- [ ] MD5 regression check against Phase 1 baseline

### Rollback Plan
**If** a new meter's timing model produces wrong-tempo audio: add `SKIP_METERS: list[str] = ["madeed"]` guard in `generate_bahr()` and log a warning. Original 4 meters are unaffected.

---

## Phase 4: Metadata Filters & Enhanced Output (1–2 days)

### Goal
**Expose the JSON's rich metadata as CLI flags so users can filter by tradition, region, and instrument context — and see that context in ID3 tags and the `--list` output.**

### Tasks

**4.1: CLI filter flags** (half day)

```python
@click.option(
    "--traditional-only",
    is_flag=True,
    help="Render only is_traditional=True pairings.",
)
@click.option(
    "--region",
    type=click.Choice(["Masri", "Shami", "Andalusi", "Pan-Arab"], case_sensitive=False),
    multiple=True,
    help="Filter by geographic tradition. Repeatable.",
)
@click.option(
    "--instrument",
    type=click.Choice(["doumbek solo", "firqa", "mixed ensemble", "tabl + riq"], case_sensitive=False),
    multiple=True,
    help="Filter by instrument context. Repeatable.",
)
```

**4.2: BPM range validation** (quarter day)

When `--bpm` is provided, check against `IqaaRecord.bpm_range`:

```python
def validate_bpm(bpm: int, record: IqaaRecord, quiet: bool) -> int:
    """If bpm outside bpm_range, warn and clamp. Return effective bpm.
    Implementation details: handle during coding session."""
    pass
```

Example terminal output:
```
⚠  Warning: 180 BPM is above the recommended range [52–96] for wahda_kabira.
   Clamping to 96 BPM. Use --no-clamp to override.
```

**4.3: Enhanced ID3 tags** (quarter day)

Extend the existing tag-writing logic:

```python
tags = {
    "TIT2": f"{record.meter_ar} — {record.iqaa}",
    "TBPM": str(effective_bpm),
    "TCON": f"Arabic Poetry / {record.mood_en}",
    "TKEY": record.syllable_pattern,
    "COMM": record.performance_notes,   # new
    "TPUB": record.geographic_tradition, # new (repurposed field)
    "TRSN": "Traditional" if record.is_traditional else "Contemporary", # new
}
```

**4.4: `--info` flag** (quarter day)

```bash
python buhoor_drums.py --info taweel wahda_kabira
```

Prints the full `IqaaRecord` fields for that pairing — useful during composition:

```
  الطويل (Al-Taweel) × Wahda Kabira
  ────────────────────────────────────────
  Corpus share    : 35%
  BPM range       : 52 – 96  (default 72)
  Steps/bar       : 8
  Time signature  : 4/4
  Geographic area : Pan-Arab
  Instrument      : firqa
  Traditional     : Yes
  Performance notes:
    DUM on beat 1; tek fills on beats 3 and 5. The 8-beat Wahda Kabira
    cycle pairs with Al-Ṭawīl's half-verse moras; keep tempo restrained
    to honor the meter's epic weight.
```

**4.5: JSON manifest export** (quarter day)

When generating audio, write a `manifest.json` to the output directory:

```json
{
  "generated_at": "2025-01-15T14:32:00Z",
  "seed": 42,
  "files": [
    {
      "filename": "taweel_wahda_kabira_72bpm.mp3",
      "meter_ar": "الطويل",
      "iqaa": "Wahda Kabira",
      "is_traditional": true,
      "bpm": 72,
      "bpm_range": [52, 96],
      "steps_per_bar": 8,
      "geographic_tradition": "Pan-Arab",
      "instrument_context": "firqa",
      "performance_notes": "..."
    }
  ]
}
```

### Success Criteria
- ✅ `--traditional-only` halves the output count (roughly), no errors on remaining renders
- ✅ `--region Masri` filters correctly — non-Masri records are skipped, not errored
- ✅ `--bpm 200` on a record with `bpm_range [52, 96]` prints a warning and clamps
- ✅ `--info taweel wahda_kabira` prints all 9 metadata fields cleanly
- ✅ `manifest.json` exists in output dir after `--all` run, valid JSON, one entry per MP3

### Deliverables
- [ ] `--traditional-only`, `--region`, `--instrument` flags implemented and tested
- [ ] `validate_bpm()` with clamping and `--no-clamp` escape hatch
- [ ] Extended ID3 tag block
- [ ] `--info` command implemented
- [ ] `manifest.json` written after each generation run

### Rollback Plan
**If** ID3 tag writes fail for any new field: revert the tag dict to Phase 1 baseline keys. Audio generation is unaffected — tagging is a post-processing step.

---

## Phase 5: Polish & Documentation (1 day)

### Goal
**Make the expanded tool production-ready with updated docs, a clean README, and a smoother onboarding path for new users.**

### Tasks

**5.1: Update `README.md`** (half day)

- Expand the meter table to all 13 meters with corpus %, iqaa count, and time signature
- Add a "Filtering" section documenting `--traditional-only`, `--region`, `--instrument`
- Update the "Adding a new variant" section to reflect the JSON-driven architecture
- Add a "Manifest output" section

**5.2: `--validate` output polish** (quarter day)

```bash
python buhoor_drums.py --validate

  Registry validation
  ═══════════════════
  JSON records loaded : 40
  Patterns available  : 40   ✅
  Step groups covered : 4, 6, 7, 8, 10, 12, 21, 32

  Missing patterns    : 0

  Tradition breakdown :
    Traditional       : 28 / 40
    Contemporary      : 12 / 40

  Geographic breakdown:
    Pan-Arab   : 21
    Masri      : 10
    Shami      :  5
    Andalusi   :  4
```

**5.3: `--version` bump to 3.0.0** (5 minutes)

Bump from `2.0.0` → `3.0.0` to reflect the breaking architecture change (JSON dependency, new modules).

### Success Criteria
- ✅ README reflects all 13 meters with correct iqaa counts
- ✅ `--validate` output is human-readable in under 20 lines
- ✅ Fresh clone + `pip install -r requirements.txt` + `python buhoor_drums.py --all` completes without manual intervention
- ✅ Version string is `3.0.0`

### Deliverables
- [ ] Updated `README.md`
- [ ] `--validate` polished output
- [ ] `requirements.txt` includes all dependencies
- [ ] Version bumped to `3.0.0`

---

## Decision Tree & Stop Conditions

```
START
  ↓
PHASE 1: Data layer separation
  ├─ MD5 checksums match → PHASE 2
  ├─ 1–3 checksum diffs → Debug timing formula, fix, recheck
  │   ├─ Fixed → PHASE 2
  │   └─ Not fixed in 4 hours → STOP — document diff, investigate before proceeding
  └─ Registry import fails → Fix module structure before any further work

PHASE 2: New iqaa patterns
  ├─ All groups render audio → PHASE 3
  ├─ 1–2 step groups broken → Comment out, note in PATTERN_AUDIT.md, proceed
  └─ Timing formula wrong for 4-step → Resolve before adding any new meters (they depend on it)

PHASE 3: New meters
  ├─ All 8 render ≥1 MP3 each → PHASE 4
  ├─ 1–3 meters broken → Skip them (SKIP_METERS guard), proceed with working ones
  └─ Regression on original 4 meters → STOP — fix before proceeding

PHASE 4: Filters & metadata
  ├─ Filters work, no regressions → PHASE 5
  └─ BPM clamping breaks existing --bpm flag → Revert validate_bpm(), ship without clamping

PHASE 5: Polish
  → DONE
```

### Explicit Stop Conditions

**STOP if:**
- Phase 1 checksum diff cannot be explained after 4 hours of debugging
- Phase 2 4-step timing model is wrong and cannot be resolved in 1 day (all subsequent phases depend on it)
- Any phase causes regression on the original 4 meters and cannot be fixed in 2 hours
- Phase 3 introduces a `generate_bahr()` refactor that breaks the `--variant` filter

---

## Risk Mitigation Summary

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 4-step timing model produces wrong tempo | Medium | High | Validate audibly before crafting other step groups; the formula is `step_dur = 60 / (bpm × steps_per_bar)` for 4-step |
| JSON `steps_per_bar` conflicts with existing script values | Medium | Medium | `validate_registry()` in Phase 1 will surface all conflicts before any new patterns are written |
| Per-variant `steps_per_bar` breaks `generate_bahr()` | Medium | High | Phase 3.2 refactors this explicitly; keep original function as `generate_bahr_v1()` fallback |
| 32-step Warshan 'Arabi is too sparse to sound musical | Low | Low | Acceptable to ship as "experimental"; label in `--list` output and manifest |
| pydub ID3 tag field names differ across versions | Low | Medium | Test tag writing with `mutagen` as a fallback library if pydub fields fail |

---

## Success Metrics

### Minimum Viable Success (after Phase 3)
- ✅ All 13 Arabic meters renderable via CLI
- ✅ `--all` generates ~40 MP3 files without error
- ✅ Zero regressions on original 4 meters

### Full Success (after Phase 5)
- ✅ `--traditional-only`, `--region`, `--instrument` filters working
- ✅ `manifest.json` written alongside every generation run
- ✅ README covers all 13 meters and the new architecture
- ✅ `--validate` confirms 40/40 patterns present

### Stretch Goals (if ahead of schedule)
- Web scraper or CLI integration to fetch classical Arabic verse examples per meter
- `--preview` mode: play a 2-bar loop in-terminal via `simpleaudio` without writing to disk
- MIDI export alternative to MP3 (for DAW integration)

---

## Scope Boundaries

### In Scope
- ✅ All 13 meters in `arabic_rhythm_data.json`
- ✅ All iqaa pairings listed in the JSON (including non-traditional ones)
- ✅ `ka` voice synthesis (doumbek finger snap)
- ✅ Metadata filter flags: `--traditional-only`, `--region`, `--instrument`
- ✅ BPM range validation and clamping against JSON `bpm_range`
- ✅ JSON manifest alongside audio output

### Out of Scope
- ❌ Real drum samples / sample packs (physics synthesis only; avoids licensing issues)
- ❌ GUI or web interface (CLI tool scope; React UI is a separate project)
- ❌ MIDI export (instrument count and timing model would need significant redesign)
- ❌ Meters not in `arabic_rhythm_data.json` (prevents scope creep; add to JSON first)
- ❌ Automatic pattern generation from NLP parsing of `performance_notes` (LLM-assisted drafting is fine; ship hand-crafted arrays)

---

## Module Structure After Phase 3

```
buhoor_drums.py          # CLI entrypoint + synthesis engine (unchanged structure)
iqaa_patterns.py         # IqaaPatternRegistry — (slug, steps) → patterns dict
meter_registry.py        # MeterRegistry — JSON loader, IqaaRecord dataclass, validator
arabic_rhythm_data.json  # Authoritative data source (read-only during runtime)
PATTERN_AUDIT.md         # Auditory validation log (Phase 2 artifact)
requirements.txt         # numpy scipy pydub click (+ mutagen if needed)
README.md                # Updated docs
```

---

## Git Commit Alignment

| Commit | Phase | Description |
|--------|-------|-------------|
| `feat: extract iqaa_patterns.py` | 1.1 | Patterns migrated, no behavior change |
| `feat: add MeterRegistry JSON loader` | 1.2 | New module, not yet wired |
| `refactor: wire registries into CLI` | 1.3 | MD5 regression gate must pass here |
| `feat: add synth_ka voice` | 2.1 | New drum voice, backward compatible |
| `feat: patterns 4-step group` | 2.2a | Maqsum, Wahda, Malfuf, Ayyub, Wahda Saghira, Fallahi, Baladi |
| `feat: patterns 6/7/8-step groups` | 2.2b | Yuruk Semai, Sudasi, Nawakht, Dawr Hindi, Wahda Kabira |
| `feat: patterns 10/32-step groups` | 2.2c | Sama'i Thaqil, Jurjina, Mudawwar Shami, Warshan 'Arabi |
| `feat: add 8 new meters` | 3.1–3.3 | All new meters wired, --list updated |
| `feat: filter flags and BPM clamping` | 4.1–4.2 | --traditional-only, --region, --instrument |
| `feat: enhanced ID3 + manifest + --info` | 4.3–4.5 | Metadata features |
| `docs: update README, bump v3.0.0` | 5 | Final polish |

---

## Next Steps

1. **Start Phase 1.1**: Run `python buhoor_drums.py --all -o /tmp/baseline -q --seed 42` and save checksums before touching any code
2. **Create `iqaa_patterns.py`**: Copy-paste existing patterns from BUHOOR dict, wrapped in the `IqaaPatternRegistry` structure
3. **Validate Phase 1 locally**: Run MD5 diff — zero diff is the gate to Phase 2
4. **Install `mutagen`** alongside `pydub` now — it's more reliable for ID3 tagging and will be needed in Phase 4
5. **Before Phase 2**: Read every `performance_notes` field for the 4-step group and draft the step arrays on paper first — 10 minutes of planning saves 2 hours of debugging

---

*Plan version: 1.0 — Covers `arabic_rhythm_data.json` as of initial upload. If the JSON is extended with new meters, run `--validate` after loading to surface gaps automatically.*
