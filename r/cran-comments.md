# cran-comments for palettecore 0.2.2

(0.2.0 is the version currently in CRAN incoming review; 0.2.2 is the
prepared update / resubmission with audit-correctness fixes.)

## Test environments

- local: macOS (Darwin 25.5.0), R 4.4.2
- GitHub Actions: ubuntu-latest (R release), see .github/workflows/ci.yml

## R CMD check --as-cran results

0 errors, 0 warnings, 2 notes:

- "New submission" — first submission of this package.
- "unable to verify current time" — local network restriction during the
  check, not a package property.

## Changes in 0.2.2

- Every diagnostic is now computed on the 8-bit quantised colours actually
  returned as HEX, never on internal floating-point values (fixes rare
  false-pass/false-warning threshold results near the boundary).
- anchor = "exact" now also snaps diverging palettes to the seed.
- Input validation for `use`, threshold names and threshold values.
- Diverging palettes require n >= 3 and report an arm-structure diagnostic.

## Notes for reviewers

- The package mirrors a Python reference implementation maintained in the
  same repository (https://github.com/heidihelena/palettecore) and is
  validated against shared cross-language parity fixtures: conversions and
  colour distances agree within 1e-6, generated palette HEX codes exactly.
- All colour science (OKLab/OKLCH, CIELAB under D65, CIEDE2000, Machado
  et al. 2009 CVD matrices) is implemented in base R with no compiled code
  and no dependencies beyond stats/utils (ggplot2 and jsonlite in Suggests).
- Generation is deterministic; no random state is used anywhere.
