# cran-comments for palettecore 0.4.1

## Resubmission

This is a resubmission addressing the CRAN review comments of 2026-08-03
(Konstanze Lauseker) on 0.4.0:

- Acronyms in the Description are now explained: OKLCH (the cylindrical
  lightness-chroma-hue representation of the Oklab perceptual colour
  space), CIEDE2000 (colour-difference formula of the International
  Commission on Illumination), sRGB (standard Red Green Blue) and WCAG
  (Web Content Accessibility Guidelines). Software names are written in
  single quotes ('Python').
- Added \value tags to scale_colour_accessible.Rd and
  scale_fill_accessible.Rd, describing the returned ggplot2 discrete
  scale object (class ScaleDiscrete, a ggproto object), what it does when
  the plot is built, and the audit warnings it emits.

## Test environments

- local: macOS (Darwin 25.5.0), R 4.4.2
- GitHub Actions: ubuntu-latest (R release), see .github/workflows/ci.yml

## R CMD check --as-cran results

0 errors, 0 warnings, 2 notes:

- "New submission" — first submission of this package.
- "unable to verify current time" — local network restriction during the
  check, not a package property.

## Notes for reviewers

- The package mirrors a 'Python' reference implementation maintained in the
  same repository (https://github.com/heidihelena/palettecore) and is
  validated against shared cross-language parity fixtures: conversions and
  colour distances agree within 1e-6, generated palette HEX codes exactly.
- All colour science (Oklab/OKLCH, CIELAB under D65, CIEDE2000, Machado
  et al. 2009 CVD matrices) is implemented in base R with no compiled code
  and no dependencies beyond stats/utils (ggplot2 and jsonlite in Suggests).
- Generation is deterministic; no random state is used anywhere.
