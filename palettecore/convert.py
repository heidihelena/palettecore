"""Colour space conversions: hex, sRGB, linear RGB, XYZ, CIELAB, OKLab, OKLCH.

All functions accept and return numpy arrays with the colour channels on the
last axis. sRGB values are in [0, 1].

White point: sRGB is interpreted under its native D65 illuminant throughout.
The sRGB->XYZ matrix below is the D65 matrix and the CIELAB reference white
is D65 (0.95047, 1.0, 1.08883). No chromatic adaptation to D50 (or any other
white) happens anywhere in this package, so CIELAB and CIEDE2000 values are
D65-relative. OKLab follows Ottosson's reference implementation, which is
likewise defined for D65 sRGB.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------- hex / sRGB


def hex_to_srgb(hex_str: str) -> np.ndarray:
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"Not a HEX colour: {hex_str!r}")
    try:
        return np.array([int(s[i : i + 2], 16) / 255.0 for i in (0, 2, 4)])
    except ValueError:
        raise ValueError(f"Not a HEX colour: {hex_str!r}") from None


def srgb_to_hex(rgb: np.ndarray) -> str:
    r, g, b = (int(round(float(np.clip(c, 0, 1)) * 255)) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


# ------------------------------------------------------------ sRGB transfer


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=float)
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(lin: np.ndarray) -> np.ndarray:
    lin = np.asarray(lin, dtype=float)
    lin = np.clip(lin, 0.0, None)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


# ------------------------------------------------------------------- OKLab

_M1 = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ]
)
_M2 = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ]
)


def linear_to_oklab(lin: np.ndarray) -> np.ndarray:
    lms = np.asarray(lin, dtype=float) @ _M1.T
    lms = np.cbrt(lms)
    return lms @ _M2.T


def oklab_to_linear(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, dtype=float)
    lms = lab @ np.linalg.inv(_M2).T
    lms = lms**3
    return lms @ np.linalg.inv(_M1).T


def srgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    return linear_to_oklab(srgb_to_linear(rgb))


def oklab_to_srgb(lab: np.ndarray) -> np.ndarray:
    return linear_to_srgb(oklab_to_linear(lab))


# ------------------------------------------------------------------- OKLCH


def oklab_to_oklch(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, dtype=float)
    L = lab[..., 0]
    C = np.hypot(lab[..., 1], lab[..., 2])
    H = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360.0
    return np.stack([L, C, H], axis=-1)


def oklch_to_oklab(lch: np.ndarray) -> np.ndarray:
    lch = np.asarray(lch, dtype=float)
    h = np.radians(lch[..., 2])
    return np.stack(
        [lch[..., 0], lch[..., 1] * np.cos(h), lch[..., 1] * np.sin(h)], axis=-1
    )


def hex_to_oklch(hex_str: str) -> np.ndarray:
    return oklab_to_oklch(srgb_to_oklab(hex_to_srgb(hex_str)))


def oklch_to_hex(lch: np.ndarray) -> str:
    return srgb_to_hex(oklab_to_srgb(oklch_to_oklab(lch)))


# ------------------------------------------------------------- XYZ / CIELAB

_M_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_WHITE_D65 = np.array([0.95047, 1.00000, 1.08883])


def linear_to_xyz(lin: np.ndarray) -> np.ndarray:
    return np.asarray(lin, dtype=float) @ _M_XYZ.T


def xyz_to_cielab(xyz: np.ndarray) -> np.ndarray:
    t = np.asarray(xyz, dtype=float) / _WHITE_D65
    delta = 6 / 29
    f = np.where(t > delta**3, np.cbrt(t), t / (3 * delta**2) + 4 / 29)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def srgb_to_cielab(rgb: np.ndarray) -> np.ndarray:
    return xyz_to_cielab(linear_to_xyz(srgb_to_linear(rgb)))


# -------------------------------------------------------------- gamut tools


def in_srgb_gamut(lch: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    lin = oklab_to_linear(oklch_to_oklab(lch))
    return np.all((lin >= -eps) & (lin <= 1 + eps), axis=-1)


def max_chroma(L: float, H: float, c_hi: float = 0.4, tol: float = 1e-4) -> float:
    """Largest OKLCH chroma at (L, H) that stays inside the sRGB gamut."""
    if not in_srgb_gamut(np.array([L, 0.0, H])):
        return 0.0
    lo, hi = 0.0, c_hi
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if in_srgb_gamut(np.array([L, mid, H])):
            lo = mid
        else:
            hi = mid
    return lo


def clamp_to_gamut(lch: np.ndarray) -> np.ndarray:
    """Reduce chroma (keeping L and H) until the colour is displayable."""
    lch = np.array(lch, dtype=float)
    c_max = max_chroma(float(lch[0]), float(lch[2]))
    lch[1] = min(lch[1], c_max)
    return lch
