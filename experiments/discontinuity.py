"""Discontinuity — palette + arrival-process generator for the two catastrophes.

Two pieces, built as a pair, on the same pitch-colour helix as the rest of the
series (angle = pitch class on a closed CIEDE2000-spaced hue ring, height =
lightness = absolute pitch).

The series is an argument about regimes of uncertainty, and these two builds
carry the half of it that the waves and the rain cannot:

  waves      gradual, cyclical, predictable accumulation
  rain       dense and distributed; many small signals at once, and the work
             is separating pattern from noise
  volcano    ENDOGENOUS discontinuity. Pressure builds inside the system.
             Warning signs exist in principle. The collapse is explicable
             afterwards. This is risk that was present but overlooked.
  meteorite  EXOGENOUS discontinuity. It arrives from outside the system's
             predictive frame, with no precursor at all. This is uncertainty
             that could not have been known.

The distinction is the whole point, so it is implemented rather than merely
described, and the implementation is what the pieces report:

  volcano.html    the hazard is a function of an OBSERVABLE state. Strain
                  accumulates, and tremor rate, swelling and harmonic tremor
                  all rise with it before every eruption. A visitor who
                  watches can learn to call the eruption early, and the piece
                  keeps the precursor trace so the run can be read backwards.
  meteorite.html  the hazard is CONSTANT. Arrival times are drawn from a
                  memoryless (exponential) process, so the expected wait to
                  the next impact is the same at every instant no matter how
                  long the sky has been empty and no matter what is on screen.
                  Nothing in the piece predicts the next strike, and that is a
                  property of the process, not a difficulty of watching.

Both pieces use the four-class C-D-G-A ladder rather than the full chromatic
one: these are the builds whose subject is whether a signal could have been
read, so their own colour code is the one that survives simulated dichromacy.
The chromatic code that collapses is digital_rain.py's, where collapsing is
the subject.

Writes output/discontinuity.json and injects palette, audit and Machado
matrices into both builds between generated-code markers, so no artwork can
drift from the engine.

Run:  PYTHONPATH=.:experiments python3 experiments/discontinuity.py
"""

from __future__ import annotations

import json
import pathlib

import numpy as np

from palettecore.convert import hex_to_srgb, srgb_to_hex
from palettecore.cvd import CONDITIONS, MACHADO_10, simulate_cvd
from palettecore.metrics import ciede2000
from pitch_color_frontier import _max_chroma, _rgb, _safe_chroma, closed_ring_hues

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "output"
HTML = [HERE / n for n in ("volcano.html", "meteorite.html")]
FLOOR = 6.0
F_C4 = 261.626

# The four sounding pitch classes and their semitone offsets from C, as in
# waves_to_shore.py. Four hues per octave is the resolution the frontier sweep
# found to clear the exploratory floor in all three simulations.
LADDER4_OFFSETS = (("C", 0), ("D", 2), ("G", 7), ("A", 9))
N_OCTAVES = 4                      # C2..C6, one octave deeper than the waves
SPAN = 12 * N_OCTAVES
BASE_OCTAVE = 2


def ladder4():
    """C-D-G-A over C2..C6, closed by the final C6.

    Hue = one of 4 CIEDE2000-spaced angles by pitch class; lightness climbs
    with absolute semitone index, exactly the helix model. The extra low
    octave is the volcano's floor: depth reads as the system at rest.
    """
    hues = closed_ring_hues(4)
    steps = [(name, 12 * octave + off, k)
             for octave in range(N_OCTAVES)
             for k, (name, off) in enumerate(LADDER4_OFFSETS)]
    steps.append(("C", SPAN, 0))
    out = []
    for name, n, k in steps:
        L = 0.30 + (0.92 - 0.30) * n / SPAN
        H = hues[k]
        C = min(_safe_chroma(round(L, 3)), _max_chroma(round(L, 3), round(H, 1)))
        octave = BASE_OCTAVE + n // 12
        # semitones from C4, so the piece can sound the ladder directly
        semis = n - 12 * (4 - BASE_OCTAVE)
        out.append({"note": f"{name}{octave}", "pc": name,
                    "f": round(F_C4 * 2 ** (semis / 12), 2),
                    "L": round(L, 3), "hue": round(float(H), 1),
                    "hex": srgb_to_hex(_rgb(L, C, H))})
    return out


def audit(entries):
    """Adjacent + full-pairwise minimum dE per vision condition.

    Minima, never means. Adjacent order is the ladder order, which is the
    order the volcano climbs under load; the pairwise minimum is the claim
    that binds when two arbitrary notes are on screen together.
    """
    rgbs = [hex_to_srgb(e["hex"]) for e in entries]
    res = {}
    for cond in (None, *CONDITIONS):
        key = cond or "normal"
        cols = [simulate_cvd(c, cond) if cond else c for c in rgbs]
        adj = [ciede2000(cols[i], cols[i + 1]) for i in range(len(cols) - 1)]
        i_worst = int(np.argmin(adj))
        pair = min(ciede2000(cols[i], cols[j])
                   for i in range(len(cols)) for j in range(i + 1, len(cols)))
        res[key] = {
            "adjacent_min": round(float(np.min(adj)), 1),
            "adjacent_below_floor": int(np.sum(np.array(adj) < FLOOR)),
            "adjacent_steps": len(adj),
            "worst_adjacent": f"{entries[i_worst]['note']}->{entries[i_worst + 1]['note']}",
            "pairwise_min": round(float(pair), 1),
        }
    return res


def inject(html_path, payload):
    begin = "// BEGIN GENERATED by discontinuity.py — do not edit by hand"
    end = "// END GENERATED"
    text = html_path.read_text()
    i, j = text.index(begin), text.index(end)
    block = f"{begin}\nconst DATA = {json.dumps(payload, indent=1)};\n"
    html_path.write_text(text[:i] + block + text[j:])


def main():
    OUT.mkdir(exist_ok=True)
    ladder = ladder4()
    result = {
        "model": "pitch-colour helix (angle = pitch class on a closed dE-spaced "
                 "hue ring, height = lightness = absolute pitch), audited on the "
                 "exact colours the artworks display",
        "floor": FLOOR,
        "range": "C2..C6, four pitch classes per octave (C, D, G, A)",
        "regimes": {
            "volcano": "endogenous discontinuity: hazard is a rising function "
                       "of an observable state, so precursors exist and the "
                       "run can be read backwards",
            "meteorite": "exogenous discontinuity: arrivals are drawn from a "
                         "memoryless exponential process, so the hazard is "
                         "constant and no precursor exists to be found",
        },
        "ladder": ladder,
        "audit": audit(ladder),
    }
    (OUT / "discontinuity.json").write_text(json.dumps(result, indent=2))

    payload = {
        "ladder": ladder,
        "audit": result["audit"],
        "machado": {k: [[round(float(v), 6) for v in row] for row in m]
                    for k, m in MACHADO_10.items()},
    }
    for path in HTML:
        if path.exists():
            inject(path, payload)

    print(f"discontinuity — {len(ladder)} notes, "
          f"{ladder[0]['note']}..{ladder[-1]['note']} (floor {FLOOR}):")
    print(f"  {'vision':13s} {'adj min':>8s} {'adj <6':>9s} {'pair min':>9s}  worst adjacent")
    for k, s in result["audit"].items():
        print(f"  {k:13s} {s['adjacent_min']:8.1f} "
              f"{s['adjacent_below_floor']:4d}/{s['adjacent_steps']:<4d} "
              f"{s['pairwise_min']:9.1f}  {s['worst_adjacent']}")
    print(f"\nwrote {OUT / 'discontinuity.json'}")
    for path in HTML:
        print(f"updated generated palette block in {path.name}"
              if path.exists() else f"skipped (missing) {path.name}")


if __name__ == "__main__":
    main()
