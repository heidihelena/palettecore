"""Quick demo: generate and audit palettes from one seed colour."""

from palettecore import generate_palette

for kind in ("sequential", "categorical", "diverging"):
    r = generate_palette("#8B6FC9", n=8, kind=kind)
    print(f"\n=== {kind} from {r.seed} ===")
    print(" ".join(r.hexes))
    for k, v in r.diagnostics.items():
        print(f"  {k}: {v}")
    for w in r.warnings:
        print(f"  WARNING: {w}")
