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

![Example palettes: sequential, diverging, categorical, and a cubehelix-inspired
run, each audited](docs/example_palettes.png)

Four palettes from one seed each, every one carrying its audit
(`tools/make_gallery.py` regenerates this). The bottom row is a **helix**
through OKLCH — designed lightness climbs while hue rotates — a multi-hue
sequential scale whose returned colours are checked for greyscale and
simulated-CVD order. It came out of a small cross-modal art experiment
(see *Does music have a colour?* below).

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
    kind="sequential",   # or "diverging", "categorical", "helix"
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
- **Helix** — a cubehelix-inspired path through OKLCH: designed OKLab
  lightness steps evenly while hue rotates `rotations` full turns from the
  seed. It is a multi-hue sequential scale, but hue-dependent luminance can
  still reverse after gamut mapping or simulated CVD. The audit therefore
  reports normal greyscale order, `cvd_luminance_monotonic`, and adjacent
  separation instead of assuming safety from the construction. Because the
  hue sweeps regardless of where it starts, the seed mainly sets the start
  hue and baseline chroma.

```python
generate_palette("#B84A3C", n=8, kind="helix", rotations=1.4, vividness=0.4)
```

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

123 tests, including a pathological-seed battery (pure primaries, near-black,
near-white, neutrals) and no-false-pass checks (impossible constraints must
warn, never silently pass).

`fixtures/parity.json` (regenerate with `tools/make_fixtures.py`) is the
cross-language contract: conversions and distances must match within 1e-6,
palette HEX codes exactly. The R implementation in `r/` is validated against
it — one reference algorithm, two frontends.

## Does music have a colour?

An inclusive art experiment built on the same engine lives in
[`experiments/`](experiments/): map the 12 pitch classes to a **helix** through
colour space — angle = pitch class, height = lightness = pitch. Every note gets
a colour; a rising scale traces the same kind of cubehelix-inspired path shown
above.

It is framed as art, not a tool, on purpose. The pitch-class → hue mapping is a
*designed* convention (Newton and Scriabin chose different colours for C), so
the piece asks the question rather than answering it. What the audit *can* say
honestly is worked out in the experiment's README, minimum-not-mean: octave
pairs remain strongly separated in the simulations, while fine semitone
identity does not survive CVD and the protanopia simulation contains four
small local luminance reversals. The frontier sweep finds that ≤4 pitch classes
per octave clears this package's exploratory ΔE design floor in the tested
simulations; that floor is not a human-validated guarantee. The colours can
enrich the shared artwork, but they do not replace sound, labels, position, or
another redundant encoding.

The experiment now has an artwork: **waves to the shore**
(`experiments/waves_to_shore.html`, no dependencies — open it and press play).
Each incoming wave carries one note whose helix colour rolls in with the crest
and sounds as the wave breaks; the beached driftwood — a point-for-point
rendering of the 10 000-point tweet-art study popularised by @yuruyurau — has
no pitch, so it takes no colour. Its palette is injected from this engine by
`experiments/waves_to_shore.py` together with its audit, and in-piece toggles
let you watch the 12-semitone code collapse under the simulated dichromacies.

## Roadmap

- [x] PyPI packaging (`pip install palettecore`)
- [ ] CRAN release (submitted, under review)
- [ ] `use="text"` mode that *constrains* generation, not just warns
- [ ] Configurable severity (<1.0) for the CVD simulations
- [ ] Fixture-level comparison against colorspacious/colorblindr
- [ ] Vectorised CIEDE2000 for faster categorical generation (currently
  ~1.7s for n=8, ~17s for n=24 on one Apple-silicon test machine)
- [ ] A methods/validation document
