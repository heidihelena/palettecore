# Choosing a seed (and n): empirical guidance

Some seed colours give the generator room to satisfy every audit check;
others start inside a known failure zone. This document maps those zones so
you can pick a starting point deliberately. It is guidance, not a substitute
for the per-palette audit: every generated palette still carries its own
diagnostics, and those are the numbers that bind.

All results below were produced with `tools/seed_sweep.py` against
palettecore 0.2.2 (diagnostics computed on the quantised, returned HEX
colours) under the stated assumptions at the end.

## Sequential: the seed's hue decides, and there is one real valley

The sequential path holds the seed's hue constant and normalises lightness,
so the seed contributes hue and chroma only. A 15° hue scan (L = 0.65,
C = 0.75 × gamut max, n = 8) of the worst-condition margin over the audit
thresholds:

| Hue region | Margin at n = 8 | Limiting condition |
|---|---|---|
| ~340°–15° (red) | **−1.3 to −0.7 (fails)** | deuteranopia |
| 15°–30° (red-orange) | +0.2 to +1.7 (tight edge) | protanopia |
| 30°–195° (orange → teal) | +0.8 to +2.4 (comfortable) | mostly normal-vision |
| ~210° (blue-cyan) | +0.3 (tight) | protanopia |
| 225°–330° (blue → magenta) | +0.4 to +2.9 | tritanopia tight at 285°–300° |

The red valley is a property of the deuteranopia projection, which collapses
adjacent red steps; it is narrow but real. The violet 285°–300° dip passes at
n = 8 but with the smallest margins on the wheel (tritanopia), which is why a
violet seed's pale end warns first as n grows.

## Categorical: the failure zone is murky chroma, not low chroma

The categorical generator inherits the seed's chroma for the whole candidate
wheel, with a floor: candidates use `max(seed_C, 0.09) × 0.92`. The chroma
response (four hues × four chroma fractions, L = 0.65, n = 8) is therefore
not monotone:

| Seed chroma | Outcome |
|---|---|
| ≤ ~0.05 (near-grey) | passes — the floor gives candidates room and the seed reads as the grey category |
| **~0.05–0.09 (murky)** | **the failure zone** — the seed is too colourful to be distinct as grey, too dull to open the wheel (worst observed: −0.5, normal vision) |
| ≥ ~0.12 | comfortable, margins +1.4 to +3.3, improving with chroma |

Seed hue barely matters for categorical; the seed is one anchor on a wheel.

## n dominates everything

n-sensitivity at three seed hues (red 0°, green 120°, violet 300°;
L = 0.65, C = 0.75 × max):

| n | red 0° | green 120° | violet 300° |
|---|---|---|---|
| 6 | +1.1 | +5.0 | +3.4 |
| 8 | −1.3 | +1.2 | +0.4 |
| 10 | −2.5 | −0.9 | −1.2 |
| 12 | −3.3 | −2.2 | −2.3 |

Under the package-default thresholds, a one-hue sequential ramp supports
**5–7 steps comfortably; 8 is near the ceiling even for the best hues; 9 or
more fails for every hue tested.** Past that point the honest options are
fewer classes, binned-and-labelled classes, or an explicit recorded decision
to relax a threshold — not a different seed.

## Practical rules

1. **One seed for both kinds:** L 0.55–0.75, chroma ≥ 0.12, hue 30°–270°.
2. **Sequential:** avoid seed hues ~340°–15°; treat 285°–300° as
   tritanopia-tight (expect the pale-end warning first).
3. **Categorical:** avoid seed chroma 0.05–0.09; either commit to colour
   (≥ 0.12) or to near-grey.
4. **Keep n ≤ 7 for sequential ramps** when you want margin, and pair
   categories with shapes or labels whenever any margin is small.

## Stated assumptions and limits

- Sweeps: 15° hue resolution (sequential), 4 hues × 4 chroma fractions
  (categorical), n ∈ {6, 8, 10, 12}; L = 0.65 unless stated; white
  background; `use="data_fill"`; package-default thresholds; Machado
  severity-1.0 dichromacy. Margins are deterministic (no sampling noise),
  but region *boundaries* are only as fine as the grid.
- Different lightness, background, thresholds, or use move the numbers;
  re-run `tools/seed_sweep.py` for your own settings.
- This is design evidence under the stated assumptions. The per-palette
  audit, not this map, is the check that travels with your figure.
