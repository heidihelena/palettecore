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

### Result (C3..C6)

- Adjacent semitone dE00 stays above the 6 floor under every simulated
  deficiency (normal 11.0, protan 7.1, deutan 6.9, tritan 9.2), because each
  step advances lightness as well as hue.
- Octave pairs are strongly separated for all viewers (min dE ~15.9-17.9).
- The flat-ring collapse is gone: moving from stacked circles to one climbing
  helix puts the CVD-safe lightness axis to work on every step.

**Honest limit:** lightness is finite, so the helix spends the displayable
lightness range over ~3-4 octaves. A full piano range (7+ octaves) would
exhaust lightness and octaves far apart would collide in lightness; the model
suits a melodic/vocal range, not the whole keyboard.
