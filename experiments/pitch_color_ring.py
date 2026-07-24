"""Pitch-to-colour experiment: a closed, ΔE-spaced 12-tone colour ring.

First-pass model (Andersen, 2026) built on palettecore's perceptual core.
The question this prototype makes testable:

    Can a circular, CIEDE2000-spaced colour code preserve the structure of a
    12-tone logarithmic pitch scale, with octave identity carried by lightness?

Design decisions, stated:
- 12-tone equal temperament from middle C: f_n = 261.626 * 2^(n/12).
- Pitch CLASS -> position on a CLOSED colour loop, placed so every adjacent
  step (including the wrap c11 -> c0) is an approximately equal CIEDE2000
  distance. Equal perceptual steps, not equal 30-degree hue angles.
- Octave -> lightness: the same 12 hue angles are reused at each octave's
  lightness, so C4 and C5 are the SAME colour position, separated only by
  lightness (pitch-class identity across octaves).
- Colour is a redundant ENHANCER of an auditory structure, never a claim that
  a given pitch "is" a given colour. The pitch-class -> hue assignment is a
  designed convention (Newton and Scriabin disagreed); only pitch-height ->
  lightness has robust cross-modal grounding.

This is an experiment that reuses palettecore internals; it is not part of the
package's public palette API.
"""

from __future__ import annotations

import json
import math
import pathlib
import struct
import wave

import numpy as np

from palettecore.convert import (
    hex_to_srgb,
    max_chroma,
    oklab_to_srgb,
    oklch_to_oklab,
    srgb_to_hex,
)
from palettecore.cvd import CONDITIONS, simulate_cvd
from palettecore.metrics import ciede2000

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
F_C4 = 261.626
OUT = pathlib.Path(__file__).resolve().parent / "output"


# --------------------------------------------------------------- colour ring


def _safe_chroma(L: float, samples: int = 180) -> float:
    """Largest chroma displayable at EVERY hue for this lightness, so a
    constant-lightness, constant-chroma ring stays fully in gamut and closes
    cleanly."""
    hues = np.linspace(0, 360, samples, endpoint=False)
    return 0.92 * min(max_chroma(L, float(h)) for h in hues)


def closed_deltaE_ring(L: float, n: int = 12, dense: int = 1440):
    """n colours around a constant-L, constant-C hue loop, placed at equal
    cumulative CIEDE2000 including the closing wrap interval.

    Returns (hex list, chosen hue angles, adjacent dE list incl. wrap)."""
    C = _safe_chroma(L)
    hues = np.linspace(0.0, 360.0, dense, endpoint=False)
    ring = np.array(
        [np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, C, h]))), 0, 1) for h in hues]
    )
    # cumulative perceptual distance around the closed loop
    d = np.zeros(dense + 1)
    for i in range(1, dense):
        d[i] = d[i - 1] + ciede2000(ring[i - 1], ring[i])
    d[dense] = d[dense - 1] + ciede2000(ring[dense - 1], ring[0])  # wrap
    perimeter = d[dense]
    targets = perimeter * np.arange(n) / n
    idx = [int(np.argmin(np.abs(d[:dense] - t))) for t in targets]
    chosen_hues = hues[idx]
    hexes = [srgb_to_hex(ring[i]) for i in idx]
    # adjacent dE on the quantised colours actually returned, incl. wrap
    rgb = [hex_to_srgb(h) for h in hexes]
    adj = [round(ciede2000(rgb[i], rgb[(i + 1) % n]), 1) for i in range(n)]
    return hexes, chosen_hues, adj


def ring_at_hues(L: float, hues) -> list[str]:
    """The same hue angles rendered at a different lightness (an octave)."""
    C = _safe_chroma(L)
    out = []
    for h in hues:
        c = min(C, max_chroma(L, float(h)))
        out.append(srgb_to_hex(np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, c, h]))), 0, 1)))
    return out


# ------------------------------------------------------------------- audit


def audit_ring(hexes):
    rgb = [hex_to_srgb(h) for h in hexes]
    sims = {c: [simulate_cvd(x, c) for x in rgb] for c in CONDITIONS}
    n = len(hexes)
    out = {}
    for cond, cols in [("normal", rgb), *sims.items()]:
        worst = min(
            ciede2000(cols[i], cols[j]) for i in range(n) for j in range(i + 1, n)
        )
        out[cond] = round(worst, 1)
    return out


# --------------------------------------------------------------- tones (wav)


def write_tone(path, freq, seconds=0.6, sr=44100, attack=0.04, release=0.10):
    """A soft harmonic tone: fundamental plus weak decaying harmonics, gentle
    onset, little high-frequency energy. Timbre held fixed across notes; each
    normalised to equal RMS as a practical loudness match."""
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    harm_amp = [1.0, 0.25, 0.12, 0.06]  # between a sine and a soft flute
    wave_ = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harm_amp))
    env = np.ones_like(t)
    na, nr = int(sr * attack), int(sr * release)
    env[:na] = np.linspace(0, 1, na)
    env[-nr:] = np.linspace(1, 0, nr)
    wave_ *= env
    wave_ /= np.sqrt(np.mean(wave_**2))  # equal-RMS normalise
    wave_ *= 0.2  # headroom
    pcm = np.clip(wave_, -1, 1)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in pcm))


# ------------------------------------------------------------------- main


def main(write_audio=True):
    OUT.mkdir(exist_ok=True)
    L_C4 = 0.65
    hexes_c4, hues, adj = closed_deltaE_ring(L_C4, n=12)
    octaves = {"C3": 0.50, "C4": 0.65, "C5": 0.78}  # ~0.13 lightness per octave

    mapping = {
        "model": "12-TET from middle C; closed CIEDE2000-spaced colour ring; octave->lightness",
        "f_hz": {NOTE_NAMES[n]: round(F_C4 * 2 ** (n / 12), 2) for n in range(12)},
        "hue_angles_deg": {NOTE_NAMES[n]: round(float(hues[n]), 1) for n in range(12)},
        "octaves": {},
        "closed_ring_adjacent_deltaE": {"values": adj, "mean": round(float(np.mean(adj)), 1),
                                        "spread": round(float(max(adj) - min(adj)), 1)},
    }
    for name, L in octaves.items():
        hx = hexes_c4 if name == "C4" else ring_at_hues(L, hues)
        mapping["octaves"][name] = {
            "lightness": L,
            "colours": {NOTE_NAMES[n]: hx[n] for n in range(12)},
            "audit_min_deltaE": audit_ring(hx),
        }

    (OUT / "pitch_color_map.json").write_text(json.dumps(mapping, indent=2))

    print("Closed 12-tone colour ring (octave C4, L=0.65)")
    for n in range(12):
        print(f"  {NOTE_NAMES[n]:2s}  {mapping['f_hz'][NOTE_NAMES[n]]:7.2f} Hz  "
              f"hue {mapping['hue_angles_deg'][NOTE_NAMES[n]]:5.1f}  {hexes_c4[n]}")
    print(f"\nAdjacent dE (incl. wrap): {adj}")
    print(f"  mean {mapping['closed_ring_adjacent_deltaE']['mean']}, "
          f"spread {mapping['closed_ring_adjacent_deltaE']['spread']}")
    print("\nMin pairwise dE within an octave, by vision:")
    for name in octaves:
        print(f"  {name} (L={octaves[name]}): {mapping['octaves'][name]['audit_min_deltaE']}")

    if write_audio:
        for n in range(12):
            write_tone(OUT / f"{n:02d}_{NOTE_NAMES[n].replace('#','s')}4.wav",
                       F_C4 * 2 ** (n / 12))
        write_tone(OUT / "12_C5.wav", F_C4 * 2)  # octave, for the endpoint demo
        print(f"\nWrote 13 tones (C4..C5) to {OUT}")
    return mapping


if __name__ == "__main__":
    main()
