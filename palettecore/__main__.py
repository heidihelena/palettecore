"""CLI: audited palettes from the shell (and for agents).

    python3 -m palettecore "#8B6FC9" -n 8 --kind sequential
    python3 -m palettecore "#8B6FC9" --kind categorical --format json
"""

from __future__ import annotations

import argparse
import sys

from .generate import generate_palette


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="palettecore",
        description="Derive, optimise and audit a scientific palette from one seed colour.",
    )
    p.add_argument("seed", help="seed colour as HEX, e.g. '#8B6FC9'")
    p.add_argument("-n", type=int, default=8, help="number of colours (2-24, default 8)")
    p.add_argument(
        "--kind",
        choices=["sequential", "diverging", "categorical"],
        default="sequential",
    )
    p.add_argument("--background", default="#FFFFFF", help="intended background HEX")
    p.add_argument(
        "--use", choices=["data_fill", "text", "line", "UI"], default="data_fill"
    )
    p.add_argument("--anchor", choices=["path", "exact"], default="path")
    p.add_argument(
        "--vividness", type=float, default=0.0,
        help="0.0 seed-faithful (default) to 1.0 chroma pushed to the gamut edge",
    )
    p.add_argument(
        "--format", choices=["text", "json", "css"], default="text", dest="fmt"
    )
    args = p.parse_args(argv)

    try:
        r = generate_palette(
            args.seed,
            n=args.n,
            kind=args.kind,
            background=args.background,
            use=args.use,
            anchor=args.anchor,
            vividness=args.vividness,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.fmt == "json":
        print(r.to_json())
    elif args.fmt == "css":
        print(r.to_css())
    else:
        print(" ".join(r.hexes))
        for k, v in r.diagnostics.items():
            print(f"  {k}: {v}")
        for w in r.warnings:
            print(f"  WARNING: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
