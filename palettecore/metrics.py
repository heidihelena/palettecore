"""Perceptual and accessibility metrics: CIEDE2000, WCAG contrast, greyscale."""

from __future__ import annotations

import numpy as np

from .convert import srgb_to_cielab, srgb_to_linear


def ciede2000(rgb1: np.ndarray, rgb2: np.ndarray) -> float:
    """CIEDE2000 colour difference between two sRGB colours (Sharma et al. 2005)."""
    L1, a1, b1 = srgb_to_cielab(rgb1)
    L2, a2, b2 = srgb_to_cielab(rgb2)

    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    C_bar = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(C_bar**7 / (C_bar**7 + 25.0**7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)

    def _hp(a, b):
        if a == 0 and b == 0:
            return 0.0
        return np.degrees(np.arctan2(b, a)) % 360.0

    h1p, h2p = _hp(a1p, b1), _hp(a2p, b2)

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        d = h2p - h1p
        if d > 180:
            d -= 360
        elif d < -180:
            d += 360
        dhp = d
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2)

    Lp_bar = (L1 + L2) / 2
    Cp_bar = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hp_bar = h1p + h2p
    else:
        d = abs(h1p - h2p)
        s = h1p + h2p
        if d <= 180:
            hp_bar = s / 2
        elif s < 360:
            hp_bar = (s + 360) / 2
        else:
            hp_bar = (s - 360) / 2

    T = (
        1
        - 0.17 * np.cos(np.radians(hp_bar - 30))
        + 0.24 * np.cos(np.radians(2 * hp_bar))
        + 0.32 * np.cos(np.radians(3 * hp_bar + 6))
        - 0.20 * np.cos(np.radians(4 * hp_bar - 63))
    )
    d_theta = 30 * np.exp(-(((hp_bar - 275) / 25) ** 2))
    R_C = 2 * np.sqrt(Cp_bar**7 / (Cp_bar**7 + 25.0**7))
    S_L = 1 + 0.015 * (Lp_bar - 50) ** 2 / np.sqrt(20 + (Lp_bar - 50) ** 2)
    S_C = 1 + 0.045 * Cp_bar
    S_H = 1 + 0.015 * Cp_bar * T
    R_T = -np.sin(np.radians(2 * d_theta)) * R_C

    return float(
        np.sqrt(
            (dLp / S_L) ** 2
            + (dCp / S_C) ** 2
            + (dHp / S_H) ** 2
            + R_T * (dCp / S_C) * (dHp / S_H)
        )
    )


def relative_luminance(rgb: np.ndarray) -> float:
    lin = srgb_to_linear(rgb)
    return float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])


def contrast_ratio(rgb1: np.ndarray, rgb2: np.ndarray) -> float:
    """WCAG 2.x contrast ratio, 1:1 to 21:1."""
    y1, y2 = relative_luminance(rgb1), relative_luminance(rgb2)
    hi, lo = max(y1, y2), min(y1, y2)
    return (hi + 0.05) / (lo + 0.05)


def greyscale_values(rgbs: np.ndarray) -> np.ndarray:
    """Relative luminance of each colour — what the palette becomes in print."""
    return np.array([relative_luminance(c) for c in np.atleast_2d(rgbs)])


def is_monotonic(values: np.ndarray, tol: float = 1e-4) -> bool:
    d = np.diff(np.asarray(values, dtype=float))
    return bool(np.all(d <= tol) or np.all(d >= -tol))
