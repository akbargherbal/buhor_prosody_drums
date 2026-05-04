# audit_phase2.py
import os
import tempfile
from buhoor_drums import render_variant, BUHOOR
from iqaa_patterns import get_pattern

# ROBUST FIX: Use the OS's native temporary directory
audit_dir = os.path.join(tempfile.gettempdir(), "buhoor_audit")
os.makedirs(audit_dir, exist_ok=True)

test_cases = [
    ("baseet", "maqsum", 4, 100),  # Group A
    ("kamil", "yuruk_semai", 6, 132),  # Group B
    ("baseet", "nawakht", 7, 92),  # Group C
    ("taweel", "wahda_kabira", 8, 72),  # Group D
    ("khafeef", "sama3i_thaqil", 10, 60),  # Group E
    ("taweel", "mudawwar_masri", 12, 80),  # Group F
    ("wafir", "sama3i_saraband", 21, 108),  # Group G
    ("taweel", "warshan_arabi", 32, 68),  # Group H
]

for bahr_key, slug, steps, bpm in test_cases:
    # Mock a variant dict to feed the renderer
    variant = {
        "name": slug,
        "label": f"Audit: {slug} ({steps}-step)",
        "bpm": bpm,
        "mood": "Audit",
        "why": "Phase 2 Auditory Test",
        "patterns": get_pattern(slug, steps),
    }

    # Temporarily inject a dummy bahr if it doesn't exist (e.g., khafeef)
    if bahr_key not in BUHOOR:
        BUHOOR[bahr_key] = {
            "time_signature": (4, 4),
            "beats_per_bar": 4,
            "steps_per_bar": steps,
            "arabic": bahr_key,
        }
    else:
        # Override steps_per_bar for the test
        BUHOOR[bahr_key]["steps_per_bar"] = steps

    print(f"Rendering {slug} ({steps} steps)...")
    render_variant(
        bahr_key, variant, bars=4, output_dir=audit_dir, effective_bpm=bpm, quiet=True
    )

print(f"\n✅ Audit files generated in {audit_dir}")
