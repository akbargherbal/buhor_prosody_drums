# بحور الشعر — Developer Fix Plan
### `buhoor_drums.py` · Arabic Poetic Meters Drum Generator

> **Governing principle:** Suno-perceptibility beats musicological purity. A drum loop that sounds Arabic and correctly conditions Suno is a success. A theoretically correct pattern that steers Suno toward Western output is a failure.

---

## Expert Verdict Summary

| ID | Verdict | Severity | Scope |
|----|---------|----------|-------|
| A1 | ❌ WRONG | 🔴 FATAL | Al-Baseet — Masmoudi Kabir triple DUM |
| A2 | ❌ WRONG | 🟠 SIGNIFICANT | Al-Taweel — Maqsum pairing non-traditional |
| A3 | ✅ VALID | ⚪ COSMETIC | All meters — corpus statistics correct |
| B1 | ❌ WRONG | 🔴 FATAL | Al-Kamil + Al-Wafir — 3/4 vs 6/8 collapse |
| B2 | ❌ WRONG | 🔴 FATAL | Al-Wafir — double-short (∪∪) absent in grid |
| B3 | ❌ WRONG | 🔴 FATAL | Al-Kamil — Samaai Darij unrecognizable |
| C1 | ❌ WRONG | 🔴 FATAL | All meters — snare is Western TR-808 model |
| C2 | ❌ WRONG | 🔴 FATAL | All meters — kick is 808 sub-bass model |
| C3 | ❌ WRONG | 🟠 SIGNIFICANT | All meters — humanization is random, not stylistic |

> ⚠️ **CRITICAL — The timbre dependency.** Expert C established a hard dependency that overrides all sequencing logic: Suno uses timbre as its primary genre-classification signal. If the kick and snare sound like a TR-808, Suno will generate Western music regardless of how accurate the rhythmic patterns are. **Fix the timbres first. Test on Suno. Only then is Suno feedback meaningful for validating patterns.**

---

## Action Plan

### Action 1 — Replace kick and snare with Arabic doumbek / tabla models
**Priority:** CRITICAL — do this before any pattern work  
**Resolves:** C1, C2

**Why:** The current 808 kick (150 Hz→50 Hz sweep, 500 ms) and TR-808 snare (200 Hz sine body) cause Suno to generate Western pop, hip-hop, or rock regardless of rhythmic correctness. This is the precondition for all Suno testing.

**Steps:**

1. Replace `synth_kick()` entirely. New model: 240 Hz fundamental, log sweep to 200 Hz (not 50 Hz), duration reduced to 0.25 s. Add a bandpass shell layer: `butter(2, [400, 800], btype='bandpass')` filtered white noise × 0.3 amplitude, decaying over 0.15 s.

```python
def synth_kick(duration: float = 0.25) -> np.ndarray:
    n     = int(SAMPLE_RATE * duration)
    t     = np.linspace(0, duration, n)
    f     = 240.0 * np.exp(np.log(200.0 / 240.0) * t / duration)
    ph    = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
    body  = np.sin(ph) * _envelope(duration, 0.002, 0.8)
    noise = np.random.uniform(-1, 1, n)
    sos   = butter(2, [400, 800], btype='bandpass', fs=SAMPLE_RATE, output='sos')
    shell = sosfilt(sos, noise) * _envelope(duration, 0.001, 1.5) * 0.3
    return ((body + shell) * 0.9).astype(np.float32)
```

2. Replace `synth_snare()` entirely. Eliminate the 200 Hz sine body. Substitute a 3200 Hz ring tone blended with highpass-filtered noise at 2500 Hz. Relative mix: ring × 0.4, snap × 0.6.

```python
def synth_snare(duration: float = 0.15) -> np.ndarray:
    n     = int(SAMPLE_RATE * duration)
    t     = np.linspace(0, duration, n)
    ring  = np.sin(2 * np.pi * 3200 * t) * _envelope(duration, 0.001, 2.0) * 0.4
    noise = np.random.uniform(-1, 1, n)
    sos   = butter(2, 2500, btype='highpass', fs=SAMPLE_RATE, output='sos')
    snap  = sosfilt(sos, noise) * _envelope(duration, 0.001, 3.0) * 0.6
    return ((ring + snap) * 0.85).astype(np.float32)
```

3. In `synth_hihat()`: lower the Butterworth high-pass cutoff from `7000` Hz to `5000` Hz. Riq jingles have more body than Western cymbals. All other parameters unchanged.

4. In `render_variant()`: update the panning dict — hihat from `0.75` to `0.60`; crash from `0.25` to `0.40`. Kick and snare are already centred at `0.50` — leave them.

```python
panning = {
    "kick" : _cpan(0.50),  # centre
    "snare": _cpan(0.50),  # centre
    "hihat": _cpan(0.60),  # mild right (was 0.75)
    "crash": _cpan(0.40),  # mild left  (was 0.25)
}
```

5. Render a test loop: `python buhoor_drums.py taweel -v wahda -d 10 -q`. Confirm no errors.

6. Upload the rendered `wahda` MP3 to Suno with **no text prompt**.

**✅ Done when:** Suno generates music with audible Arabic character — oud, riq, maqam-flavored melody — from a no-prompt upload of the wahda variant. No guitar, Western bass, or trap hi-hats.

---

### Action 2 — Rebuild all binary patterns using mora-based grid sizing
**Priority:** HIGH — begin after Action 1 Suno test passes  
**Resolves:** A1, B1, B2, B3 — and the systemic encoding failure across all four meters

**Why:** Expert B's IOI analysis shows every pattern in the script produces IOI sequences that do not match the prosodic feet they claim to represent. The root cause is confusing onset placement with duration encoding. The fix: adopt a mora grid where **1 step = 1 mora (∪)** and **2 steps = 1 long (—)**. This forces grid size changes for three of the four meters.

#### Mora grid reference

| Meter | Foot | New `steps_per_bar` | Target IOI sequence |
|-------|------|---------------------|---------------------|
| Al-Taweel | ∪—— \| ∪——— | **12** (was 16) | `1, 2, 2, 1, 2, 2, 2` |
| Al-Baseet | ——∪— \| —∪— | **12** (was 16) | `2, 2, 1, 2, 2, 1, 2` |
| Al-Kamil | ∪∪—∪— × 3 | **21** (was 12) | `1, 1, 2, 1, 2` per foot × 3 |
| Al-Wafir | ∪—∪∪— × 2 | **14** (was 12) | `1, 2, 1, 1, 2` per foot × 2 |

**Steps:**

1. **Al-Taweel:** Change `steps_per_bar` from `16` to `12`. Rebuild kick pattern to IOI `1,2,2,1,2,2,2`. Example kick array: `[1,1,0,1,0, 1,1,0,1,0,1,0]`. Rebuild snare, hihat, crash arrays to complement.

2. **Al-Baseet:** Change `steps_per_bar` from `16` to `12`. Replace the triple-kick Masmoudi Kabir with the authentic two-DUM structure (Expert A: `[DUM . DUM . . . TEK . DUM . . .]`). Example: `kick [1,0,1,0,0,0, 0,0,1,0,0,0]`, `snare [0,0,0,0,0,0,1,0,0,0,1,0]`. This resolves both A1 and the encoding failure.

3. **Al-Kamil:** Change `steps_per_bar` to `21`. Move the Samaai Darij DUM to step index `0` (not index `2`). Pattern rationale: `∪∪—` = steps 0,1,2 where step 0 is the DUM onset.

4. **Al-Wafir:** Change `steps_per_bar` to `14`. Rebuild the hihat so the `∪∪` pair produces IOIs of `1-1` (two adjacent single-step onsets). The current IOI of `1-2` reads as long (—), which is wrong. Kick should anchor the `—` positions at steps 1 and 8.

5. For every rebuilt pattern: add the IOI sequence as a comment directly above the pattern array. Example:
```python
# IOI: 1, 2, 2, 1, 2, 2, 2  →  ∪ — — | ∪ — — —  (fa'oolun mafa'eelun)
"kick": [1,1,0,1,0, 1,1,0,1,0,1,0],
```

6. Re-render all variants: `python buhoor_drums.py all -d 10 -q`. Upload one file per meter to Suno and confirm Arabic-character output persists across all four.

**✅ Done when:** IOI sequences for all rebuilt patterns match their stated prosodic feet. All four meters render without errors. Suno output for each meter retains the Arabic character established in Action 1.

---

### Action 3 — Demote Maqsum as primary variant for Al-Taweel
**Priority:** MEDIUM — implement alongside or immediately after Action 2  
**Resolves:** A2

**Why:** Expert A confirmed Maqsum is a non-traditional pairing not found in Egyptian tarab or Levantine maqam practice. The `wahda` variant (already in the script) is the canonical choice. This is a reordering and labeling fix — no pattern changes required.

**Steps:**

1. In the `"taweel"` entry of `BUHOOR`, reorder `variants` so that `"wahda"` appears at index 0, before `"maqsum"`.

2. In the `"maqsum"` variant dict, update the `"why"` field:
```python
"why": (
    "NON-TRADITIONAL PAIRING. Maqsum does not appear in classical Egyptian tarab "
    "or Levantine maqam settings of Al-Taweel. Included as an experimental variant. "
    "Prefer Wahda for Suno conditioning."
),
```

3. Update the bahr `"description"` string to name Wahda as the primary cycle, with Maqsum listed as secondary/experimental.

**✅ Done when:** `"wahda"` is the first variant in the taweel list. The `"maqsum"` variant carries the non-traditional warning in its `why` field.

---

### Action 4 — Replace uniform humanization with instrument-hierarchical dynamics
**Priority:** MEDIUM — implement after Actions 1–3 are validated  
**Resolves:** C3

**Why:** The current `humanize()` applies identical ±12% velocity variance to all four instruments. In Arabic percussion, DUM strokes are the structural anchor; ghost strokes (TEK, KA) are consistently 40–60% quieter. Uniform variance produces instability, not expressiveness.

**Steps:**

1. Add a per-channel base velocity dict in `render_variant()`:
```python
BASE_VELOCITY = {
    "kick" : 1.00,
    "snare": 0.50,
    "hihat": 0.45,
    "crash": 0.70,
}
```

2. Modify `humanize()` to accept a `base_velocity` parameter (default `1.0`). Update the velocity formula:
```python
def humanize(pattern, timing_jitter=0.007, velocity_variance=0.12, base_velocity=1.0):
    hits = []
    for i, hit in enumerate(pattern):
        if hit:
            t_off = random.uniform(-timing_jitter, timing_jitter)
            vel   = base_velocity + random.uniform(-velocity_variance, velocity_variance)
            vel   = max(0.2, min(1.4, vel))
            hits.append((i, t_off, vel))
    return hits
```

3. Pass `base_velocity=BASE_VELOCITY[channel]` when calling `humanize()` for each channel in `render_variant()`.

4. In non-quiet mode, print peak velocity per channel after each variant renders for easy verification.

**✅ Done when:** Kick channel peaks read 90–100%. Snare and hihat channels read 40–60%. Loops sound balanced and organic.

---

## Deferred Items

| ID | Status | Reason |
|----|--------|--------|
| A3 | Deferred permanently | Expert A confirmed corpus statistics are correct and defensible. No action required. |
| B1 (formula) | Deferred | The `step_s` formula is arithmetically correct. The perceptual collapse it exposes is resolved by Action 2 grid rebuilds. The formula itself does not change. |
| Crash / duff timbre | Deferred — post-Suno validation | Expert C flags the 4 kHz crash as a category mismatch if intended as a duff frame drum (300–600 Hz). The crash is low-usage in current patterns (bar 1 only). Revisit after Action 1 is validated. |

---

## Execution Sequence

This is a **gated sequential model**, not a parallelisable checklist.

```
STEP 1  Code Action 1
        Replace synth_kick(), synth_snare(), synth_hihat() cutoff, and panning.

STEP 2  ⛩ SUNO GATE
        Render wahda variant. Upload to Suno with no text prompt.
        → Arabic output? Proceed to Step 3.
        → Western output? Debug timbres. Do not proceed until gate passes.

STEP 3  Code Action 2
        Mora-based pattern rebuild for all four meters.
        Verify IOI sequences in comments. Render all variants.
        Suno-test one loop per meter.

STEP 4  Code Actions 3 and 4
        These are independent of each other and can be done in either order.
```

---

## A Note on Verification

This codebase spans three knowledge domains that cannot be verified by code review alone. The acceptance conditions above are the minimum bar. The authoritative verification is always human listening — a person with Arabic rhythmic literacy hearing each output and confirming it sounds like the named iqa'.

> The script's 3-out-of-5 success rate came from the gap between writing patterns and listening to them. The mora-grid rebuild (Action 2) closes the encoding gap. The Suno gate (after Action 1) closes the verification gap. Both are required.

---

*— End of Developer Fix Plan —*
