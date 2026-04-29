# Domain expert tasks for extending `arabic_rhythm_data.json`

Two-column layout showing required expert skills and tasks grouped by low vs medium effort, with direct mapping to Python script fields.

---

## 🧠 Required Domain Expert Skills

- **ʿArūḍ scholar**
  _Classical prosody_

- **Practicing musician**
  _Arabic maqam + iqaa_

- **Doumbek / tabla player**
  _Hands-on iqaa patterns_

> Most tasks need the first two; tasks 5–6 benefit from all three together.

---

## 🟢 Low Effort

_Tacit knowledge — no lookup needed (~5–15 min per row)_

### 1. Add `is_traditional` (boolean)

- True/false per row
- Currently buried in prose ("NON-TRADITIONAL PAIRING")
- Formalizing enables automatic warnings

**Unlocks:** `variant["why"]` auto-flag
**Who:** ʿArūḍ scholar + musician

---

### 2. Add `mood_en` (English mood label)

- Translate Arabic character arrays into short phrases
- Example: _"Epic, spacious, dignified"_
- Useful for prompt generation

**Unlocks:** `variant["mood"]`
**Who:** musician

---

### 3. Add `geographic_tradition` (tag)

- Values: `"Masri"`, `"Shami"`, `"Andalusi"`, `"Gulf"`, `"Maghrebi"`
- Often implied by iqaa name

**Unlocks:** CLI `--region` filter
**Who:** musician + regional expert

---

### 4. Add `variant_slug` (ASCII CLI name)

- Example: `sama3i_darij`, `wahda_kabira`
- Derived from existing iqaa field

**Unlocks:** `variant["name"]`, output filenames
**Who:** any expert

---

### 5. Add `syllable_pattern` (to بحر master rows)

- Mora notation (∪——) exists in script but not JSON
- Copy from classical references

**Unlocks:**

- `bahr["syllable_pattern"]`
- `steps_per_bar` derivation

**Who:** ʿArūḍ scholar

---

## 🟠 Medium Effort

_Musical judgment required (~15–30 min per row)_

### 6. Add `default_bpm` + `bpm_range`

- Example: `92`, `[72, 116]`
- Based on canonical tempo expectations

**Unlocks:**

- `variant["bpm"]`
- BPM validation

**Who:** musician

---

### 7. Add `steps_per_bar` (mora grid size)

- Examples:
  - الطويل (4/4) → 12
  - الكامل (3/4) → 21
  - الوافر (6/8) → 14

- Mostly mechanical, some require judgment

**Unlocks:**

- `bahr["steps_per_bar"]` (core timing engine)

**Who:** musician

---

### 8. Add `instrument_context` (tag)

- Examples:
  - `"doumbek solo"`
  - `"tabl + riq"`
  - `"firqa"`

- Guides sound weighting

**Unlocks:**

- `BASE_VELOCITY` per channel

**Who:** doumbek player + musician

---

### 9. Add `corpus_pct` (to بحر master rows)

- Example:
  - الطويل ≈ 35%
  - الكامل ≈ 18%

- From classical corpus statistics

**Unlocks:**

- CLI sorting (`--list`)
- Documentation

**Who:** ʿArūḍ scholar

---

### 10. Add `performance_notes` (1–2 sentences)

- Covers:
  - DUM placement
  - Ornamentation (ziyāda)
  - Tempo behavior

**Unlocks:**

- `variant["why"]`
- Description / prompt generation

**Who:** doumbek player + musician
