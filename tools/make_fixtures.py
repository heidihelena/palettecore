"""Write fixtures/parity.json — the cross-language parity contract.

Any other implementation (the R package first) must reproduce these numbers:
conversions and distances within 1e-6, palette HEX codes exactly.
Regenerate only when the reference algorithm intentionally changes.
"""

import json
import pathlib

import numpy as np

from palettecore.convert import hex_to_srgb, srgb_to_cielab, srgb_to_oklab, oklab_to_oklch
from palettecore.cvd import CONDITIONS, simulate_cvd
from palettecore.generate import generate_palette
from palettecore.metrics import ciede2000, contrast_ratio

HEXES = [
    "#8B6FC9", "#FFFFFF", "#000000", "#FF0000", "#00FF00", "#0000FF",
    "#FFFF00", "#00FFFF", "#FF00FF", "#808080", "#1A2B3C", "#D95F02",
    "#66A61E", "#FFFFCC", "#010101", "#FEFEFE",
]
PAIRS = [
    ("#8B6FC9", "#3C7A2B"), ("#000000", "#FFFFFF"), ("#FF0000", "#00FF00"),
    ("#8B6FC9", "#8B6FCA"), ("#808080", "#818181"), ("#D95F02", "#66A61E"),
]
PALETTES = [
    {"seed": "#8B6FC9", "n": 8, "kind": "sequential"},
    {"seed": "#8B6FC9", "n": 8, "kind": "categorical"},
    {"seed": "#8B6FC9", "n": 8, "kind": "diverging"},
    {"seed": "#8B6FC9", "n": 8, "kind": "sequential", "anchor": "exact"},
    {"seed": "#1A2B3C", "n": 5, "kind": "sequential"},
    {"seed": "#D95F02", "n": 12, "kind": "categorical"},
    {"seed": "#FFFF00", "n": 6, "kind": "sequential"},
    {"seed": "#808080", "n": 4, "kind": "sequential"},
    {"seed": "#8B6FC9", "n": 6, "kind": "sequential", "background": "#000000"},
]


def main():
    fx = {
        "version": 1,
        "tolerance": {"float": 1e-6, "hex": "exact"},
        "conversions": [],
        "ciede2000": [],
        "cvd": [],
        "contrast": [],
        "palettes": [],
    }
    for h in HEXES:
        rgb = hex_to_srgb(h)
        lab = srgb_to_oklab(rgb)
        fx["conversions"].append(
            {
                "hex": h,
                "srgb": [round(float(v), 10) for v in rgb],
                "oklab": [round(float(v), 10) for v in lab],
                "oklch": [round(float(v), 10) for v in oklab_to_oklch(lab)],
                "cielab_d65": [round(float(v), 10) for v in srgb_to_cielab(rgb)],
            }
        )
    for a, b in PAIRS:
        fx["ciede2000"].append(
            {"a": a, "b": b, "deltaE": round(ciede2000(hex_to_srgb(a), hex_to_srgb(b)), 10)}
        )
    for h in HEXES:
        entry = {"hex": h}
        for c in CONDITIONS:
            sim = simulate_cvd(hex_to_srgb(h), c)
            entry[c] = [round(float(v), 10) for v in sim]
        fx["cvd"].append(entry)
    for h in HEXES[:8]:
        fx["contrast"].append(
            {
                "hex": h,
                "vs_white": round(contrast_ratio(hex_to_srgb(h), hex_to_srgb("#FFFFFF")), 10),
                "vs_black": round(contrast_ratio(hex_to_srgb(h), hex_to_srgb("#000000")), 10),
            }
        )
    for spec in PALETTES:
        r = generate_palette(**spec)
        fx["palettes"].append({"spec": spec, "hexes": r.hexes, "warnings_count": len(r.warnings)})

    out = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "parity.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(fx, indent=1))
    print(f"wrote {out} ({len(fx['conversions'])} conversions, {len(fx['palettes'])} palettes)")


if __name__ == "__main__":
    main()
