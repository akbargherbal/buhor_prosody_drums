"""
iqaa_patterns.py — Arabic Percussion Pattern Registry
══════════════════════════════════════════════════════
A flat registry mapping (variant_slug, steps_per_bar) → patterns dict.
Each patterns dict has keys matching SYNTH_MAP voices (kick, snare, hihat, crash,
and future 'ka'). Each value is a list of 0/1 step flags whose length equals
steps_per_bar.

Naming convention for keys
──────────────────────────
variant_slug : the ASCII slug used in filenames and -v filtering, matching the
               "name" field of each variant in the BUHOOR dict. New iqaat added
               in Phase 2 will use the JSON variant_slug field directly.
steps_per_bar: integer step count for the meter grid that variant was crafted for.
               Two iqaat with the same name but different step counts are distinct
               entries — e.g. ("maqsum", 4) vs ("maqsum", 12).

Phase 1 scope
─────────────
Only the 11 variants from the original BUHOOR dict are registered here. Phase 2
adds patterns for all new step-count groups (4, 6, 7, 8, 10, 32) required by the
arabic_rhythm_data.json iqaat.

Usage
─────
    from iqaa_patterns import get_pattern, IqaaPatternRegistry

    pat = get_pattern("wahda", 12)  # returns dict or None
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
#  Registry
#  Key  : (variant_slug: str, steps_per_bar: int)
#  Value: {"kick": [...], "snare": [...], "hihat": [...], "crash": [...]}
#         Lists must have exactly steps_per_bar elements, values 0 or 1.
# ─────────────────────────────────────────────────────────────────────────────

IqaaPatternRegistry: dict[tuple[str, int], dict[str, list[int]]] = {

    # ══════════════════════════════════════════════════════════════════════════
    #  الطويل — Al-Taweel   (steps_per_bar = 12, mora grid, 4/4)
    #  IOI: 1, 2, 2, 1, 2, 2, 2  →  ∪ — — | ∪ — — —  (fa'oolun mafa'eelun)
    # ══════════════════════════════════════════════════════════════════════════

    ("wahda", 12): {
        # Sparse meditative 4/4 — DUM only on bar 1, single ghost snare, dotted hihat
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

    ("maqsum", 12): {
        # NON-TRADITIONAL — experimental pairing; all 7 mora-onset positions voiced
        # Onsets: 0(∪) 1(—) 3(—) 5(∪) 6(—) 8(—) 10(—)
        "kick":  [1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0],
        "snare": [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

    ("fallahy", 12): {
        # Rustic folk 4/4 syncopation — kick 0,3,5,10; TEK on 6,9
        "kick":  [1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0],
        "hihat": [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  الكامل — Al-Kamil   (steps_per_bar = 21, mora grid, 3/4)
    #  IOI: 1, 1, 2, 1, 2  per foot × 3  →  ∪∪—∪— × 3  (mutafa'ilun)
    #  Foot onsets (abs): 0,1,2,4,5 | 7,8,9,11,12 | 14,15,16,18,19
    # ══════════════════════════════════════════════════════════════════════════

    ("samaai_darij", 21): {
        # DUM on bar downbeat (step 0, 7, 14); TEK on — positions (2,5,9,12,16,19)
        "kick":  [1,0,0,0,0,0,0, 1,0,0,0,0,0,0, 1,0,0,0,0,0,0],
        "snare": [0,0,1,0,1,0,0, 0,0,1,0,1,0,0, 0,0,1,0,1,0,0],
        "hihat": [1,1,1,0,1,1,0, 1,1,1,0,1,1,0, 1,1,1,0,1,1,0],
        "crash": [1,0,0,0,0,0,0, 0,0,0,0,0,0,0, 0,0,0,0,0,0,0],
    },

    ("andalusi_flow", 21): {
        # Kick on first — of each foot (abs 2, 9, 16); dotted hihat (every 3)
        "kick":  [0,0,1,0,0,0,0, 0,0,1,0,0,0,0, 0,0,1,0,0,0,0],
        "snare": [0,0,0,0,1,0,0, 1,0,0,0,1,0,0, 1,0,0,0,1,0,0],
        "hihat": [1,0,0,1,0,0,1, 0,0,1,0,0,1,0, 0,1,0,0,1,0,0],
        "crash": [1,0,0,0,0,0,0, 0,0,0,0,0,0,0, 0,0,0,0,0,0,0],
    },

    ("muwashshah_syncopated", 21): {
        # Syncopated muwashshah 3/4 — kick anticipates foot entries; dense hihat
        "kick":  [1,0,1,0,0,0,0, 1,0,0,0,1,0,0, 1,0,0,1,0,0,0],
        "snare": [0,0,1,0,1,0,0, 0,0,1,0,0,1,0, 0,0,1,0,0,1,0],
        "hihat": [1,1,0,1,1,0,1, 1,0,1,1,0,1,1, 0,1,1,0,1,1,0],
        "crash": [1,0,0,0,0,0,0, 0,0,0,0,0,0,0, 0,0,0,0,0,0,0],
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  البسيط — Al-Baseet   (steps_per_bar = 12, mora grid, 4/4)
    #  IOI: 2, 2, 1, 2, 2, 1, 2  →  — — ∪ — | — ∪ —  (mustaf'ilun fa'ilun)
    # ══════════════════════════════════════════════════════════════════════════

    ("masmoudi_kabir", 12): {
        # Authentic two-DUM: DUM . DUM . . . TEK . DUM . TEK .
        "kick":  [1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

    ("march", 12): {
        # Kick on every — position (0,2,5,7,10); snare on ∪ (4,9)
        "kick":  [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        "hihat": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

    ("zaffa", 12): {
        # Double kick opening (——), festive syncopation after
        "kick":  [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        "hihat": [1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  الوافر — Al-Wafir   (steps_per_bar = 14, mora grid, 6/8)
    #  IOI: 1, 2, 1, 1, 2  per foot × 2  →  ∪—∪∪— × 2  (mufa'alatun)
    #  Foot 1 onsets: 0(∪), 1(—), 3(∪), 4(∪), 5(—)
    #  Foot 2 onsets: 7(∪), 8(—), 10(∪), 11(∪), 12(—)
    # ══════════════════════════════════════════════════════════════════════════

    ("muwashshah", 14): {
        # Kick on first — per foot (1, 8); snare on second — (5, 12)
        # Hihat traces ∪ at foot-start and ∪∪ pairs (3-4, 10-11)
        "kick":  [0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0],
        "hihat": [1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

    ("wafir_ripple", 14): {
        # Both — per foot on kick (1,5,8,12); snare on foot-start ∪ (0,7)
        # Hihat adjacent hits (3-4, 10-11) encode the ∪∪ double-short
        "kick":  [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
        "snare": [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        "hihat": [1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
        "crash": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },

}


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_pattern(variant_slug: str, steps: int) -> dict[str, list[int]] | None:
    """Return the pattern dict for (variant_slug, steps_per_bar), or None if absent.

    Args:
        variant_slug: The ASCII slug (e.g. "wahda", "maqsum").
        steps:        The step count the pattern was crafted for.

    Returns:
        Pattern dict with voice keys → step lists, or None if not registered.
    """
    return IqaaPatternRegistry.get((variant_slug, steps))


def list_registered() -> list[tuple[str, int]]:
    """Return a sorted list of all registered (slug, steps) keys."""
    return sorted(IqaaPatternRegistry.keys())


def validate_patterns() -> list[str]:
    """Sanity-check every registered pattern.

    Returns a list of error strings; empty list means all patterns are valid.
    Checks:
      - All voices have exactly steps_per_bar elements
      - All elements are 0 or 1
    """
    errors: list[str] = []
    for (slug, steps), patterns in IqaaPatternRegistry.items():
        for voice, grid in patterns.items():
            if len(grid) != steps:
                errors.append(
                    f"({slug!r}, {steps})[{voice!r}]: "
                    f"expected {steps} steps, got {len(grid)}"
                )
            bad = [v for v in grid if v not in (0, 1)]
            if bad:
                errors.append(
                    f"({slug!r}, {steps})[{voice!r}]: "
                    f"non-binary values {bad}"
                )
    return errors
