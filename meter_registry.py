"""
meter_registry.py — JSON-Driven Meter Registry
═══════════════════════════════════════════════
Loads arabic_rhythm_data.json and exposes it as typed IqaaRecord dataclasses
grouped by meter slug.

Responsibilities
────────────────
  load_registry(json_path)  → dict[meter_slug, list[IqaaRecord]]
  validate_registry(...)    → list of gap strings (missing patterns)
  METER_AR_TO_SLUG          → Arabic → ASCII slug mapping

Separation of concerns
───────────────────────
This module knows nothing about audio synthesis.  It only describes *what*
should be rendered; iqaa_patterns.py describes *how* (the drum grids).

Usage
─────
    from pathlib import Path
    from meter_registry import load_registry, validate_registry
    from iqaa_patterns import IqaaPatternRegistry

    registry = load_registry(Path("arabic_rhythm_data.json"))
    gaps = validate_registry(registry, IqaaPatternRegistry)
    for g in gaps:
        print(g)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  Arabic meter name → ASCII CLI slug
# ─────────────────────────────────────────────────────────────────────────────

METER_AR_TO_SLUG: dict[str, str] = {
    "الطويل": "taweel",
    "الكامل": "kamil",
    "البسيط": "baseet",
    "الوافر": "wafir",
    "الرمل": "ramal",
    "الرجز": "rajaz",
    "الخفيف": "khafeef",
    "المتقارب": "mutaqarib",
    "الهزج": "hazaj",
    "السريع": "sari",
    "المتدارك": "mutadarak",
    "المديد": "madeed",
}

# Inverse mapping (slug → Arabic) — built once at import time
SLUG_TO_METER_AR: dict[str, str] = {v: k for k, v in METER_AR_TO_SLUG.items()}


# ─────────────────────────────────────────────────────────────────────────────
#  Data model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IqaaRecord:
    """One row from arabic_rhythm_data.json, fully typed."""

    meter_slug: str  # ASCII slug derived from meter_ar
    meter_ar: str  # Arabic name of the poetic meter
    iqaa: str  # Human-readable iqaa name (e.g. "Sama'i Darij")
    is_traditional: bool  # Traditional pairing vs contemporary experiment
    mood_en: str  # English mood description
    geographic_tradition: str  # "Pan-Arab", "Masri", "Shami", "Andalusi", etc.
    variant_slug: str  # ASCII slug for the iqaa (used as pattern key)
    default_bpm: int  # Canonical tempo for this pairing
    bpm_range: tuple[int, int]  # (min_bpm, max_bpm) valid range
    steps_per_bar: int  # Step grid length
    instrument_context: str  # "doumbek solo", "firqa", "tabl + riq", etc.
    performance_notes: str  # DUM/TEK/KA placement description
    syllable_pattern: str  # Mora-notation string (∪ / —)
    corpus_pct: float  # Approximate % of classical corpus using this meter


# ─────────────────────────────────────────────────────────────────────────────
#  Loader
# ─────────────────────────────────────────────────────────────────────────────


def load_registry(json_path: Path) -> dict[str, list[IqaaRecord]]:
    """Load arabic_rhythm_data.json and return a meter_slug → [IqaaRecord] dict.

    Args:
        json_path: Path to the JSON file.

    Returns:
        Ordered dict mapping each meter slug to a list of its IqaaRecords.

    Raises:
        FileNotFoundError: if json_path does not exist (with a clear message).
        ValueError:        if the JSON is malformed or a meter_ar is unknown.
    """
    if not json_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {json_path}\n"
            f"  Tip: pass --data <path> pointing to arabic_rhythm_data.json, "
            f"or place the file next to buhoor_drums.py."
        )

    try:
        raw: list[dict] = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {json_path}: {exc}") from exc

    if not isinstance(raw, list):
        raise ValueError(f"{json_path}: expected a JSON array at top level.")

    registry: dict[str, list[IqaaRecord]] = {}
    unknown_meters: list[str] = []

    for i, row in enumerate(raw):
        meter_ar = row.get("meter_ar", "")
        slug = METER_AR_TO_SLUG.get(meter_ar)
        if slug is None:
            if meter_ar not in unknown_meters:
                unknown_meters.append(meter_ar)
            continue  # skip rows with unknown meter; report after loop

        bpm_range_raw = row.get("bpm_range", [0, 300])
        record = IqaaRecord(
            meter_slug=slug,
            meter_ar=meter_ar,
            iqaa=row.get("iqaa", ""),
            is_traditional=bool(row.get("is_traditional", False)),
            mood_en=row.get("mood_en", ""),
            geographic_tradition=row.get("geographic_tradition", ""),
            variant_slug=row.get("variant_slug", ""),
            default_bpm=int(row.get("default_bpm", 90)),
            bpm_range=(int(bpm_range_raw[0]), int(bpm_range_raw[1])),
            steps_per_bar=int(row.get("steps_per_bar", 16)),
            instrument_context=row.get("instrument_context", ""),
            performance_notes=row.get("performance_notes", ""),
            syllable_pattern=row.get("syllable_pattern", ""),
            corpus_pct=float(row.get("corpus_pct", 0.0)),
        )
        registry.setdefault(slug, []).append(record)

    if unknown_meters:
        # Non-fatal: warn and continue.  New meters can be added to
        # METER_AR_TO_SLUG when they are fully implemented.
        print(
            f"  ⚠  meter_registry: {len(unknown_meters)} unknown meter_ar value(s) "
            f"skipped — add to METER_AR_TO_SLUG to enable:\n"
            + "\n".join(f"       {m!r}" for m in unknown_meters),
            file=sys.stderr,
        )

    return registry


# ─────────────────────────────────────────────────────────────────────────────
#  Validator
# ─────────────────────────────────────────────────────────────────────────────


def validate_registry(
    registry: dict[str, list[IqaaRecord]],
    pattern_registry: dict[tuple[str, int], dict],
    *,
    meter_filter: list[str] | None = None,
) -> list[str]:
    """Return a list of gap strings for (meter, variant_slug, steps) combos
    that appear in the JSON registry but have no entry in pattern_registry.

    Args:
        registry:         Output of load_registry().
        pattern_registry: IqaaPatternRegistry dict.
        meter_filter:     If given, only check these meter slugs.  Useful
                          in Phase 1 to scope the report to the current 4 meters.

    Returns:
        List of human-readable gap strings; empty means no gaps.
    """
    gaps: list[str] = []
    slugs_to_check = meter_filter if meter_filter is not None else list(registry.keys())

    for meter_slug in slugs_to_check:
        records = registry.get(meter_slug, [])
        for rec in records:
            key = (rec.variant_slug, rec.steps_per_bar)
            if key not in pattern_registry:
                gaps.append(
                    f"  MISSING  {meter_slug:<12} | {rec.variant_slug:<30} | "
                    f"{rec.steps_per_bar} steps  ({rec.iqaa})"
                )
    return gaps


# ─────────────────────────────────────────────────────────────────────────────
#  BUHOOR-dict validator (Phase 1 cross-check)
# ─────────────────────────────────────────────────────────────────────────────


def validate_buhoor_patterns(
    buhoor: dict,
    pattern_registry: dict[tuple[str, int], dict],
) -> list[str]:
    """Check that every variant currently in the BUHOOR dict has a matching
    entry in IqaaPatternRegistry.  This is the Phase 1 regression gate.

    Args:
        buhoor:           The BUHOOR dict from buhoor_drums.py.
        pattern_registry: IqaaPatternRegistry dict.

    Returns:
        List of gap strings; empty means all BUHOOR variants are covered.
    """
    gaps: list[str] = []
    for meter_slug, bahr in buhoor.items():
        steps = bahr["steps_per_bar"]
        for variant in bahr["variants"]:
            slug = variant["name"]
            if (slug, steps) not in pattern_registry:
                gaps.append(f"  MISSING  {meter_slug:<12} | {slug:<28} | {steps} steps")
    return gaps


# ─────────────────────────────────────────────────────────────────────────────
#  Summary helpers
# ─────────────────────────────────────────────────────────────────────────────


def registry_summary(
    registry: dict[str, list[IqaaRecord]],
    pattern_registry: dict[tuple[str, int], dict],
) -> str:
    """Return a multi-line human-readable summary of registry coverage."""
    total_records = sum(len(v) for v in registry.values())
    covered = sum(
        1
        for records in registry.values()
        for rec in records
        if (rec.variant_slug, rec.steps_per_bar) in pattern_registry
    )
    step_groups = sorted(
        {rec.steps_per_bar for records in registry.values() for rec in records}
    )
    trad_count = sum(
        1 for records in registry.values() for rec in records if rec.is_traditional
    )
    geo_counts: dict[str, int] = {}
    for records in registry.values():
        for rec in records:
            geo_counts[rec.geographic_tradition] = (
                geo_counts.get(rec.geographic_tradition, 0) + 1
            )

    lines = [
        f"  JSON records loaded : {total_records}",
        f"  Patterns available  : {covered} / {total_records}"
        + ("   ✅" if covered == total_records else ""),
        f"  Step groups covered : {', '.join(str(s) for s in step_groups)}",
        "",
        f"  Missing patterns    : {total_records - covered}",
        "",
        f"  Tradition breakdown :",
        f"    Traditional       : {trad_count} / {total_records}",
        f"    Contemporary      : {total_records - trad_count} / {total_records}",
        "",
        f"  Geographic breakdown:",
    ]
    for geo, count in sorted(geo_counts.items(), key=lambda x: -x[1]):
        lines.append(f"    {geo:<11}: {count:>2}")

    return "\n".join(lines)
