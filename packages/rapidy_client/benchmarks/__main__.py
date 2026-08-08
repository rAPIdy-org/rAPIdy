from __future__ import annotations

import argparse
import asyncio
import json
from typing import Literal, cast

from ._harness import (
    BASELINE_PATH,
    BASELINE_VARIANTS,
    DEFAULT_ITERATIONS,
    DEFAULT_WARMUP,
    FULL_STACK,
    FULL_STACK_VARIANTS,
    HEADROOM_PATH,
    MEMORY_PEAK_LIMIT_BYTES,
    VARIANTS,
    VariantResult,
    build_baseline,
    build_headroom,
    check_baseline,
    format_breakdown,
    measure_full_stack_ratio,
    measure_stream_memory,
    run_breakdown,
)


def _stored_results(data: dict[str, object]) -> list[VariantResult]:
    variants = data.get("variants")
    if not isinstance(variants, dict) or tuple(variants) != VARIANTS:
        raise ValueError("headroom variants are missing or out of order")
    results: list[VariantResult] = []
    for name in VARIANTS:
        values = variants[name]
        if not isinstance(values, dict):
            raise TypeError(f"invalid headroom variant {name!r}")
        overhead = values.get("overhead_pct")
        results.append(
            VariantResult(
                name=name,
                p50_us=float(values["p50_us"]),
                p99_us=float(values["p99_us"]),
                overhead_pct=None if overhead is None else float(overhead),
            )
        )
    return results


def _check_headroom() -> int:
    try:
        data = json.loads(HEADROOM_PATH.read_text(encoding="utf-8"))
        if data.get("schema") != "rapidy-client/headroom@1":
            raise ValueError("unsupported headroom schema")
        if data.get("kind") != "bring-up-headroom" or data.get("gate") is not False:
            raise ValueError("headroom metadata is invalid")
        results = _stored_results(data)
        headroom = data["headroom"]
        if not isinstance(headroom, dict):
            raise TypeError("headroom verdict is missing")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"invalid headroom snapshot: {exc}")
        return 1

    print(format_breakdown(results))
    verdict = "OK" if headroom.get("within_threshold") else "WARN"
    print(
        f"{verdict}: advisory headroom overhead={headroom.get('overhead_pct')}% "
        f"p99={headroom.get('p99_us')}us (gate=false)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rapidy-client headroom harness")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-headroom", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--freeze-baseline", action="store_true")
    mode.add_argument("--check-baseline", action="store_true")
    mode.add_argument("--check-memory", action="store_true")
    parser.add_argument("--stack", default=FULL_STACK)
    parser.add_argument("--variants")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    args = parser.parse_args(argv)
    if args.check_headroom:
        return _check_headroom()
    if args.check_memory:
        peak = asyncio.run(measure_stream_memory())
        print(f"stream memory peak={peak} bytes limit={MEMORY_PEAK_LIMIT_BYTES} bytes")
        return 0 if peak <= MEMORY_PEAK_LIMIT_BYTES else 1
    if args.check_baseline:
        variants = tuple(
            part.strip() for part in (args.variants or "").split(",") if part.strip()
        )
        if variants != FULL_STACK_VARIANTS:
            parser.error("--check-baseline requires --variants no-di,+di in that order")
        current = {
            variant: asyncio.run(
                measure_full_stack_ratio(
                    variant=cast("Literal['no-di', '+di']", variant),
                    iterations=args.iterations,
                    warmup=args.warmup,
                )
            )
            for variant in variants
        }
        try:
            passed, detail = check_baseline(current)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            print(f"invalid baseline: {exc}")
            return 1
        print(
            f"no-di diagnostic={detail['no_di_ratio']:.4f}; "
            f"+di baseline={detail['baseline_ratio']:.4f} "
            f"current={detail['current_ratio']:.4f} "
            f"limit={detail['limit']:.4f}"
        )
        return 0 if passed else 1

    variants = BASELINE_VARIANTS if args.freeze_baseline else VARIANTS
    results = asyncio.run(
        run_breakdown(
            iterations=args.iterations,
            warmup=args.warmup,
            variants=variants,
        )
    )
    print(format_breakdown(results))
    if args.freeze_baseline:
        try:
            baseline = build_baseline(
                results,
                stack=args.stack,
                samples=args.iterations,
            )
        except ValueError as exc:
            parser.error(str(exc))
        BASELINE_PATH.write_text(
            json.dumps(baseline, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.freeze:
        HEADROOM_PATH.write_text(
            json.dumps(build_headroom(results), indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
