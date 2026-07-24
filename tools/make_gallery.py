"""Render docs/example_palettes.png — the four example palettes for the README.

Rows 1-3 are the original palette kinds; row 4 is a cubehelix-inspired OKLCH
run. Every row is labelled with the returned palette's audited normal and
worst simulated-CVD minimum, never a mean.
"""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from palettecore import generate_palette

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


def main():
    DOCS.mkdir(exist_ok=True)
    rows = [
        ("Sequential", "one hue, even ΔE steps, monotone luminance",
         generate_palette("#3C7AC0", n=8, kind="sequential")),
        ("Diverging", "two poles, light neutral centre",
         generate_palette("#B84A3C", n=9, kind="diverging")),
        ("Categorical", "unordered groups, CVD-audited, vividness=0.6",
         generate_palette("#B57EDC", n=8, kind="categorical", vividness=0.6)),
        ("Helix (cubehelix-inspired)", "designed lightness climbs while hue rotates",
         generate_palette("#B84A3C", n=8, kind="helix", rotations=1.4, vividness=0.4)),
    ]

    fig, axes = plt.subplots(len(rows), 1, figsize=(9, 5.2))
    for ax, (title, description, result) in zip(axes, rows):
        hexes = result.hexes
        minima = (
            result.diagnostics.get("min_adjacent_deltaE")
            or result.diagnostics["min_pairwise_deltaE"]
        )
        sub = (
            f"{description} — normal min ΔE {minima['normal']:.1f}; "
            f"worst simulated-CVD min {min(minima[c] for c in minima if c != 'normal'):.1f}"
        )
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
