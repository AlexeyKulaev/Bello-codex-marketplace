#!/usr/bin/env python3
"""Print a concise, current Codex model-and-effort catalog for the advisor."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


TARGET_MODELS = (
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
)


def summarize_catalog(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise ValueError("model catalog must contain a models array")

    by_slug = {
        item.get("slug"): item
        for item in payload["models"]
        if isinstance(item, dict) and isinstance(item.get("slug"), str)
    }
    missing = [slug for slug in TARGET_MODELS if slug not in by_slug]
    if missing:
        raise ValueError(f"model catalog is missing: {', '.join(missing)}")

    result: list[dict[str, Any]] = []
    for slug in TARGET_MODELS:
        item = by_slug[slug]
        levels = item.get("supported_reasoning_levels")
        if not isinstance(levels, list):
            raise ValueError(f"{slug} has no supported_reasoning_levels array")
        efforts = []
        for level in levels:
            if not isinstance(level, dict) or not isinstance(level.get("effort"), str):
                raise ValueError(f"{slug} contains an invalid reasoning level")
            efforts.append(
                {
                    "effort": level["effort"],
                    "description": level.get("description"),
                }
            )
        result.append(
            {
                "model": slug,
                "description": item.get("description"),
                "default_effort": item.get("default_reasoning_level"),
                "supported_efforts": efforts,
                "speed_tiers": item.get("additional_speed_tiers", []),
            }
        )
    return result


def load_catalog(*, timeout_seconds: float, bundled_only: bool) -> tuple[list[dict[str, Any]], str]:
    attempts = [(True, "bundled")] if bundled_only else [(False, "current"), (True, "bundled fallback")]
    errors: list[str] = []
    for bundled, label in attempts:
        command = ["codex", "debug", "models"]
        if bundled:
            command.append("--bundled")
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            payload = json.loads(completed.stdout)
            return summarize_catalog(payload), label
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{label}: {exc}")
    raise RuntimeError("; ".join(errors))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--bundled-only",
        action="store_true",
        help="Skip catalog refresh and inspect only the catalog shipped with Codex",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        models, source = load_catalog(
            timeout_seconds=args.timeout,
            bundled_only=args.bundled_only,
        )
        result = {
            "source": f"codex debug models ({source})",
            "models": models,
        }
    except (RuntimeError, ValueError) as exc:
        print(f"model catalog unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
