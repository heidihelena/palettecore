"""v0.2.2 fixes: the audit must describe the returned HEX colours exactly,
anchor/use/threshold inputs must validate, diverging must be structural."""

import numpy as np
import pytest

from palettecore.convert import hex_to_srgb
from palettecore.cvd import CONDITIONS, simulate_cvd
from palettecore.generate import generate_palette
from palettecore.metrics import ciede2000


def _recompute_min_adjacent(hexes, condition):
    rgbs = [hex_to_srgb(h) for h in hexes]
    if condition != "normal":
        rgbs = [simulate_cvd(c, condition) for c in rgbs]
    return min(ciede2000(rgbs[i], rgbs[i + 1]) for i in range(len(rgbs) - 1))


def _recompute_min_pairwise(hexes, condition):
    rgbs = [hex_to_srgb(h) for h in hexes]
    if condition != "normal":
        rgbs = [simulate_cvd(c, condition) for c in rgbs]
    n = len(rgbs)
    return min(ciede2000(rgbs[i], rgbs[j]) for i in range(n) for j in range(i + 1, n))


# ------------------------------------------- audit == returned colours


@pytest.mark.parametrize("seed", ["#8B6FC9", "#86DC0A", "#1A2B3C", "#D95F02"])
def test_sequential_audit_matches_returned_hexes(seed):
    r = generate_palette(seed, n=12, kind="sequential")
    for cond in ("normal",) + CONDITIONS:
        reported = r.diagnostics["min_adjacent_deltaE"][cond]
        recomputed = _recompute_min_adjacent(r.hexes, cond)
        assert reported == round(recomputed, 1), f"{seed}/{cond}"


@pytest.mark.parametrize("seed", ["#8B6FC9", "#86DC0A"])
def test_categorical_audit_matches_returned_hexes(seed):
    r = generate_palette(seed, n=8, kind="categorical")
    for cond in ("normal",) + CONDITIONS:
        reported = r.diagnostics["min_pairwise_deltaE"][cond]
        recomputed = _recompute_min_pairwise(r.hexes, cond)
        assert reported == round(recomputed, 1), f"{seed}/{cond}"


def test_reviewer_case_86DC0A_no_false_pass():
    # Pre-0.2.2 this reported deuteranopia 6.0 (no warning) while the
    # returned HEX colours recomputed to 5.896 (below the threshold).
    r = generate_palette("#86DC0A", n=12, kind="sequential")
    recomputed = _recompute_min_adjacent(r.hexes, "deuteranopia")
    assert r.diagnostics["min_adjacent_deltaE"]["deuteranopia"] == round(recomputed, 1)
    if recomputed < 6.0:
        assert any("deuteranopia" in w for w in r.warnings)


def test_warning_iff_reported_value_below_threshold():
    # No false passes and no false warnings, per condition.
    r = generate_palette("#86DC0A", n=12, kind="sequential")
    th = r.diagnostics["thresholds_used"]
    for cond in ("normal",) + CONDITIONS:
        below = r.diagnostics["min_adjacent_deltaE"][cond] < th[cond]
        warned = any(w.startswith(f"{cond}:") for w in r.warnings)
        assert below == warned, cond


# ------------------------------------------------------- anchor=exact


def test_diverging_anchor_exact_contains_seed():
    r = generate_palette("#8B6FC9", n=8, kind="diverging", anchor="exact")
    assert "#8B6FC9" in r.hexes
    assert r.diagnostics["seed_nearest_stop_deltaE"] == 0.0


def test_diverging_anchor_path_reports_true_distance():
    r = generate_palette("#8B6FC9", n=8, kind="diverging", anchor="path")
    assert r.diagnostics["anchor"] == "path"
    assert r.diagnostics["seed_nearest_stop_deltaE"] >= 0.0


# --------------------------------------------------- input validation


@pytest.mark.parametrize("bad_use", ["Text", "typo", "fill", ""])
def test_invalid_use_rejected(bad_use):
    with pytest.raises(ValueError, match="Unknown use"):
        generate_palette("#8B6FC9", n=8, use=bad_use)


def test_unknown_threshold_name_rejected():
    with pytest.raises(ValueError, match="Unknown threshold name"):
        generate_palette("#8B6FC9", n=8, thresholds={"deutan": 6.0})


@pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), -1.0, "6"])
def test_bad_threshold_value_rejected(bad_val):
    with pytest.raises(ValueError, match="finite non-negative"):
        generate_palette("#8B6FC9", n=8, thresholds={"normal": bad_val})


# ------------------------------------------------------ diverging n/structure


def test_diverging_n2_rejected():
    with pytest.raises(ValueError, match="n >= 3"):
        generate_palette("#8B6FC9", n=2, kind="diverging")


def test_diverging_structure_reported_and_sound():
    r = generate_palette("#8B6FC9", n=9, kind="diverging")
    s = r.diagnostics["diverging_structure"]
    assert s["arms_monotonic"] and s["centre_interior"]
    assert 0 < s["centre_index"] < 8


# ------------------------------------------------------ still deterministic


def test_categorical_caching_preserves_determinism():
    a = generate_palette("#8B6FC9", n=8, kind="categorical")
    b = generate_palette("#8B6FC9", n=8, kind="categorical")
    assert a.hexes == b.hexes and a.diagnostics == b.diagnostics
