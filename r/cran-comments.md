# cran-comments for palettecore 0.2.0

## Test environments

- local: macOS (Darwin 25.5.0), R 4.4.2

## R CMD check --as-cran results

0 errors, 0 warnings, 2 notes:

- "New submission" — first submission of this package.
- "unable to verify current time" — local network restriction during the
  check, not a package property.

## Notes for reviewers

- The package mirrors a Python reference implementation maintained in the
  same repository (https://github.com/heidihelena/palettecore) and is
  validated against shared cross-language parity fixtures: conversions and
  colour distances agree within 1e-6, generated palette HEX codes exactly.
- All colour science (OKLab/OKLCH, CIELAB under D65, CIEDE2000, Machado
  et al. 2009 CVD matrices) is implemented in base R with no compiled code
  and no dependencies beyond stats/utils (ggplot2 and jsonlite in Suggests).
- Generation is deterministic; no random state is used anywhere.
