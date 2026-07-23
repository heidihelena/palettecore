"""Colour-vision deficiency simulation.

Machado, Oliveira & Fernandes (2009) matrices at severity 1.0, applied in
linear sRGB.

Conventions, stated explicitly:

- Severity is on the [0, 1] scale of the original paper (some libraries
  write the same endpoint as 100). Only severity 1.0 is implemented here.
- Severity 1.0 simulates *complete dichromacy* (protanopia, deuteranopia,
  tritanopia). It does not model the milder and more common anomalous
  trichromacies; a palette passing here has been checked against the
  extreme case only.
- The transformation can push colours outside displayable sRGB. Policy:
  simulated colours are clamped channel-wise to [0, 1] in linear RGB after
  the transform, because the clamped colour is what a display shows a
  viewer — audit distances are therefore measured on displayed colours.
  The magnitude of the pre-clamp excursion is exposed via
  out_of_gamut_excursion so the audit can report when clamping may distort
  measured separation.
- These are the matrices as published; no fixture-level parity with other
  implementations (colorspacious, colorblindr, ...) has been established,
  and their pipelines may differ in interpolation, severity convention, or
  gamut handling.
"""

from __future__ import annotations

import numpy as np

from .convert import linear_to_srgb, srgb_to_linear

MACHADO_10 = {
    "protanopia": np.array(
        [
            [0.152286, 1.052583, -0.204868],
            [0.114503, 0.786281, 0.099216],
            [-0.003882, -0.048116, 1.051998],
        ]
    ),
    "deuteranopia": np.array(
        [
            [0.367322, 0.860646, -0.227968],
            [0.280085, 0.672501, 0.047413],
            [-0.011820, 0.042940, 0.968881],
        ]
    ),
    "tritanopia": np.array(
        [
            [1.255528, -0.076749, -0.178779],
            [-0.078411, 0.930809, 0.147602],
            [0.004733, 0.691367, 0.303900],
        ]
    ),
}

CONDITIONS = tuple(MACHADO_10)


def _simulate_linear(rgb: np.ndarray, condition: str) -> np.ndarray:
    m = MACHADO_10[condition]
    return srgb_to_linear(np.asarray(rgb, dtype=float)) @ m.T


def simulate_cvd(rgb: np.ndarray, condition: str) -> np.ndarray:
    """Displayed appearance of an sRGB colour under complete dichromacy.

    Clamped to [0, 1] per the module gamut policy above.
    """
    lin = np.clip(_simulate_linear(rgb, condition), 0.0, 1.0)
    return np.clip(linear_to_srgb(lin), 0.0, 1.0)


def out_of_gamut_excursion(rgb: np.ndarray, condition: str) -> float:
    """Largest linear-RGB excursion outside [0, 1] before clamping.

    0.0 means the simulated colour was displayable as-is; larger values
    mean clamping altered the colour, and measured separations involving it
    should be read with that in mind.
    """
    lin = _simulate_linear(rgb, condition)
    return float(max(0.0, float(np.max(lin - 1.0)), float(np.max(-lin))))
