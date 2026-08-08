from __future__ import annotations

import argparse
import asyncio
import json

from _harness import (
    BASELINE_PATH,
    DEFAULT_ITERATIONS,
    DEFAULT_WARMUP,
    FULL_STACK,
    FULL_STACK_VARIANTS,
    build_baseline,
    format_breakdown,
    run_breakdown,
)


def _parse_variants(value: str) -> tuple[str, ...]:
    variants = tuple(part.strip() for part in value.split(",") if part.strip())
    if not variants or any(name not in FULL_STACK_VARIANTS for name in variants):
        raise argparse.ArgumentTypeError(
            f"variants must be a comma-separated subset of {FULL_STACK_VARIANTS!r}"
        )
    if len(set(variants)) != len(variants):
        raise argparse.ArgumentTypeError("variants must not contain duplicates")
    return variants


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rapidy-client full-stack benchmark")
    parser.add_argument(
        "--variants",
        type=_parse_variants,
        default=FULL_STACK_VARIANTS,
    )
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--freeze-baseline", action="store_true")
    args = parser.parse_args(argv)

    variants = ("bare_httpx2", *args.variants)
    results = asyncio.run(
        run_breakdown(
            iterations=args.iterations,
            warmup=args.warmup,
            variants=variants,
        )
    )
    print(format_breakdown(results))

    if args.freeze_baseline:
        if args.variants != FULL_STACK_VARIANTS:
            parser.error(
                "--freeze-baseline requires the complete no-di,+di variant set"
            )
        baseline = build_baseline(
            results,
            stack=FULL_STACK,
            samples=args.iterations,
        )
        BASELINE_PATH.write_text(
            json.dumps(baseline, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
