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

## pitch_color_helix.py — the helix correction (recommended art model)

Model pitch as a **helix**, not stacked circles: angle = pitch class, height =
designed lightness = absolute pitch. The returned colours are still audited:
hue-dependent luminance can reverse locally after a CVD simulation, so a
monotonic OKLab construction is not automatically monotonic for every viewer.

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

Luminance order is increasing for normal vision, deuteranopia and tritanopia
in this run. The protanopia simulation has four small local reversals (worst
relative-luminance step about -0.0125). That rules out a blanket claim that
colour alone carries fine melodic contour to every viewer.

Honest reading (an earlier draft wrongly claimed every step clears 6 from the
*mean*; the minimum disproves it):

- **Normal vision:** every adjacent semitone clears the floor (min 6.5) — the
  full 12-tone code is distinguishable.
- **Under CVD:** about half the adjacent semitones fall below 6 (min 0.7-1.9),
  because the per-semitone lightness step (~0.017 L, ~1.5-2 dE) cannot lift a
  hue that has collapsed onto the dichromat axis. The colour does NOT convey
  fine semitone identity to a CVD viewer.
- **What DOES remain strong in the simulations:** octave and broad register.
  Octave pairs stay >=15.9 dE. Local higher-vs-lower order is not guaranteed:
  protanopia has four small luminance reversals and many adjacent colours fall
  below the design floor. Position, motion, labels, and sound remain the
  binding encodings; colour is an enhancer.

**Two structural limits, both real:**
1. Lightness is finite, so the helix spends the displayable range over ~3-4
   octaves; a full piano range would exhaust it.
2. It is a *gamut-constrained* perceptual helix, not constant-radius: safe
   chroma pinches near L 0.32 and 0.92, so hue steps carry less dE at the
   extremes (visible as normal vision's tightest step, 6.5, at the pale top).

Increasing adjacent simulated-CVD separation would need a steeper lightness
climb per step, which spends the lightness range faster and shrinks the usable
span below 3-4 octaves. Broad register separation and fine semitone separation
cannot both clear the chosen floor across a useful range: a genuine trade-off,
not a clean win.

## pitch_color_frontier.py — where does it clear the exploratory design floor?

Two sweeps, both reported as MINIMUM adjacent dE and count below the dE 6 floor
(never the mean), asking when adjacent steps clear the package's floor in all
three CVD simulations. ΔE 6 is a configurable package design rule, not a
human-validated accessibility cutoff or a guarantee of safety.

```
PYTHONPATH=.:experiments python3 experiments/pitch_color_frontier.py
PYTHONPATH=.:experiments python3 experiments/render_frontier.py
```

### A. Range sweep (12 classes/octave) — this lever does not reach

| octaves | dL/step | normal min | worst-CVD min | clears floor (all CVD)? |
|---|---|---|---|---|
| 1 | 0.052 | 8.5 | 3.5 | no |
| 2 | 0.026 | 7.3 | 1.5 | no |
| 3 | 0.017 | 6.6 | 0.9 | no |
| 4 | 0.013 | 6.3 | 0.5 | no |
| 6 | 0.009 | 6.1 | 0.2 | no |

Even compressed to a single octave (steepest possible lightness climb), the
full chromatic scale reaches only 3.5 dE under CVD. Range compression never
crosses the floor. (Normal vision also drifts toward its own limit, 6.1, at 6
octaves, as hues pack tighter and chroma pinches.)

### B. Resolution sweep (fixed 3 octaves) — this lever does

| classes/octave | normal min | worst-CVD min | clears floor (all CVD)? |
|---|---|---|---|
| 12 | 6.6 | 0.9 | no |
| 7 | 11.6 | 1.1 | no |
| 6 | 13.7 | 2.2 | no |
| 5 (pentatonic) | 16.8 | 4.0 | no (5 steps under) |
| 4 | 22.9 | 6.1 | **YES** |
| 3 | 30.2 | 7.2 | **YES** |

### Conclusion

Within this model, the binding constraint is the number of **hues**, not the
pitch range. Shrinking the range does not make the 12-tone chromatic mapping
clear the simulated-CVD design floor; reducing to <=4 classes per octave does
for this tested span. Pentatonic (5) comes close (worst-CVD 4.0).

This mirrors the palette result: normal vision tolerates more categories than
a CVD viewer. Here, with lightness already spent on pitch height, the CVD
budget for pitch class is about four distinct hues under the package defaults.

## waves_to_shore.html — the artwork (waves to the shore)

The findings above, staged as a piece you can watch and hear. A 14 000-point
sea rolls toward a shore; each incoming wave carries one note, coloured by the
helix model (hue = pitch class, lightness = pitch); the colour arrives with
the crest and the tone sounds the moment the wave breaks. The driftwood on the
sand is the 10 000-point tweet-art study popularised by @yuruyurau, rendered
point for point and beached as the control: it has no pitch, so it takes no
colour from the mapping.

```
PYTHONPATH=.:experiments python3 experiments/waves_to_shore.py   # palette + audit + inject
open experiments/waves_to_shore.html                             # then press play
```

The piece is self-contained (canvas + WebAudio, no dependencies). Its colours
and the Machado matrices are **injected** by `waves_to_shore.py` from the
palettecore engine — the artwork cannot drift from the audit, which lands in
`output/waves_to_shore.json` (a still is in `output/waves_to_shore.png`). Two
toggles put the experiments' findings on stage: a vision menu applies the
Machado dichromacy simulations to the whole scene, and a scale menu switches
between the default ladder (4 pitch classes per octave — C, D, G, A over
C3..C6) and the full 12-semitone helix, whose colour code visibly collapses
under the simulations.

Audit of the shipping ladders, minimum ΔE (floor 6, package design rule):

| Vision | ladder4 adj min | ladder4 pairwise min | ladder12 adj min | ladder12 pairwise min |
|---|---|---|---|---|
| normal | 23.2 | 18.7 | 6.5 | 6.5 |
| protanopia | 11.4 | 10.5 | 0.7 | 0.7 |
| deuteranopia | 14.2 | 7.0 | 1.6 | 1.6 |
| tritanopia | **5.8** | **5.8** | 1.9 | 1.9 |

Honest notes: the 4-class ladder does **not** fully clear the floor — its
C3→D3 step measures 5.8 under simulated tritanopia, just below 6, so the UI
says "near the audited floor", not "clears". (The frontier's clean result used
equal divisions of the octave; the musical C-D-G-A set trades a little ΔE for
consonance, and the audit reports what it costs.) The 12-semitone ladder
collapses under every simulation exactly as the helix audit predicts — in the
piece you can watch it happen. The pitch-class → hue mapping remains a
designed convention, and sound stays the binding encoding; the colour is an
enhancer, which is the point of the driftwood.

### waves_ambient.html — fullscreen, for studying

The same sea, edge to edge: no driftwood, almost no text, an interface that
fades when the pointer rests. Click anywhere for sound. Built to be embedded
on a host site as background sound-and-colour (typography hooks for
Nudica/Nudica Italic with a system fallback; colours are the audited C-D-G-A
ladder, embedded with provenance). `window.__frame(t)` renders any sim time
deterministically — the note walk has its own seeded PRNG — so a recording
pipeline can produce frame-exact video with a sample-accurate, separately
synthesized soundtrack.

### waves_live.html — the sea listens (interactive, for shared spaces)

The reactive variant: microphone or a dropped audio file feeds an analyser,
and **each wave is born at the horizon wearing the colour of the music at
that moment** — dominant pitch class (folded chromagram, ~65–2100 Hz) sets
the hue, spectral-centroid register sets the lightness, on the full 12-class
helix. A wave takes about half a minute to reach the shore, so the screen
holds the last few phrases of the song. Loudness drives the swell, onsets
flash the foam, the waterline sheen follows the music instantly, and when
the room goes quiet the sea idles on a slow note walk instead of dying.
Audio stays in the analyser node — nothing is recorded or sent anywhere.

Same caveat as everywhere above: this uses the 12-class code, which is *not*
distinguishable under simulated CVD; it is art for a wall, not an accessible
encoding.

### waves_screensaver.html — the sea as a screensaver

Silent, controls-free, cursor hidden, runs forever on the generative note
walk; a credit line breathes in for eight seconds every five minutes. Works
with any web-page screensaver wrapper (WebViewScreenSaver on macOS,
web-page-screensaver on Windows, a kiosk browser on Linux) — instructions in
the file header. `window.__loop(10)` pins a 10-wave note cycle so that every
animation frequency completes an integer number of cycles at sim t = 20π,
which is how the distributable seamless ~55 s loop video is rendered
(`window.__frame(t)` as in the ambient variant).
