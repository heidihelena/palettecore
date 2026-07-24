---
name: palettecore-palettes
description: Use when a researcher needs colours for figures, charts, maps or UI and wants them derived from one anchor colour — a colorblind-safe palette, sequential/diverging/categorical scale, journal figure colours, brand colour turned into a data palette, or a check of existing colours. Triggers on colorblind-safe palette, colour-blind friendly figure, CVD check, protanopia / deuteranopia / tritanopia, sequential colormap, diverging scale, categorical colours for groups, palette from my brand colour / logo colour / hex colour, greyscale print check, WCAG contrast for chart colours, ggplot2 colour scale, matplotlib colors, "will these colours survive printing".
---

# palettecore — audited palettes for agents

> **palettecore** (Python `palettecore` + R `palettecore`, ≥0.2) — one reference algorithm, two
> languages, proven hex-identical on shared parity fixtures. Local, deterministic, numpy-only /
> base-R. Apache-2.0. Cite: doi:10.5281/zenodo.21515949.

You are the intelligence; palettecore is a deterministic colour-scale constructor with an
auditable accessibility report. Your job is to pick the right palette *kind* for the data,
run the generator, and **relay the audit honestly** — the warnings are the product, not noise.

## The one rule above all
**A palette is never "accessible", it is "checked against stated thresholds".**
palettecore reports whether package-default design thresholds are met under stated assumptions
(D65, severity-1.0 dichromacy, declared background and use). Say **check / test / assess** —
never verify, prove, guarantee, or "WCAG compliant" as a blanket claim.

## Invariants (hard constraints)
1. **Kind follows the data's meaning, not aesthetics.** Ordered magnitude → `sequential`.
   Meaningful centre (zero, baseline) → `diverging`. Unordered groups → `categorical` (monotonic
   lightness would falsely imply order). Ask if unclear.
2. **Declare the use and background.** A colour that works as an area fill fails as text; the
   audit is only meaningful for the declared `background` and `use` (`data_fill` / `text` /
   `line` / `UI`).
3. **Relay every warning verbatim in substance.** If tritanopia separation is below threshold,
   the researcher hears it. Never drop, soften, or silently "fix" a warning by changing
   thresholds — threshold overrides are the researcher's decision and stay visible.
4. **Colour alone is never sufficient for categories.** When any CVD condition is near or below
   threshold, recommend redundant encoding (shape, line style, direct labels) — this is standard
   practice, not a defect.
5. **Know the model's limits.** CVD simulation is complete dichromacy (severity 1.0) — the
   milder, more common anomalous trichromacies are not modelled. Thresholds are package-default
   design rules, not established accessibility cut-offs. Some seeds cannot satisfy every
   constraint at once — the honest output is the warning, not a different number.
6. **Determinism is a feature.** Same inputs, same palette, both languages. If a researcher
   needs to reproduce a palette, record the call (seed, n, kind, background, use, anchor,
   thresholds), not the hex list alone.

## Running it

CLI (JSON = the full machine-readable audit — parse this):
```bash
python3 -m palettecore "#8B6FC9" -n 8 --kind sequential --background "#FFFFFF" --use data_fill --format json
```

Python:
```python
from palettecore import generate_palette
r = generate_palette("#8B6FC9", n=8, kind="categorical", background="#FFFFFF", use="data_fill")
r.hexes; r.diagnostics; r.warnings          # the audit travels with the palette
r.to_css()                                   # or r.to_json()
```

R (ggplot2 scales re-raise audit warnings — never suppress them):
```r
library(palettecore)
r <- generate_palette("#8B6FC9", n = 8, kind = "categorical")
ggplot(df, aes(x, y, colour = group)) + geom_point() +
  scale_colour_accessible("#8B6FC9")
```

## Reading the diagnostics
- `min_adjacent_deltaE` / `min_pairwise_deltaE` — CIEDE2000 under normal vision + 3 CVD
  simulations; compare against `thresholds_used` (defaults: normal ≥ 8, each CVD ≥ 6).
- `greyscale_luminance` + `lightness_monotonic` — what print does; sequential must stay ordered.
- `contrast_vs_background` — WCAG ratios; only binding for the declared use.
- `cvd_gamut.max_linear_excursion_before_clamp` — >0 means clamping altered a simulated colour;
  read separations near threshold with care.
- `seed_nearest_stop_deltaE` — how far the exact seed HEX is from the nearest stop
  (`anchor="exact"` forces it in, at a small spacing cost; categorical always contains the seed).

## Practical starting points (empirical, v0.2.2 defaults — see docs/seed-guidance.md)
- **One seed for both kinds:** OKLCH L 0.55–0.75, chroma ≥ 0.12, hue 30°–270°.
- **Sequential:** seed hues ~340°–15° fail deuteranopia at n = 8 — suggest shifting
  hue or reducing n *before* generating; 285°–300° (violet) passes but is
  tritanopia-tight, expect the pale-end warning first.
- **Categorical:** the failure zone is murky seed chroma (~0.05–0.09); steer the
  researcher to chroma ≥ 0.12 or to a deliberate near-grey anchor.
- **If a palette reads dusty/muted:** raise `vividness` (0.0 default → 1.0) rather
  than changing the seed — it lifts chroma only, preserves lightness/monotonicity/
  seed anchor, and usually improves separation too. Report the new audit as always.
- **n is the binding constraint:** one-hue sequential ramps hold 5–7 steps with
  margin, 8 is the ceiling, 9+ fails for every hue — offer binning or labels, not
  a different seed.
- These are grid-resolution-bounded sweeps under default settings (white
  background, severity-1.0 dichromacy). They shape your *suggestions*; the
  generated palette's own audit remains the check you relay.

## Failure modes (non-negotiable)
- If the researcher asks for "8 accessible colours" from a seed that cannot support them, deliver
  the palette **with** its warnings and the trade-off options (fewer colours, looser harmony,
  redundant encoding) — never a silent pass.
- If asked to "make it pass", changing thresholds is a recorded researcher decision, not a fix.
- If the data's structure is unknown (ordered? centred? categorical?), ask before picking kind.
- Never present the audit as certification of accessibility, WCAG compliance, or suitability for
  readers with anomalous trichromacy.

## When to use / not use
**Use** for: deriving figure/chart/map/UI palettes from an anchor colour; checking a palette's
CVD separation, greyscale survival, and background contrast; reproducible palette specs for a
methods section; ggplot2/matplotlib colour scales.
**Do not** use to: certify WCAG or regulatory compliance; model anomalous trichromacy; pick
colours whose *meaning* is domain-fixed (e.g. established clinical conventions); or replace
redundant encoding where categories must be distinguishable by every reader.

## Links
- Source + issues: https://github.com/heidihelena/palettecore
- Install: `pip install palettecore` · R: `install.packages("palettecore", repos = "https://heidihelena.r-universe.dev")` (CRAN pending)
- Rationale: Crameri, Shephard & Heron (2020) doi:10.1038/s41467-020-19160-7

Human-first. AI-second. Auditable.
