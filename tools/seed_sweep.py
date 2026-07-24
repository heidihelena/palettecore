"""Reproduce the seed-region sweeps behind docs/seed-guidance.md.

Usage:
    PYTHONPATH=. python3 tools/seed_sweep.py hue      # sequential 15-deg hue scan
    PYTHONPATH=. python3 tools/seed_sweep.py chroma   # categorical chroma response
    PYTHONPATH=. python3 tools/seed_sweep.py n        # sequential n sensitivity
    PYTHONPATH=. python3 tools/seed_sweep.py grid     # coarse hue x lightness grid

Margins are the worst-condition difference between the audited minimum
CIEDE2000 and its package-default threshold; negative means the audit warns.
Deterministic: same inputs always give the same table.
"""

import sys

import numpy as np

from palettecore.convert import max_chroma, oklch_to_hex
from palettecore.generate import DEFAULT_THRESHOLDS, generate_palette


def margin(r, key):
    return min(r.diagnostics[key][c] - DEFAULT_THRESHOLDS[c] for c in DEFAULT_THRESHOLDS)


def worst(r, key):
    return min(DEFAULT_THRESHOLDS, key=lambda c: r.diagnostics[key][c] - DEFAULT_THRESHOLDS[c])


def seed_hex(L, C, H):
    return oklch_to_hex(np.array([L, C, H]))


def sweep_hue(L=0.65, frac=0.75, n=8):
    print(f"sequential hue scan: L={L}, C={frac}*max, n={n}")
    for H in range(0, 360, 15):
        C = frac * max_chroma(L, H)
        r = generate_palette(seed_hex(L, C, H), n=n, kind="sequential")
        print(f"  H={H:3d} C={C:.3f} {margin(r, 'min_adjacent_deltaE'):+.2f} ({worst(r, 'min_adjacent_deltaE')})")


def sweep_chroma(L=0.65, n=8):
    print(f"categorical chroma response: L={L}, n={n}")
    for H in (0, 90, 180, 270):
        for f in (0.3, 0.5, 0.7, 0.9):
            C = f * max_chroma(L, H)
            r = generate_palette(seed_hex(L, C, H), n=n, kind="categorical")
            print(f"  H={H:3d} f={f} C={C:.3f} {margin(r, 'min_pairwise_deltaE'):+.2f} ({worst(r, 'min_pairwise_deltaE')})")


def sweep_n(L=0.65, frac=0.75):
    print(f"sequential n sensitivity: L={L}, C={frac}*max")
    for H in (0, 120, 300):
        hexc = seed_hex(L, frac * max_chroma(L, H), H)
        for n in (6, 8, 10, 12):
            r = generate_palette(hexc, n=n, kind="sequential")
            print(f"  H={H:3d} n={n:2d} {margin(r, 'min_adjacent_deltaE'):+.2f} ({worst(r, 'min_adjacent_deltaE')})")


def sweep_grid(frac=0.75, n=8):
    print(f"coarse grid: C={frac}*max, n={n}, sequential + categorical")
    for L in (0.88, 0.75, 0.60, 0.45):
        for H in range(0, 360, 30):
            C = frac * max_chroma(L, H)
            hexc = seed_hex(L, C, H)
            s = generate_palette(hexc, n=n, kind="sequential")
            k = generate_palette(hexc, n=n, kind="categorical")
            print(
                f"  L={L} H={H:3d} C={C:.2f} "
                f"seq {margin(s, 'min_adjacent_deltaE'):+.1f} ({worst(s, 'min_adjacent_deltaE')[:4]}) "
                f"cat {margin(k, 'min_pairwise_deltaE'):+.1f} ({worst(k, 'min_pairwise_deltaE')[:4]})"
            )


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "hue"
    {"hue": sweep_hue, "chroma": sweep_chroma, "n": sweep_n, "grid": sweep_grid}[which]()
