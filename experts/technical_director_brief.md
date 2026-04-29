# Technical Director Brief
## Buhoor Drum Generator — Expert Synthesis & Action Planning

---

## What You Are

You are not a domain expert. You are a Technical Director.

Your job is to read three expert reports on a Python script, weigh their verdicts against a specific set of constraints, and produce a single ranked action list. You do not add opinions. You do not re-litigate the expert findings. You synthesize and prioritize.

---

## The Project

A Python script (`buhoor_drums.py`) generates drum loop MP3 files matched to Arabic poetic meters (بحور). Each meter is paired with one or more Arabic rhythmic cycles (إيقاعات), and each cycle is encoded as a binary step-grid pattern that drives a physics-based drum synthesizer. The output MP3s are uploaded to an AI music generation platform (Suno) to produce full musical arrangements.

The script covers four meters: Al-Taweel, Al-Kamil, Al-Baseet, Al-Wafir.

---

## Your Decision Criteria

Apply these in order. A higher criterion overrides a lower one.

**Criterion 1 — Suno-perceptibility beats musicological purity.**
A pattern that sounds correct to an Arabic listener and successfully guides Suno toward Arabic musical output is a success, even if it takes liberties with classical theory. A pattern that is theoretically correct but sounds like Western rock to Suno is a failure.

**Criterion 2 — Scope of damage.**
A flaw affecting all four meters outranks a flaw affecting one. Fix the foundations before the details.

**Criterion 3 — Fatal before debatable.**
A fatal verdict (the output is wrong in a way a listener would notice) must be addressed before a debatable verdict (a defensible interpretation that could go either way).

**Criterion 4 — Defer the cosmetic.**
Issues that are technically incorrect but inaudible, or only matter for academic publication, go to the bottom of the list or are explicitly deferred.

---

## Verdict Schema

Each expert answer below follows this schema:

```
VERDICT:   [ VALID | WRONG | UNCERTAIN | DEBATABLE ]
SEVERITY:  [ FATAL | SIGNIFICANT | COSMETIC ]
SCOPE:     [ ALL METERS | SPECIFIC METER(S): ___ ]
FINDING:   [The expert's answer in their own words]
```

Fill every field before handing this document to the Technical Director. An incomplete schema entry will be treated as UNCERTAIN / SIGNIFICANT by default.

---

## Expert A — Classical Arabic Prosody & Rhythmic Theory

*This expert holds deep knowledge of ʿilm al-ʿarūḍ (Arabic prosody) and ʿilm al-īqāʿ (Arabic musical rhythm), including both theoretical tradition and contemporary performance practice.*

---

**A1.** The script places the kick on steps 1, 5, 9 for Masmoudi Kabir and calls this a "triple DUM." In authentic practice, does Masmoudi Kabir have three DUM strokes, or two — and does the step placement here (beats 1, 2, 3 of a 4/4 bar) correctly reflect the cycle's internal accent structure?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

**A2.** The script assigns Maqsum to Al-Taweel on the basis of the iambic (∪——) feel. Is Maqsum actually the canonical rhythmic companion to Al-Taweel in Egyptian tarab or Levantine maqam practice, or is this a reasonable but non-traditional pairing invented for this tool?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

**A3.** The script labels the corpus share of Al-Taweel at ~35%, Al-Kamil ~18%, Al-Baseet ~12%, Al-Wafir ~10%. Are these figures defensible against a named classical corpus, or are they approximations of uncertain provenance?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

## Expert B — Binary Step-Grid Encoding of Non-Western Rhythmic Cycles

*This expert understands the representational limits of step sequencer grids, timing arithmetic for compound and simple meters, and whether binary patterns can faithfully encode the prosodic structure they claim to represent.*

---

**B1.** The script uses identical step counts (12 steps) for both 3/4 (Al-Kamil) and 6/8 (Al-Wafir) but uses different beats_per_bar values (3 vs. 2), which changes step_s. Does this produce a perceptually correct difference between waltz-feel and compound-duple-feel, or does it collapse both into the same perceived subdivision?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

**B2.** The script encodes the ∪∪ double-short of Al-Wafir using adjacent hihat hits at steps 4+5 and 10+11, and explicitly states that "equidistant pulses are mathematically incapable" of encoding the fāṣila ṣughrā. Is this adjacent-hit encoding actually audible as a double-short to a listener, or does it sound like an eighth-note pair with no prosodic character?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

**B3.** The samaai_darij variant for Al-Kamil places the kick on step 3 (not step 1), on the reasoning that the DUM should land on the long syllable of the anapestic foot ∪∪—. Is this placement consistent with how Samaai Darij is actually played by Arabic percussionists, or does it produce a pattern that practitioners would not recognize?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

## Expert C — Physics-Based Drum Synthesis & DSP

*This expert understands digital audio synthesis, IIR filter design, panning laws, and the perceptual relationship between synthesized timbres and the Arabic percussion instruments they are intended to evoke.*

---

**C1.** The snare is synthesized as a 200 Hz sine body blended with filtered noise — a standard Western snare model. Does this timbre bear any resemblance to an Arabic riq (رق) or tabla stroke, or will it be perceived as a Western snare drum by Suno, pulling generated music away from Arabic character?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

**C2.** The kick's exponential pitch sweep produces a 500 ms transient (150 Hz → 50 Hz). The doumbek DUM is shorter and has a distinct membrane resonance this model does not include. Will Suno treat this sound as a kick drum and generate music accordingly, or will the timbre mismatch cause it to drift toward Western output?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

**C3.** The humanization applies uniform random jitter (±7 ms) and velocity variance (±12%) identically to all four instruments. In Arabic percussion practice, the relationship between a DUM and the ghost strokes around it is stylistically shaped, not random. Does uniform randomization produce a result that sounds humanized, or merely unstable?

```
VERDICT:   
SEVERITY:  
SCOPE:     
FINDING:   
```

---

## Your Output

Read all nine verdicts above. Apply the four decision criteria in order. Produce the following:

**Section 1 — Summary of fatal blockers**
List only the verdicts marked FATAL. For each: state the problem in one sentence, state which meter(s) it affects, and state why it is fatal under the decision criteria.

**Section 2 — Ranked action list**
Number each action starting from 1 (highest priority). For each action:
- State what must be changed in the script
- State which verdict(s) it resolves
- State the acceptance condition — how will we know this action succeeded

**Section 3 — Explicitly deferred items**
List verdicts you are deferring and why. Be specific. "Defer until post-Suno validation" is acceptable. "Not important" is not.

**Section 4 — The first thing to build**
One paragraph. Given everything above, what is the single next thing that should be coded, tested on Suno, and confirmed before anything else is touched? Justify the choice against the decision criteria.
