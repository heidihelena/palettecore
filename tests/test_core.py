"""Correctness anchors for palette-core.

The conversion and CIEDE2000 fixtures double as the cross-language parity
targets: the future R implementation must reproduce these numbers.
"""

import numpy as np
import pytest

from palettecore.convert import (
    hex_to_oklch,
    hex_to_srgb,
    in_srgb_gamut,
    max_chroma,
    oklab_to_oklch,
    oklch_to_hex,
    srgb_to_cielab,
    srgb_to_hex,
    srgb_to_oklab,
)
from palettecore.cvd import CONDITIONS, simulate_cvd
from palettecore.generate import generate_palette
from palettecore.metrics import ciede2000, contrast_ratio, is_monotonic


# ------------------------------------------------------------- conversions


def test_hex_roundtrip():
    for h in ["#8B6FC9", "#000000", "#FFFFFF", "#FF0000", "#1A2B3C"]:
        assert srgb_to_hex(hex_to_srgb(h)) == h


def test_oklab_reference_white():
    # Ottosson reference: sRGB white is OKLab (1, 0, 0)
    lab = srgb_to_oklab(np.array([1.0, 1.0, 1.0]))
    assert np.allclose(lab, [1.0, 0.0, 0.0], atol=1e-4)


def test_oklab_roundtrip():
    lch = hex_to_oklch("#8B6FC9")
    assert oklch_to_hex(lch) == "#8B6FC9"


def test_cielab_white():
    lab = srgb_to_cielab(np.array([1.0, 1.0, 1.0]))
    assert np.allclose(lab, [100.0, 0.0, 0.0], atol=0.05)


def test_oklch_hue_of_pure_red():
    lch = oklab_to_oklch(srgb_to_oklab(np.array([1.0, 0.0, 0.0])))
    assert abs(lch[2] - 29.23) < 0.5  # published OKLCH hue of sRGB red


# --------------------------------------------------------------- CIEDE2000


def test_ciede2000_identity():
    c = hex_to_srgb("#8B6FC9")
    assert ciede2000(c, c) == pytest.approx(0.0, abs=1e-9)


def test_ciede2000_symmetric():
    a, b = hex_to_srgb("#8B6FC9"), hex_to_srgb("#3C7A2B")
    assert ciede2000(a, b) == pytest.approx(ciede2000(b, a), abs=1e-9)


def test_ciede2000_black_white():
    de = ciede2000(hex_to_srgb("#000000"), hex_to_srgb("#FFFFFF"))
    assert de == pytest.approx(100.0, abs=0.1)


# ------------------------------------------------------------------- gamut


def test_max_chroma_shrinks_at_extremes():
    h = 300.0
    assert max_chroma(0.97, h) < max_chroma(0.65, h)
    assert max_chroma(0.15, h) < max_chroma(0.65, h)


def test_in_gamut():
    assert in_srgb_gamut(np.array([0.65, 0.05, 300.0]))
    assert not in_srgb_gamut(np.array([0.97, 0.3, 300.0]))


# --------------------------------------------------------------------- CVD


def test_cvd_preserves_range():
    for cond in CONDITIONS:
        sim = simulate_cvd(hex_to_srgb("#8B6FC9"), cond)
        assert np.all(sim >= 0) and np.all(sim <= 1)


def test_deuteranopia_collapses_red_green():
    red, green = hex_to_srgb("#D95F02"), hex_to_srgb("#66A61E")
    normal = ciede2000(red, green)
    sim = ciede2000(simulate_cvd(red, "deuteranopia"), simulate_cvd(green, "deuteranopia"))
    assert sim < normal  # the whole point of simulating


# ---------------------------------------------------------------- contrast


def test_contrast_black_on_white():
    assert contrast_ratio(hex_to_srgb("#000000"), hex_to_srgb("#FFFFFF")) == pytest.approx(
        21.0, abs=0.01
    )


# ------------------------------------------------------------- generation


def test_sequential_basic():
    r = generate_palette("#8B6FC9", n=8, kind="sequential")
    assert len(r.hexes) == 8
    assert len(set(r.hexes)) == 8
    assert r.diagnostics["lightness_monotonic"]


def test_sequential_equalish_steps():
    r = generate_palette("#8B6FC9", n=8, kind="sequential")
    steps = r.diagnostics["adjacent_deltaE"]["normal"]
    assert max(steps) / min(steps) < 1.5  # near-equal by construction


def test_categorical_basic():
    r = generate_palette("#8B6FC9", n=8, kind="categorical")
    assert len(set(r.hexes)) == 8
    assert r.diagnostics["min_pairwise_deltaE"]["normal"] > 0


def test_categorical_anchors_seed_hue():
    r = generate_palette("#8B6FC9", n=6, kind="categorical")
    seed_h = hex_to_oklch("#8B6FC9")[2]
    first_h = hex_to_oklch(r.hexes[0])[2]
    assert abs(((first_h - seed_h) + 180) % 360 - 180) < 5


def test_diverging_basic():
    r = generate_palette("#8B6FC9", n=8, kind="diverging")
    assert len(r.hexes) == 8
    assert any("design assumption" in w for w in r.warnings)


def test_text_use_flags_pale_swatches():
    r = generate_palette("#8B6FC9", n=8, kind="sequential", use="text")
    assert any("WCAG" in w for w in r.warnings)


def test_neutral_seed_warns():
    r = generate_palette("#888888", n=5, kind="sequential")
    assert any("near-neutral" in w for w in r.warnings)


def test_exports():
    r = generate_palette("#8B6FC9", n=4)
    assert '"palette"' in r.to_json()
    assert "--palette-1:" in r.to_css()
