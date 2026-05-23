# Phased Implementation Plan: Tone.js Synthesis Layer
## *Buhoor Arabic Poetic Meter Drum Generator*

**Plan type:** Investigation spike with shippable increments
**Risk posture:** Validate before committing. Every phase is independently revertable.
**Executing agent:** Read this document in full before writing a single line of code.

---

## 1. Executive Summary & Locked Decisions

### 1.1 Current State vs. Goal

| | Current State | Goal of This Plan |
|---|---|---|
| **Synthesis** | `numpy` + `scipy` Butterworth filters in `buhoor_drums.py` | Tone.js FM synthesis (`MembraneSynth`, `MetalSynth`, `NoiseSynth`) called via Playwright |
| **Export** | `pydub` + `ffmpeg` → MP3 with ID3 tags | Unchanged — `pydub` + `ffmpeg` + ID3 tags remain |
| **CLI** | `buhoor_drums_v2.py` with all flags | Unchanged |
| **Metadata** | `arabic_rhythm_data.json`, `manifest.json` | Unchanged |
| **Meter scope** | 13 meters, 44 variants | **Al-Taweel and Al-Kamil only for this plan** |
| **Instrument scope** | kick, snare, ka, hihat, crash | **kick, snare, hihat in Phase 1–3; ka and crash in Phase 2** |

### 1.2 Locked Decisions

The following are **closed for debate**. Do not re-litigate, re-architect, or propose
alternatives to any item in this table.

| # | Decision | Rationale |
|---|---|---|
| L1 | Python remains the primary runtime and orchestrator | Non-negotiable project constraint |
| L2 | Tone.js is a rendering subprocess called from Python via Playwright | The only integration path consistent with L1 |
| L3 | `pydub` + `ffmpeg` continue to handle MP3 encoding and ID3 tagging | The ID3 pipeline is correct and must not be touched |
| L4 | `arabic_rhythm_data.json` is not modified | It is the authoritative metadata source and is shared across components |
| L5 | `humanize()` in `buhoor_drums.py` continues to compute jitter and velocity | Python owns humanisation; Tone.js receives a pre-computed hit schedule |
| L6 | The new synthesis path is gated behind a `--tonejs` CLI flag | Allows A/B comparison; does not break existing behaviour |
| L7 | `manifest.json` and all ID3 tags are written by Python as before | No metadata capability is lost |
| L8 | `SAMPLE_RATE = 44100` is not changed | All downstream consumers depend on this constant |
| L9 | The IPC contract is: Python → JSON hit schedule → Tone.js → base64 WAV bytes → Python | Established in Phase 1; all later phases depend on it |

---

## 2. Pre-Coding Checklist & Baseline Assumptions

**Execute every item in this section before touching any code. Do not proceed to Phase 1
if any item fails.**

### 2.1 Verify the Current Stack is Green

```bash
# Run a single-variant render on Al-Taweel to confirm the stack is healthy
python buhoor_drums_v2.py taweel -v wahda_kabira --bpm 80

# Expected: one MP3 file written to the output directory, no errors
# STOP if: any import error, ffmpeg error, or no file produced
```

### 2.2 Install and Verify Playwright

```bash
pip install playwright
playwright install chromium

# Smoke test — must print browser version string and exit cleanly
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('about:blank')
    print('Playwright OK:', browser.version)
    browser.close()
"

# STOP if: ImportError, chromium download fails, or smoke test raises any exception
```

### 2.3 Confirm Target Functions Exist

```bash
python -c "
from buhoor_drums import render_variant, humanize, SYNTH_MAP, BUHOOR, SAMPLE_RATE
assert 'taweel' in BUHOOR
assert 'kamil' in BUHOOR
assert all(k in SYNTH_MAP for k in ['kick', 'snare', 'hihat', 'ka', 'crash'])
assert SAMPLE_RATE == 44100
print('All assertions passed.')
"

# STOP if: any AssertionError or ImportError
```

### 2.4 Note the Surgical Replacement Target

The block to be replaced in `buhoor_drums.py` begins at this line:

```python
sounds = {name: fn() for name, fn in SYNTH_MAP.items()}
```

And ends before:

```python
wavfile.write(wav_p, SAMPLE_RATE, pcm)
```

Everything before and after this block — including `humanize()`, `wavfile.write()`,
`AudioSegment.from_wav()`, and `audio.export()` with ID3 tags — **is not touched**.

---

## 3. Phase 1 — Prove the Core Contract

**Objective:** Establish that Python can pass a hit schedule to Tone.js via Playwright and
receive back valid WAV bytes. This is the highest-risk unknown. Nothing else is built
until this is proven.

**Scope:** Kick drum only. Al-Taweel pattern only. No humanisation. No CLI integration.

**New files created in this phase:**
- `tonejs_renderer.html` (Tone.js rendering page)
- `tonejs_bridge.py` (Python ↔ Playwright interface)
- `test_phase1.py` (validation script)

**Files touched:** None in the existing codebase.

---

### Task 1.1 — Create `tonejs_renderer.html`

Create a new file `tonejs_renderer.html` in the project root. It must do exactly the
following and nothing else:

1. Load Tone.js from CDN (pin to a specific version — do not use `@latest`).
2. Expose a single global async function `window.renderPattern(jsonString)`.
3. Inside `renderPattern`:
   - Parse `jsonString` as a JSON array of hit objects: `[{inst, time_s, velocity}]`
   - Call `Tone.Offline()` for the duration derived from the last hit's `time_s` + 0.5 s
   - Instantiate exactly these three synths inside the offline context:
     ```
     kick  → Tone.MembraneSynth  { pitchDecay: 0.07, octaves: 5,
                                    envelope: { attack: 0.001, decay: 0.35,
                                                sustain: 0, release: 0.5 } }
     snare → Tone.NoiseSynth     { noise: { type: 'white' },
                                    envelope: { attack: 0.001, decay: 0.16,
                                                sustain: 0, release: 0.1 } }
     hihat → Tone.MetalSynth     { frequency: 700, envelope: { attack: 0.001,
                                    decay: 0.04, sustain: 0, release: 0.04 },
                                    harmonicity: 5.1, modulationIndex: 32,
                                    resonance: 4000, octaves: 1.5 }
     ```
   - For each hit object, schedule `triggerAttackRelease` at `hit.time_s` with
     `hit.velocity` as the velocity argument.
   - After `Tone.Offline()` resolves, convert the returned `ToneAudioBuffer` to a
     stereo interleaved WAV (44100 Hz, 16-bit, standard RIFF header).
   - Return the WAV as a base64-encoded string.
4. The page must have no visible UI, no CSS, no additional scripts.

**Do not add:** reverb, compression, effects chains, additional instruments, UI elements,
or any logic not listed above. The page is a headless renderer — not an application.

**Verification (do not proceed to Task 1.2 until this passes):**

Open `tonejs_renderer.html` in a browser console and run:

```javascript
const b64 = await window.renderPattern(
  JSON.stringify([{inst: 'kick', time_s: 0.0, velocity: 1.0},
                  {inst: 'kick', time_s: 0.5, velocity: 1.0}])
);
console.log(b64.slice(0, 20));  // Must print a non-empty base64 string
```

**STOP if:** `renderPattern` is undefined, throws, or returns an empty string.

---

### Task 1.2 — Create `tonejs_bridge.py`

Create a new file `tonejs_bridge.py` in the project root. It must expose exactly one
public function:

```python
def render_to_wav_bytes(hit_schedule: list[dict], html_path: str) -> bytes:
    """
    Launches a headless Chromium, loads html_path, calls window.renderPattern()
    with hit_schedule serialised as JSON, and returns the decoded WAV bytes.

    hit_schedule: list of {inst: str, time_s: float, velocity: float}
    html_path:    absolute path to tonejs_renderer.html
    Returns:      raw WAV bytes (RIFF, 44100 Hz, stereo, 16-bit)
    """
```

Implementation constraints:
- Use `playwright.sync_api.sync_playwright` — not the async API.
- Pass `html_path` as a `file://` URI.
- Serialise `hit_schedule` with `json.dumps`.
- Call `page.evaluate("(json) => window.renderPattern(json)", json_string)`.
- Decode the returned base64 string with `base64.b64decode`.
- Return raw bytes. Do not write to disk inside this function.
- Browser instance must be closed in a `finally` block regardless of outcome.

**Do not add:** retry logic, caching, async wrappers, CLI entry points, or logging beyond
a single `print` statement for duration timing.

---

### Task 1.3 — Create `test_phase1.py`

Create `test_phase1.py` in the project root:

```python
from pathlib import Path
import tonejs_bridge

HTML = str(Path(__file__).parent / "tonejs_renderer.html")

schedule = [
    {"inst": "kick", "time_s": 0.000, "velocity": 1.0},
    {"inst": "kick", "time_s": 0.500, "velocity": 1.0},
    {"inst": "kick", "time_s": 1.000, "velocity": 1.0},
    {"inst": "kick", "time_s": 1.500, "velocity": 1.0},
]

wav_bytes = tonejs_bridge.render_to_wav_bytes(schedule, HTML)

out = Path("test_phase1_output.wav")
out.write_bytes(wav_bytes)
print(f"Written {len(wav_bytes)} bytes → {out}")
assert len(wav_bytes) > 44, "WAV file is too small — likely empty render"
print("Phase 1 PASSED.")
```

**Run:**

```bash
python test_phase1.py
```

### Phase 1 Success Criteria

| Check | Observable Proof |
|---|---|
| `test_phase1_output.wav` exists | File present in project root |
| File size > 100 KB | `ls -lh test_phase1_output.wav` |
| File plays correctly | Open in any audio player — 4 kick hits at 120 BPM, ~2 s duration |
| No ffmpeg invoked | Confirm `ffmpeg` is not in `tonejs_bridge.py` |
| Existing stack unmodified | `python buhoor_drums_v2.py taweel -v wahda_kabira --bpm 80` still produces correct MP3 |

**STOP if any check fails. Do not proceed to Phase 2.**

### Phase 1 Rollback

Delete `tonejs_renderer.html`, `tonejs_bridge.py`, `test_phase1.py`, and
`test_phase1_output.wav`. The existing codebase is untouched.

---

## 4. Phase 2 — Instrument Completeness

**Prerequisite:** Phase 1 all success criteria met.

**Objective:** Add ka and crash to `tonejs_renderer.html` and validate that the ka
approximation is perceptually credible. This is the second highest-risk item — there is
no native Tone.js equivalent for the doumbek finger snap.

**Files modified:** `tonejs_renderer.html` only.
**Files created:** `test_phase2.py`.

---

### Task 2.1 — Add Ka to `tonejs_renderer.html`

Add a fourth synth inside the `renderPattern` function:

```javascript
ka → Tone.MetalSynth {
  frequency: 5000,
  envelope: { attack: 0.001, decay: 0.04, sustain: 0, release: 0.04 },
  harmonicity: 2.0,
  modulationIndex: 8,
  resonance: 5000,
  octaves: 0.5
}
```

Wire `inst === 'ka'` hits to this synth. Set `ka.volume.value = -10` to match the
relative level of the Python `synth_ka` output (which applies a `0.60` scalar).

**Do not modify** the kick, snare, or hihat synth definitions.

### Task 2.2 — Add Crash to `tonejs_renderer.html`

Add a fifth synth:

```javascript
crash → Tone.NoiseSynth {
  noise: { type: 'white' },
  envelope: { attack: 0.003, decay: 1.2, sustain: 0, release: 0.5 }
}
```

Set `crash.volume.value = -8`. Wire `inst === 'crash'` hits to this synth.

### Task 2.3 — Create `test_phase2.py`

```python
from pathlib import Path
import tonejs_bridge

HTML = str(Path(__file__).parent / "tonejs_renderer.html")

# One bar of a typical Taweel-compatible iqaa pattern
schedule = [
    {"inst": "kick",  "time_s": 0.000, "velocity": 1.0},
    {"inst": "crash", "time_s": 0.000, "velocity": 0.7},
    {"inst": "snare", "time_s": 0.250, "velocity": 0.5},
    {"inst": "ka",    "time_s": 0.375, "velocity": 0.4},
    {"inst": "hihat", "time_s": 0.000, "velocity": 0.45},
    {"inst": "hihat", "time_s": 0.125, "velocity": 0.45},
    {"inst": "hihat", "time_s": 0.250, "velocity": 0.45},
    {"inst": "hihat", "time_s": 0.375, "velocity": 0.45},
    {"inst": "kick",  "time_s": 0.500, "velocity": 0.8},
    {"inst": "hihat", "time_s": 0.500, "velocity": 0.45},
    {"inst": "hihat", "time_s": 0.625, "velocity": 0.45},
]

wav_bytes = tonejs_bridge.render_to_wav_bytes(schedule, HTML)
Path("test_phase2_output.wav").write_bytes(wav_bytes)
print(f"Written {len(wav_bytes)} bytes. Listen and evaluate ka credibility.")
```

### Phase 2 Success Criteria

| Check | Observable Proof |
|---|---|
| All 5 instruments render without error | No exception from `render_to_wav_bytes` |
| Ka is audibly distinct from snare and hihat | Listening test — must sound like a short, high-pitched click, not a snare |
| Crash has a slow, washy decay | Listening test — must sustain for ~1 s |
| File size > 200 KB | `ls -lh test_phase2_output.wav` |

### Phase 2 Stop Condition — Ka Evaluation Gate

After listening to `test_phase2_output.wav`, a human must make a binary judgement:

- **Ka is credible** → Proceed to Phase 3.
- **Ka is not credible** → STOP. Document the finding in `Session_Handover.md`. Do not
  proceed. The investigation will require a `Tone.Sampler` with a real doumbek sample,
  which is out of scope for this plan and must be separately scoped.

### Phase 2 Rollback

Revert `tonejs_renderer.html` to its Phase 1 state using version control. Delete
`test_phase2.py` and `test_phase2_output.wav`.

---

## 5. Phase 3 — Humanisation IPC

**Prerequisite:** Phase 2 all success criteria met and Ka evaluation gate passed.

**Objective:** Verify that timing jitter and velocity values computed by Python's
`humanize()` function survive the JSON serialisation boundary and are applied by Tone.js
with sufficient precision.

**Files modified:** None in existing codebase. `tonejs_renderer.html` receives one
addition. `test_phase3.py` is created.

**Do not modify:** `humanize()` in `buhoor_drums.py`. It runs unchanged. This phase only
validates that its output can be serialised and consumed correctly.

---

### Task 3.1 — Extend `tonejs_renderer.html` for Jitter

The hit schedule JSON schema is extended to include panning:

```json
{ "inst": "kick", "time_s": 0.012, "velocity": 0.94, "pan": 0.0 }
```

Inside `renderPattern`, before the offline context, create a `Tone.Panner` per instrument
and wire each synth through its panner. Apply `hit.pan` (range -1.0 to 1.0) per hit.

**Do not change** synth definitions, the offline context setup, or the WAV encoding logic.

### Task 3.2 — Create `test_phase3.py`

This test calls `humanize()` directly and bridges its output to Tone.js:

```python
from pathlib import Path
from buhoor_drums import humanize, BUHOOR
import tonejs_bridge, json

HTML = str(Path(__file__).parent / "tonejs_renderer.html")
bahr = BUHOOR["taweel"]

# Eight-step pattern for one bar — matches wahda_kabira kick line
base_pattern = [1, 0, 0, 1, 0, 1, 0, 0]
step_s = 4 * 60.0 / (80 * 8)  # 4 beats, 8 steps, 80 BPM

hits = humanize(base_pattern, timing_jitter=0.007,
                velocity_variance=0.12, base_velocity=1.0)

schedule = [
    {"inst": "kick",
     "time_s": round(step_idx * step_s + t_off, 6),
     "velocity": round(vel, 4),
     "pan": 0.0}
    for step_idx, t_off, vel in hits
]

print("Schedule sample:", json.dumps(schedule[:3], indent=2))
wav_bytes = tonejs_bridge.render_to_wav_bytes(schedule, HTML)
Path("test_phase3_output.wav").write_bytes(wav_bytes)
print(f"Written {len(wav_bytes)} bytes.")

# Verify timing spread — jitter must be present
times = [h["time_s"] for h in schedule]
mechanical = [i * step_s for i in range(len(base_pattern)) if base_pattern[i]]
diffs = [abs(t - m) for t, m in zip(times, mechanical)]
assert any(d > 0 for d in diffs), "No jitter applied — humanize() produced mechanical output"
print("Phase 3 PASSED — jitter confirmed.")
```

### Phase 3 Success Criteria

| Check | Observable Proof |
|---|---|
| `test_phase3_output.wav` plays with subtly uneven timing | Listening test — must not sound like a drum machine grid |
| Jitter assertion passes | Script prints `Phase 3 PASSED` |
| `humanize()` in `buhoor_drums.py` is not modified | `git diff buhoor_drums.py` shows no changes |

**STOP if the jitter assertion fails or the output sounds perfectly mechanical.**

### Phase 3 Rollback

Revert `tonejs_renderer.html` to its Phase 2 state. Delete `test_phase3.py` and
`test_phase3_output.wav`.

---

## 6. Phase 4 — Integration into `render_variant()`

**Prerequisite:** All three prior phases passed with all success criteria met.

**Objective:** Wire the Tone.js rendering path into `buhoor_drums.py` behind a `--tonejs`
CLI flag. Scope is limited to Al-Taweel and Al-Kamil. All other meters continue to use
the existing scipy path.

**Files modified:** `buhoor_drums.py` only. One isolated block.
**Files created:** None.

---

### Task 4.1 — Add `--tonejs` Flag to CLI

In `buhoor_drums_v2.py` (the Click entry point, not `buhoor_drums.py`), add:

```python
@click.option('--tonejs', is_flag=True, default=False,
              help='Use Tone.js FM synthesis via Playwright (Al-Taweel and Al-Kamil only).')
```

Pass `use_tonejs=tonejs` down to `render_variant()`. Add `use_tonejs: bool = False` to
`render_variant()`'s signature.

**Do not change** any other CLI option, any other function signature, or any other part
of the Click command definition.

### Task 4.2 — Replace the Synthesis Block in `render_variant()`

In `buhoor_drums.py`, locate the block beginning with:

```python
sounds = {name: fn() for name, fn in SYNTH_MAP.items()}
```

And ending just before:

```python
wavfile.write(wav_p, SAMPLE_RATE, pcm)
```

Replace this entire block — and only this block — with a conditional:

```python
if use_tonejs and bahr_key in ("taweel", "kamil"):
    from tonejs_bridge import render_to_wav_bytes
    from pathlib import Path
    import io

    html_path = str(Path(__file__).parent / "tonejs_renderer.html")

    # Build hit schedule from the already-humanised hits dict
    # (hits is computed above by humanize() — that code is unchanged)
    schedule = []
    for inst, hit_list in all_hits.items():
        pan = panning.get(inst, (0.5, 0.5))
        pan_value = pan[1] - pan[0]          # approximate mono pan [-1, 1]
        for step_idx, t_off, vel in hit_list:
            t_sec = step_idx * step_s + t_off
            schedule.append({"inst": inst, "time_s": round(t_sec, 6),
                              "velocity": round(vel, 4), "pan": round(pan_value, 4)})

    schedule.sort(key=lambda h: h["time_s"])
    wav_bytes = render_to_wav_bytes(schedule, html_path)
    audio = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")

else:
    # --- Original synthesis path (unchanged) ---
    sounds = {name: fn() for name, fn in SYNTH_MAP.items()}
    # ... (existing mix loop, normalisation, wavfile.write, AudioSegment.from_wav)
    audio = AudioSegment.from_wav(wav_p)
```

After this conditional block, execution continues at `audio.export(mp3_p, ...)` unchanged.

**Dangerous zone:** The `humanize()` call and the `hits` dict it produces must fire
**before** this block, as they do today. Do not move, inline, or refactor `humanize()`.
Verify that `all_hits` is the correct variable name for the per-instrument hit lists in
the current codebase before writing this code.

**Minimum change rule:** Add only the `if use_tonejs` branch and the `else` wrapper.
Do not rename variables, reorder imports, or modify anything outside this block.

### Task 4.3 — Side-by-Side Validation

```bash
# Generate the same variant with both engines
python buhoor_drums_v2.py taweel -v wahda_kabira --bpm 80
python buhoor_drums_v2.py taweel -v wahda_kabira --bpm 80 --tonejs

python buhoor_drums_v2.py kamil -v maqsum --bpm 90
python buhoor_drums_v2.py kamil -v maqsum --bpm 90 --tonejs
```

Confirm:
- Both produce MP3 files with identical filenames (minus a suffix if needed for A/B).
- Both MP3 files have correct ID3 tags (`exiftool` or `id3info`).
- Both appear in `manifest.json`.

### Phase 4 Success Criteria

| Check | Observable Proof |
|---|---|
| `--tonejs` flag produces a valid MP3 | File exists, plays, is > 100 KB |
| ID3 tags are intact on Tone.js output | `id3info` shows correct Arabic title, genre, publisher |
| `manifest.json` entry is written for Tone.js render | Entry present with correct metadata |
| Default path (no flag) is completely unaffected | `git diff` shows only the conditional block was added |
| All other meters (baseet, wafir, etc.) still work | Run 3 arbitrary meters without `--tonejs` flag |

**STOP if ID3 tags are missing from the Tone.js output or if `manifest.json` is not
written. This indicates the `audio` variable is not being passed correctly to
`audio.export()`.**

### Phase 4 Rollback

Revert `buhoor_drums.py` to its pre-Phase 4 state using version control. Remove the
`--tonejs` flag from `buhoor_drums_v2.py`. The `tonejs_bridge.py` and
`tonejs_renderer.html` files remain for reference but are no longer called.

---

## 7. Phase 5 — Suno Seed Quality Evaluation

**Prerequisite:** Phase 4 all success criteria met.

**Objective:** Determine empirically whether the Tone.js output is a better seed for Suno
(or equivalent AI music generation services) than the scipy output. This phase produces
an evidence-based recommendation, not a code change.

**Files modified:** None. This phase is evaluation only.

---

### Task 5.1 — Generate Evaluation Pair

```bash
# Scipy render (existing engine)
python buhoor_drums_v2.py taweel -v wahda_kabira --bpm 80

# Tone.js render (new engine)
python buhoor_drums_v2.py taweel -v wahda_kabira --bpm 80 --tonejs
```

Rename outputs clearly:
- `taweel_wahda_kabira_80bpm_SCIPY.mp3`
- `taweel_wahda_kabira_80bpm_TONEJS.mp3`

### Task 5.2 — Blind Suno Upload Test

Upload each file to Suno as a style seed with identical prompt text. Generate 3 outputs
per seed. Evaluate on three axes:

| Axis | What to listen for |
|---|---|
| **Rhythmic fidelity** | Does the generative output preserve the 4/4 metre and the doumbek character? |
| **Timbral influence** | Is there audible Arabic percussion colouring in the generated output? |
| **Consistency** | Across 3 generations per seed, how stable is the style? |

### Phase 5 Success Criteria & Decision Gate

| Outcome | Decision |
|---|---|
| Tone.js seed produces equal or better results on ≥ 2 of 3 axes | Proceed to full migration of all 13 meters and 44 variants (separate plan) |
| Tone.js seed produces worse results on ≥ 2 of 3 axes | Revert to scipy. Retain `tonejs_bridge.py` and `tonejs_renderer.html` in a branch for future reference |
| Results are indistinguishable | Document and present to stakeholder. Do not migrate — the complexity cost is not justified by equal output quality |

---

## 8. Strict Scope Boundaries

### In Scope

- `tonejs_renderer.html` — new file, renderer only
- `tonejs_bridge.py` — new file, bridge only
- `buhoor_drums.py` — one conditional block inside `render_variant()` only
- `buhoor_drums_v2.py` — one `--tonejs` flag addition only
- Al-Taweel and Al-Kamil meters only
- Kick, snare, hihat, ka, crash instruments

### Out of Scope — Do Not Implement, Do Not Scaffold

- Any UI, web application, or interactive browser interface
- `Tone.Sampler` with real audio samples (requires a separate asset pipeline)
- Effects chains: reverb, delay, compression, EQ
- Removal of `ffmpeg` or `pydub` from the stack
- Migration of any meter beyond Al-Taweel and Al-Kamil
- Changes to `arabic_rhythm_data.json`, `iqaa_patterns.py`, or `meter_registry.py`
- Changes to `manifest.json` structure or ID3 tag content
- `lamejs` in-browser MP3 encoding (Python handles MP3 encoding)
- Async Playwright (use sync API only)
- Any refactoring of functions not named in this plan

---

## 9. Session Handover Protocol

At the end of every working session, generate a `Session_Handover.md` file in the
project root containing exactly the following sections:

```markdown
# Session Handover — [Date]

## Current Phase and Task
[e.g., "Phase 2, Task 2.2 — Crash instrument added, Ka not yet validated"]

## What Was Done
[Bullet list of completed tasks with file names]

## Files Changed
[List of files modified or created, with a one-line description of the change]

## Files NOT Changed
[Confirm explicitly: buhoor_drums.py, arabic_rhythm_data.json, iqaa_patterns.py, etc.]

## Current Status
[ ] Phase 1 complete
[ ] Phase 2 complete — Ka gate: PASS / FAIL / PENDING
[ ] Phase 3 complete
[ ] Phase 4 complete
[ ] Phase 5 complete — Decision: MIGRATE / REVERT / INCONCLUSIVE

## Known Issues or Blockers
[Any STOP conditions encountered, open questions, or deferred problems]

## Exact First Step for Next Session
[One specific command or code action — not a phase summary]
```

The next agent or session must read `Session_Handover.md` before any other file and must
not begin work until the current phase's pre-conditions are confirmed met.

---

*This plan authorises investigation only. Full migration to Tone.js synthesis across all
13 meters and 44 variants is explicitly out of scope and requires a separate plan
contingent on a MIGRATE decision from Phase 5.*
