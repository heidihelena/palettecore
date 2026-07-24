"""Pitch-to-colour, helix model (not stacked circles).

Correction to pitch_color_ring.py: pitch is a HELIX, not a closed circle.
- angle around the helix = pitch class (cyclic, 12 hues from the closed
  CIEDE2000-spaced ring)
- height = lightness = absolute pitch (monotonic over the whole range)

Because lightness rises monotonically with absolute pitch, and lightness is
the one channel a dichromat keeps, notes an octave apart are always separated
for every viewer. The within-octave hue collapse under CVD only bites when two
notes sit at the SAME height; on the helix, melodic motion moves height, so
the octave/lightness axis carries the CVD-safe disambiguation automatically.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np

from palettecore.convert import hex_to_srgb, max_chroma, oklab_to_srgb, oklch_to_oklab, srgb_to_hex
from palettecore.cvd import CONDITIONS, simulate_cvd
from palettecore.metrics import ciede2000
from pitch_color_ring import closed_deltaE_ring  # the 12 ΔE-spaced hue angles

NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
F_C4 = 261.626
OUT = pathlib.Path(__file__).resolve().parent / "output"


def _safe_chroma(L, samples=180):
    return 0.92 * min(max_chroma(L, float(h)) for h in np.linspace(0, 360, samples, endpoint=False))


def helix(n_low=-12, n_high=24, L_lo=0.32, L_hi=0.92):
    """Absolute semitone index n (0 = C4) over a range; lightness climbs
    monotonically with n, hue cycles every 12. Returns list of dicts."""
    _, hues, _ = closed_deltaE_ring(0.65, n=12)  # pitch-class hue angles
    span = n_high - n_low
    out = []
    for n in range(n_low, n_high + 1):
        L = L_lo + (L_hi - L_lo) * (n - n_low) / span
        pc = n % 12
        h = float(hues[pc])
        C = min(_safe_chroma(L), max_chroma(L, h))
        rgb = np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, C, h]))), 0, 1)
        octave = 4 + (n // 12)
        out.append({"n": n, "note": f"{NOTE[pc]}{octave}", "pc": NOTE[pc],
                    "f": round(F_C4 * 2 ** (n / 12), 2), "L": round(L, 3),
                    "hue": round(h, 1), "hex": srgb_to_hex(rgb)})
    return out


def _min_pairwise(rgbs, cond):
    n = len(rgbs)
    cols = [simulate_cvd(c, cond) if cond else c for c in rgbs]
    return round(min(ciede2000(cols[i], cols[j]) for i in range(n) for j in range(i + 1, n)), 1)


def main():
    OUT.mkdir(exist_ok=True)
    hx = helix()
    rgbs = [hex_to_srgb(p["hex"]) for p in hx]

    # Adjacent semitone steps (melodic neighbours) under each vision.
    adj = {}
    for cond in (None, *CONDITIONS):
        key = cond or "normal"
        adj[key] = round(float(np.mean(
            [ciede2000(simulate_cvd(rgbs[i], cond) if cond else rgbs[i],
                       simulate_cvd(rgbs[i + 1], cond) if cond else rgbs[i + 1])
             for i in range(len(rgbs) - 1)])), 1)

    # Octave neighbours (n, n+12): the CVD-safe separation lightness buys.
    octpairs = {}
    for cond in (None, *CONDITIONS):
        key = cond or "normal"
        vals = [ciede2000(simulate_cvd(rgbs[i], cond) if cond else rgbs[i],
                          simulate_cvd(rgbs[i + 12], cond) if cond else rgbs[i + 12])
                for i in range(len(rgbs) - 12)]
        octpairs[key] = round(float(np.min(vals)), 1)

    mapping = {"model": "pitch helix: angle=pitch class (ΔE-spaced hues), height=lightness=absolute pitch",
               "notes": hx,
               "mean_adjacent_semitone_deltaE": adj,
               "min_octave_pair_deltaE": octpairs}
    (OUT / "pitch_color_helix.json").write_text(json.dumps(mapping, indent=2))

    print("Pitch helix (C3..C6), height = lightness = absolute pitch\n")
    print(f"  {'note':5s} {'f(Hz)':>8s}  {'L':>5s}  {'hue':>5s}  hex")
    for p in hx:
        if p["pc"] == "C" or p["n"] in (hx[0]["n"], hx[-1]["n"]):
            print(f"  {p['note']:5s} {p['f']:8.2f}  {p['L']:.3f}  {p['hue']:5.1f}  {p['hex']}   <- C, octave marker")
    print(f"\nMean ADJACENT semitone ΔE (melodic neighbours), by vision:\n  {adj}")
    print(f"Min OCTAVE-pair ΔE (n vs n+12), by vision:\n  {octpairs}")
    print("\nReading: adjacent semitones still lean on hue (CVD-weak), but any octave move is\n"
          "CVD-safe via lightness — so the helix carries pitch height to every viewer.")


if __name__ == "__main__":
    main()
