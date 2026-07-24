# experiments

Research prototypes that reuse palettecore's perceptual core but are **not**
part of the package API.

## pitch_color_ring.py — a 12-tone colour ring

A first-pass cross-modal model (Andersen, 2026): map the 12 pitch classes of
equal temperament to a **closed** colour loop whose adjacent CIEDE2000 steps
(including the wrap) are approximately equal, and carry octave by lightness.
Colour is a redundant **enhancer** of pitch, never a claim that a note "is" a
colour.

```
PYTHONPATH=. python3 experiments/pitch_color_ring.py   # ring + audit + tones
PYTHONPATH=. python3 experiments/render_wheel.py        # the wheel figure
```

Outputs (in `output/`, audio git-ignored): `pitch_color_map.json`,
`pitch_color_wheel.png`, and 13 `.wav` tones (C4..C5).

### What the first run shows

- **Normal vision:** the closed ring is evenly stepped (adjacent dE00 mean
  ~12.5, spread ~0.7) — a clean perceptual analogue of equal temperament.
- **Colour-vision deficiency:** the ring collapses (min pairwise dE ~0.7-2.1),
  because a constant-lightness hue ring is exactly what dichromacy flattens,
  and lightness is already spent on octave. This is the finding, not a bug: it
  is *why* colour here must enhance an auditory signal, never replace it.

### What it does NOT do

It builds the stimulus and audits its perceptual structure. It does not test
the human claims (does colour improve pitch ordering, interval discrimination,
melody memory, or help under hearing loss). Those need a listening study; this
is the defensible stimulus generator that would feed one.

## pitch_color_helix.py — the helix correction (recommended model)

Pitch is a **helix**, not stacked circles: angle = pitch class, height =
lightness = absolute pitch. Because lightness rises monotonically with pitch
and lightness is the CVD-safe channel, this model is distinguishable for every
viewer, not just normal vision.

```
PYTHONPATH=.:experiments python3 experiments/pitch_color_helix.py
PYTHONPATH=.:experiments python3 experiments/render_helix.py
```

### Result (C3..C6) — reported as the MINIMUM adjacent step, not the mean

The audit emits the full per-interval vector. What it shows (min | mean |
steps of 36 below the dE 6 floor):

| Vision | min | mean | below 6 |
|---|---|---|---|
| normal | 6.5 | 11.0 | 0 |
| protanopia | 0.7 | 7.1 | 17 |
| deuteranopia | 1.6 | 6.9 | 16 |
| tritanopia | 1.9 | 9.2 | 17 |

Octave-pair minimum: 15.9-17.9 across all conditions.

Honest reading (an earlier draft wrongly claimed every step clears 6 from the
*mean*; the minimum disproves it):

- **Normal vision:** every adjacent semitone clears the floor (min 6.5) — the
  full 12-tone code is distinguishable.
- **Under CVD:** about half the adjacent semitones fall below 6 (min 0.7-1.9),
  because the per-semitone lightness step (~0.017 L, ~1.5-2 dE) cannot lift a
  hue that has collapsed onto the dichromat axis. The colour does NOT convey
  fine semitone identity to a CVD viewer.
- **What DOES survive CVD:** pitch *height* and *octave*. Lightness is
  monotonic with pitch and octave pairs stay >=15.9 dE, so a CVD viewer reliably
  reads higher-vs-lower, register and melodic contour — just not which of two
  neighbouring semitones. That is the scoped, true enhancer claim.

**Two structural limits, both real:**
1. Lightness is finite, so the helix spends the displayable range over ~3-4
   octaves; a full piano range would exhaust it.
2. It is a *gamut-constrained* perceptual helix, not constant-radius: safe
   chroma pinches near L 0.32 and 0.92, so hue steps carry less dE at the
   extremes (visible as normal vision's tightest step, 6.5, at the pale top).

Making semitones CVD-safe would need a steeper lightness climb per step, which
spends the lightness range faster and shrinks the usable span below 3-4
octaves. Height-safe-for-all and semitone-safe-for-all cannot both hold across
a useful range: a genuine pass / fail / not-resolvable result, not a clean win.
