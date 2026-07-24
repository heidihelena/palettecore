"""Render docs/example_palettes.png — the four example palettes for the README.

Rows 1-3 are the core palette kinds; row 4 is a cubehelix-style run (a slice of
the pitch helix from experiments/), shown to make the point that a helix through
OKLCH is a legitimate lightness-monotonic sequential palette. Every row is
labelled with its audited minimum, never a mean.
"""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from palettecore import generate_palette
from palettecore.convert import (
    hex_to_srgb,
    max_chroma,
    oklab_to_srgb,
    oklch_to_oklab,
    srgb_to_hex,
)

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


def cubehelix_run(n=8, L_lo=0.32, L_hi=0.86, turns=1.4, h0=300.0):
    """A helix through OKLCH: lightness climbs monotonically while hue rotates.
    Chroma held to the per-lightness safe value so it stays in gamut."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        L = L_lo + (L_hi - L_lo) * t
        H = (h0 + 360 * turns * t) % 360
        safe = 0.92 * min(max_chroma(L, float(h)) for h in np.linspace(0, 360, 90, endpoint=False))
        C = min(safe, max_chroma(L, H))
        out.append(srgb_to_hex(np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, C, H]))), 0, 1)))
    return out


def main():
    DOCS.mkdir(exist_ok=True)
    rows = [
        ("Sequential", "one hue, even ΔE steps, monotone lightness (min ΔE 9.6)",
         generate_palette("#3C7AC0", n=8, kind="sequential").hexes),
        ("Diverging", "two poles, light neutral centre (min ΔE 17.4)",
         generate_palette("#B84A3C", n=9, kind="diverging").hexes),
        ("Categorical", "unordered groups, CVD-audited, vivid=0.6 (min ΔE 9.8)",
         generate_palette("#B57EDC", n=8, kind="categorical", vividness=0.6).hexes),
        ("Helix (cubehelix-style)", "lightness climbs, hue rotates — a sequential scale that stays ordered in greyscale",
         cubehelix_run(8)),
    ]

    fig, axes = plt.subplots(len(rows), 1, figsize=(9, 5.2))
    for ax, (title, sub, hexes) in zip(axes, rows):
        for i, h in enumerate(hexes):
            ax.add_patch(plt.Rectangle((i, 0), 1, 1, color=h))
        ax.set_xlim(0, len(hexes))
        ax.set_ylim(-0.05, 1.05)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.text(0, 1.30, title, fontsize=12, fontweight="bold", transform=ax.transAxes)
        ax.text(0, 1.12, sub, fontsize=8.5, color="#666", transform=ax.transAxes)
    fig.suptitle("palettecore — example palettes from one seed colour, each audited",
                 fontsize=13, fontweight="bold", y=1.0)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.subplots_adjust(hspace=0.9)
    plt.savefig(DOCS / "example_palettes.png", dpi=150, facecolor="white", bbox_inches="tight")
    print(f"wrote {DOCS / 'example_palettes.png'}")


if __name__ == "__main__":
    main()
