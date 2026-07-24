"""Render the pitch-class colour wheel (normal vs simulated deuteranopia)
from experiments/output/pitch_color_map.json. Run pitch_color_ring.py first.
"""

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from palettecore.convert import hex_to_srgb, srgb_to_hex
from palettecore.cvd import simulate_cvd

OUT = pathlib.Path(__file__).resolve().parent / "output"
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def main():
    m = json.loads((OUT / "pitch_color_map.json").read_text())
    hexes = [m["octaves"]["C4"]["colours"][n] for n in NOTES]
    deut = [srgb_to_hex(simulate_cvd(hex_to_srgb(h), "deuteranopia")) for h in hexes]

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), subplot_kw={"projection": "polar"})
    for ax, cols, title in [(axes[0], hexes, "What most readers see"),
                            (axes[1], deut, "Simulated deuteranopia")]:
        N = 12
        width = 2 * np.pi / N
        theta = np.pi / 2 - np.arange(N) * width
        ax.bar(theta, np.ones(N), width=width * 0.98, bottom=0.6,
               color=cols, edgecolor="white", linewidth=1.5)
        for i, n in enumerate(NOTES):
            ax.text(theta[i], 1.72, n, ha="center", va="center",
                    fontsize=11, fontweight="bold", color="#333")
        ax.set_ylim(0, 1.9)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["polar"].set_visible(False)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=14)
    fig.suptitle("A closed dE-spaced colour ring for the 12 pitch classes (octave = lightness)",
                 fontsize=13, fontweight="bold")
    fig.text(0.5, 0.03,
             "Left: equal perceptual steps around the loop. Right: the same ring under "
             "deuteranopia collapses.\nThe 12-hue ring holds only for normal vision; "
             "colour must ENHANCE the pitch, not replace it.",
             ha="center", fontsize=8.5, color="#555")
    plt.subplots_adjust(top=0.86, bottom=0.16, wspace=0.25)
    plt.savefig(OUT / "pitch_color_wheel.png", dpi=150, facecolor="white")
    print(f"wrote {OUT / 'pitch_color_wheel.png'}")


if __name__ == "__main__":
    main()
