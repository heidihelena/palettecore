# palettecore

[![PyPI](https://img.shields.io/pypi/v/palettecore)](https://pypi.org/project/palettecore/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21515949.svg)](https://doi.org/10.5281/zenodo.21515949)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Derive, optimise and **audit** a scientific colour palette from one seed colour.

Existing tools let researchers pick established colour maps. This one starts
from the researcher's own anchor colour and returns a palette **plus its
diagnostics** — because "harmonised" and "accessible" are separate properties,
and a generator that returns bare HEX codes is hiding the second one.

Grounded in Crameri, Shephard & Heron (2020), *The misuse of colour in science
communication*, Nature Communications 11:5444.

Free and open source, Apache-2.0. Python core now; R package with
`scale_colour_accessible()` / `scale_fill_accessible()` in `r/`, checked
against the same fixtures.

## What it checks (not "verifies")

Every palette ships with:

- adjacent / pairwise **CIEDE2000** distances under normal vision
- the same distances under simulated **protanopia, deuteranopia, tritanopia**
- **lightness monotonicity** and relative luminance (a greyscale proxy —
  real print output depends on the printer's colour management)
- **sRGB gamut** status (chroma is clamped, never channel-clipped)
- **WCAG contrast** against the declared background, judged by declared use
- **warnings** whenever a threshold is not met — the honest output for seeds
  that cannot satisfy every constraint at once

Every diagnostic is computed on the 8-bit quantised colours actually returned
as HEX (since 0.2.2), so the audit describes exactly the palette you receive.

## Install

```bash
pip install palettecore
```

```r
install.packages("palettecore", repos = "https://heidihelena.r-universe.dev")
# CRAN submission under review
```

## Usage

Python:

```python
from palettecore import generate_palette

result = generate_palette(
    seed="#8B6FC9",
    n=8,
    kind="sequential",   # or "diverging", "categorical"
    background="#FFFFFF",
    use="data_fill",     # or "text", "line", "UI"
    anchor="path",       # or "exact" — see Stated conventions
)
result.hexes         # 8 HEX codes
result.diagnostics   # the audit
result.warnings      # what did NOT pass
```

Command line (also the agent-friendly entry point — `--format json` returns
the full machine-readable audit):

```bash
python3 -m palettecore "#8B6FC9" -n 8 --kind sequential --format json
```

## Choosing a seed (and n)

Some seeds start inside a known failure zone; the map is in
[docs/seed-guidance.md](docs/seed-guidance.md) (reproducible with
`tools/seed_sweep.py`). The short version, under package-default thresholds:

- One seed that serves both kinds: **L 0.55–0.75, chroma ≥ 0.12, hue 30°–270°**.
- Sequential ramps from seed hues ~340°–15° fail deuteranopia at n = 8;
  285°–300° is tritanopia-tight (the pale end warns first as n grows).
- Categorical's failure zone is **murky chroma (~0.05–0.09)** — commit to
  colour (≥ 0.12) or to near-grey, not the band between.
- **n dominates:** a one-hue sequential ramp holds 5–7 steps comfortably,
  8 is near the ceiling for every hue, 9+ fails everywhere tested.

Region guidance never replaces the per-palette audit; the diagnostics that
ship with your palette are the numbers that bind.

**Vividness.** A muted seed gives a muted family (the default is
seed-faithful). If a palette reads too dusty, raise `vividness` from `0.0`
toward `1.0` — it lifts chroma toward the gamut edge without touching
lightness, so sequential monotonicity, equal-step spacing and the exact seed
anchor are all preserved, and the default reproduces earlier versions
exactly. More chroma also tends to *improve* separation, so vivid and
accessible are usually allies, not opposites.

```python
generate_palette("#B57EDC", n=8, kind="categorical", vividness=0.6)
```

## How it works

All work happens in **OKLCH** (path construction, gamut clamping) with
**CIEDE2000** as the distance metric. Nothing is interpolated in RGB or HSL.

- **Sequential** — a dense OKLCH path at the seed hue (monotonic lightness,
  chroma envelope scaled by seed chroma, gamut-clamped per stop), then n stops
  chosen by arc-length reparametrisation: equal spacing in cumulative
  CIEDE2000, so near-equal perceptual steps hold by construction rather than
  by free optimisation.
- **Categorical** — seed anchored exactly, then greedy farthest-point
  placement on a constrained hue circle (lightness band, moderated chroma),
  followed by swap-improvement passes on the maximin objective: maximise the
  minimum pairwise distance across normal vision *and* all three CVD
  simulations.
- **Diverging** — two sequential halves meeting at a near-neutral light
  centre. The second pole (seed hue + 180°) is a design assumption and is
  flagged as such in the warnings.

## Stated conventions

These are the decisions a reader needs before trusting any number the audit
reports.

**White point.** sRGB is interpreted under its native D65 illuminant
throughout; the CIELAB reference white is D65 and no chromatic adaptation to
D50 (or anything else) occurs anywhere. CIELAB/CIEDE2000 values are
D65-relative.

**CVD model.** Machado, Oliveira & Fernandes (2009) matrices at severity 1.0
on the paper's [0, 1] scale (some libraries write the same endpoint as 100).
Severity 1.0 simulates *complete dichromacy*; the milder anomalous
trichromacies are not modelled, so a palette passing here has been checked
against the extreme case only. The matrices are used as published — no
fixture-level parity with other implementations (colorspacious, colorblindr,
…) has been established, and their pipelines may differ.

**CVD gamut policy.** The Machado transform can leave displayable sRGB.
Simulated colours are clamped channel-wise in linear RGB, because the clamped
colour is what a display actually shows — audit distances are measured on
displayed colours. The pre-clamp excursion magnitude is reported in the
diagnostics (`cvd_gamut.max_linear_excursion_before_clamp`) so you can see
when clamping may have distorted a measured separation.

**Seed anchoring.** Categorical palettes always contain the seed exactly.
For sequential/diverging the seed defines the path (hue + chroma envelope)
but the exact HEX is not guaranteed to appear; `anchor="exact"` snaps the
nearest stop to the seed at the cost of slightly uneven spacing, and the
audit reports `seed_nearest_stop_deltaE` under either policy.

**Thresholds.** The ΔE floors (normal ≥ 8, each CVD condition ≥ 6) are
package-default design rules, **not** established universal accessibility
cut-offs. They are configurable (`thresholds=`), recorded in every result
(`thresholds_used`), and labelled as defaults there too.

**Determinism.** No random state anywhere — candidate grids, greedy selection
and swap passes are deterministic, so identical inputs always give identical
palettes. No seed to store.

## Dependencies

numpy only. All colour science — OKLab/OKLCH, CIELAB, CIEDE2000, the Machado
matrices — is implemented in-package so the numbers are inspectable and
portable.

## Tests and cross-language parity

```bash
python3 -m pytest tests/ -q
```

71 tests, including a pathological-seed battery (pure primaries, near-black,
near-white, neutrals) and no-false-pass checks (impossible constraints must
warn, never silently pass).

`fixtures/parity.json` (regenerate with `tools/make_fixtures.py`) is the
cross-language contract: conversions and distances must match within 1e-6,
palette HEX codes exactly. The R implementation in `r/` is validated against
it — one reference algorithm, two frontends.

## Roadmap

- [x] PyPI packaging (`pip install palettecore`)
- [ ] CRAN release (submitted, under review)
- [ ] `use="text"` mode that *constrains* generation, not just warns
- [ ] Configurable severity (<1.0) for the CVD simulations
- [ ] Fixture-level comparison against colorspacious/colorblindr
- [ ] Vectorised CIEDE2000 for faster categorical generation (currently
  ~2s for n=8, ~24s for n=24)
- [ ] A methods/validation document
