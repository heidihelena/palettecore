"""Where does the pitch helix become semitone-safe for every viewer?

Two sweeps that map the tension the helix audit exposed: height/octave is
CVD-safe, but adjacent-semitone identity is not, because the per-step lightness
increment is too small to lift a CVD-collapsed hue above the dE 6 floor.

  A. RANGE sweep (12 classes/octave): shrink the pitch range so lightness
     climbs faster per semitone. How few octaves buy semitone-safety for all?
  B. RESOLUTION sweep (fixed 3 octaves): fewer classes/octave = bigger hue
     steps. How coarse must the scale be before every step clears 6 for all?

Everything is reported as the MINIMUM adjacent dE and the count of steps below
the floor, per observer — never the mean.
"""

from __future__ import annotations

import functools
import json
import pathlib

import numpy as np

from palettecore.convert import max_chroma, oklab_to_srgb, oklch_to_oklab
from palettecore.cvd import CONDITIONS, simulate_cvd
from palettecore.metrics import ciede2000

OUT = pathlib.Path(__file__).resolve().parent / "output"
FLOOR = 6.0


@functools.lru_cache(maxsize=4096)
def _max_chroma(Lr, Hr):
    return max_chroma(Lr, Hr)


@functools.lru_cache(maxsize=2048)
def _safe_chroma(Lr, samples=120):
    return 0.92 * min(_max_chroma(Lr, round(float(h), 1))
                      for h in np.linspace(0, 360, samples, endpoint=False))


def _rgb(L, C, H):
    return np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, C, H]))), 0, 1)


@functools.lru_cache(maxsize=64)
def closed_ring_hues(k, L=0.61, dense=1440):
    """k hue angles equally spaced by cumulative CIEDE2000 around a closed,
    constant-L, constant-C loop (the wrap interval included)."""
    C = _safe_chroma(round(L, 3))
    hues = np.linspace(0, 360, dense, endpoint=False)
    ring = np.array([_rgb(L, C, h) for h in hues])
    d = np.zeros(dense + 1)
    for i in range(1, dense):
        d[i] = d[i - 1] + ciede2000(ring[i - 1], ring[i])
    d[dense] = d[dense - 1] + ciede2000(ring[dense - 1], ring[0])
    targets = d[dense] * np.arange(k) / k
    idx = [int(np.argmin(np.abs(d[:dense] - t))) for t in targets]
    return tuple(float(hues[i]) for i in idx)


def helix_colours(k_per_oct, octaves, L_lo=0.30, L_hi=0.92):
    """k_per_oct equal divisions of the octave, wound through `octaves` turns,
    lightness climbing monotonically with absolute step index."""
    hues = closed_ring_hues(k_per_oct)
    total = k_per_oct * octaves
    cols = []
    for n in range(total + 1):
        L = L_lo + (L_hi - L_lo) * n / total
        H = hues[n % k_per_oct]
        C = min(_safe_chroma(round(L, 3)), _max_chroma(round(L, 3), round(H, 1)))
        cols.append(_rgb(L, C, H))
    return cols


def adjacent_min(cols):
    """min adjacent dE and #below-floor per observer (the honest claim)."""
    out = {}
    for cond in (None, *CONDITIONS):
        key = cond or "normal"
        vec = [ciede2000(simulate_cvd(cols[i], cond) if cond else cols[i],
                         simulate_cvd(cols[i + 1], cond) if cond else cols[i + 1])
               for i in range(len(cols) - 1)]
        out[key] = {"min": round(float(np.min(vec)), 1),
                    "below_floor": int(np.sum(np.array(vec) < FLOOR)),
                    "steps": len(vec)}
    return out


def _cvd_worst_min(stats):
    """Worst (smallest) minimum across the three CVD conditions."""
    return min(stats[c]["min"] for c in CONDITIONS)


def main():
    OUT.mkdir(exist_ok=True)
    result = {"floor": FLOOR, "range_sweep": {}, "resolution_sweep": {}}

    print("A. RANGE sweep (12 classes/octave). CVD-min = worst min over the 3 deficiencies.\n")
    print(f"  {'octaves':>7s} {'dL/step':>8s} {'normal':>7s} {'CVD-min':>8s} {'CVD steps<6':>12s}  semitone-safe?")
    for octaves in (1, 2, 3, 4, 6):
        cols = helix_colours(12, octaves)
        st = adjacent_min(cols)
        cvd_min = _cvd_worst_min(st)
        cvd_below = sum(st[c]["below_floor"] for c in CONDITIONS)
        safe = all(st[c]["min"] >= FLOOR for c in CONDITIONS)
        dL = round(0.62 / (12 * octaves), 4)
        result["range_sweep"][octaves] = {"dL_per_step": dL, "stats": st,
                                          "cvd_min": cvd_min, "semitone_safe_all_cvd": safe}
        print(f"  {octaves:7d} {dL:8.4f} {st['normal']['min']:7.1f} {cvd_min:8.1f} "
              f"{cvd_below:12d}  {'YES' if safe else 'no'}")

    print("\nB. RESOLUTION sweep (fixed 3 octaves). Fewer classes/octave = bigger hue steps.\n")
    print(f"  {'classes':>7s} {'normal':>7s} {'CVD-min':>8s} {'CVD steps<6':>12s}  semitone-safe?")
    for k in (12, 7, 6, 5, 4, 3):
        cols = helix_colours(k, 3)
        st = adjacent_min(cols)
        cvd_min = _cvd_worst_min(st)
        cvd_below = sum(st[c]["below_floor"] for c in CONDITIONS)
        safe = all(st[c]["min"] >= FLOOR for c in CONDITIONS)
        result["resolution_sweep"][k] = {"stats": st, "cvd_min": cvd_min,
                                         "semitone_safe_all_cvd": safe}
        print(f"  {k:7d} {st['normal']['min']:7.1f} {cvd_min:8.1f} "
              f"{cvd_below:12d}  {'YES' if safe else 'no'}")

    (OUT / "pitch_color_frontier.json").write_text(json.dumps(result, indent=2))
    print(f"\nwrote {OUT / 'pitch_color_frontier.json'}")
    return result


if __name__ == "__main__":
    main()
