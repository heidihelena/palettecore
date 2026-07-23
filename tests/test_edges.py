"""Pathological seeds, edge cases, and no-false-pass checks."""

import numpy as np
import pytest

from palettecore.convert import hex_to_srgb
from palettecore.cvd import CONDITIONS, out_of_gamut_excursion
from palettecore.generate import generate_palette
from palettecore.metrics import ciede2000

PATHOLOGICAL_SEEDS = [
    "#FFFFFF",
    "#000000",
    "#FFFF00",
    "#00FF00",
    "#00FFFF",
    "#FF00FF",
    "#808080",
    "#010101",
    "#FEFEFE",
]


@pytest.mark.parametrize("seed", PATHOLOGICAL_SEEDS)
@pytest.mark.parametrize("kind", ["sequential", "categorical"])
def test_pathological_seeds_never_crash(seed, kind):
    r = generate_palette(seed, n=8, kind=kind)
    assert len(r.hexes) == 8
    assert all(h.startswith("#") and len(h) == 7 for h in r.hexes)


@pytest.mark.parametrize("seed", ["#FFFFFF", "#000000", "#808080", "#010101", "#FEFEFE"])
def test_neutral_pathological_seeds_warn(seed):
    r = generate_palette(seed, n=8, kind="sequential")
    assert any("near-neutral" in w for w in r.warnings)


@pytest.mark.parametrize("seed", ["#FFFF00", "#00FF00", "#00FFFF", "#FF00FF"])
def test_gamut_boundary_seeds_stay_displayable(seed):
    for kind in ("sequential", "categorical"):
        r = generate_palette(seed, n=8, kind=kind)
        for h in r.hexes:
            rgb = hex_to_srgb(h)
            assert np.all(rgb >= 0) and np.all(rgb <= 1)


# ------------------------------------------------------------------ n range


def test_n_one_rejected_clearly():
    with pytest.raises(ValueError, match="between 2 and 24"):
        generate_palette("#8B6FC9", n=1)


def test_n_two():
    r = generate_palette("#8B6FC9", n=2, kind="sequential")
    assert len(r.hexes) == 2 and r.hexes[0] != r.hexes[1]


@pytest.mark.parametrize("n", [12, 20])
def test_large_n_categorical(n):
    r = generate_palette("#8B6FC9", n=n, kind="categorical")
    assert len(set(r.hexes)) == n


def test_large_n_sequential_warns_not_false_passes():
    # 20 stops light-to-dark cannot keep adjacent dE00 >= 8: the audit must
    # say so rather than pass silently.
    r = generate_palette("#8B6FC9", n=20, kind="sequential")
    assert r.diagnostics["min_adjacent_deltaE"]["normal"] < 8
    assert any("below" in w for w in r.warnings)


def test_non_integer_n_rejected():
    with pytest.raises(ValueError):
        generate_palette("#8B6FC9", n=8.5)


# -------------------------------------------------------------- invalid hex


@pytest.mark.parametrize("bad", ["#GGGGGG", "8B6FC", "", "#12345", "not a colour"])
def test_invalid_hex_raises_valueerror(bad):
    with pytest.raises(ValueError, match="HEX"):
        generate_palette(bad, n=8)


# ------------------------------------------------------------- backgrounds


@pytest.mark.parametrize("bg", ["#FFFFFF", "#000000"])
def test_black_and_white_backgrounds(bg):
    r = generate_palette("#8B6FC9", n=8, kind="sequential", background=bg)
    assert len(r.hexes) == 8
    assert len(r.diagnostics["contrast_vs_background"]) == 8


def test_pale_seed_on_white_text_warns_not_false_passes():
    # A very pale yellow seed cannot yield eight text-safe shades on white.
    r = generate_palette("#FFFFCC", n=8, kind="sequential", use="text")
    assert any("WCAG" in w for w in r.warnings)


# ------------------------------------------------------------ reproducible


def test_generation_is_deterministic():
    for kind in ("sequential", "categorical", "diverging"):
        a = generate_palette("#8B6FC9", n=8, kind=kind)
        b = generate_palette("#8B6FC9", n=8, kind=kind)
        assert a.hexes == b.hexes
        assert a.diagnostics == b.diagnostics


# ------------------------------------------------------------------ anchor


def test_anchor_path_reports_seed_distance():
    r = generate_palette("#8B6FC9", n=8, kind="sequential", anchor="path")
    assert "seed_nearest_stop_deltaE" in r.diagnostics
    assert r.diagnostics["anchor"] == "path"


def test_anchor_exact_puts_seed_in_palette():
    r = generate_palette("#8B6FC9", n=8, kind="sequential", anchor="exact")
    assert "#8B6FC9" in r.hexes
    assert r.diagnostics["seed_nearest_stop_deltaE"] == 0.0


def test_categorical_always_contains_seed():
    r = generate_palette("#8B6FC9", n=8, kind="categorical")
    assert r.hexes[0] == "#8B6FC9"
    assert r.diagnostics["anchor"] == "exact"


def test_bad_anchor_rejected():
    with pytest.raises(ValueError, match="anchor"):
        generate_palette("#8B6FC9", n=8, anchor="snap")


# --------------------------------------------------------------- CVD gamut


def test_cvd_excursion_reported():
    r = generate_palette("#FF00FF", n=8, kind="categorical")
    exc = r.diagnostics["cvd_gamut"]["max_linear_excursion_before_clamp"]
    assert set(exc) == set(CONDITIONS)
    assert all(v >= 0 for v in exc.values())


def test_excursion_zero_for_safe_colour():
    grey = hex_to_srgb("#777777")
    for c in CONDITIONS:
        assert out_of_gamut_excursion(grey, c) == pytest.approx(0.0, abs=1e-6)


# --------------------------------------------------------------- thresholds


def test_thresholds_recorded_and_overridable():
    r = generate_palette("#8B6FC9", n=8, thresholds={"tritanopia": 4.0})
    used = r.diagnostics["thresholds_used"]
    assert used["tritanopia"] == 4.0
    assert used["normal"] == 8.0
    assert "not" in used["note"]


def test_stricter_threshold_creates_warning():
    r = generate_palette("#8B6FC9", n=8, thresholds={"normal": 25.0})
    assert any("normal" in w and "below" in w for w in r.warnings)
