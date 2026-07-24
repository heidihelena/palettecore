"""Palette generation and audit.

The public entry point is generate_palette(). It never returns bare HEX
codes: the result always carries diagnostics (adjacent/pairwise CIEDE2000
under normal vision and three simulated colour-vision deficiencies,
lightness monotonicity, greyscale behaviour, gamut status, WCAG contrast
against the declared background) plus warnings. Passing every check is a
property of the audit, not a promise of the generator.

Determinism: generation uses no random state anywhere — candidate grids,
greedy selection and swap passes are all deterministic, so the same inputs
always produce the same palette.

Seed anchoring: the categorical palette always contains the seed exactly.
For sequential/diverging/helix the seed defines the path but the exact HEX
is not guaranteed to be a stop; anchor="exact" snaps the nearest stop to the
seed at the cost of slightly uneven spacing, and the audit reports the
seed-to-nearest-stop distance either way.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .convert import (
    hex_to_oklch,
    hex_to_srgb,
    max_chroma,
    oklab_to_srgb,
    oklch_to_oklab,
    srgb_to_hex,
)
from .cvd import CONDITIONS, out_of_gamut_excursion, simulate_cvd
from .metrics import ciede2000, contrast_ratio, greyscale_values, is_monotonic

# Package defaults. These are design rules chosen for this package, NOT
# established universal accessibility cut-offs — override via thresholds=.
DEFAULT_THRESHOLDS = {
    "normal": 8.0,
    "protanopia": 6.0,
    "deuteranopia": 6.0,
    "tritanopia": 6.0,
}


@dataclass
class PaletteResult:
    hexes: list[str]
    kind: str
    seed: str
    background: str
    use: str
    diagnostics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        import json

        return json.dumps(
            {
                "palette": self.hexes,
                "kind": self.kind,
                "seed": self.seed,
                "background": self.background,
                "use": self.use,
                "diagnostics": self.diagnostics,
                "warnings": self.warnings,
            },
            indent=2,
        )

    def to_css(self, prefix: str = "palette") -> str:
        lines = [":root {"]
        lines += [f"  --{prefix}-{i + 1}: {h.lower()};" for i, h in enumerate(self.hexes)]
        lines.append("}")
        return "\n".join(lines)


# --------------------------------------------------------------- sequential


def _sequential_path(seed_lch, n, background_rgb, samples=512, vividness=0.0):
    """Dense OKLCH path at the seed hue, then pick n stops equally spaced in
    cumulative CIEDE2000 — arc-length reparametrisation instead of a free
    optimiser, which makes the equal-step property hold by construction.

    vividness in [0, 1] lifts each stop's chroma from the seed-scaled level
    toward the per-stop gamut maximum (0 = seed-faithful, 1 = as vivid as
    the gamut allows). Lightness is untouched, so monotonicity and the
    equal-step arc-length reparametrisation are preserved at any vividness."""
    L_seed, C_seed, H_seed = (float(v) for v in seed_lch)

    bg_is_light = np.mean(background_rgb) > 0.5
    L_hi, L_lo = (0.955, 0.30) if bg_is_light else (0.90, 0.22)

    t = np.linspace(0.0, 1.0, samples)
    L = L_hi + (L_lo - L_hi) * t
    # Chroma envelope: rises from near-neutral at the light end, peaks past
    # the middle, eases off toward dark. Scaled by the seed's own chroma so
    # a muted seed yields a muted family.
    envelope = np.sin(np.pi * np.clip(t * 0.82 + 0.09, 0, 1)) ** 0.8
    C_target = C_seed * (0.25 + 0.95 * envelope)

    rgbs = np.empty((samples, 3))
    for i in range(samples):
        c_max = max_chroma(L[i], H_seed)
        c_base = min(C_target[i], c_max)
        c = c_base + vividness * (c_max - c_base)
        rgbs[i] = np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L[i], c, H_seed]))), 0, 1)

    # Cumulative perceptual arc length, then equal spacing along it.
    d = np.zeros(samples)
    for i in range(1, samples):
        d[i] = d[i - 1] + ciede2000(rgbs[i - 1], rgbs[i])
    # Nearest sample per target (not threshold-crossing): robust to last-ulp
    # libm differences, which matters for cross-language parity.
    targets = np.linspace(0, d[-1], n)
    idx = np.array([int(np.argmin(np.abs(d - t))) for t in targets])
    return rgbs[idx]


# ------------------------------------------------------------------- helix


def _helix_path(seed_lch, n, background_rgb, rotations=1.0, vividness=0.0):
    """A cubehelix-inspired path through OKLCH: OKLab lightness steps evenly
    while hue rotates `rotations` full turns from the seed hue. Chroma follows
    the per-stop gamut, so it eases off at the light and dark ends on its own.

    Designed OKLab lightness is monotonic by construction. The audit separately
    checks the returned HEX colours' relative luminance, simulated-CVD
    separation, and simulated-CVD luminance order; none is assumed from the
    construction alone."""
    L_seed, C_seed, H_seed = (float(v) for v in seed_lch)
    bg_is_light = np.mean(background_rgb) > 0.5
    L_hi, L_lo = (0.955, 0.30) if bg_is_light else (0.90, 0.22)

    out = np.empty((n, 3))
    for i in range(n):
        t = i / (n - 1)
        L = L_hi + (L_lo - L_hi) * t
        H = (H_seed + 360.0 * rotations * t) % 360.0
        c_max = max_chroma(L, H)
        c_base = min(max(C_seed, 0.08), c_max)
        c = c_base + vividness * (c_max - c_base)
        out[i] = np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, c, H]))), 0, 1)
    return out


# -------------------------------------------------------------- categorical


def _min_pairwise_all_conditions(rgbs):
    """Minimum pairwise CIEDE2000 across normal vision and all CVD simulations."""
    n = len(rgbs)
    sims = {c: np.array([simulate_cvd(x, c) for x in rgbs]) for c in CONDITIONS}
    worst = np.inf
    for i in range(n):
        for j in range(i + 1, n):
            worst = min(worst, ciede2000(rgbs[i], rgbs[j]))
            for c in CONDITIONS:
                worst = min(worst, ciede2000(sims[c][i], sims[c][j]))
    return worst


def _categorical(seed_lch, n, vividness=0.0):
    """Anchor the seed, then greedy farthest-point placement on a constrained
    hue circle, followed by swap-improvement passes on the maximin objective.

    vividness in [0, 1] lifts the candidate chroma from the seed-scaled level
    toward the per-hue gamut ceiling (0 = seed-faithful, muted seed gives a
    muted family; 1 = as vivid as the gamut allows). The seed swatch itself
    keeps its own chroma, since a categorical palette always contains the
    seed exactly."""
    L_seed, C_seed, H_seed = (float(v) for v in seed_lch)
    L_band = float(np.clip(L_seed, 0.55, 0.78))

    hues = np.arange(0.0, 360.0, 4.0)
    levels = [L_band - 0.06, L_band, L_band + 0.06]
    candidates = []
    for h in hues:
        for L in levels:
            ceiling = 0.92 * max_chroma(L, h)
            c_base = min(max(C_seed, 0.09), max_chroma(L, h)) * 0.92
            c = c_base + vividness * (ceiling - c_base)
            rgb = np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, c, h]))), 0, 1)
            candidates.append(rgb)
    candidates = np.array(candidates)

    seed_rgb = np.clip(
        oklab_to_srgb(oklch_to_oklab(np.array([L_seed, C_seed, H_seed]))), 0, 1
    )

    # CVD simulations are deterministic per colour — precompute once instead
    # of re-simulating inside every score evaluation (the dominant cost).
    def _pack(rgb):
        return (rgb, {c: simulate_cvd(rgb, c) for c in CONDITIONS})

    cand_packed = [_pack(c) for c in candidates]
    chosen = [_pack(seed_rgb)]

    def score(packed, current):
        rgb, sims = packed
        s = np.inf
        for x_rgb, x_sims in current:
            s = min(s, ciede2000(rgb, x_rgb))
            for cond in CONDITIONS:
                s = min(s, ciede2000(sims[cond], x_sims[cond]))
        return s

    while len(chosen) < n:
        scores = [score(p, chosen) for p in cand_packed]
        chosen.append(cand_packed[int(np.argmax(scores))])

    # Swap-improvement: try to lift the weakest link.
    for _ in range(2):
        for i in range(1, n):  # never move the seed anchor
            rest = chosen[:i] + chosen[i + 1 :]
            best_p, best_s = chosen[i], score(chosen[i], rest)
            for p in cand_packed[::3]:
                s = score(p, rest)
                if s > best_s:
                    best_p, best_s = p, s
            chosen[i] = best_p

    return np.array([rgb for rgb, _ in chosen])


# ---------------------------------------------------------------- diverging


def _diverging(seed_lch, n, background_rgb, vividness=0.0):
    """Seed pole → near-neutral centre → derived opposite pole. The second
    hue (seed hue + 180°) is a design assumption, flagged in warnings."""
    L, C, H = (float(v) for v in seed_lch)
    opp = np.array([L, C, (H + 180.0) % 360.0])
    half = (n + 1) // 2
    a = _sequential_path(np.array([L, C, H]), half, background_rgb, vividness=vividness)
    b = _sequential_path(opp, half, background_rgb, vividness=vividness)
    if n % 2 == 1:
        return np.vstack([b[::-1][:-1], a])  # shared light centre stop
    return np.vstack([b[::-1][: n // 2], a[half - n // 2 :]])


# ------------------------------------------------------------------- audit


def _audit(rgbs, kind, background_rgb, use, thresholds):
    n = len(rgbs)
    diag: dict = {}
    warnings: list[str] = []

    sims = {c: np.array([simulate_cvd(x, c) for x in rgbs]) for c in CONDITIONS}

    if kind in ("sequential", "diverging", "helix"):
        adjacent = {"normal": [ciede2000(rgbs[i], rgbs[i + 1]) for i in range(n - 1)]}
        for c in CONDITIONS:
            adjacent[c] = [ciede2000(sims[c][i], sims[c][i + 1]) for i in range(n - 1)]
        diag["adjacent_deltaE"] = {k: [round(v, 1) for v in vs] for k, vs in adjacent.items()}
        diag["min_adjacent_deltaE"] = {k: round(min(vs), 1) for k, vs in adjacent.items()}
        for cond, floor in thresholds.items():
            if min(adjacent[cond]) < floor:
                warnings.append(
                    f"{cond}: minimum adjacent dE {min(adjacent[cond]):.1f} is below the "
                    f"{floor:.0f} threshold — adjacent classes may merge for some readers."
                )
    else:
        pairwise = {"normal": np.inf}
        for c in CONDITIONS:
            pairwise[c] = np.inf
        for i in range(n):
            for j in range(i + 1, n):
                pairwise["normal"] = min(pairwise["normal"], ciede2000(rgbs[i], rgbs[j]))
                for c in CONDITIONS:
                    pairwise[c] = min(pairwise[c], ciede2000(sims[c][i], sims[c][j]))
        diag["min_pairwise_deltaE"] = {k: round(v, 1) for k, v in pairwise.items()}
        for cond, floor in thresholds.items():
            if pairwise[cond] < floor:
                warnings.append(
                    f"{cond}: minimum pairwise dE {pairwise[cond]:.1f} is below the "
                    f"{floor:.0f} threshold — pair categories with shape or direct labels."
                )

    grey = greyscale_values(rgbs)
    diag["greyscale_luminance"] = [round(v, 3) for v in grey]
    if kind in ("sequential", "helix"):
        diag["lightness_monotonic"] = is_monotonic(grey)
        if not is_monotonic(grey):
            warnings.append(
                "Greyscale luminance is not monotonic — luminance alone does not preserve order."
            )
        if kind == "helix":
            cvd_luminance_monotonic = {
                c: is_monotonic(greyscale_values(sims[c])) for c in CONDITIONS
            }
            diag["cvd_luminance_monotonic"] = cvd_luminance_monotonic
            failed = [c for c, passed in cvd_luminance_monotonic.items() if not passed]
            if failed:
                warnings.append(
                    "Simulated-CVD luminance is not monotonic for "
                    f"{', '.join(failed)} — hue-dependent reversals may disrupt order; "
                    "do not rely on colour alone."
                )
    elif kind == "categorical":
        spread = float(grey.max() - grey.min())
        diag["greyscale_spread"] = round(spread, 3)
        if spread > 0.45:
            warnings.append(
                "Large lightness spread — one category may look more important than others."
            )
    elif kind == "diverging":
        i_max = int(np.argmax(grey))
        left_ok = is_monotonic(grey[: i_max + 1])
        right_ok = is_monotonic(grey[i_max:])
        centre_ok = 0 < i_max < n - 1
        diag["diverging_structure"] = {
            "centre_index": i_max,
            "arms_monotonic": bool(left_ok and right_ok),
            "centre_interior": centre_ok,
        }
        if not (left_ok and right_ok and centre_ok):
            warnings.append(
                "Diverging structure is broken — lightness should rise to an interior "
                "light centre and fall again; an arm reverses or the centre sits at an end."
            )

    contrasts = [round(contrast_ratio(c, background_rgb), 2) for c in rgbs]
    diag["contrast_vs_background"] = contrasts
    if use == "text":
        bad = [i + 1 for i, r in enumerate(contrasts) if r < 4.5]
        if bad:
            warnings.append(
                f"Swatches {bad} fall below WCAG AA 4.5:1 for normal text on this background."
            )
    elif use in ("line", "UI"):
        bad = [i + 1 for i, r in enumerate(contrasts) if r < 3.0]
        if bad:
            warnings.append(
                f"Swatches {bad} fall below 3:1 against the background — thin marks may vanish."
            )

    diag["srgb_gamut"] = "all in gamut (chroma clamped where needed)"

    excursions = {
        c: round(max(out_of_gamut_excursion(x, c) for x in rgbs), 4) for c in CONDITIONS
    }
    diag["cvd_gamut"] = {
        "policy": "distances measured after clamping simulated colours to "
        "displayable sRGB — the colour a viewer actually sees",
        "max_linear_excursion_before_clamp": excursions,
    }
    diag["thresholds_used"] = {
        **{k: float(v) for k, v in thresholds.items()},
        "note": "package-default design rules (or user overrides), not "
        "established accessibility cut-offs",
    }
    return diag, warnings


# ------------------------------------------------------------- entry point


def generate_palette(
    seed: str,
    n: int = 8,
    kind: str = "sequential",
    background: str = "#FFFFFF",
    use: str = "data_fill",
    thresholds: dict | None = None,
    anchor: str = "path",
    vividness: float = 0.0,
    rotations: float = 1.0,
) -> PaletteResult:
    """Generate an audited palette from one seed colour.

    kind:      'sequential' | 'diverging' | 'categorical' | 'helix'
    use:       'data_fill' | 'text' | 'line' | 'UI'
    rotations: helix only — how many full hue turns the cubehelix makes over
               its lightness range (may be fractional or negative for the
               other direction). Ignored, and rejected if non-default, for
               other kinds.
    anchor:    'path' (seed defines the path; exact HEX may not appear) or
               'exact' (nearest sequential/diverging/helix stop snapped to the
               seed, at the cost of slightly uneven spacing). Categorical
               palettes always contain the seed exactly, regardless of this
               setting.
    vividness: 0.0 (default, seed-faithful — a muted seed gives a muted
               family) to 1.0 (chroma pushed toward the gamut edge). Applies
               to every kind: it lifts chroma only, never lightness, so
               sequential monotonicity, equal-step spacing, and the exact
               seed anchor are all preserved. The default reproduces earlier
               versions byte-for-byte.

    Every diagnostic is computed on the 8-bit quantised colours that are
    actually returned as HEX, never on internal floating-point values, so
    the audit describes exactly the palette the caller receives.
    """
    if kind not in ("sequential", "diverging", "categorical", "helix"):
        raise ValueError(f"Unknown palette kind: {kind!r}")
    if anchor not in ("path", "exact"):
        raise ValueError(f"Unknown anchor policy: {anchor!r}")
    if not isinstance(rotations, (int, float)) or not np.isfinite(rotations):
        raise ValueError(f"rotations must be a finite number, got {rotations!r}")
    if kind != "helix" and rotations != 1.0:
        raise ValueError("rotations only applies to kind='helix'")
    if use not in ("data_fill", "text", "line", "UI"):
        raise ValueError(
            f"Unknown use: {use!r} (expected 'data_fill', 'text', 'line' or 'UI')"
        )
    if not isinstance(vividness, (int, float)) or not np.isfinite(vividness) or not 0.0 <= vividness <= 1.0:
        raise ValueError(f"vividness must be a number in [0, 1], got {vividness!r}")
    if not isinstance(n, int) or not 2 <= n <= 24:
        raise ValueError(f"n must be an integer between 2 and 24, got {n!r}")
    if kind == "diverging" and n < 3:
        raise ValueError("diverging palettes need n >= 3 (two poles and a centre)")
    for key, val in (thresholds or {}).items():
        if key not in DEFAULT_THRESHOLDS:
            raise ValueError(
                f"Unknown threshold name: {key!r} (expected one of {sorted(DEFAULT_THRESHOLDS)})"
            )
        if not isinstance(val, (int, float)) or not np.isfinite(val) or val < 0:
            raise ValueError(f"Threshold {key!r} must be a finite non-negative number, got {val!r}")

    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    seed_lch = hex_to_oklch(seed)
    background_rgb = hex_to_srgb(background)

    vividness = float(vividness)
    rotations = float(rotations)
    if kind == "sequential":
        rgbs = _sequential_path(seed_lch, n, background_rgb, vividness=vividness)
    elif kind == "diverging":
        rgbs = _diverging(seed_lch, n, background_rgb, vividness=vividness)
    elif kind == "helix":
        rgbs = _helix_path(seed_lch, n, background_rgb, rotations=rotations, vividness=vividness)
    else:
        rgbs = _categorical(seed_lch, n, vividness=vividness)

    seed_rgb = hex_to_srgb(seed)
    if kind in ("sequential", "diverging", "helix") and anchor == "exact":
        i_near = int(np.argmin([ciede2000(c, seed_rgb) for c in rgbs]))
        rgbs[i_near] = seed_rgb

    # Quantise to the 8-bit colours the caller actually receives BEFORE any
    # diagnostic runs — auditing float values can flip threshold results.
    hexes = [srgb_to_hex(c) for c in rgbs]
    rgbs = np.array([hex_to_srgb(h) for h in hexes])

    diag, warnings = _audit(rgbs, kind, background_rgb, use, thresholds)
    diag["vividness"] = vividness
    if kind == "helix":
        diag["rotations"] = rotations
    diag["anchor"] = anchor if kind != "categorical" else "exact"
    diag["seed_nearest_stop_deltaE"] = round(
        min(ciede2000(c, seed_rgb) for c in rgbs), 1
    )

    if kind == "diverging":
        warnings.append(
            "Diverging second pole derived as seed hue + 180 deg — a design assumption, "
            "not implied by the seed. Override by generating from the other pole too."
        )
    if float(seed_lch[1]) < 0.02:
        warnings.append("Seed is near-neutral — hue is poorly defined; family hue is arbitrary.")

    return PaletteResult(
        hexes=hexes,
        kind=kind,
        seed=seed.upper() if seed.startswith("#") else "#" + seed.upper(),
        background=background,
        use=use,
        diagnostics=diag,
        warnings=warnings,
    )
