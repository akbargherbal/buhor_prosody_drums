# Proposal: Investigation into Tone.js-Assisted Audio Synthesis
## *Buhoor Arabic Poetic Meter Drum Generator*

**Status:** Proposal for technical investigation
**Scope:** Audio synthesis layer only — no change to project architecture, CLI, or metadata systems
**Prepared for:** Project developer

---

## 1. Background

The Buhoor Drum Generator is a command-line tool that synthesises drum loops aligned to
the rhythmic character of 13 classical Arabic poetic meters (*بحور*). It produces MP3
files with ID3 metadata and a generation manifest, driven by the `arabic_rhythm_data.json`
registry. The synthesis engine is written entirely in Python, using `numpy`, `scipy`,
`pydub`, and `ffmpeg`.

The project has recently been considered as a source of **seed audio for AI music
generation services** such as Suno. This shifts the primary evaluation criterion for the
audio output: from *prosodic accuracy* — which the current stack handles well — toward
*perceptual naturalness*, which determines how effectively a seed audio track influences
generative output.

This proposal suggests a focused investigation into whether replacing the current
synthesis layer with a Tone.js-based renderer — while keeping the entire Python stack
intact — would better serve that end goal, and whether the change would be practical.

---

## 2. The Current Synthesis Approach

### 2.1 How It Works

The current engine synthesises each percussion instrument from first principles using
signal processing primitives:

| Instrument | Method |
|---|---|
| **Kick** | Exponential frequency sweep (240 Hz → 40 Hz) over a sine wave; bandpass-filtered noise shell blended in |
| **Snare** | 3,200 Hz tonal ring mixed with high-pass-filtered white noise burst |
| **Ka** | 5,000 Hz sine ring with ultra-short high-pass noise; models doumbek finger snap |
| **Hi-hat** | White noise passed through a 7 kHz Butterworth high-pass filter |
| **Crash** | Broadband noise through a 4 kHz high-pass with slow exponential decay |

Envelopes are constructed using a custom `_envelope()` function applying linear attack and
exponential decay via `numpy`. Stereo panning uses a constant-power law. Timing is
computed by manually converting BPM and step subdivisions to sample offsets.

Output is rendered to WAV in memory and exported to MP3 via `pydub` and `ffmpeg`.

### 2.2 Strengths

- **Self-contained and reproducible.** No external assets. Every render is deterministic
  given the same `--seed` value. The generation manifest records all parameters precisely.
- **Fully scriptable.** The `--all`, `--region`, `--traditional-only`, and
  `--instrument` flags allow batch generation of the entire 44-variant corpus in a single
  command — a capability critical for systematic corpus work.
- **Rich metadata pipeline.** ID3 tags (Arabic name, time signature, mood, tradition,
  performance notes) are written automatically from the JSON registry. No other synthesis
  approach in this category handles metadata at this level of detail.
- **Humanisation controls.** `--jitter`, `--velocity-variance`, and `--seed` give
  precise, reproducible control over timing and velocity variation.
- **Stable dependencies.** `numpy`, `scipy`, and `pydub` are mature libraries with
  stable APIs and long support horizons.

### 2.3 Limitations

- **Tonal flatness in metallic and membrane instruments.** The hi-hat and ka — the
  instruments most sensitive to spectral character — are approximated using filtered noise.
  This is physically plausible but produces a tonally flat result. Real metallic percussion
  generates complex inharmonic overtone series through resonance; a single Butterworth
  high-pass filter cannot model this.
- **Kick lacks membrane behaviour.** The current kick uses a manually coded frequency
  glide, which approximates the pitch drop of a drum strike but does not model the
  interaction between membrane tension, air coupling, and shell resonance that gives a
  struck drum its characteristic initial transient.
- **Limited relevance to AI seed quality.** AI music generation services analyse the
  harmonic and spectral content of seed audio to infer style. Synthesis-by-filtered-noise
  produces a restricted spectral profile. The richer the harmonic content of the seed,
  the more information the model has to work with.

---

## 3. The Proposed Approach

### 3.1 Tone.js as a Rendering Subprocess

Tone.js is a Web Audio framework that implements FM-based synthesis for percussion
instruments. Its `MembraneSynth`, `MetalSynth`, and `NoiseSynth` classes model instrument
behaviour at a higher level of physical fidelity than the current scipy-based approach.

The proposed change is **narrow in scope**: replace only the audio rendering step with a
Tone.js-based renderer, called from Python as a subprocess via **Playwright** — a
browser automation library installable via `pip`. Everything else in the project remains
unchanged.

The revised pipeline would be:

```
Python CLI
  → reads arabic_rhythm_data.json          [unchanged]
  → resolves meter / variant / BPM          [unchanged]
  → applies humanisation (jitter, velocity) [unchanged]
  → generates pattern grid                  [unchanged]
  → calls Playwright (headless Chromium)
      → loads Tone.js rendering page
      → passes pattern + BPM as JSON
      → runs Tone.Offline() → AudioBuffer
      → encodes MP3 via lamejs
      → returns MP3 bytes to Python
  → Python writes MP3 to output directory   [unchanged]
  → Python writes ID3 tags                  [unchanged]
  → Python appends to manifest.json         [unchanged]
```

`ffmpeg` would no longer be required. `pydub`'s role in MP3 encoding would be replaced
by `lamejs` (a ~60 KB pure-JS port of LAME) running inside the headless browser.
`numpy` and `scipy` would remain available for any signal processing needs outside
synthesis.

### 3.2 What Changes and What Does Not

| Component | Status |
|---|---|
| CLI interface and all flags | **Unchanged** |
| `arabic_rhythm_data.json` registry | **Unchanged** |
| Meter definitions, BPM clamping, tradition filters | **Unchanged** |
| Pattern grid generation | **Unchanged** |
| Humanisation (`--jitter`, `--velocity-variance`, `--seed`) | **Unchanged** |
| ID3 tagging | **Unchanged** |
| `manifest.json` generation | **Unchanged** |
| MP3 output filenames and directory structure | **Unchanged** |
| `ffmpeg` system dependency | **Removed** |
| `pydub` MP3 encoding | **Replaced by lamejs inside Playwright** |
| `numpy` / `scipy` synthesis functions | **Replaced by Tone.js synths** |
| New dependency | `playwright` (pip-installable) |

### 3.3 Synthesis Quality Comparison

| Instrument | Current (scipy) | Proposed (Tone.js) |
|---|---|---|
| **Kick** | Sine + frequency glide + bandpass noise | `MembraneSynth`: FM pitch sweep with octave spread and pitch decay modelling membrane behaviour |
| **Hi-hat** | White noise → Butterworth high-pass | `MetalSynth`: FM synthesis with harmonicity and modulation index; produces inharmonic overtone series |
| **Snare** | Tonal ring + high-pass noise | `NoiseSynth`: shaped noise with configurable ADSR |
| **Ka** | Short sine ring + high-pass noise | `MetalSynth` retuned to ~5 kHz, very short decay — requires validation |
| **Crash** | Broadband noise + slow decay | `NoiseSynth` with extended 1.2 s envelope — direct port |

The Ka instrument merits particular attention. It is the most culturally specific sound in
the set — the doumbek finger snap — and has no direct equivalent in Tone.js's built-in
preset library. Whether a retuned `MetalSynth` is a credible approximation or whether it
requires a real doumbek sample via `Tone.Sampler` is an open question that only listening
tests can resolve. This is one of the key questions the investigation should answer.

---

## 4. Relevance to the AI Music Generation Use Case

Suno and comparable services (Udio, MusicGen) accept audio uploads as style seeds. Their
internal analysis models examine spectral content, rhythmic density, and timbral character
to infer genre and instrumentation.

Two factors affect seed quality in this context:

**Harmonic richness.** FM synthesis produces overtone series with multiple partials.
Filtered noise produces a spectral shape but limited pitch content. Models trained on
real-world recordings respond more predictably to harmonically rich input. A Tone.js-
rendered hi-hat, for instance, contains frequency components that a model might associate
with specific instrument classes — information absent from a noise-filtered approximation.

**Encoding quality.** The current pipeline encodes to MP3 via `pydub` / `ffmpeg` from a
`float32` numpy array. The proposed pipeline encodes via `lamejs` from the same
`AudioBuffer` type that Web Audio uses natively, with configurable bitrate up to 320k.
The perceptual difference at 192k is likely negligible; at 320k, there is no meaningful
lossy artefact that would affect seed analysis.

Neither factor guarantees better generative output from Suno — that depends on the
model's internal representations, which are not publicly documented. However, the
direction of the change (more harmonic content, lower encoding artefacts) is consistent
with best practices for seed audio preparation.

---

## 5. Questions the Investigation Should Answer

The following are proposed as the scope of a preliminary investigation:

1. **Ka credibility.** Does a `MetalSynth` retuned to ~5 kHz produce a convincing doumbek
   finger snap, or is a real sample required? If a sample is required, does that
   reintroduce asset management complexity that offsets the simplicity gain?

2. **Playwright overhead.** What is the per-render latency of spinning up a headless
   Chromium, loading Tone.js, and running `Tone.Offline()`? Is batch generation of all 44
   variants within an acceptable time window compared to the current stack?

3. **Humanisation fidelity.** Can `--jitter` and `--velocity-variance` values computed in
   Python be passed into the Tone.js render page and applied with sufficient precision?
   The IPC boundary (Python → JSON → browser) introduces a serialisation step that should
   be validated.

4. **Seed quality in practice.** Does a Tone.js-rendered pattern, when uploaded to Suno
   as a style seed, produce qualitatively different generative output compared to the
   current scipy-rendered pattern? This is the most direct measure of whether the change
   delivers on its primary motivation.

5. **Dependency trade-off acceptability.** Replacing `ffmpeg` (a system binary) with
   `playwright` (a pip package that downloads Chromium) is a lateral move in terms of
   external dependencies, not a simplification. Whether this trade-off is acceptable
   depends on the deployment context — local use, CI/CD, or a hosted service each have
   different considerations.

---

## 6. Proposed Next Step

A proof-of-concept limited to **two meters** (Al-Taweel and Al-Kamil, representing 4/4
and 3/4 time signatures) and **three instruments** (kick, hi-hat, snare) would be
sufficient to answer questions 1 through 4 above. The Ka and Crash instruments, and the
full 44-variant corpus, would remain on the current stack until the investigation
concludes.

This scope limits the investment to a bounded spike with a clear evaluation criterion:
does the rendered output sound more natural, and does it perform better as a Suno seed?
If the answer to either question is no, the current stack is retained without loss.

---

*This proposal does not advocate for a specific outcome. It recommends a time-bounded
investigation to determine whether the change is warranted before any commitment is made.*
