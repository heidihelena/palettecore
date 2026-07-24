"""The vividness control: default is byte-identical, higher lifts chroma,
applies to every kind, and stays validated + audited."""

import numpy as np
import pytest

from palettecore.convert import hex_to_oklch
from palettecore.generate import generate_palette


def _mean_chroma(hexes):
    return float(np.mean([hex_to_oklch(h)[1] for h in hexes]))


@pytest.mark.parametrize("kind", ["sequential", "diverging", "categorical"])
def test_default_vividness_is_identical(kind):
    a = generate_palette("#8B6FC9", n=8, kind=kind)
    b = generate_palette("#8B6FC9", n=8, kind=kind, vividness=0.0)
    assert a.hexes == b.hexes
    assert a.diagnostics == b.diagnostics


@pytest.mark.parametrize("kind", ["sequential", "diverging", "categorical"])
def test_vividness_raises_chroma(kind):
    muted = generate_palette("#B57EDC", n=8, kind=kind, vividness=0.0)
    vivid = generate_palette("#B57EDC", n=8, kind=kind, vividness=1.0)
    assert _mean_chroma(vivid.hexes) > _mean_chroma(muted.hexes)


def test_vividness_recorded_in_diagnostics():
    r = generate_palette("#B57EDC", n=6, kind="categorical", vividness=0.7)
    assert r.diagnostics["vividness"] == 0.7


def test_vividness_preserves_sequential_monotonicity():
    # lifting chroma must not disturb the lightness order
    r = generate_palette("#3C7AC0", n=8, kind="sequential", vividness=1.0)
    assert r.diagnostics["lightness_monotonic"]


def test_vividness_keeps_categorical_seed_exact():
    r = generate_palette("#B57EDC", n=8, kind="categorical", vividness=1.0)
    assert "#B57EDC" in r.hexes


@pytest.mark.parametrize("bad", [-0.1, 1.5, "hi", float("nan"), float("inf"), None])
def test_vividness_out_of_range_rejected(bad):
    with pytest.raises(ValueError, match="vividness"):
        generate_palette("#8B6FC9", n=8, vividness=bad)


def test_vivid_palette_still_audited():
    r = generate_palette("#B57EDC", n=8, kind="categorical", vividness=1.0)
    # audit still runs and the palette is still valid HEX
    assert "min_pairwise_deltaE" in r.diagnostics
    assert all(h.startswith("#") and len(h) == 7 for h in r.hexes)
