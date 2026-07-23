"""palettecore: derive, optimise and audit a scientific palette from one seed colour.

The output is never just HEX codes — every palette ships with diagnostics
(CIEDE2000 spacing under normal vision and simulated CVD, greyscale
behaviour, gamut status, WCAG contrast) and explicit warnings.
"""

from .cvd import CONDITIONS, out_of_gamut_excursion, simulate_cvd
from .generate import DEFAULT_THRESHOLDS, PaletteResult, generate_palette
from .metrics import ciede2000, contrast_ratio

__version__ = "0.2.2"
__all__ = [
    "generate_palette",
    "PaletteResult",
    "simulate_cvd",
    "out_of_gamut_excursion",
    "ciede2000",
    "contrast_ratio",
    "CONDITIONS",
    "DEFAULT_THRESHOLDS",
]
