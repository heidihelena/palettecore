"""Pitch-to-colour, helix model (not stacked circles).

Correction to pitch_color_ring.py: model pitch as a HELIX, not a closed circle.
- angle around the helix = pitch class (cyclic, 12 hues from the closed
  CIEDE2000-spaced ring)
- height = lightness = absolute pitch (monotonic over the whole range)

Designed lightness rises monotonically with absolute pitch. The audit must
still check the returned colours under each simulation: hue-dependent
luminance can reverse locally, and adjacent notes can collapse even while
octave pairs remain well separated.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np

from palettecore.convert import hex_to_srgb, max_chroma, oklab_to_srgb, oklch_to_oklab, srgb_to_hex
from palettecore.cvd import CONDITIONS, simulate_cvd
from palettecore.metrics import ciede2000, greyscale_values
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

    # Pitch order is an increasing-luminance claim, not merely a colour-
    # difference claim. Report local reversals explicitly for every model.
    luminance_order = {}
    for cond in (None, *CONDITIONS):
        key = cond or "normal"
        cols = [simulate_cvd(c, cond) if cond else c for c in rgbs]
        vals = greyscale_values(np.array(cols))
        steps = np.diff(vals)
        luminance_order[key] = {
            "monotonic_increasing": bool(np.all(steps >= -1e-4)),
            "n_reversals": int(np.sum(steps < -1e-4)),
            "worst_step": round(float(np.min(steps)), 4),
        }

    # Adjacent semitone steps (melodic neighbours): the FULL per-interval
    # vector under each vision, so min (not just mean) drives the claim.
    adj = {}
    for cond in (None, *CONDITIONS):
        key = cond or "normal"
        vec = [ciede2000(simulate_cvd(rgbs[i], cond) if cond else rgbs[i],
                         simulate_cvd(rgbs[i + 1], cond) if cond else rgbs[i + 1])
               for i in range(len(rgbs) - 1)]
        i_worst = int(np.argmin(vec))
        adj[key] = {
            "min": round(float(np.min(vec)), 1),
            "mean": round(float(np.mean(vec)), 1),
            "max": round(float(np.max(vec)), 1),
            "spread": round(float(np.max(vec) - np.min(vec)), 1),
            "cv": round(float(np.std(vec) / np.mean(vec)), 2),
            "worst_interval": f"{hx[i_worst]['note']}->{hx[i_worst + 1]['note']}",
            "worst_value": round(float(np.min(vec)), 1),
            "n_below_6": int(np.sum(np.array(vec) < 6.0)),
        }

    # Octave neighbours (n, n+12): the strong separation lightness buys in
    # these simulations.
    octpairs = {}
    for cond in (None, *CONDITIONS):
        key = cond or "normal"
        vals = [ciede2000(simulate_cvd(rgbs[i], cond) if cond else rgbs[i],
                          simulate_cvd(rgbs[i + 12], cond) if cond else rgbs[i + 12])
                for i in range(len(rgbs) - 12)]
        octpairs[key] = round(float(np.min(vals)), 1)

    mapping = {"model": "gamut-constrained perceptual pitch helix: angle=pitch class "
                        "(ΔE-spaced hues), height=lightness=absolute pitch; chroma = "
                        "per-lightness safe value (narrows near L extremes)",
               "notes": hx,
               "adjacent_semitone_deltaE": adj,
               "luminance_order": luminance_order,
               "min_octave_pair_deltaE": octpairs}
    (OUT / "pitch_color_helix.json").write_text(json.dumps(mapping, indent=2))

    print("Gamut-constrained perceptual pitch helix (C3..C6)\n")
    print(f"  {'note':5s} {'f(Hz)':>8s}  {'L':>5s}  {'hue':>5s}  hex")
    for p in hx:
        if p["pc"] == "C" or p["n"] in (hx[0]["n"], hx[-1]["n"]):
            print(f"  {p['note']:5s} {p['f']:8.2f}  {p['L']:.3f}  {p['hue']:5.1f}  {p['hex']}   <- C")
    print("\nADJACENT semitone ΔE (melodic neighbours), full vector by vision:")
    print(f"  {'vision':13s} {'min':>5s} {'mean':>5s} {'max':>5s} {'spread':>7s} {'<6':>4s}  worst")
    for k, s in adj.items():
        print(f"  {k:13s} {s['min']:5.1f} {s['mean']:5.1f} {s['max']:5.1f} {s['spread']:7.1f} "
              f"{s['n_below_6']:4d}  {s['worst_interval']} ({s['worst_value']})")
    print("\nLUMINANCE order with rising pitch:")
    for k, s in luminance_order.items():
        print(
            f"  {k:13s} monotonic={str(s['monotonic_increasing']):5s} "
            f"reversals={s['n_reversals']:2d}  worst step={s['worst_step']:+.4f}"
        )
    print(f"\nMin OCTAVE-pair ΔE (n vs n+12), by vision:\n  {octpairs}")
    print("\nReading: the claim to report is the MINIMUM adjacent ΔE per condition, and how\n"
          "many steps fall below the threshold — not the mean.")


if __name__ == "__main__":
    main()
