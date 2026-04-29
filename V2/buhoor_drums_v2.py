#!/usr/bin/env python3
# NEW SCRIPT FIXED.
"""
بحور الشعر — Arabic Poetic Meters Drum Generator
═══════════════════════════════════════════════════════════════
Generates drum loops reflecting the rhythmic soul of four
major Arabic poetic meters (بحور):

  الطويل  Al-Taweel  — فَعُولُن مَفَاعِيلُن  — 4/4  flowing / epic
  الكامل  Al-Kamil   — مُتَفَاعِلُن          — 3/4  ternary / waltz
  البسيط  Al-Baseet  — مُسْتَفْعِلُن فَاعِلُن — 4/4  march / declarative
  الوافر  Al-Wafir   — مُفَاعَلَتُن          — 6/8  rippling / lyrical

Each bahr produces 2-3 MP3 drum loops drawn from matching
Arabic rhythmic cycles (أوزان موسيقية).

Usage
─────
  python buhoor_drums.py                # interactive menu
  python buhoor_drums.py taweel         # one bahr by name
  python buhoor_drums.py kamil baseet   # multiple buhoor
  python buhoor_drums.py all            # everything
"""

import math
import numpy as np
import random
import os
import sys
import click
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
from pydub import AudioSegment

# ── Optional registry modules (additive; rendering does NOT depend on them) ──
try:
    from iqaa_patterns import IqaaPatternRegistry, get_pattern, validate_patterns
    from meter_registry import (
        load_registry,
        validate_registry,
        validate_buhoor_patterns,
        registry_summary,
    )
    _REGISTRY_AVAILABLE = True
except ImportError:
    _REGISTRY_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# Defaults — overridden at runtime by CLI options
SAMPLE_RATE = 44100
OUTPUT_DIR = "/mnt/user-data/outputs/buhoor"
TARGET_DURATION_S = 10.0

# ─────────────────────────────────────────────────────────────
#  DRUM SOUND SYNTHESIS
#  Same physics-based approach as the reference script.
#  kick = 808-style pitched sweep
#  snare = tonal body + noise burst
#  hihat = high-pass noise
#  crash = broadband noise, slow decay
# ─────────────────────────────────────────────────────────────


def _envelope(
    duration_s: float, attack: float = 0.002, decay_ratio: float = 0.8
) -> np.ndarray:
    n = int(SAMPLE_RATE * duration_s)
    env = np.zeros(n)
    atk_n = int(SAMPLE_RATE * attack)
    if atk_n:
        env[:atk_n] = np.linspace(0, 1, atk_n)
    dec_n = n - atk_n
    env[atk_n:] = np.exp(-np.linspace(0, decay_ratio * 10, dec_n))
    return env


def synth_kick(duration: float = 0.25) -> np.ndarray:
    """Doumbek DUM model — 240 Hz fundamental with log sweep to 200 Hz,
    plus a bandpass shell layer (400–800 Hz) for doumbek body resonance.
    Replaces the 808-style 150→50 Hz sub-bass sweep that triggered Western
    genre classification in Suno."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)
    f = 240.0 * np.exp(np.log(200.0 / 240.0) * t / duration)
    ph = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
    body = np.sin(ph) * _envelope(duration, 0.002, 0.8)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(2, [400, 800], btype="bandpass", fs=SAMPLE_RATE, output="sos")
    shell = sosfilt(sos, noise) * _envelope(duration, 0.001, 1.5) * 0.3
    return ((body + shell) * 0.9).astype(np.float32)


def synth_snare(duration: float = 0.15) -> np.ndarray:
    """Doumbek TEK/KA model — 3200 Hz ring tone blended with highpass noise
    at 2500 Hz.  Eliminates the 200 Hz sine body that caused Suno to classify
    output as Western pop/rock.  Mix: ring × 0.4, snap × 0.6."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)
    ring = np.sin(2 * np.pi * 3200 * t) * _envelope(duration, 0.001, 2.0) * 0.4
    noise = np.random.uniform(-1, 1, n)
    sos = butter(2, 2500, btype="highpass", fs=SAMPLE_RATE, output="sos")
    snap = sosfilt(sos, noise) * _envelope(duration, 0.001, 3.0) * 0.6
    return ((ring + snap) * 0.85).astype(np.float32)


def synth_hihat(duration: float = 0.08, open_hat: bool = False) -> np.ndarray:
    duration = 0.25 if open_hat else duration
    n = int(SAMPLE_RATE * duration)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(
        4, 5000, btype="high", fs=SAMPLE_RATE, output="sos"
    )  # riq jingles: more body than Western cymbals
    filt = sosfilt(sos, noise)
    decay = 1.2 if open_hat else 3.0
    return (filt * _envelope(duration, 0.001, decay) * 0.55).astype(np.float32)


def synth_crash(duration: float = 1.20) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, 4000, btype="high", fs=SAMPLE_RATE, output="sos")
    filt = sosfilt(sos, noise)
    return (filt * _envelope(duration, 0.003, 0.5) * 0.45).astype(np.float32)


SYNTH_MAP = {
    "kick": synth_kick,
    "snare": synth_snare,
    "hihat": synth_hihat,
    "crash": synth_crash,
}

# ─────────────────────────────────────────────────────────────
#  BUHOOR DEFINITIONS
#
#  Timing model
#  ────────────
#  step_duration = beats_per_bar × 60 / (bpm × steps_per_bar)
#
#  4/4  meters : beats_per_bar=4, steps_per_bar=16 (16th-note grid)
#               bpm = quarter-note tempo
#
#  3/4  meters : beats_per_bar=3, steps_per_bar=12 (16th-note grid)
#               bpm = quarter-note tempo
#
#  6/8  meters : beats_per_bar=2, steps_per_bar=12 (16th-note grid)
#               bpm = dotted-quarter tempo (the "felt" beat)
#               step = 60 / (bpm × 6)  ← 1/12 of a 6/8 bar
#
# ─────────────────────────────────────────────────────────────

BUHOOR: dict = {
    # ╔══════════════════════════════════════════════════════════╗
    # ║  الطويل — Al-Taweel                                     ║
    # ║  فَعُولُن مَفَاعِيلُن × 2                               ║
    # ║  Syllabic pattern :  ∪—— | ∪———                        ║
    # ║  Binary (iambic), 4/4, moderate — the "king of meters" ║
    # ║  ~35 % of classical Arabic corpus                       ║
    # ╚══════════════════════════════════════════════════════════╝
    "taweel": {
        "arabic": "الطويل",
        "taf_eela": "فَعُولُن مَفَاعِيلُن",
        "transliteration": "fa'oolun mafa'eelun",
        "syllable_pattern": "∪—— | ∪———",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 12,  # mora grid: 1 step = 1 mora (∪), 2 steps = 1 long (—)
        "description": (
            "Al-Taweel is the undisputed king — the most used meter in Arabic poetry, "
            "covering roughly 35 % of the classical corpus. Its taf'eela 'fa'oolun mafa'eelun' "
            "creates an iambic (short→long) flow that breathes like a long sentence. "
            "Rhythmically it lives in 4/4 with a slight upbeat/anacrusis feel. "
            "Wahda Kabeera (وحدة كبيرة) is the primary and most traditional cycle for this meter. "
            "Fallahi (فلاحي) provides folk energy. "
            "Maqsum (مقسوم) is an experimental variant — non-traditional for Al-Taweel "
            "and not found in classical Egyptian tarab or Levantine maqam practice."
        ),
        "variants": [
            # ── Wahda is the canonical/primary variant (Action 3) ──
            {
                "name": "wahda",
                "label": "Wahda Kabeera (وحدة كبيرة)",
                "bpm": 72,
                "mood": "Meditative, spacious",
                "why": (
                    "Slow 4/4 with wide open space — the long vowels of mafa'eelun "
                    "need room to resonate. Perfect for elegiac or philosophical verse. "
                    "Primary and most traditional cycle for Al-Taweel."
                ),
                # IOI: 1, 2, 2, 1, 2, 2, 2  →  ∪ — — | ∪ — — —  (fa'oolun mafa'eelun)
                # Sparse — meditative: DUM only on bar 1, single ghost snare, dotted hihat
                "patterns": {
                    "kick": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                    "hihat": [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
            {
                "name": "maqsum",
                "label": "Maqsum (مقسوم)",
                "bpm": 90,
                "mood": "Narrative, dignified",
                "why": (
                    "NON-TRADITIONAL PAIRING. Maqsum does not appear in classical Egyptian tarab "
                    "or Levantine maqam settings of Al-Taweel. Included as an experimental variant. "
                    "Prefer Wahda for Suno conditioning. "
                    "The DUM on beat 1 anchors the long syllable (—) of fa'oolun; "
                    "all seven mora-onset positions are voiced."
                ),
                # IOI: 1, 2, 2, 1, 2, 2, 2  →  ∪ — — | ∪ — — —
                # All 7 onset positions voiced: 0(∪) 1(—) 3(—) 5(∪) 6(—) 8(—) 10(—)
                "patterns": {
                    "kick": [1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0],
                    "snare": [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                    "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
            {
                "name": "fallahy",
                "label": "Fallahi (فلاحي)",
                "bpm": 100,
                "mood": "Folk, earthy, energetic",
                "why": (
                    "Rustic 4/4 with syncopation — used in zajal and Levantine folk "
                    "poetry recitation. The cross-rhythm hihat mirrors the iambic push."
                ),
                # IOI: 1, 2, 2, 1, 2, 2, 2  →  ∪ — — | ∪ — — —
                # Syncopated folk feel — kick on 0,3,5,10; TEK on 6,9
                "patterns": {
                    "kick": [1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0],
                    "snare": [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0],
                    "hihat": [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
        ],
    },
    # ╔══════════════════════════════════════════════════════════╗
    # ║  الكامل — Al-Kamil                                      ║
    # ║  مُتَفَاعِلُن × 3                                        ║
    # ║  Syllabic pattern : ∪∪— | ∪∪— | ∪∪—                   ║
    # ║  Ternary (ascending), 3/4 — "the complete"             ║
    # ║  ~18 % of corpus; favored for ghazal & love verse      ║
    # ╚══════════════════════════════════════════════════════════╝
    "kamil": {
        "arabic": "الكامل",
        "taf_eela": "مُتَفَاعِلُن",
        "transliteration": "mutafa'ilun",
        "syllable_pattern": "∪∪—∪— | ∪∪—∪— | ∪∪—∪—",
        "time_signature": (3, 4),
        "beats_per_bar": 3,
        "steps_per_bar": 21,  # mora grid: mutafa'ilun = ∪∪—∪— = 7 morae × 3 feet
        "description": (
            "Al-Kamil — 'the complete' — is the second most used meter. "
            "Its taf'eela mutafa'ilun (∪∪—∪—, seven morae) is unmistakably ascending — "
            "two short pickup syllables rush forward into the long landing, then another "
            "short-long tail. It carries warmth, emotion, and a dancing quality, hence its "
            "dominance in love poetry. In music it belongs to 3/4. "
            "Samaai (سماعي) cycles are its natural home. "
            "[BPM here = quarter-note beat; 3 per bar]"
        ),
        "variants": [
            {
                "name": "samaai_darij",
                "label": "Samaai Darij (سماعي دارج)",
                "bpm": 104,
                "mood": "Lyrical, elegant, danceable",
                "why": (
                    "3/4 cycle — mutafa'ilun (∪∪—∪—) is ascending/anapestic. "
                    "DUM falls on step 0 (bar downbeat), anchoring the foot entry; "
                    "TEK lands on the — positions (2, 5 within each foot) "
                    "to voice the long-syllable landings."
                ),
                # IOI: 1, 1, 2, 1, 2  per foot × 3  →  ∪∪—∪— × 3  (mutafa'ilun)
                # Foot onsets: 0,1,2,4,5 | 7,8,9,11,12 | 14,15,16,18,19
                # DUM at step 0 (fix plan: move from step 2 to step 0)
                "patterns": {
                    "kick": [
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ],
                    "snare": [
                        0,
                        0,
                        1,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        1,
                        0,
                        0,
                    ],
                    "hihat": [
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                    ],
                    "crash": [
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ],
                },
            },
            {
                "name": "andalusi_flow",
                "label": "Andalusian 6/8 Flow (أندلسي)",
                "bpm": 88,
                "mood": "Flowing, Andalusian, gentle",
                "why": (
                    "NOTE: Previously mislabeled 'Jurjina'. Real Jurjina is a strict "
                    "10/8 cycle and cannot fit a 21-step grid. This is an original "
                    "Andalusian muwashshah-style pattern. Kick falls on the — (long) "
                    "positions within each foot for a gentler anacrustic feel."
                ),
                # IOI: 1, 1, 2, 1, 2  per foot × 3  →  ∪∪—∪— × 3
                # Kick on first — of each foot (abs steps 2, 9, 16); dotted hihat (every 3)
                "patterns": {
                    "kick": [
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                    ],
                    "snare": [
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                    ],
                    "hihat": [
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                    ],
                    "crash": [
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ],
                },
            },
            {
                "name": "muwashshah_syncopated",
                "label": "Muwashshah Syncopated (موشح متشابك)",
                "bpm": 116,
                "mood": "Upbeat, festive, celebratory",
                "why": (
                    "NOTE: Previously mislabeled 'Dawr Hindi'. Real Dawr Hindi is a "
                    "strict 7/8 cycle (3+2+2) with no 3/4 equivalent in Arabic practice. "
                    "This is an original syncopated muwashshah-flavored 3/4 pattern. "
                    "Common in tarab gatherings."
                ),
                # IOI: 1, 1, 2, 1, 2  per foot × 3  →  ∪∪—∪— × 3
                # Syncopated: kick anticipates foot entries; dense hihat
                "patterns": {
                    "kick": [
                        1,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                    ],
                    "snare": [
                        0,
                        0,
                        1,
                        0,
                        1,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                        0,
                        0,
                        1,
                        0,
                        0,
                        1,
                        0,
                    ],
                    "hihat": [
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                        1,
                        1,
                        0,
                    ],
                    "crash": [
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ],
                },
            },
        ],
    },
    # ╔══════════════════════════════════════════════════════════╗
    # ║  البسيط — Al-Baseet                                     ║
    # ║  مُسْتَفْعِلُن فَاعِلُن × 2                              ║
    # ║  Syllabic pattern : ——∪— | —∪—                         ║
    # ║  Binary (heavy), 4/4 — authoritative, declarative      ║
    # ║  ~12 % of corpus; satire, pride, complaint              ║
    # ╚══════════════════════════════════════════════════════════╝
    "baseet": {
        "arabic": "البسيط",
        "taf_eela": "مُسْتَفْعِلُن فَاعِلُن",
        "transliteration": "mustaf'ilun fa'ilun",
        "syllable_pattern": "——∪— | —∪—",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 12,  # mora grid: 1 step = 1 mora (∪), 2 steps = 1 long (—)
        "description": (
            "Al-Baseet — 'the spread out' — opens with two consecutive long syllables (——) "
            "that land like a firm step. This immediate weight gives it authority: "
            "it was the meter of satire, complaint, pride, and declaration. "
            "Unlike Al-Taweel's flowing iamb, Al-Baseet plants its feet first "
            "and then moves. Masmoudi Kabir (المصمودي الكبير) with its two-DUM structure "
            "mirrors this perfectly. Also suited to military march and Zaffa."
        ),
        "variants": [
            {
                "name": "masmoudi_kabir",
                "label": "Masmoudi Kabir (مصمودي كبير)",
                "bpm": 100,
                "mood": "Heavy, powerful, declarative",
                "why": (
                    "The heaviest Arabic 4/4 cycle. Authentic two-DUM structure "
                    "(Expert A): DUM . DUM . . . TEK . DUM . TEK . "
                    "Replaces the non-standard triple-DUM pattern. "
                    "The two opening DUMs mirror the spondaic —— of mustaf'ilun. "
                    "Used in classical Egyptian tarab."
                ),
                # IOI: 2, 2, 1, 2, 2, 1, 2  →  — — ∪ — | — ∪ —  (mustaf'ilun fa'ilun)
                # [DUM . DUM . . . TEK . DUM . TEK .]
                "patterns": {
                    "kick": [1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],
                    "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
            {
                "name": "march",
                "label": "Askari March (مارش عسكري)",
                "bpm": 112,
                "mood": "Martial, decisive, strict",
                "why": (
                    "The —— opening of mustaf'ilun is literally a left-right march step. "
                    "Arabs used Al-Baseet in warrior poetry (حماسة) — this cycle "
                    "brings that energy to life. Kick on all — positions, snare on ∪."
                ),
                # IOI: 2, 2, 1, 2, 2, 1, 2  →  — — ∪ — | — ∪ —
                # Kick on every — position (0,2,5,7,10); snare on ∪ (4,9)
                "patterns": {
                    "kick": [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0],
                    "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
                    "hihat": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
            {
                "name": "zaffa",
                "label": "Zaffa (زفة) — Processional",
                "bpm": 96,
                "mood": "Festive, ceremonial, proud",
                "why": (
                    "Wedding processional. Al-Baseet's declarative character suits "
                    "pride and celebration — the Zaffa cycle adds ceremony and swing."
                ),
                # IOI: 2, 2, 1, 2, 2, 1, 2  →  — — ∪ — | — ∪ —
                # Double kick opening (——), festive syncopation after
                "patterns": {
                    "kick": [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
                    "hihat": [1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
        ],
    },
    # ╔══════════════════════════════════════════════════════════╗
    # ║  الوافر — Al-Wafir                                      ║
    # ║  مُفَاعَلَتُن × 2 + فَعُولُن                             ║
    # ║  Syllabic pattern : ∪—∪∪— | ∪—∪∪— | ∪——              ║
    # ║  Ternary-hybrid, 6/8 — rippling, abundant, lyrical     ║
    # ║  ~10 % of corpus; ghazal, love, longing                ║
    # ╚══════════════════════════════════════════════════════════╝
    "wafir": {
        "arabic": "الوافر",
        "taf_eela": "مُفَاعَلَتُن",
        "transliteration": "mufa'alatun",
        "syllable_pattern": "∪—∪∪— | ∪—∪∪—",
        "time_signature": (6, 8),
        "beats_per_bar": 2,  # 2 dotted-quarter pulses per bar
        "steps_per_bar": 14,  # mora grid: mufa'alatun = ∪—∪∪— = 7 morae × 2 feet
        "description": (
            "Al-Wafir — 'the abundant / rippling' — has an undulating wave-like quality. "
            "Mufa'alatun (∪—∪∪—) rolls forward: short pickup, long crest, then two quick "
            "adjacent ripples (∪∪), then another long crest. "
            "The ∪∪ pair is encoded as two ADJACENT step-grid hits — the only way to "
            "represent the double-short in a mora sequencer. Equidistant pulses would "
            "produce IOI 1-2 (a long), which misrepresents the fāṣila ṣughrā (فاصلة صغرى). "
            "Kick anchors the first — of each foot (steps 1 and 8). "
            "[BPM here = dotted-quarter note; 2 per bar]"
        ),
        "variants": [
            {
                "name": "muwashshah",
                "label": "Muwashshah (موشح أندلسي)",
                "bpm": 80,
                "mood": "Elegant, Andalusian, flowing",
                "why": (
                    "Andalusian muwashshah style, slow 6/8. Kick anchors the first — "
                    "of each foot (steps 1, 8). Snare voices the second — (steps 5, 12). "
                    "Hihat traces ∪ at foot-start (0, 7) and ∪∪ pairs (3-4, 10-11)."
                ),
                # IOI: 1, 2, 1, 1, 2  per foot × 2  →  ∪—∪∪— × 2  (mufa'alatun)
                # Foot 1 onsets: 0(∪), 1(—), 3(∪), 4(∪), 5(—)
                # Foot 2 onsets: 7(∪), 8(—), 10(∪), 11(∪), 12(—)
                "patterns": {
                    "kick": [0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0],
                    "hihat": [1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
            {
                "name": "wafir_ripple",
                "label": "Wafir Ripple (وافر متموج)",
                "bpm": 92,
                "mood": "Forward-moving, rippling, lyrical",
                "why": (
                    "NOTE: Previously mislabeled 'Jurjina'. Real Jurjina is 10/8 and "
                    "cannot fit this 14-step grid. Both — positions per foot are voiced "
                    "on the kick (steps 1,5,8,12), giving the rippling wave feel. "
                    "Hihat adjacent hits (3-4, 10-11) correctly encode the ∪∪ double-short."
                ),
                # IOI: 1, 2, 1, 1, 2  per foot × 2  →  ∪—∪∪— × 2
                # Kick on both — per foot: 1,5,8,12; snare on foot-start ∪ (0,7)
                "patterns": {
                    "kick": [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
                    "snare": [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                    "hihat": [1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            },
        ],
    },
}

# ─────────────────────────────────────────────────────────────
#  HUMANIZATION
#  Subtle timing jitter + velocity variance → natural feel.
#  Arabic percussion is organic; strict quantization sounds wrong.
# ─────────────────────────────────────────────────────────────


def humanize(
    pattern: list,
    timing_jitter: float = 0.007,
    velocity_variance: float = 0.12,
    base_velocity: float = 1.0,
) -> list[tuple]:
    """Return [(step_idx, time_offset_s, velocity_mul), …] for each hit.

    Args:
        timing_jitter:     Max ±seconds of per-hit timing offset (default 0.007).
        velocity_variance: Max ±fraction of per-hit velocity nudge (default 0.12).
        base_velocity:     Per-channel base level before variance is applied.
                           DUM (kick) = 1.00; TEK/KA (snare) = 0.50;
                           hihat = 0.45; crash = 0.70.
    """
    hits = []
    for i, hit in enumerate(pattern):
        if hit:
            t_off = random.uniform(-timing_jitter, timing_jitter)
            vel = base_velocity + random.uniform(-velocity_variance, velocity_variance)
            vel = max(0.2, min(1.4, vel))
            hits.append((i, t_off, vel))
    return hits


# ─────────────────────────────────────────────────────────────
#  RENDER
# ─────────────────────────────────────────────────────────────


def render_variant(
    bahr_key: str,
    variant: dict,
    bars: int = 4,
    *,
    output_dir: str = OUTPUT_DIR,
    bitrate: str = "192k",
    jitter: float = 0.007,
    velocity_variance: float = 0.12,
    bpm_override: int | None = None,
    quiet: bool = False,
) -> str:
    """Synthesize one rhythmic variant → MP3. Returns the output path."""
    bahr = BUHOOR[bahr_key]
    steps_per_bar = bahr["steps_per_bar"]
    beats_per_bar = bahr["beats_per_bar"]
    bpm = bpm_override if bpm_override is not None else variant["bpm"]

    # Derived timing
    step_s = beats_per_bar * 60.0 / (bpm * steps_per_bar)
    total_steps = steps_per_bar * bars
    total_n = int(total_steps * step_s * SAMPLE_RATE) + SAMPLE_RATE  # +1 s tail

    mix = np.zeros((total_n, 2), dtype=np.float32)

    sounds = {name: fn() for name, fn in SYNTH_MAP.items()}

    # Constant-power panning law: L = cos(p·π/2), R = sin(p·π/2)
    # Ensures L²+R²=1 regardless of position, preventing the 12 dB headroom
    # imbalance that linear amplitude scaling (e.g. 0.25 / 1.00) would cause.
    def _cpan(p: float) -> tuple:
        a = p * (math.pi / 2)
        return math.cos(a), math.sin(a)

    panning = {
        "kick": _cpan(0.50),  # centre
        "snare": _cpan(0.50),  # centre
        "hihat": _cpan(0.60),  # mild right (was 0.75)
        "crash": _cpan(0.40),  # mild left  (was 0.25)
    }

    # Per-channel base velocities (Action 4).
    # DUM strokes are the structural anchor; ghost strokes (TEK, KA) sit
    # consistently 40–60 % quieter. Uniform variance without a base level
    # collapses this hierarchy.
    BASE_VELOCITY = {
        "kick": 1.00,
        "snare": 0.50,
        "hihat": 0.45,
        "crash": 0.70,
    }

    channel_peaks: dict[str, float] = {}

    for inst, base_pat in variant["patterns"].items():
        sound = sounds[inst]
        pan_l, pan_r = panning.get(inst, (0.75, 0.75))
        full_pat = base_pat * bars
        hits = humanize(
            full_pat,
            timing_jitter=jitter,
            velocity_variance=velocity_variance,
            base_velocity=BASE_VELOCITY.get(inst, 1.0),
        )

        ch_peak = 0.0
        for step_idx, t_off, vel in hits:
            t_sec = step_idx * step_s + t_off
            start = max(0, int(t_sec * SAMPLE_RATE))
            end = min(start + len(sound), total_n)
            n = end - start
            if n > 0:
                mix[start:end, 0] += sound[:n] * pan_l * vel
                mix[start:end, 1] += sound[:n] * pan_r * vel
            ch_peak = max(ch_peak, vel)
        channel_peaks[inst] = ch_peak

    if not quiet:
        peak_str = "  ".join(
            f"{ch}:{v*100:.0f}%" for ch, v in channel_peaks.items() if v > 0
        )
        click.echo(f"    peak vel  │ {peak_str}")

    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.9
    pcm = (mix * 32767).astype(np.int16)

    ts = bahr["time_signature"]
    fname = f"{bahr_key}_{variant['name']}_{bpm}bpm"
    wav_p = f"/tmp/{fname}.wav"
    mp3_p = os.path.join(output_dir, fname + ".mp3")

    wavfile.write(wav_p, SAMPLE_RATE, pcm)
    audio = AudioSegment.from_wav(wav_p)
    audio.export(
        mp3_p,
        format="mp3",
        bitrate=bitrate,
        tags={
            "title": f"{bahr['arabic']} — {variant['label']}",
            "artist": "Buhoor Drum Generator",
            "album": "Arabic Poetic Meters / بحور الشعر",
            "comment": f"{bpm} BPM | {bars} bars | {ts[0]}/{ts[1]} | {variant['mood']}",
        },
    )
    os.remove(wav_p)
    return mp3_p


# ─────────────────────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────


def _wrap(text: str, width: int = 70, indent: str = "  ") -> str:
    words, line, lines = text.split(), indent, []
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line)
            line = indent + w
        else:
            line += (" " if line.strip() else "") + w
    lines.append(line)
    return "\n".join(lines)


def print_header():
    print("\n╔" + "═" * 56 + "╗")
    print("║" + "   بحور الشعر — Arabic Poetic Meters Drum Gen   ".center(56) + "║")
    print("╚" + "═" * 56 + "╝\n")


def print_bahr_header(key: str):
    b = BUHOOR[key]
    ts = b["time_signature"]
    print(f"\n{'═'*60}")
    print(f"  {b['arabic']}  —  Al-{key.title()}")
    print(f"  تفعيلة : {b['taf_eela']}")
    print(f"  Pattern: {b['syllable_pattern']}")
    print(f"  Meter  : {ts[0]}/{ts[1]}")
    print(f"{'═'*60}")
    print(_wrap(b["description"]))
    print()


def print_pattern_grid(variant: dict, bpm_override: int | None = None):
    effective_bpm = bpm_override if bpm_override is not None else variant["bpm"]
    bpm_label = (
        f"{effective_bpm} BPM  (override; default {variant['bpm']})"
        if bpm_override is not None
        else f"{variant['bpm']} BPM"
    )
    print(f"  ▶ {variant['label']}  │  {bpm_label}  │  {variant['mood']}")
    print(f"    Rationale: {variant['why']}")
    print(f"    {'─'*50}")
    for inst in ("kick", "snare", "hihat", "crash"):
        if inst not in variant["patterns"]:
            continue
        steps = variant["patterns"][inst]
        grid = "".join("█" if s else "·" for s in steps)
        n_hits = sum(steps)
        print(f"    {inst:<8}│ {grid}  ({n_hits})")
    print()


# ─────────────────────────────────────────────────────────────
#  GENERATE ONE BAHR
# ─────────────────────────────────────────────────────────────


def generate_bahr(
    key: str,
    target_s: float = TARGET_DURATION_S,
    *,
    variant_filter: tuple[str, ...] = (),
    output_dir: str = OUTPUT_DIR,
    bitrate: str = "192k",
    jitter: float = 0.007,
    velocity_variance: float = 0.12,
    bpm_override: int | None = None,
    quiet: bool = False,
) -> list[str]:
    """Render all (or selected) variants for one bahr. Returns list of MP3 paths."""
    if not quiet:
        print_bahr_header(key)
    bahr = BUHOOR[key]
    paths = []
    for variant in bahr["variants"]:
        if variant_filter and variant["name"] not in variant_filter:
            continue
        effective_bpm = bpm_override if bpm_override is not None else variant["bpm"]
        bar_s = bahr["beats_per_bar"] * 60.0 / effective_bpm
        bars = math.ceil(target_s / bar_s)
        if not quiet:
            print_pattern_grid(variant, bpm_override=bpm_override)
        path = render_variant(
            key,
            variant,
            bars,
            output_dir=output_dir,
            bitrate=bitrate,
            jitter=jitter,
            velocity_variance=velocity_variance,
            bpm_override=bpm_override,
        )
        size_kb = os.path.getsize(path) // 1024
        click.echo(f"    ✅  {os.path.basename(path)}  ({size_kb} KB)\n")
        paths.append(path)
    return paths


# ─────────────────────────────────────────────────────────────
#  INTERACTIVE MENU
# ─────────────────────────────────────────────────────────────


def interactive_menu() -> list[str]:
    print_header()
    click.echo("  Select a bahr to generate drum loops for:\n")
    keys = list(BUHOOR.keys())
    for i, k in enumerate(keys, 1):
        b = BUHOOR[k]
        ts = b["time_signature"]
        nv = len(b["variants"])
        click.echo(
            f"  [{i}] {b['arabic']:<14}  Al-{k.title():<10}  "
            f"{ts[0]}/{ts[1]}  —  {nv} variants"
        )
    click.echo(f"  [{len(keys)+1}] All buhoor\n")

    while True:
        raw = click.prompt("  Your choice", prompt_suffix="").strip()
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(keys):
                return [keys[n - 1]]
            if n == len(keys) + 1:
                return keys
        elif raw.lower() in keys:
            return [raw.lower()]
        elif raw.lower() == "all":
            return keys
        click.echo("  Please enter a valid number or bahr name.")


# ─────────────────────────────────────────────────────────────
#  VALID BAHR NAMES (for click validation)
# ─────────────────────────────────────────────────────────────

BAHR_NAMES = list(BUHOOR.keys())


# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "buhoor",
    nargs=-1,
    metavar="[BAHR]...",
)
@click.option(
    "--all",
    "select_all",
    is_flag=True,
    help="Generate all buhoor (same as passing every name).",
)
@click.option(
    "-o",
    "--output-dir",
    default=OUTPUT_DIR,
    show_default=True,
    envvar="BUHOOR_OUTPUT_DIR",
    help="Directory for output MP3 files.",
    type=click.Path(file_okay=False),
)
@click.option(
    "-d",
    "--duration",
    default=TARGET_DURATION_S,
    show_default=True,
    type=click.FloatRange(min=1.0),
    metavar="SECONDS",
    help="Target loop duration in seconds.",
)
@click.option(
    "-v",
    "--variant",
    "variant_filter",
    multiple=True,
    metavar="NAME",
    help=(
        "Render only the named variant(s). "
        "Repeatable: -v maqsum -v wahda. "
        "Default: all variants."
    ),
)
@click.option(
    "--seed",
    default=42,
    show_default=True,
    type=int,
    help="Random seed for humanization (use -1 for a random seed).",
)
@click.option(
    "--jitter",
    default=0.007,
    show_default=True,
    type=click.FloatRange(min=0.0, max=0.05),
    metavar="SECONDS",
    help="Max ±timing jitter per hit in seconds.",
)
@click.option(
    "--velocity-variance",
    default=0.12,
    show_default=True,
    type=click.FloatRange(min=0.0, max=1.0),
    help="Max ±velocity nudge fraction (0 = robotic, 1 = chaotic).",
)
@click.option(
    "--bpm",
    "bpm_override",
    default=None,
    type=click.IntRange(min=20, max=300),
    metavar="BPM",
    help=(
        "Override the tempo for every rendered variant. "
        "Accepts 20–300 BPM. Default: each variant's own BPM."
    ),
)
@click.option(
    "--bitrate",
    default="192k",
    show_default=True,
    type=click.Choice(["128k", "192k", "256k", "320k"], case_sensitive=False),
    help="MP3 output bitrate.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress descriptions and pattern grids; show only file output.",
)
@click.option(
    "-l",
    "--list",
    "list_buhoor",
    is_flag=True,
    help="List available buhoor (and their variants) then exit.",
)
@click.option(
    "--data",
    "data_path",
    default=None,
    type=click.Path(dir_okay=False),
    metavar="PATH",
    help=(
        "Path to arabic_rhythm_data.json. "
        "Defaults to arabic_rhythm_data.json next to this script. "
        "Required for --validate."
    ),
)
@click.option(
    "--validate",
    "run_validate",
    is_flag=True,
    help=(
        "Validate pattern coverage against the JSON registry, then exit. "
        "Requires --data or a co-located arabic_rhythm_data.json."
    ),
)
@click.version_option("2.0.0", "-V", "--version")
def main(
    buhoor,
    select_all,
    output_dir,
    duration,
    variant_filter,
    seed,
    jitter,
    velocity_variance,
    bpm_override,
    bitrate,
    quiet,
    list_buhoor,
    data_path,
    run_validate,
):
    """بحور الشعر — Arabic Poetic Meters Drum Generator

    \b
    Generate drum loops for one or more Arabic poetic meters (بحور):
      taweel   الطويل   4/4   epic / flowing
      kamil    الكامل   3/4   lyrical / waltz
      baseet   البسيط   4/4   march / declarative
      wafir    الوافر   6/8   rippling / lyrical

    \b
    Examples:
      python buhoor_drums.py                         # interactive menu
      python buhoor_drums.py taweel                  # one bahr
      python buhoor_drums.py kamil baseet            # two buhoor
      python buhoor_drums.py --all                   # everything
      python buhoor_drums.py taweel -v maqsum        # one variant only
      python buhoor_drums.py --all -d 30 -q          # 30 s, quiet
      python buhoor_drums.py --all --seed -1         # random humanization
    """
    # ── --list: just show the catalogue and exit ──────────────
    if list_buhoor:
        print_header()
        for k in BUHOOR:
            b = BUHOOR[k]
            ts = b["time_signature"]
            click.echo(f"  {b['arabic']:<14}  al-{k:<10}  {ts[0]}/{ts[1]}")
            for v in b["variants"]:
                click.echo(f"      • {v['name']:<28}  {v['bpm']} BPM  {v['mood']}")
            click.echo()
        return

    # ── --validate: check pattern coverage and exit ───────────
    if run_validate:
        if not _REGISTRY_AVAILABLE:
            raise click.UsageError(
                "--validate requires iqaa_patterns.py and meter_registry.py "
                "to be importable from the same directory as this script."
            )
        # Resolve JSON path
        _script_dir = Path(__file__).parent
        _json_path = (
            Path(data_path) if data_path
            else _script_dir / "arabic_rhythm_data.json"
        )
        click.echo("\n  Registry validation")
        click.echo("  ═══════════════════")

        # 1) Internal sanity check on IqaaPatternRegistry itself
        pat_errors = validate_patterns()
        if pat_errors:
            click.echo("  ❌  IqaaPatternRegistry has invalid entries:")
            for e in pat_errors:
                click.echo(f"       {e}")
        else:
            click.echo(f"  ✅  IqaaPatternRegistry: all patterns well-formed")

        # 2) Cross-check BUHOOR dict variants against IqaaPatternRegistry
        click.echo()
        click.echo("  BUHOOR dict coverage (current 4 meters):")
        buhoor_gaps = validate_buhoor_patterns(BUHOOR, IqaaPatternRegistry)
        if buhoor_gaps:
            click.echo(f"  ❌  {len(buhoor_gaps)} BUHOOR variant(s) missing patterns:")
            for g in buhoor_gaps:
                click.echo(g)
        else:
            total_variants = sum(len(b["variants"]) for b in BUHOOR.values())
            click.echo(
                f"  ✅  All {total_variants} BUHOOR variants present in "
                f"IqaaPatternRegistry — 0 missing"
            )

        # 3) JSON registry coverage (if file is available)
        click.echo()
        if _json_path.exists():
            try:
                json_registry = load_registry(_json_path)
                click.echo(
                    f"  JSON registry  ({_json_path.name}):"
                )
                click.echo(registry_summary(json_registry, IqaaPatternRegistry))
                click.echo()
                current_meters = list(BUHOOR.keys())
                json_gaps_current = validate_registry(
                    json_registry, IqaaPatternRegistry,
                    meter_filter=current_meters,
                )
                json_gaps_all = validate_registry(
                    json_registry, IqaaPatternRegistry,
                )
                click.echo(
                    f"  JSON gaps (current 4 meters only) : "
                    f"{len(json_gaps_current)}"
                )
                click.echo(
                    f"  JSON gaps (all meters)            : "
                    f"{len(json_gaps_all)}"
                )
                if json_gaps_all:
                    click.echo(
                        "  (gaps listed below — craft patterns in iqaa_patterns.py "
                        "to close them)"
                    )
                    for g in json_gaps_all[:20]:  # cap output to 20 lines
                        click.echo(g)
                    if len(json_gaps_all) > 20:
                        click.echo(f"  … and {len(json_gaps_all) - 20} more")
            except (FileNotFoundError, ValueError) as exc:
                click.echo(f"  ⚠  Could not load JSON registry: {exc}")
        else:
            click.echo(
                f"  ⚠  JSON file not found at {_json_path}  "
                f"(pass --data <path> to specify location)"
            )
        click.echo()
        return

    # ── Validate BAHR arguments ───────────────────────────────
    bad = [a for a in buhoor if a not in BUHOOR]
    if bad:
        raise click.BadArgumentUsage(
            f"Unknown bahr: {', '.join(bad)}. "
            f"Valid names: {', '.join(BUHOOR)} (or use --all)."
        )

    # ── Seed RNGs ─────────────────────────────────────────────
    effective_seed = random.randint(0, 2**31) if seed == -1 else seed
    random.seed(effective_seed)
    np.random.seed(effective_seed)
    if not quiet and seed == -1:
        click.echo(f"  Random seed: {effective_seed}\n")

    # ── Select buhoor ─────────────────────────────────────────
    if select_all or (not buhoor and not list_buhoor):
        if not buhoor:
            # No args and no --all → interactive menu
            if not select_all:
                selected = interactive_menu()
            else:
                selected = BAHR_NAMES
        else:
            selected = BAHR_NAMES
    else:
        selected = list(buhoor)

    # ── Create output dir ─────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)

    if not quiet:
        click.echo(
            f"\n  Synthesizing ~{duration:.0f} s per variant "
            f"(seed={effective_seed}) …\n"
        )

    # ── Render ────────────────────────────────────────────────
    all_paths: list[str] = []
    for key in selected:
        all_paths.extend(
            generate_bahr(
                key,
                target_s=duration,
                variant_filter=variant_filter,
                output_dir=output_dir,
                bitrate=bitrate,
                jitter=jitter,
                velocity_variance=velocity_variance,
                bpm_override=bpm_override,
                quiet=quiet,
            )
        )

    # ── Summary ───────────────────────────────────────────────
    click.echo(f"\n{'═'*60}")
    click.echo(f"  Output directory : {output_dir}")
    click.echo(f"  Total files      : {len(all_paths)}")
    for p in all_paths:
        size_kb = os.path.getsize(p) // 1024
        click.echo(f"    • {os.path.basename(p):50s}  ({size_kb} KB)")
    click.echo()


if __name__ == "__main__":
    main()
