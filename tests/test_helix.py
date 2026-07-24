"""The helix (cubehelix) kind: monotonic lightness, rotations, guards."""

import numpy as np
import pytest

from palettecore.convert import hex_to_oklch
from palettecore.generate import generate_palette


def test_helix_basic():
    r = generate_palette("#3C7AC0", n=8, kind="helix")
    assert len(r.hexes) == 8
    assert len(set(r.hexes)) == 8


def test_helix_lightness_monotonic():
    # the defining property: a helix stays ordered in greyscale
    r = generate_palette("#3C7AC0", n=10, kind="helix")
    assert r.diagnostics["lightness_monotonic"]


def test_helix_hue_actually_rotates():
    r = generate_palette("#3C7AC0", n=8, kind="helix", rotations=1.0)
    hues = [hex_to_oklch(h)[2] for h in r.hexes]
    # more than one distinct hue region visited (not a single-hue ramp)
    assert max(hues) - min(hues) > 60


def test_helix_records_rotations():
    r = generate_palette("#3C7AC0", n=8, kind="helix", rotations=1.5)
    assert r.diagnostics["rotations"] == 1.5


def test_helix_negative_rotations_differs():
    a = generate_palette("#3C7AC0", n=8, kind="helix", rotations=1.0)
    b = generate_palette("#3C7AC0", n=8, kind="helix", rotations=-1.0)
    assert a.hexes != b.hexes


def test_helix_vividness_applies():
    muted = generate_palette("#3C7AC0", n=8, kind="helix", vividness=0.0)
    vivid = generate_palette("#3C7AC0", n=8, kind="helix", vividness=1.0)
    mc = np.mean([hex_to_oklch(h)[1] for h in muted.hexes])
    vc = np.mean([hex_to_oklch(h)[1] for h in vivid.hexes])
    assert vc > mc


def test_helix_anchor_exact():
    r = generate_palette("#3C7AC0", n=8, kind="helix", anchor="exact")
    assert "#3C7AC0" in r.hexes


def test_rotations_rejected_for_other_kinds():
    with pytest.raises(ValueError, match="rotations only applies"):
        generate_palette("#3C7AC0", n=8, kind="sequential", rotations=2.0)


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), "x"])
def test_rotations_must_be_finite(bad):
    with pytest.raises(ValueError, match="rotations"):
        generate_palette("#3C7AC0", n=8, kind="helix", rotations=bad)


def test_helix_audited_like_sequential():
    r = generate_palette("#3C7AC0", n=8, kind="helix")
    assert "min_adjacent_deltaE" in r.diagnostics
    assert "greyscale_luminance" in r.diagnostics
