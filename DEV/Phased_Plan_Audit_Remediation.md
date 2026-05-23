# Phased Implementation Plan
## Arabic Prosody & Drums — Audit Remediation
**Generated from:** `audit_report.md` + `executive_summary.md` (2026-05-23)  
**Template:** `Phased_Plan_Executive_Summary.md`  
**Target projects:** `buhor_prosody_drums` (Python) · `arabic-poetry-drum-machine` (HTML/JS)

---

## 1. Executive Summary & Locked Decisions

### Current State vs. Goal

| | Current State | After This Plan |
|---|---|---|
| README meter count | Says "13", implements 12 | Accurate count with correct script name |
| Al-Hazaj steps_per_bar | `4` (wrong — loops at 2× speed) | `8` (two full feet, correct timing) |
| Al-Hazaj JSON entries | None for 8-step patterns | At least 2 iqaa entries added |
| Phase 1 orphan slugs | `"fallahy"`, `"samaai_darij"` (unreachable) | Renamed to match JSON; dead code eliminated |
| `beats_per_bar` derivation | Hardcoded if/elif chain in `buhoor_drums.py` | Moved to `arabic_rhythm_data.json` as a field |
| `manifest.json` schema | No `no_clamp` provenance field | `"no_clamp": bool` added to every entry |
| Duplicate JSON file | Root + `DATA/` copies (can silently diverge) | `DATA/` copy deleted; one source of truth |
| Phantom audit test | `wafir/sama3i_saraband` tests unreachable pairing | Removed or given real JSON backing |
| Al-Sari divergence | Undocumented contradiction between projects | Documented in both READMEs |
| Core philosophy split | Undocumented iqaa-first vs prosody-first | "Design Philosophy" section in both READMEs |
| Al-Wafir diacritics | Inconsistent across projects | Standardized to `مُفَاعَلَتُنْ` |
| Web app BPM default | 120 BPM flat for all meters | Per-meter recommended BPM in `BAHUR` |
| Web app ziHaf notice | Absent | One-line UI disclosure added |

### Locked Decisions

These are **closed for debate**. Do not re-litigate, do not propose alternatives.

| Decision | Rationale |
|---|---|
| The Python project's iqaa-first approach is **kept as-is** | It is an ethnomusicological choice, not a bug |
| The web app's prosody-first approach is **kept as-is** | It is a structural-mathematical choice, not a bug |
| Al-Sari divergence is **documented, not unified** | Both forms are scholarly defensible; unifying would require choosing a side |
| Al-Munsarih is **not added** to the Python project in this plan | Adding a new meter is out of scope; the README fix is in scope |
| The `.pkl` poem dataset integration is **out of scope** | Integration is a future feature, not a remediation task |
| `iqaa_patterns.py` Phase 1 orphan patterns are **renamed, not deleted** | They may have value once JSON backing is added |
| Synthesis code in `buhoor_drums.py` (`synth_kick`, `synth_snare`, etc.) is **untouched** | Audio synthesis is not a remediation target |

---

## 2. Pre-Coding Checklist & Baseline Assumptions

**Hard Gate: Do not proceed to Phase 1 if any item below fails.**

### 2.1 Environment Baseline (Python Project)

Run these commands from the `buhor_prosody_drums/` root before touching any file:

```bash
# 1. Confirm Python version
python --version
# Expected: Python 3.10.x or higher. STOP if lower.

# 2. Confirm dependencies are installed
python -c "import numpy, scipy, pydub, click; print('OK')"
# Expected: "OK". STOP if ImportError.

# 3. Confirm the existing JSON loads cleanly
python -c "
import json, pathlib
data = json.loads(pathlib.Path('arabic_rhythm_data.json').read_text(encoding='utf-8'))
print(f'JSON OK: {len(data)} records')
"
# Expected: "JSON OK: 44 records" (or the current count). STOP if exception.

# 4. Confirm validate flag runs without Python errors (registry gaps expected)
python buhoor_drums.py --validate
# Expected: runs without traceback. Gaps printed are expected and OK.

# 5. Confirm iqaa_patterns loads and validate_patterns is clean
python -c "
from iqaa_patterns import validate_patterns
errs = validate_patterns()
print('Pattern errors:', errs if errs else 'NONE')
"
# Expected: "Pattern errors: NONE". STOP if any errors are reported.

# 6. Record current file checksums for rollback reference
python -c "
import hashlib, pathlib
for f in ['buhoor_drums.py', 'iqaa_patterns.py', 'meter_registry.py', 'arabic_rhythm_data.json']:
    h = hashlib.md5(pathlib.Path(f).read_bytes()).hexdigest()
    print(f'{h}  {f}')
"
# SAVE THIS OUTPUT. It is your rollback baseline.
```

### 2.2 Environment Baseline (Web App Project)

```bash
# 1. Confirm index.html loads in browser without console errors
# Open src/index.html in a browser. Open DevTools console.
# Expected: no red errors. Bahr selector renders. Play button works.
# STOP if any console errors are present before this plan begins.

# 2. Confirm Tone.js is local and bundled
ls src/Tone.js
# Expected: file present. STOP if missing (means CDN dependency is broken).
```

### 2.3 Assumption Checks

```python
# Run this block. All assertions must pass before proceeding.
from buhoor_drums import BUHOOR
from iqaa_patterns import IqaaPatternRegistry, get_pattern
from meter_registry import METER_AR_TO_SLUG

# A1: Hazaj exists and has steps_per_bar = 4 (this is the bug we are about to fix)
assert BUHOOR['hazaj']['steps_per_bar'] == 4, "STOP: Hazaj steps already changed — re-read the codebase."

# A2: Orphan slugs exist with wrong spelling
assert ('fallahy', 12) in IqaaPatternRegistry, "STOP: 'fallahy' slug not found — may already be fixed."
assert ('samaai_darij', 21) in IqaaPatternRegistry, "STOP: 'samaai_darij' slug not found — may already be fixed."

# A3: Correct slugs do NOT yet exist (confirming rename is needed)
assert ('fallahi', 12) not in IqaaPatternRegistry, "STOP: 'fallahi' 12-step already exists — Phase 3 may be done."
assert ('samaai_darij', 21) in IqaaPatternRegistry  # This one is OK both ways

# A4: No hazaj JSON records exist (we will add them in Phase 3)
# ⚠ PS (Session 2, 2026-05-23): This assertion is WRONG. The JSON already contains
# 3 Hazaj records: malfuf(4), ayyub(4), wahda_saghira(4). All three have matching
# patterns in IqaaPatternRegistry and ARE renderable. The BUHOOR steps_per_bar=4
# bug (A1) is still present and still needs fixing — Hazaj renders but at wrong
# timing (4 steps = one foot instead of two). Do NOT treat this assertion failure
# as a stop condition. Skip A4 and proceed. Task 3.5 adds two genuinely new records
# (mudawwar_masri/8 and maqsum/4) which do not exist in the JSON today.
import json, pathlib
data = json.loads(pathlib.Path('arabic_rhythm_data.json').read_text(encoding='utf-8'))
hazaj_records = [r for r in data if r['meter_ar'] == 'الهزج']
# assert len(hazaj_records) == 0  # REMOVED — actual count is 3, see PS above
print(f"Hazaj records in JSON: {len(hazaj_records)} (expected ≥3; malfuf/ayyub/wahda_saghira at 4 steps)")

print("All assumption checks passed. Proceed to Phase 1.")
```

---

## 3. Phases

---

## Phase 0 — Snapshot & Scaffolding
**Risk:** None  
**Goal:** Create rollback copies of every file that will be modified.  
**Dependency:** Pre-coding checklist must have passed.

### Task 0.1 — Create rollback copies

```bash
# From buhor_prosody_drums/ root:
cp buhoor_drums.py     buhoor_drums.py.bak
cp iqaa_patterns.py    iqaa_patterns.py.bak
cp arabic_rhythm_data.json arabic_rhythm_data.json.bak

# From arabic-poetry-drum-machine/ root:
cp src/index.html src/index.html.bak
```

**Success criteria:** Four `.bak` files exist. Nothing else changes.  
**Stop condition:** If any `cp` fails (permissions, disk space), STOP.

---

## Phase 1 — Documentation Fixes (Zero Code Risk)
**Risk:** None — README and comment changes only  
**Goal:** Eliminate misleading documentation in both projects.  
**Dependency:** Phase 0 complete.

### Task 1.1 — Fix Python README: meter count and script name
**File:** `buhor_prosody_drums/README.md`  
**Exact changes — two locations only. Do not touch anything else.**

**Change 1** — Opening description (currently says "13"):
```
FIND:    "The 13 meters covered represent nearly **100% of the classical Arabic poetic corpus**"
REPLACE: "The 12 meters covered represent nearly **100% of the classical Arabic poetic corpus**"
```

**Change 2** — Every occurrence of `buhoor_drums_v2.py` in code blocks:
```
FIND:    buhoor_drums_v2.py
REPLACE: buhoor_drums.py
```
There are 8 occurrences in the Usage section and Options section. Replace all of them. Do not change any other text on those lines.

**Success criteria:**
- `grep -c "buhoor_drums_v2" README.md` returns `0`.
- `grep -c "13 meters" README.md` returns `0`.
- `grep -c "12 meters" README.md` returns `1`.
- All usage examples still make syntactic sense when read as prose.

**Stop condition:** If the grep above returns any nonzero count for the removed strings, STOP.

---

### Task 1.2 — Add Al-Wafir Diacritics Standardization (Python)
**File:** `buhor_prosody_drums/buhoor_drums.py`  
**Exact location:** The `BUHOOR["wafir"]` dict, `"taf_eela"` key.

```python
# FIND (exact string):
"taf_eela": "مُفَاعَلَتُن",

# REPLACE WITH:
"taf_eela": "مُفَاعَلَتُنْ",
```

**Minimum change rule:** One character (adding Sukun ْ on the terminal Nun). Do not touch any other field in the wafir dict.

**Success criteria:** `python -c "from buhoor_drums import BUHOOR; print(BUHOOR['wafir']['taf_eela'])"` prints `مُفَاعَلَتُنْ`.

---

### Task 1.3 — Add Design Philosophy Section to Python README
**File:** `buhor_prosody_drums/README.md`  
**Exact location:** Insert as a new H2 section immediately after the `## Background` section and before `## Requirements`.

**Insert exactly this block (verbatim):**
```markdown
## Design Philosophy: Iqaa-First Approach

This tool takes an **iqaa-first (ethnomusicological) approach**: drum patterns are sourced from traditional Arabic percussion cycles (*iqaat*) that musicians have historically performed alongside each meter. These are curated cultural pairings, not mathematical derivations from syllabic structure.

This is a deliberate choice. An alternative **prosody-first (structural) approach** would derive patterns directly from the binary long/short syllable sequence of each meter's prosodic feet. That approach produces structurally accurate patterns but does not reflect what traditional ensembles actually play.

**Al-Sari note:** This project uses the classical theoretical foot sequence for Al-Sari (`مُسْتَفْعِلُنْ مُسْتَفْعِلُنْ مَفْعُولَاتُ`). Other tools may use the ziHaf-collapsed practical form (`مُسْتَفْعِلُنْ مُسْتَفْعِلُنْ فَاعِلُنْ`). Both are scholarly defensible.
```

**Minimum change rule:** Insert this block only. Do not edit any adjacent section.

**Success criteria:** README renders correctly in a Markdown viewer. Section appears between Background and Requirements.

---

### Task 1.4 — Add Design Philosophy Note to Web App
**File:** `arabic-poetry-drum-machine/src/index.html`  
**Exact location:** The `<!-- Key/Legend -->` div at the bottom of `render()`. Append one sentence to the existing legend div's inner content.

**Find this string in the legend div:**
```
الألوان تميز التفاعيل المختلفة
```

**Replace with:**
```
الألوان تميز التفاعيل المختلفة &nbsp;·&nbsp; <span style="font-style:italic">تعكس الأنماط البنية العروضية النظرية — لا الإيقاعات الموسيقية التقليدية</span>
```

This adds: *"Patterns reflect the theoretical prosodic structure — not traditional musical iqaat."*

**Minimum change rule:** One inline addition inside one div. Do not touch any surrounding JavaScript or CSS.

**Success criteria:** Legend text visible in browser. No new console errors.

---

### Task 1.5 — Add ziHaf Disclosure to Web App UI
**File:** `arabic-poetry-drum-machine/src/index.html`  
**Exact location:** The legend div (same one as Task 1.4, but a separate line — add after the legend div's closing tag, before the closing of the parent container).

**Append this block immediately after the closing `</div>` of the legend:**
```html
<!-- Ziḥāf disclosure -->
<div style="margin-top:8px;padding:8px 14px;background:var(--color-background-secondary);border-radius:8px;font-size:10px;color:var(--color-text-tertiary);direction:rtl">
  ⚠ تعرض هذه الأداة الأشكال النظرية الأساسية للبحور دون تطبيق الزحافات والعلل. — Patterns shown are the canonical base forms; ziḥāf and ʿilal (poetic license variations) are not modelled.
</div>
```

**Minimum change rule:** One new div appended. No changes to existing HTML structure.

**Success criteria:** Disclosure text appears below the legend in the browser. No layout breakage.

---

**Phase 1 Gate:** Run `python buhoor_drums.py --list` and confirm it outputs 12 meters with the correct script invocation. Run `python -c "from buhoor_drums import BUHOOR; print(len(BUHOOR))"` and confirm `12`. Open `index.html` in browser and confirm the legend and disclosure are visible. **Do not proceed to Phase 2 if any of these fail.**

---

## Phase 2 — Data Layer Fixes
**Risk:** Low — JSON and Python data file changes only, no synthesis logic touched  
**Goal:** Establish a single source of truth for the JSON; fix orphaned slug names in `iqaa_patterns.py`; remove phantom audit test.  
**Dependency:** Phase 1 gate passed.

### Task 2.1 — Rename Orphaned Slugs in `iqaa_patterns.py`
**File:** `buhor_prosody_drums/iqaa_patterns.py`  
**Exact changes — two key renames only.**

**Change 1:** Rename `"fallahy"` → `"fallahi"` (to match JSON `variant_slug`)
```python
# FIND (exact key):
    ("fallahy", 12): {

# REPLACE WITH:
    ("fallahi", 12): {
```

**Change 2:** Rename `"samaai_darij"` → `"samaai_darij_legacy"` (to avoid collision with Phase 2's `"sama3i_darij"` at 21 steps, and to make the orphan status explicit)
```python
# FIND (exact key):
    ("samaai_darij", 21): {

# REPLACE WITH:
    ("samaai_darij_legacy", 21): {
```

Add this comment on the line above the renamed key:
```python
    # LEGACY: Renamed from "samaai_darij". Superseded by ("sama3i_darij", 21) in Phase 2.
    # No JSON record points to this key. Kept for reference; safe to remove in a future cleanup.
```

**Minimum change rule:** Two key renames, one comment added. Do not change pattern values inside either dict. Do not touch any other key.

**Success criteria:**
```python
from iqaa_patterns import IqaaPatternRegistry
assert ('fallahi', 12) in IqaaPatternRegistry
assert ('fallahy', 12) not in IqaaPatternRegistry
assert ('samaai_darij_legacy', 21) in IqaaPatternRegistry
assert ('samaai_darij', 21) not in IqaaPatternRegistry  # Wait — this one IS used by Phase 2 JSON!
```

**⚠ Careful:** `("sama3i_darij", 21)` (with `3` not `ai`) is a **separate, valid Phase 2 key** that IS pointed to by JSON records. Do not rename or touch it. Only rename the old Phase 1 `"samaai_darij"` key.

Run `python -c "from iqaa_patterns import validate_patterns; print(validate_patterns())"` — must return `[]`.

---

### Task 2.2 — Delete Duplicate JSON from `DATA/` Folder
**File:** `buhor_prosody_drums/DATA/arabic_rhythm_data.json`

```bash
# Verify both files are identical before deleting
python -c "
import hashlib, pathlib
h1 = hashlib.md5(pathlib.Path('arabic_rhythm_data.json').read_bytes()).hexdigest()
h2 = hashlib.md5(pathlib.Path('DATA/arabic_rhythm_data.json').read_bytes()).hexdigest()
print('IDENTICAL' if h1 == h2 else f'DIFFERENT: {h1} vs {h2}')
"
# Expected: "IDENTICAL". If "DIFFERENT": STOP. Do not delete. Investigate which is newer.
```

If identical:
```bash
del DATA\arabic_rhythm_data.json   # Windows
# or
rm DATA/arabic_rhythm_data.json    # Unix
```

**Success criteria:** `DATA/arabic_rhythm_data.json` no longer exists. Root `arabic_rhythm_data.json` still loads cleanly via `python buhoor_drums.py --validate`.

**Stop condition:** If the hash check shows DIFFERENT, **STOP**. The files have diverged. Bring both copies to the human for review before deciding which is authoritative.

---

### Task 2.3 — Fix Phantom Test in `audit_phase2.py`
**File:** `buhor_prosody_drums/audit_phase2.py`  
**Exact location:** The `test_cases` list, the Group G entry.

**Find:**
```python
    ("wafir", "sama3i_saraband", 21, 108),  # Group G
```

**Replace with:**
```python
    # NOTE: sama3i_saraband has no JSON record for Al-Wafir.
    # This test bypasses the JSON loader and tests a phantom pairing.
    # Removed until a JSON entry for wafir/sama3i_saraband is authored.
    # ("wafir", "sama3i_saraband", 21, 108),  # Group G — PHANTOM, see audit_report.md §6.4
```

**Minimum change rule:** Comment out one line. Add two comment lines explaining why. Do not touch any other test case.

**Success criteria:** `python audit_phase2.py` runs to completion with 7 test cases (not 8) and prints `✅ Audit files generated in ...`.

---

### Task 2.4 — Rename `audit_phase2.py` → `smoke_test_renders.py`
**Files:** `buhor_prosody_drums/audit_phase2.py` · `Phased_Plan_Audit_Remediation.md` (gate command)  
**Rationale:** The name `audit_phase2.py` is misleading on two counts: (1) it implies a `audit_phase1.py` sibling; (2) "phase 2" collides with this plan's own Phase 2 terminology. The script's actual role is an end-to-end audio render smoke test — it calls `render_variant()` and produces MP3 files. The new name reflects that accurately.

**Step 1 — Rename the file:**
```bash
# From buhor_prosody_drums/ root:
git mv audit_phase2.py smoke_test_renders.py
# If not using git:
mv audit_phase2.py smoke_test_renders.py
```

**Step 2 — Update the internal label string inside `smoke_test_renders.py`:**
```python
# FIND:
            "why": "Phase 2 Auditory Test",

# REPLACE WITH:
            "why": "Render smoke test",
```

**Minimum change rule:** File rename + one string inside it. Do not touch any test cases, imports, or logic.

**Success criteria:**
```bash
python smoke_test_renders.py
# Expected: runs to completion, prints ✅ Audit files generated in ...
ls audit_phase2.py 2>/dev/null && echo "OLD FILE STILL EXISTS — FAIL" || echo "Rename OK ✅"
```

**Stop condition:** If `smoke_test_renders.py` produces a traceback, STOP and restore from `.bak`.

---

**Phase 2 Gate:**
```bash
python -c "from iqaa_patterns import validate_patterns; errs = validate_patterns(); assert errs == [], errs; print('OK')"
python buhoor_drums.py --validate
python smoke_test_renders.py
```
All three must complete without errors or exceptions. **Do not proceed to Phase 3 if any fail.**

---

## Phase 3 — Structural Code Fix: Al-Hazaj + `beats_per_bar` Data-Driven
**Risk:** Medium — touches `BUHOOR` dict (timing model) and dynamic registry loader  
**Goal:** Fix Al-Hazaj timing bug; move `beats_per_bar` from hardcoded if/elif to JSON field.  
**Dependency:** Phase 2 gate passed.

### Task 3.1 — Add `beats_per_bar` to Every JSON Record
**File:** `buhor_prosody_drums/arabic_rhythm_data.json`

Every record in the JSON must receive a new field `"beats_per_bar"`. The values are derived from the existing hardcoded if/elif table in `buhoor_drums.py` (which we will remove in Task 3.3). This is a mechanical transformation — do not invent new values.

**Mapping table (steps_per_bar → beats_per_bar):**

| steps_per_bar | beats_per_bar | Rationale |
|---|---|---|
| 4 | 4 | Standard 4-beat bar |
| 6 | 6 | 6/8 compound |
| 7 | 7 | 7/8 odd meter |
| 8 | 4 | 8-step = 2 groups of 4 |
| 10 | 10 | 10/8 as in Al-Khafeef |
| 12 | 4 | 12-step = 3 groups of 4 |
| 14 | 2 | 14-step Wafir = 2 beats |
| 21 | 3 | Sama'i = 7 bars of 3 |
| 32 | 8 | Warshan = 4 bars of 8 |

**Procedure:** For each record in the JSON array, read `steps_per_bar`, look up `beats_per_bar` from the table above, and add `"beats_per_bar": <value>` as a new field immediately after `"steps_per_bar"`. Do not change any other field.

**Verification:**
```python
import json, pathlib
data = json.loads(pathlib.Path('arabic_rhythm_data.json').read_text(encoding='utf-8'))
assert all('beats_per_bar' in r for r in data), "Missing beats_per_bar in some records"
print(f"All {len(data)} records have beats_per_bar. OK.")
```

**Stop condition:** If any record has a `steps_per_bar` value NOT in the mapping table, STOP and report to the human. Do not guess.

---

### Task 3.2 — Fix Al-Hazaj `steps_per_bar` in `BUHOOR` Dict
**File:** `buhor_prosody_drums/buhoor_drums.py`  
**Exact location:** The `BUHOOR["hazaj"]` dict definition.

**Find (exact block):**
```python
    "hazaj": {
        "arabic": "الهزج",
        "taf_eela": "مَفَاعِيلُنْ مَفَاعِيلُنْ",
        "transliteration": "mafa'eelun mafa'eelun",
        "syllable_pattern": "∪——— | ∪———",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 4,
```

**Replace `steps_per_bar` value only:**
```python
        "steps_per_bar": 8,
```

**Also update `syllable_pattern` to reflect both feet (cosmetic, for accuracy):**
```python
        "syllable_pattern": "∪——— | ∪———",
```
This is already correct (two feet shown). No change needed.

**Minimum change rule:** Change the single value `4` to `8` on the `steps_per_bar` line. Do not change `beats_per_bar` (stays at `4`), do not change any other field.

**Immediate verification:**
```python
from importlib import reload
import buhoor_drums
reload(buhoor_drums)
assert buhoor_drums.BUHOOR['hazaj']['steps_per_bar'] == 8
assert buhoor_drums.BUHOOR['hazaj']['beats_per_bar'] == 4
print("Hazaj steps_per_bar fix confirmed.")
```

---

### Task 3.3 — Replace Hardcoded if/elif with JSON-Driven `beats_per_bar`
**File:** `buhor_prosody_drums/buhoor_drums.py`  
**Exact location:** The dynamic registry loading block (marked `# DYNAMIC REGISTRY LOADING (Phase 3 & 4)`), specifically the `_beats` derivation if/elif chain.

**Find this exact block:**
```python
                            _beats = _rec.steps_per_bar
                            if _rec.steps_per_bar == 21:
                                _beats = 3
                            elif _rec.steps_per_bar == 10:
                                _beats = 10
                            elif _rec.steps_per_bar == 7:
                                _beats = 7
                            elif _rec.steps_per_bar == 6:
                                _beats = 6
                            elif _rec.steps_per_bar == 32:
                                _beats = 8
                            elif _rec.steps_per_bar == 8:
                                _beats = 4
                            elif _rec.steps_per_bar == 4:
                                _beats = 4
                            elif _rec.steps_per_bar == 12:
                                _beats = 4
                            elif _rec.steps_per_bar == 14:
                                _beats = 2
                            else:
                                _beats = BUHOOR[_slug]["beats_per_bar"]
```

**Replace with:**
```python
                            # beats_per_bar is now authoritative in the JSON record (Task 3.1).
                            # Fallback to BUHOOR dict only if the field is absent (legacy records).
                            _beats = getattr(_rec, 'beats_per_bar', None) or BUHOOR[_slug]["beats_per_bar"]
```

**Important:** `IqaaRecord` in `meter_registry.py` must also receive a `beats_per_bar` field. See Task 3.4 before running this.

**Dangerous zone:** Do not touch any code above or below this if/elif block. The `_new_variants.append(...)` call immediately following must remain unchanged.

---

### Task 3.4 — Add `beats_per_bar` Field to `IqaaRecord` Dataclass
**File:** `buhor_prosody_drums/meter_registry.py`  
**Exact location:** The `IqaaRecord` dataclass field definitions.

**Find the `steps_per_bar` field:**
```python
    steps_per_bar: int  # Step grid length
```

**Add the new field immediately after it:**
```python
    steps_per_bar: int  # Step grid length
    beats_per_bar: int  # Beats per bar (time signature numerator context)
```

**Also update `load_registry()`** — find the `IqaaRecord(...)` constructor call and add the new field:

**Find:**
```python
            steps_per_bar=int(row.get("steps_per_bar", 16)),
            instrument_context=row.get("instrument_context", ""),
```

**Replace with:**
```python
            steps_per_bar=int(row.get("steps_per_bar", 16)),
            beats_per_bar=int(row.get("beats_per_bar", 4)),
            instrument_context=row.get("instrument_context", ""),
```

**Minimum change rule:** One dataclass field added. One constructor argument added. Do not touch any other field or method.

---

### Task 3.5 — Add Al-Hazaj JSON Records (Two Iqaat)
**File:** `buhor_prosody_drums/arabic_rhythm_data.json`  
**Action:** Append two new records to the JSON array (before the closing `]`).

> **PS (Session 2, 2026-05-23):** The JSON already has 3 Hazaj records (malfuf/4,
> ayyub/4, wahda_saghira/4) — contrary to what the handover and A4 assumed. These
> are retained as-is. The two records below are genuinely new additions: one 8-step
> record (mudawwar_masri) which has no current equivalent, and one 4-step record
> (maqsum) which is also absent from the existing Hazaj entries. Proceed as written.

```json
  {
    "meter_ar": "الهزج",
    "iqaa": "Mudawwar Masri",
    "is_traditional": true,
    "mood_en": "Joyful, festive, light",
    "geographic_tradition": "Masri",
    "variant_slug": "mudawwar_masri",
    "default_bpm": 96,
    "bpm_range": [72, 132],
    "steps_per_bar": 8,
    "beats_per_bar": 4,
    "instrument_context": "doumbek solo",
    "performance_notes": "DUM on beat 1; tek on beat 5. Al-Hazaj's two مَفَاعِيلُنْ feet map cleanly onto the 8-beat frame; the festive character of the meter is served by a brisk, light touch on the tek strokes.",
    "syllable_pattern": "∪——— | ∪———",
    "corpus_pct": 2.0
  },
  {
    "meter_ar": "الهزج",
    "iqaa": "Maqsum",
    "is_traditional": true,
    "mood_en": "Joyful, festive, light",
    "geographic_tradition": "Pan-Arab",
    "variant_slug": "maqsum",
    "default_bpm": 108,
    "bpm_range": [84, 148],
    "steps_per_bar": 4,
    "beats_per_bar": 4,
    "instrument_context": "doumbek solo",
    "performance_notes": "DUM on beats 1 and 3; tek on 2 and 4. At this step count one Maqsum bar equals one مَفَاعِيلُنْ foot; Al-Hazaj's folk festive character is amplified by Maqsum's driving binary pulse.",
    "syllable_pattern": "∪——— | ∪———",
    "corpus_pct": 2.0
  }
```

**Note:** `("mudawwar_masri", 8)` and `("maqsum", 4)` patterns already exist in `IqaaPatternRegistry`. No new entries needed in `iqaa_patterns.py` for these.

**Verification:**
```python
import json, pathlib
data = json.loads(pathlib.Path('arabic_rhythm_data.json').read_text(encoding='utf-8'))
hazaj = [r for r in data if r['meter_ar'] == 'الهزج']
assert len(hazaj) == 2, f"Expected 2 hazaj records, got {len(hazaj)}"
print("Hazaj JSON records OK.")
```

---

**Phase 3 Gate:**
```python
# Full integration smoke test
import json, pathlib, sys
from buhoor_drums import BUHOOR

# Hazaj fix
assert BUHOOR['hazaj']['steps_per_bar'] == 8

# Hazaj has variants (loaded from JSON)
assert len(BUHOOR['hazaj']['variants']) >= 1, "Hazaj has no variants — JSON loader may have failed"

# beats_per_bar is correct for hazaj variants
for v in BUHOOR['hazaj']['variants']:
    assert 'beats_per_bar' in v, f"Variant {v['name']} missing beats_per_bar"

# validate_patterns still clean
from iqaa_patterns import validate_patterns
assert validate_patterns() == []

print("Phase 3 gate passed.")
```

```bash
# Render a hazaj loop to confirm audio is produced correctly
python buhoor_drums.py hazaj --duration 5 -o /tmp/hazaj_test -q
ls /tmp/hazaj_test/
# Expected: at least one .mp3 file present. Play it — it should loop at the correct speed.
```

**Do not proceed to Phase 4 if Phase 3 gate fails.** Rollback: `cp buhoor_drums.py.bak buhoor_drums.py && cp meter_registry.py.bak meter_registry.py && cp arabic_rhythm_data.json.bak arabic_rhythm_data.json` (Note: `meter_registry.py.bak` was not created in Phase 0. Add it to the rollback snapshot now if it was modified.)

---

## Phase 4 — Manifest Schema Enhancement
**Risk:** Low — adds a field to output only; no synthesis logic touched  
**Goal:** Record whether `--no-clamp` was used in every manifest entry.  
**Dependency:** Phase 3 gate passed.

### Task 4.1 — Add `no_clamp` to Manifest Entry Builder
**File:** `buhor_prosody_drums/buhoor_drums.py`  
**Exact location:** The `generate_bahr()` function, the `manifest_entry` dict construction.

**Find:**
```python
        manifest_entry = {
            "filename": os.path.basename(path),
            "meter_ar": bahr["arabic"],
            "iqaa": variant["label"],
            "is_traditional": variant.get("is_traditional", True),
            "bpm": effective_bpm,
            "bpm_range": variant.get("bpm_range", [0, 300]),
            "steps_per_bar": steps_per_bar,
            "geographic_tradition": variant.get("geographic_tradition", "Pan-Arab"),
            "instrument_context": variant.get("instrument_context", ""),
            "performance_notes": variant.get("why", ""),
        }
```

**Replace with:**
```python
        manifest_entry = {
            "filename": os.path.basename(path),
            "meter_ar": bahr["arabic"],
            "iqaa": variant["label"],
            "is_traditional": variant.get("is_traditional", True),
            "bpm": effective_bpm,
            "bpm_range": variant.get("bpm_range", [0, 300]),
            "no_clamp": no_clamp,
            "steps_per_bar": steps_per_bar,
            "geographic_tradition": variant.get("geographic_tradition", "Pan-Arab"),
            "instrument_context": variant.get("instrument_context", ""),
            "performance_notes": variant.get("why", ""),
        }
```

**Minimum change rule:** One new key-value pair (`"no_clamp": no_clamp`) inserted. The `no_clamp` variable is already in scope in `generate_bahr()` via its function signature. Confirm this before proceeding.

**Also:** `no_clamp` must be passed through from `main()` → `generate_bahr()`. Check that the function call in `main()` already passes `no_clamp=no_clamp`. If it does, no change needed there.

**Success criteria:**
```bash
python buhoor_drums.py hazaj --duration 3 -o /tmp/manifest_test -q
python -c "
import json
m = json.load(open('/tmp/manifest_test/manifest.json'))
for f in m['files']:
    assert 'no_clamp' in f, 'no_clamp missing from entry'
    assert isinstance(f['no_clamp'], bool)
print('manifest.json schema OK:', m['files'][0]['no_clamp'])
"
```

---

**Phase 4 Gate:** Run the success criteria block above. Inspect one manifest entry and confirm `"no_clamp": false` is present. **Do not proceed to Phase 5 if absent.**

---

## Phase 5 — Web App: Per-Meter BPM Defaults
**Risk:** Low — JavaScript data structure change; no synthesis or DOM logic touched  
**Goal:** Give each meter a `defaultBpm` so the app starts at a culturally appropriate tempo.  
**Dependency:** Phase 4 gate passed (or this phase can run independently in parallel if desired).

### Task 5.1 — Extend `BAHUR` with `defaultBpm` Values
**File:** `arabic-poetry-drum-machine/src/index.html`  
**Exact location:** The `BAHUR` constant definition in the `<script>` block.

The `BAHUR` object currently maps meter name → array of foot strings. Convert it to map meter name → object with `feet` and `defaultBpm` keys.

**Current format:**
```javascript
const BAHUR = {
  'الطَّوِيل': ['فَعُولُنْ','مَفَاعِيلُنْ','فَعُولُنْ','مَفَاعِلُنْ'],
  // ...
};
```

**New format:**
```javascript
const BAHUR = {
  'الطَّوِيل':     { feet: ['فَعُولُنْ','مَفَاعِيلُنْ','فَعُولُنْ','مَفَاعِلُنْ'],  defaultBpm: 80  },
  'الْمَدِيد':    { feet: ['فَاعِلَاتُنْ','فَاعِلُنْ','فَاعِلَاتُنْ'],              defaultBpm: 88  },
  'الْبَسِيط':    { feet: ['مُسْتَفْعِلُنْ','فَاعِلُنْ','مُسْتَفْعِلُنْ','فَاعِلُنْ'], defaultBpm: 96  },
  'الْوَافِر':    { feet: ['مَفَاعَلَتُنْ','مَفَاعَلَتُنْ','فَعُولُنْ'],              defaultBpm: 84  },
  'الْكَامِل':    { feet: ['مُتَفَاعِلُنْ','مُتَفَاعِلُنْ','مُتَفَاعِلُنْ'],          defaultBpm: 96  },
  'الْهَزَج':     { feet: ['مَفَاعِيلُنْ','مَفَاعِيلُنْ'],                           defaultBpm: 104 },
  'الرَّجَز':     { feet: ['مُسْتَفْعِلُنْ','مُسْتَفْعِلُنْ','مُسْتَفْعِلُنْ'],      defaultBpm: 96  },
  'الرَّمَل':     { feet: ['فَاعِلَاتُنْ','فَاعِلَاتُنْ','فَاعِلَاتُنْ'],            defaultBpm: 88  },
  'السَّرِيع':    { feet: ['مُسْتَفْعِلُنْ','مُسْتَفْعِلُنْ','فَاعِلُنْ'],           defaultBpm: 108 },
  'الْمُنْسَرِح': { feet: ['مُسْتَفْعِلُنْ','مَفْعُولَاتُ','مُسْتَفْعِلُنْ'],        defaultBpm: 96  },
  'الْخَفِيف':   { feet: ['فَاعِلَاتُنْ','مُسْتَفْعِلُنْ','فَاعِلَاتُنْ'],          defaultBpm: 72  },
  'الْمُضَارِع':  { feet: ['مَفَاعِيلُنْ','فَاعِلَاتُنْ'],                           defaultBpm: 88  },
  'الْمُقْتَضَب': { feet: ['مَفْعُولَاتُ','مُسْتَفْعِلُنْ'],                         defaultBpm: 100 },
  'الْمُجْتَثّ':  { feet: ['مُسْتَفْعِلُنْ','فَاعِلَاتُنْ'],                         defaultBpm: 96  },
  'الْمُتَقَارِب':{ feet: ['فَعُولُنْ','فَعُولُنْ','فَعُولُنْ','فَعُولُنْ'],          defaultBpm: 88  },
  'الْمُتَدَارَك':{ feet: ['فَاعِلُنْ','فَاعِلُنْ','فَاعِلُنْ','فَاعِلُنْ'],          defaultBpm: 112 },
};
```

### Task 5.2 — Update All Code That References `BAHUR[b]` as an Array

Because `BAHUR[b]` now returns an object instead of an array, every reference must be updated to use `.feet`. There are exactly **4** locations:

**Location 1 — `buildPat()` function:**
```javascript
// FIND:
function buildPat(bahr) {
  const feet = BAHUR[bahr], bits = [], meta = [], bnd = new Set();

// REPLACE:
function buildPat(bahr) {
  const feet = BAHUR[bahr].feet, bits = [], meta = [], bnd = new Set();
```

**Location 2 — Bahr selector button render (in `render()`):**
```javascript
// FIND:
        Object.keys(BAHUR).forEach(b => {
          html += `<button ... onclick="setBahr('${b}')">${b}</button>`;
        });

// No change needed here — only key iteration, not value access.
```

**Location 3 — Step count display label:**
```javascript
// FIND:
          <span style="font-size:11px;...">${p.len} steps · ${BAHUR[bahr].length} feet</span>

// REPLACE:
          <span style="font-size:11px;...">${p.len} steps · ${BAHUR[bahr].feet.length} feet</span>
```

**Location 4 — Default BPM initialization:**
```javascript
// FIND:
      let bahr = 'الطَّوِيل', bpm = 120, playing = false, step = -1;

// REPLACE:
      let bahr = 'الطَّوِيل', bpm = BAHUR['الطَّوِيل'].defaultBpm, playing = false, step = -1;
```

**Location 5 — `setBahr()` function — update BPM when meter changes:**
```javascript
// FIND:
      function setBahr(b) {
        if (playing) stopPlay();
        bahr = b;
        step = -1;
        render();
      }

// REPLACE:
      function setBahr(b) {
        if (playing) stopPlay();
        bahr = b;
        bpm = BAHUR[b].defaultBpm;
        step = -1;
        render();
      }
```

**Minimum change rule:** Only the five locations above. No other JavaScript logic changes.

**Dangerous zone:** Do not change `T{}`, `CLR{}`, `initInst()`, `startPlay()`, `stopPlay()`, or any CSS.

**Success criteria:**
- Open `index.html` in browser. No console errors.
- Selecting "الطويل" shows BPM slider at 80.
- Selecting "الخفيف" shows BPM slider at 72.
- Selecting "الهزج" shows BPM slider at 104.
- Play button starts audio for each meter.
- "X feet" count in controls still shows correctly.

**Stop condition:** If any console error appears, STOP. Roll back `index.html` from `.bak`.

---

**Phase 5 Gate:** Open the browser. Cycle through at least 5 meters using the selector buttons. Confirm the BPM slider updates on each selection. Confirm play/stop works for each. **Do not proceed to Phase 6 if any meter fails to update BPM or play audio.**

---

## Phase 6 — Session Handover Document
**Risk:** None  
**Goal:** Produce a handover document so the next session can pick up exactly where this one left off.  
**Dependency:** All prior gates passed. Generate regardless of phase completion status — capture current state accurately.

### Task 6.1 — Generate `Session_Handover.md`

Create `DEV/session_summaries/Session_Remediation_1_Handover.md` in the Python project with the following template filled in:

```markdown
# Session Handover — Audit Remediation Session 1
**Date:** [DATE]
**Plan reference:** Phased_Plan_Audit_Remediation.md
**Status at session end:** [COMPLETE / PARTIAL — stopped at Phase X]

## What Was Done
- [ ] Phase 0: Rollback snapshots created
- [ ] Phase 1: Documentation fixes (README, philosophy sections, ziHaf notice)
- [ ] Phase 2: Data layer fixes (slug renames, duplicate JSON deleted, phantom test removed)
- [ ] Phase 3: Al-Hazaj structural fix + beats_per_bar data-driven
- [ ] Phase 4: Manifest schema (no_clamp field)
- [ ] Phase 5: Web app per-meter BPM defaults

## Files Modified
| File | Change |
|---|---|
| buhor_prosody_drums/README.md | Meter count, script name, Design Philosophy section |
| buhor_prosody_drums/buhoor_drums.py | Al-Hazaj steps_per_bar, manifest schema, beats_per_bar loader, Al-Wafir diacritics |
| buhor_prosody_drums/iqaa_patterns.py | Slug renames (fallahy→fallahi, samaai_darij→legacy) |
| buhor_prosody_drums/meter_registry.py | IqaaRecord.beats_per_bar field added |
| buhor_prosody_drums/arabic_rhythm_data.json | beats_per_bar field added to all records; 2 Hazaj records added |
| buhor_prosody_drums/smoke_test_renders.py | Renamed from audit_phase2.py; phantom test commented out (Task 2.3); internal label updated (Task 2.4) |
| buhor_prosody_drums/DATA/ | arabic_rhythm_data.json deleted |
| arabic-poetry-drum-machine/src/index.html | BAHUR restructured, defaultBpm added, ziHaf notice, design philosophy note |

## Current Status
[Describe exactly which tasks completed and which did not]

## Known Issues / Remaining Gaps
[List anything that could not be completed or was discovered during implementation]

## Exact First Step for Next Session
[State the precise task (e.g., "Begin Phase 3, Task 3.5 — add hazaj JSON records")]

## Rollback Baseline Checksums
[Paste the MD5 checksums from Task 0.1 here]
```

---

## 4. Strict Scope Boundaries

### In Scope (This Plan Only)
- Bug fixes listed in audit Recommendations R1–R14
- Two Al-Hazaj JSON records (minimum to make the meter renderable)
- Per-meter `defaultBpm` values (web app)
- Documentation additions to both READMEs

### Out of Scope — Do Not Implement, Do Not Scaffold
- Adding Al-Munsarih (المنسرح) or any other new meter to the Python engine
- Adding ziHaf/ʿilal fuzzy matching to the web app
- Integrating `40_IMMORTAL_ARABIC_POEMS.pkl` with either project
- Adding the web app's `T{}` foot table to the Python engine as a pattern source
- Any UI redesign or visual enhancement to either project beyond the specified text additions
- Adding more than 2 Al-Hazaj iqaa entries (a full complement can be done in a future session)
- Changing any drum synthesis parameters (`synth_kick`, `synth_snare`, etc.)
- Changing any Tone.js instrument parameters (`MembraneSynth`, `NoiseSynth`, `MetalSynth`)
- Changing or adding any CLI options to `buhoor_drums.py`
- Modifying `outputs/buhoor/manifest.json` directly (it is a generated artifact, not a source file)

---

## 5. Stop Conditions (Global)

If any of the following occur at any point, **STOP ALL CODING** and report to the human:

1. `validate_patterns()` returns any non-empty list after a change to `iqaa_patterns.py`
2. `python buhoor_drums.py --validate` produces a Python traceback (gaps are OK, exceptions are not)
3. The browser console shows any JavaScript error in `index.html` after any change
4. The hash check in Task 2.2 shows the two JSON files are DIFFERENT
5. Any assumption check from §2.3 fails in an unexpected direction (i.e., the "bug" was already fixed)
6. A `cp` or `rm` command fails
7. Any rendered MP3 file from the hazaj Phase 3 gate test is zero bytes or unplayable
8. You find yourself modifying a file not listed in this plan's scope

---

*End of plan. Total phases: 6 (0–5) + handover. Estimated sessions: 1–2.*
