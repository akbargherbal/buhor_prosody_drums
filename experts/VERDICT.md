# TECHNICAL DIRECTOR OUTPUT

## Buhoor Drum Generator — Synthesis & Action Plan

---

## PRE-SYNTHESIS: Verdict Compilation

Before the ranked list, here are the nine verdicts as I read them, with schema fields assigned where experts left them implicit.

| ID                                  | VERDICT | SEVERITY    | SCOPE              |
| ----------------------------------- | ------- | ----------- | ------------------ |
| A1 — Masmoudi Kabir triple DUM      | WRONG   | FATAL       | Al-Baseet          |
| A2 — Maqsum / Al-Taweel pairing     | WRONG   | SIGNIFICANT | Al-Taweel          |
| A3 — Corpus statistics              | VALID   | COSMETIC    | All meters         |
| B1 — 3/4 vs 6/8 perceptual collapse | WRONG   | FATAL       | Al-Kamil, Al-Wafir |
| B2 — Wafir double-short encoding    | WRONG   | FATAL       | Al-Wafir           |
| B3 — Samaai Darij kick placement    | WRONG   | FATAL       | Al-Kamil           |
| C1 — Snare / Western timbre         | WRONG   | FATAL       | All meters         |
| C2 — Kick / 808 sub-bass timbre     | WRONG   | FATAL       | All meters         |
| C3 — Uniform humanization           | WRONG   | SIGNIFICANT | All meters         |

---

## SECTION 1 — FATAL BLOCKERS

**B1 — Perceptual collapse of 3/4 and 6/8**
The 12-step grid produces an identical stream of equidistant pulses for both Al-Kamil and Al-Wafir; without correct onset patterns, the meters are acoustically indistinguishable. Fatal under Criterion 2 (affects two meters) and Criterion 1 (Suno cannot differentiate them).

**B2 — Wafir double-short is mathematically absent**
The IOI analysis proves the fāṣila ṣughrā (∪∪) does not exist in the encoded pattern. The hihat pair produces a long (—), not two shorts. Fatal under Criterion 1: the output does not encode what it claims to encode, and Suno will receive a false rhythmic signal.

**B3 — Samaai Darij is unrecognizable**
Kick on step 3 with IOIs of 4-4-4 produces a syncopated quarter-note pulse, not a DUM-anchored Samaai Darij. Fatal under Criterion 3: no Arabic percussionist would recognize it, meaning Suno will not either.

**C1 — Snare is a Western rock snare**
The 200 Hz sine + broadband noise model is the canonical TR-808 snare. It has zero resemblance to a riq or tabla TEK. Fatal under Criterion 1: timbre overrides rhythm in AI music models. This single sound will pull Suno into a Western pop/rock latent space regardless of how correct the patterns are.

**C2 — Kick is an 808 sub-bass**
The 150 Hz → 50 Hz sweep over 500 ms is a classic hip-hop kick. The doumbek DUM sits at 180–260 Hz with a short decay and shell resonance this model lacks entirely. Fatal under Criterion 1 for the same reason as C1: timbre is the primary genre signal to Suno.

**Note on B1/B2/B3 interaction:** Expert B's audit also reveals that _all four meters_ have binary patterns whose IOIs do not match the prosodic feet they claim to represent. This is a systemic encoding failure, not an isolated bug. It is treated below as a single root cause.

---

## SECTION 2 — RANKED ACTION LIST

---

**ACTION 1 — Replace kick and snare synthesis with Arabic doumbek/tabla models**

_Resolves: C1, C2_

What to change: Replace `synth_kick()` and `synth_snare()` with Expert C's corrected implementations verbatim. The kick moves to 240 Hz fundamental, ~250 ms decay, with a bandpass shell resonance layer (400–800 Hz). The snare becomes a high-frequency edge strike (3.2 kHz ring + 2.5 kHz highpass noise), eliminating the 200 Hz body entirely. Also adjust panning to near-center per Expert C's corrected `render_variant()` block.

Acceptance condition: Upload one loop to Suno with no prompt text. If the generated music contains Arabic maqam elements, oud, or frame drum accompaniment — rather than guitar, Western bass, or trap hi-hats — the timbre is working. This is the binary Suno gate.

_Why first:_ Criterion 1 is the supreme criterion. Expert C states explicitly that "timbre overrides rhythm in these models." Correct patterns fed through 808 timbres will still produce Western output. The timbre fix is the precondition for all pattern work to be testable. There is no point validating rhythm on Suno until the instruments speak Arabic.

---

**ACTION 2 — Rebuild the binary patterns using mora-based grid sizing**

_Resolves: B1, B2, B3, and the systemic pattern failure across all four meters_

What to change: Adopt Expert B's mora-counting methodology. 1 step = 1 mora (∪), 2 steps = 1 long (—). This requires:

- **Al-Taweel**: Change `steps_per_bar` from 16 to 12. Replace all four instrument arrays with mora-correct patterns. Update `beats_per_bar` accordingly.
- **Al-Baseet**: Same restructure to 12-step grid.
- **Al-Kamil**: The current 12-step grid cannot encode three _mutafāʿilun_ feet (7 morae × 3 = 21 steps). Either move to a 21-step grid per foot, or use a 7-step single-foot grid looped — whichever preserves the Samaai Darij DUM on beat 1 (step 0), not step 2.
- **Al-Wafir**: Move to a 14-step grid (7 morae × 2 feet). Replace the hihat pattern so the ∪∪ produces IOIs of 1-1, not 1-2.

Acceptance condition: Perform Expert B's IOI analysis on every new pattern. The resulting IOI sequence must map to the claimed prosodic foot without gaps or mismatches. Document the IOI table alongside the pattern array in the code comments.

_Why second:_ These are fatal pattern errors (B1, B2, B3) with scope across all four meters. But they cannot be validated on Suno until Action 1 is complete — Suno feedback is meaningless through 808 timbres. The patterns should be rebuilt in parallel with or immediately after timbre work.

---

**ACTION 3 — Replace the Maqsum variant for Al-Taweel with Wahda**

_Resolves: A2_

What to change: Demote the `maqsum` variant from primary to optional or remove it. Promote the `wahda` variant (already in the script at 72 BPM) as the canonical cycle for Al-Taweel. If Maqsum is retained, add an inline comment marking it as a non-traditional pairing and noting Expert A's finding. Expert A's recommended alternative — Wahda — is already implemented; this action is therefore primarily a labeling and documentation change, with a possible reordering of variant priority.

Acceptance condition: The `wahda` variant appears first in Al-Taweel's variant list. Any retained `maqsum` variant carries a comment: `# Non-traditional pairing — use with caution; Wahda is the canonical choice for Al-Taweel.`

_Why third:_ This is SIGNIFICANT but not FATAL. The Wahda variant already exists and works. The Maqsum issue is a mislabeling problem that could mislead a user uploading to Suno, but it does not corrupt the generated audio the way B1–B3 or C1–C2 do. It ranks here because it is a fast fix.

---

**ACTION 4 — Replace uniform humanization with instrument-hierarchical dynamics**

_Resolves: C3_

What to change: In `render_variant()`, replace the uniform `±12%` velocity variance with a two-tier model. DUM strokes (kick channel) receive a narrow variance (±5–8%). TEK/ghost strokes (snare and hihat channels) receive a fixed downward offset (–40% to –50% of the DUM level), with a narrower variance (±8%). This is not random humanization — it is structural dynamic shaping. The jitter parameter (±7 ms) can remain as a global CLI option but should be documented as applying equally to all strokes pending a more sophisticated implementation.

Acceptance condition: Print peak velocity values per channel to stdout in non-quiet mode. DUMs should consistently read 85–95% of peak. TEK/ghost strokes should consistently read 40–60% of peak. No stroke should randomly exceed its channel ceiling.

_Why fourth:_ This is SIGNIFICANT but not instrument-identity-breaking the way the timbre errors are. Uniform randomization sounds unstable, but it does not send Suno into the wrong genre. This is an expressiveness fix, not a genre-classification fix. It ranks after the structural repairs.

---

## SECTION 3 — EXPLICITLY DEFERRED ITEMS

**A3 — Corpus statistics (VALID / COSMETIC)**
Deferred permanently. Expert A confirms the figures are correct and defensible. No action required. The comment block in the script is accurate.

**B1 partial — The formula `step_s = beats_per_bar × 60 / (bpm × steps_per_bar)`**
The formula is arithmetically correct. The problem it exposes (perceptual collapse) is resolved by Action 2's pattern rebuild. The formula itself does not need to change; the grid sizes and onset patterns do. Defer any further formula discussion until post-Action-2 Suno testing confirms the rebuilt patterns produce the expected perceptual difference.

**Hihat and crash cutoff frequencies (C1 partial)**
Expert C flags the hihat HPF at 7 kHz (should be 5 kHz for riq jingles) and the crash at 4 kHz (wrong instrument model entirely if intended as duff). The corrected `synth_hihat()` in Expert C's code block addresses the hihat. The crash-as-duff issue is deferred: the crash is a low-usage instrument in the current patterns (appears mainly on bar 1), and the timbral priority for Suno conditioning is kick and snare. Revisit after Action 1 is validated on Suno.

---

## SECTION 4 — THE FIRST THING TO BUILD

**Build the corrected kick and snare synthesis functions, render one loop, and upload it to Suno with no text prompt before touching a single pattern array.**

Expert C's finding — that timbre overrides rhythm in AI music models — establishes a hard dependency that makes all pattern work unverifiable until it is resolved. Here is the logic chain: if the current 808 kick and Western snare are in place, Suno will interpret the audio as hip-hop or rock regardless of whether the step patterns encode perfect _mutafāʿilun_. This means any Suno test run you do right now, or after Action 2, is returning noise. You cannot distinguish "pattern is wrong" from "timbre is steering Suno away" from the output alone. The timbre fix is the only way to make Suno's response interpretable as feedback on your patterns.

The fix itself is concrete and bounded: Expert C has provided complete, drop-in replacement functions for `synth_kick()` and `synth_snare()`, with corrected panning values. This is a one-session implementation. Once a single Wahda loop renders through the new timbres and Suno responds with Arabic-character output, you have established the foundation on which every subsequent pattern fix can be meaningfully tested. Under Criterion 1, this is the only rational starting point.
