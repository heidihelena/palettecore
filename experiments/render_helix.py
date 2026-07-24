"""Render the 3D pitch helix (normal vs simulated deuteranopia) from
experiments/output/pitch_color_helix.json. Run pitch_color_helix.py first.
"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from palettecore.convert import hex_to_srgb, srgb_to_hex
from palettecore.cvd import simulate_cvd

OUT = pathlib.Path(__file__).resolve().parent / "output"


def _xyz(p):
    ang = 2 * np.pi * (p["n"] % 12) / 12
    return np.cos(ang), np.sin(ang), p["n"]


def main():
    pts = json.loads((OUT / "pitch_color_helix.json").read_text())["notes"]
    fig = plt.figure(figsize=(11, 6))
    for k, (title, sim) in enumerate([("What most readers see", None),
                                      ("Simulated deuteranopia", "deuteranopia")]):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        xs, ys, zs, cs = [], [], [], []
        for p in pts:
            x, y, z = _xyz(p)
            xs.append(x); ys.append(y); zs.append(z)
            c = p["hex"]
            if sim:
                c = srgb_to_hex(simulate_cvd(hex_to_srgb(c), sim))
            cs.append(c)
        ax.plot(xs, ys, zs, color="#bbb", lw=0.8, zorder=1)
        ax.scatter(xs, ys, zs, c=cs, s=90, edgecolors="white", linewidths=0.6,
                   depthshade=False, zorder=2)
        for p in pts:
            if p["pc"] == "C":
                x, y, z = _xyz(p)
                ax.text(x, y, z, f"  {p['note']}", fontsize=9, fontweight="bold", color="#333")
        ax.set_title(title, fontsize=12, fontweight="bold", pad=0)
        ax.set_zlabel("absolute pitch = lightness", fontsize=9)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        ax.view_init(elev=12, azim=-60)
    fig.suptitle("Pitch helix: angle = pitch class, height = lightness = absolute pitch",
                 fontsize=13, fontweight="bold", y=0.97)
    fig.text(0.5, 0.04,
             "Under deuteranopia the hues flatten, but the vertical climb (lightness) survives.\n"
             "Adjacent semitone dE stays above threshold; octave pairs are strongly separated for all viewers.",
             ha="center", fontsize=8.3, color="#555")
    plt.subplots_adjust(top=0.9, bottom=0.13, wspace=0.05)
    plt.savefig(OUT / "pitch_color_helix.png", dpi=150, facecolor="white")
    print(f"wrote {OUT / 'pitch_color_helix.png'}")


if __name__ == "__main__":
    main()
