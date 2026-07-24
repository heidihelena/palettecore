"""Render the frontier sweeps from experiments/output/pitch_color_frontier.json.
Run pitch_color_frontier.py first."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = pathlib.Path(__file__).resolve().parent / "output"


def main():
    r = json.loads((OUT / "pitch_color_frontier.json").read_text())
    floor = r["floor"]
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11, 4.6))

    # A: range sweep
    octs = sorted(int(k) for k in r["range_sweep"])
    cvd = [r["range_sweep"][str(o)]["cvd_min"] for o in octs]
    nrm = [r["range_sweep"][str(o)]["stats"]["normal"]["min"] for o in octs]
    axA.plot(octs, nrm, "o-", color="#2a78d6", label="normal vision")
    axA.plot(octs, cvd, "s-", color="#d95926", label="worst CVD condition")
    axA.axhline(floor, ls="--", color="#888", lw=1)
    axA.text(octs[-1], floor + 0.2, "dE 6 floor", ha="right", fontsize=8, color="#666")
    axA.set_title("A. Range sweep (12 classes/octave)", fontsize=11, fontweight="bold")
    axA.set_xlabel("pitch range (octaves)")
    axA.set_ylabel("minimum adjacent dE00")
    axA.set_ylim(0, 12)
    axA.legend(fontsize=8, frameon=False)

    # B: resolution sweep
    ks = sorted(int(k) for k in r["resolution_sweep"])
    cvdB = [r["resolution_sweep"][str(k)]["cvd_min"] for k in ks]
    nrmB = [r["resolution_sweep"][str(k)]["stats"]["normal"]["min"] for k in ks]
    axB.plot(ks, nrmB, "o-", color="#2a78d6", label="normal vision")
    axB.plot(ks, cvdB, "s-", color="#d95926", label="worst CVD condition")
    axB.axhline(floor, ls="--", color="#888", lw=1)
    axB.axvline(4, ls=":", color="#1baf7a", lw=1.5)
    axB.text(4.1, 28, "CVD-safe\nat <=4/octave", fontsize=8, color="#0f6e56")
    axB.set_title("B. Resolution sweep (3 octaves)", fontsize=11, fontweight="bold")
    axB.set_xlabel("pitch classes per octave")
    axB.set_ylabel("minimum adjacent dE00")
    axB.legend(fontsize=8, frameon=False)

    fig.suptitle("Semitone-safety frontier: only fewer classes/octave crosses the floor for every viewer",
                 fontsize=12, fontweight="bold")
    fig.text(0.5, 0.01, "Reported as MINIMUM adjacent dE (not mean). Range compression never reaches the floor; "
             "resolution does, at <=4 classes/octave.", ha="center", fontsize=8.2, color="#555")
    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    plt.savefig(OUT / "pitch_color_frontier.png", dpi=150, facecolor="white")
    print(f"wrote {OUT / 'pitch_color_frontier.png'}")


if __name__ == "__main__":
    main()
