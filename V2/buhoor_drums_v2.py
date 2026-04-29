#!/usr/bin/env python3
"""
بحور الشعر — Arabic Poetic Meters Drum Generator
═══════════════════════════════════════════════════════════════
Generates drum loops reflecting the rhythmic soul of the 13
major Arabic poetic meters (بحور).

Usage
─────
  python buhoor_drums_v2.py                # interactive menu
  python buhoor_drums_v2.py taweel         # one bahr by name
  python buhoor_drums_v2.py kamil baseet   # multiple buhoor
  python buhoor_drums_v2.py --all          # everything
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
    sos = butter(4, 5000, btype="high", fs=SAMPLE_RATE, output="sos")
    filt = sosfilt(sos, noise)
    decay = 1.2 if open_hat else 3.0
    return (filt * _envelope(duration, 0.001, decay) * 0.55).astype(np.float32)


def synth_crash(duration: float = 1.20) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, 4000, btype="high", fs=SAMPLE_RATE, output="sos")
    filt = sosfilt(sos, noise)
    return (filt * _envelope(duration, 0.003, 0.5) * 0.45).astype(np.float32)


def synth_ka(duration: float = 0.06) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)
    ring = np.sin(2 * np.pi * 5000 * t) * _envelope(duration, 0.001, 4.0) * 0.3
    noise = np.random.uniform(-1, 1, n)
    sos = butter(2, 4000, btype="highpass", fs=SAMPLE_RATE, output="sos")
    snap = sosfilt(sos, noise) * _envelope(duration, 0.001, 5.0) * 0.7
    return ((ring + snap) * 0.60).astype(np.float32)


SYNTH_MAP = {
    "kick": synth_kick,
    "snare": synth_snare,
    "hihat": synth_hihat,
    "crash": synth_crash,
    "ka": synth_ka,
}

# ─────────────────────────────────────────────────────────────
#  BUHOOR DEFINITIONS
# ─────────────────────────────────────────────────────────────

BUHOOR: dict = {
    "taweel": {
        "arabic": "الطويل",
        "taf_eela": "فَعُولُن مَفَاعِيلُن",
        "transliteration": "fa'oolun mafa'eelun",
        "syllable_pattern": "∪—— | ∪———",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 12,
        "description": "Al-Taweel is the undisputed king — the most used meter in Arabic poetry. Its taf'eela creates an iambic flow that breathes like a long sentence.",
        "variants": [
            {
                "name": "wahda",
                "label": "Wahda Kabeera (وحدة كبيرة)",
                "bpm": 72,
                "mood": "Meditative, spacious",
                "why": "Primary and most traditional cycle for Al-Taweel.",
                "patterns": {
                    "kick": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                    "hihat": [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
                    "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                },
            }
        ],
    },
    "kamil": {
        "arabic": "الكامل",
        "taf_eela": "مُتَفَاعِلُن",
        "transliteration": "mutafa'ilun",
        "syllable_pattern": "∪∪—∪— | ∪∪—∪— | ∪∪—∪—",
        "time_signature": (3, 4),
        "beats_per_bar": 3,
        "steps_per_bar": 21,
        "description": "Al-Kamil — 'the complete' — is the second most used meter. It carries warmth, emotion, and a dancing quality, hence its dominance in love poetry.",
        "variants": [],
    },
    "baseet": {
        "arabic": "البسيط",
        "taf_eela": "مُسْتَفْعِلُن فَاعِلُن",
        "transliteration": "mustaf'ilun fa'ilun",
        "syllable_pattern": "——∪— | —∪—",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 12,
        "description": "Al-Baseet — 'the spread out' — opens with two consecutive long syllables that land like a firm step. This immediate weight gives it authority.",
        "variants": [],
    },
    "wafir": {
        "arabic": "الوافر",
        "taf_eela": "مُفَاعَلَتُن",
        "transliteration": "mufa'alatun",
        "syllable_pattern": "∪—∪∪— | ∪—∪∪—",
        "time_signature": (6, 8),
        "beats_per_bar": 2,
        "steps_per_bar": 14,
        "description": "Al-Wafir — 'the abundant / rippling' — has an undulating wave-like quality. Mufa'alatun rolls forward: short pickup, long crest, then two quick ripples.",
        "variants": [],
    },
    "ramal": {
        "arabic": "الرمل",
        "taf_eela": "فَاعِلَاتُنْ فَاعِلَاتُنْ فَاعِلَاتُنْ",
        "transliteration": "fa'ilatun fa'ilatun fa'ilatun",
        "syllable_pattern": "—∪—— | —∪—— | —∪——",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 4,
        "description": "Al-Ramal — 'the running' — has a gentle, flowing, and romantic character. Often used for tender verse and muwashshahat.",
        "variants": [],
    },
    "rajaz": {
        "arabic": "الرجز",
        "taf_eela": "مُسْتَفْعِلُنْ مُسْتَفْعِلُنْ مُسْتَفْعِلُنْ",
        "transliteration": "mustaf'ilun mustaf'ilun mustaf'ilun",
        "syllable_pattern": "——∪— | ——∪— | ——∪—",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 4,
        "description": "Al-Rajaz — 'the trembling' — is an even, didactic meter often used for narrative, educational poems, and rhythmic chanting.",
        "variants": [],
    },
    "khafeef": {
        "arabic": "الخفيف",
        "taf_eela": "فَاعِلَاتُنْ مُسْتَفْعِلُنْ فَاعِلَاتُنْ",
        "transliteration": "fa'ilatun mustaf'ilun fa'ilatun",
        "syllable_pattern": "—∪—— | ——∪— | —∪——",
        "time_signature": (10, 8),
        "beats_per_bar": 10,
        "steps_per_bar": 10,
        "description": "Al-Khafeef — 'the light' — is an ornate, musical meter heavily favored in Andalusian poetry and classical muwashshahat.",
        "variants": [],
    },
    "mutaqarib": {
        "arabic": "المتقارب",
        "taf_eela": "فَعُولُنْ فَعُولُنْ فَعُولُنْ فَعُولُنْ",
        "transliteration": "fa'oolun fa'oolun fa'oolun fa'oolun",
        "syllable_pattern": "∪—— | ∪—— | ∪—— | ∪——",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 8,
        "description": "Al-Mutaqarib — 'the converging' — has a driving, heroic, and epic quality, famously used in patriotic anthems and narrative epics.",
        "variants": [],
    },
    "hazaj": {
        "arabic": "الهزج",
        "taf_eela": "مَفَاعِيلُنْ مَفَاعِيلُنْ",
        "transliteration": "mafa'eelun mafa'eelun",
        "syllable_pattern": "∪——— | ∪———",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 4,
        "description": "Al-Hazaj — 'the trilling' — is a short, joyful, and festive meter, often used in lighthearted folk songs and celebratory verse.",
        "variants": [],
    },
    "sari": {
        "arabic": "السريع",
        "taf_eela": "مُسْتَفْعِلُنْ مُسْتَفْعِلُنْ مَفْعُولَاتُ",
        "transliteration": "mustaf'ilun mustaf'ilun maf'oolatu",
        "syllable_pattern": "——∪— | ——∪— | ——∪",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 4,
        "description": "Al-Sari — 'the swift' — is a vibrant, energetic meter that propels the listener forward, suitable for dynamic and spirited poetry.",
        "variants": [],
    },
    "mutadarak": {
        "arabic": "المتدارك",
        "taf_eela": "فَاعِلُنْ فَاعِلُنْ فَاعِلُنْ فَاعِلُنْ",
        "transliteration": "fa'ilun fa'ilun fa'ilun fa'ilun",
        "syllable_pattern": "—∪— | —∪— | —∪— | —∪—",
        "time_signature": (4, 4),
        "beats_per_bar": 4,
        "steps_per_bar": 4,
        "description": "Al-Mutadarak — 'the continuous' — is a swift, innovative meter with a galloping rhythm, popular in modern and experimental Arabic poetry.",
        "variants": [],
    },
    "madeed": {
        "arabic": "المديد",
        "taf_eela": "فَاعِلَاتُنْ فَاعِلُنْ فَاعِلَاتُنْ",
        "transliteration": "fa'ilatun fa'ilun fa'ilatun",
        "syllable_pattern": "—∪—— | —∪— | —∪——",
        "time_signature": (7, 8),
        "beats_per_bar": 7,
        "steps_per_bar": 7,
        "description": "Al-Madeed — 'the extended' — is a rare, elegiac meter with a nostalgic and tranquil mood, offering a floating, asymmetrical rhythm.",
        "variants": [],
    },
}

# ─────────────────────────────────────────────────────────────
#  DYNAMIC REGISTRY LOADING (Phase 3)
# ─────────────────────────────────────────────────────────────
if _REGISTRY_AVAILABLE:
    _json_path = Path(__file__).parent / "arabic_rhythm_data.json"
    if _json_path.exists():
        try:
            _json_registry = load_registry(_json_path)
            for _slug, _records in _json_registry.items():
                if _slug in BUHOOR:
                    _new_variants = []
                    for _rec in _records:
                        _pat = get_pattern(_rec.variant_slug, _rec.steps_per_bar)
                        if _pat:
                            # Derive beats_per_bar to maintain timing model for heterogeneous variants
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

                            _new_variants.append(
                                {
                                    "name": _rec.variant_slug,
                                    "label": _rec.iqaa,
                                    "bpm": _rec.default_bpm,
                                    "mood": _rec.mood_en,
                                    "why": _rec.performance_notes,
                                    "patterns": _pat,
                                    "steps_per_bar": _rec.steps_per_bar,
                                    "beats_per_bar": _beats,
                                    "is_traditional": _rec.is_traditional,
                                    "geographic_tradition": _rec.geographic_tradition,
                                    "corpus_pct": _rec.corpus_pct,
                                }
                            )
                    if _new_variants:
                        BUHOOR[_slug]["variants"] = _new_variants
                        BUHOOR[_slug]["corpus_pct"] = _records[0].corpus_pct
        except Exception as e:
            print(f"Warning: Could not load JSON registry: {e}", file=sys.stderr)

# ─────────────────────────────────────────────────────────────
#  HUMANIZATION
# ─────────────────────────────────────────────────────────────


def humanize(
    pattern: list,
    timing_jitter: float = 0.007,
    velocity_variance: float = 0.12,
    base_velocity: float = 1.0,
) -> list[tuple]:
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
    bahr = BUHOOR[bahr_key]

    # Phase 3: Use per-variant step/beat counts to support heterogeneous iqaat
    steps_per_bar = variant.get("steps_per_bar", bahr["steps_per_bar"])
    beats_per_bar = variant.get("beats_per_bar", bahr["beats_per_bar"])
    bpm = bpm_override if bpm_override is not None else variant["bpm"]

    step_s = beats_per_bar * 60.0 / (bpm * steps_per_bar)
    total_steps = steps_per_bar * bars
    total_n = int(total_steps * step_s * SAMPLE_RATE) + SAMPLE_RATE

    mix = np.zeros((total_n, 2), dtype=np.float32)
    sounds = {name: fn() for name, fn in SYNTH_MAP.items()}

    def _cpan(p: float) -> tuple:
        a = p * (math.pi / 2)
        return math.cos(a), math.sin(a)

    panning = {
        "kick": _cpan(0.50),
        "snare": _cpan(0.50),
        "ka": _cpan(0.50),
        "hihat": _cpan(0.60),
        "crash": _cpan(0.40),
    }

    BASE_VELOCITY = {
        "kick": 1.00,
        "snare": 0.50,
        "ka": 0.40,
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
    corpus_pct = b.get("corpus_pct", 0.0)
    pct_str = f"  Corpus : {corpus_pct}%" if corpus_pct else ""
    print(f"\n{'═'*60}")
    print(f"  {b['arabic']}  —  Al-{key.title()}")
    print(f"  تفعيلة : {b['taf_eela']}")
    print(f"  Pattern: {b['syllable_pattern']}")
    print(f"  Meter  : {ts[0]}/{ts[1]}{pct_str}")
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
    trad_str = "Traditional" if variant.get("is_traditional", True) else "Contemporary"
    geo_str = variant.get("geographic_tradition", "Pan-Arab")

    print(f"  ▶ {variant['label']}  │  {bpm_label}  │  {variant['mood']}")
    print(f"    Context  : {trad_str}, {geo_str}")
    print(f"    Rationale: {variant['why']}")
    print(f"    {'─'*50}")
    for inst in ("kick", "snare", "ka", "hihat", "crash"):
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
    if not quiet:
        print_bahr_header(key)
    bahr = BUHOOR[key]
    paths = []
    for variant in bahr["variants"]:
        if variant_filter and variant["name"] not in variant_filter:
            continue
        effective_bpm = bpm_override if bpm_override is not None else variant["bpm"]

        # Phase 3: Use per-variant beats_per_bar to maintain timing model
        beats_per_bar = variant.get("beats_per_bar", bahr["beats_per_bar"])
        bar_s = beats_per_bar * 60.0 / effective_bpm
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
            quiet=quiet,
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
            f"  [{i:2d}] {b['arabic']:<14}  Al-{k.title():<10}  "
            f"{ts[0]}/{ts[1]}  —  {nv} variants"
        )
    click.echo(f"  [{len(keys)+1:2d}] All buhoor\n")

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


BAHR_NAMES = list(BUHOOR.keys())

# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("buhoor", nargs=-1, metavar="[BAHR]...")
@click.option("--all", "select_all", is_flag=True, help="Generate all buhoor.")
@click.option(
    "-o",
    "--output-dir",
    default=OUTPUT_DIR,
    show_default=True,
    help="Directory for output MP3 files.",
    type=click.Path(file_okay=False),
)
@click.option(
    "-d",
    "--duration",
    default=TARGET_DURATION_S,
    show_default=True,
    type=click.FloatRange(min=1.0),
    help="Target loop duration in seconds.",
)
@click.option(
    "-v",
    "--variant",
    "variant_filter",
    multiple=True,
    help="Render only the named variant(s).",
)
@click.option(
    "--seed",
    default=42,
    show_default=True,
    type=int,
    help="Random seed for humanization.",
)
@click.option(
    "--jitter",
    default=0.007,
    show_default=True,
    type=click.FloatRange(min=0.0, max=0.05),
    help="Max ±timing jitter per hit in seconds.",
)
@click.option(
    "--velocity-variance",
    default=0.12,
    show_default=True,
    type=click.FloatRange(min=0.0, max=1.0),
    help="Max ±velocity nudge fraction.",
)
@click.option(
    "--bpm",
    "bpm_override",
    default=None,
    type=click.IntRange(min=20, max=300),
    help="Override the tempo for every rendered variant.",
)
@click.option(
    "--bitrate",
    default="192k",
    show_default=True,
    type=click.Choice(["128k", "192k", "256k", "320k"], case_sensitive=False),
    help="MP3 output bitrate.",
)
@click.option(
    "-q", "--quiet", is_flag=True, help="Suppress descriptions and pattern grids."
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
    help="Path to arabic_rhythm_data.json.",
)
@click.option(
    "--validate",
    "run_validate",
    is_flag=True,
    help="Validate pattern coverage against the JSON registry, then exit.",
)
@click.version_option("3.0.0", "-V", "--version")
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
    """بحور الشعر — Arabic Poetic Meters Drum Generator"""

    if list_buhoor:
        print_header()
        for k in BUHOOR:
            b = BUHOOR[k]
            ts = b["time_signature"]
            corpus_pct = b.get("corpus_pct", 0.0)
            pct_str = f"{corpus_pct}%" if corpus_pct else ""
            click.echo(f"  {b['arabic']:<14}  al-{k:<10}  {ts[0]}/{ts[1]:<4} {pct_str}")
            for v in b["variants"]:
                trad_str = (
                    "traditional" if v.get("is_traditional", True) else "contemporary"
                )
                geo_str = v.get("geographic_tradition", "Pan-Arab")
                click.echo(
                    f"      • {v['name']:<20} ({trad_str}, {geo_str})  {v['bpm']:>3} BPM  {v['mood']}"
                )
            click.echo()
        return

    if run_validate:
        if not _REGISTRY_AVAILABLE:
            raise click.UsageError("Requires iqaa_patterns.py and meter_registry.py.")
        _script_dir = Path(__file__).parent
        _json_path = (
            Path(data_path) if data_path else _script_dir / "arabic_rhythm_data.json"
        )
        click.echo("\n  Registry validation\n  ═══════════════════")

        pat_errors = validate_patterns()
        if pat_errors:
            click.echo("  ❌  IqaaPatternRegistry has invalid entries:")
            for e in pat_errors:
                click.echo(f"       {e}")
        else:
            click.echo(f"  ✅  IqaaPatternRegistry: all patterns well-formed")

        click.echo()
        if _json_path.exists():
            try:
                json_registry = load_registry(_json_path)
                click.echo(f"  JSON registry  ({_json_path.name}):")
                click.echo(registry_summary(json_registry, IqaaPatternRegistry))
                click.echo()
                json_gaps_all = validate_registry(json_registry, IqaaPatternRegistry)
                click.echo(
                    f"  JSON gaps (all meters)            : {len(json_gaps_all)}"
                )
                if json_gaps_all:
                    for g in json_gaps_all[:20]:
                        click.echo(g)
            except Exception as exc:
                click.echo(f"  ⚠  Could not load JSON registry: {exc}")
        else:
            click.echo(f"  ⚠  JSON file not found at {_json_path}")
        click.echo()
        return

    bad = [a for a in buhoor if a not in BUHOOR]
    if bad:
        raise click.BadArgumentUsage(f"Unknown bahr: {', '.join(bad)}.")

    effective_seed = random.randint(0, 2**31) if seed == -1 else seed
    random.seed(effective_seed)
    np.random.seed(effective_seed)
    if not quiet and seed == -1:
        click.echo(f"  Random seed: {effective_seed}\n")

    if select_all or (not buhoor and not list_buhoor):
        selected = BAHR_NAMES if select_all else interactive_menu()
    else:
        selected = list(buhoor)

    os.makedirs(output_dir, exist_ok=True)

    if not quiet:
        click.echo(
            f"\n  Synthesizing ~{duration:.0f} s per variant (seed={effective_seed}) …\n"
        )

    all_paths = []
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

    click.echo(f"\n{'═'*60}")
    click.echo(f"  Output directory : {output_dir}")
    click.echo(f"  Total files      : {len(all_paths)}")
    for p in all_paths:
        size_kb = os.path.getsize(p) // 1024
        click.echo(f"    • {os.path.basename(p):50s}  ({size_kb} KB)")
    click.echo()


if __name__ == "__main__":
    main()
