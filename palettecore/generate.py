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
For sequential/diverging the seed defines the path (hue + chroma envelope)
but the exact HEX is not guaranteed to be a stop; anchor="exact" snaps the
nearest stop to the seed at the cost of slightly uneven spacing, and the
audit reports the seed-to-nearest-stop distance either way.
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


def _sequential_path(seed_lch, n, background_rgb, samples=512):
    """Dense OKLCH path at the seed hue, then pick n stops equally spaced in
    cumulative CIEDE2000 — arc-length reparametrisation instead of a free
    optimiser, which makes the equal-step property hold by construction."""
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
        c = min(C_target[i], c_max)
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


def _categorical(seed_lch, n):
    """Anchor the seed, then greedy farthest-point placement on a constrained
    hue circle, followed by swap-improvement passes on the maximin objective."""
    L_seed, C_seed, H_seed = (float(v) for v in seed_lch)
    L_band = float(np.clip(L_seed, 0.55, 0.78))

    hues = np.arange(0.0, 360.0, 4.0)
    levels = [L_band - 0.06, L_band, L_band + 0.06]
    candidates = []
    for h in hues:
        for L in levels:
            c = min(max(C_seed, 0.09), max_chroma(L, h)) * 0.92
            rgb = np.clip(oklab_to_srgb(oklch_to_oklab(np.array([L, c, h]))), 0, 1)
            candidates.append(rgb)
    candidates = np.array(candidates)

    seed_rgb = np.clip(
        oklab_to_srgb(oklch_to_oklab(np.array([L_seed, C_seed, H_seed]))), 0, 1
    )
    chosen = [seed_rgb]

    def score(cand, current):
        s = np.inf
        for x in current:
            s = min(s, ciede2000(cand, x))
            for cond in CONDITIONS:
                s = min(s, ciede2000(simulate_cvd(cand, cond), simulate_cvd(x, cond)))
        return s

    while len(chosen) < n:
        scores = [score(c, chosen) for c in candidates]
        chosen.append(candidates[int(np.argmax(scores))])

    # Swap-improvement: try to lift the weakest link.
    for _ in range(2):
        for i in range(1, n):  # never move the seed anchor
            rest = chosen[:i] + chosen[i + 1 :]
            best_rgb, best_s = chosen[i], score(chosen[i], rest)
            for c in candidates[::3]:
                s = score(c, rest)
                if s > best_s:
                    best_rgb, best_s = c, s
            chosen[i] = best_rgb

    return np.array(chosen)


# ---------------------------------------------------------------- diverging


def _diverging(seed_lch, n, background_rgb):
    """Seed pole → near-neutral centre → derived opposite pole. The second
    hue (seed hue + 180°) is a design assumption, flagged in warnings."""
    L, C, H = (float(v) for v in seed_lch)
    opp = np.array([L, C, (H + 180.0) % 360.0])
    half = (n + 1) // 2
    a = _sequential_path(np.array([L, C, H]), half, background_rgb)
    b = _sequential_path(opp, half, background_rgb)
    if n % 2 == 1:
        return np.vstack([b[::-1][:-1], a])  # shared light centre stop
    return np.vstack([b[::-1][: n // 2], a[half - n // 2 :]])


# ------------------------------------------------------------------- audit


def _audit(rgbs, kind, background_rgb, use, thresholds):
    n = len(rgbs)
    diag: dict = {}
    warnings: list[str] = []

    sims = {c: np.array([simulate_cvd(x, c) for x in rgbs]) for c in CONDITIONS}

    if kind in ("sequential", "diverging"):
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
    if kind == "sequential":
        diag["lightness_monotonic"] = is_monotonic(grey)
        if not is_monotonic(grey):
            warnings.append("Greyscale luminance is not monotonic — order is lost in print.")
    elif kind == "categorical":
        spread = float(grey.max() - grey.min())
        diag["greyscale_spread"] = round(spread, 3)
        if spread > 0.45:
            warnings.append(
                "Large lightness spread — one category may look more important than others."
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
) -> PaletteResult:
    """Generate an audited palette from one seed colour.

    kind:   'sequential' | 'diverging' | 'categorical'
    use:    'data_fill' | 'text' | 'line' | 'UI'
    anchor: 'path' (seed defines the path; exact HEX may not appear) or
            'exact' (nearest sequential stop snapped to the seed, at the
            cost of slightly uneven spacing). Categorical palettes always
            contain the seed exactly, regardless of this setting.
    """
    if kind not in ("sequential", "diverging", "categorical"):
        raise ValueError(f"Unknown palette kind: {kind!r}")
    if anchor not in ("path", "exact"):
        raise ValueError(f"Unknown anchor policy: {anchor!r}")
    if not isinstance(n, int) or not 2 <= n <= 24:
        raise ValueError(f"n must be an integer between 2 and 24, got {n!r}")

    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    seed_lch = hex_to_oklch(seed)
    background_rgb = hex_to_srgb(background)

    if kind == "sequential":
        rgbs = _sequential_path(seed_lch, n, background_rgb)
    elif kind == "diverging":
        rgbs = _diverging(seed_lch, n, background_rgb)
    else:
        rgbs = _categorical(seed_lch, n)

    seed_rgb = hex_to_srgb(seed)
    if kind == "sequential" and anchor == "exact":
        i_near = int(np.argmin([ciede2000(c, seed_rgb) for c in rgbs]))
        rgbs[i_near] = seed_rgb

    diag, warnings = _audit(rgbs, kind, background_rgb, use, thresholds)
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
        hexes=[srgb_to_hex(c) for c in rgbs],
        kind=kind,
        seed=seed.upper() if seed.startswith("#") else "#" + seed.upper(),
        background=background,
        use=use,
        diagnostics=diag,
        warnings=warnings,
    )
