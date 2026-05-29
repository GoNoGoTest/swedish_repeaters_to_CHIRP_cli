"""Validation helpers for normalized channels."""

from __future__ import annotations

from collections import Counter

from models import NormalizedChannel


def validate_channels(channels: list[NormalizedChannel]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for channel in channels:
        if not channel.name:
            counts["missing_name"] += 1
        if not (0 < channel.frequency_mhz < 10000):
            counts["invalid_frequency"] += 1
        if channel.duplex not in {"", "+", "-"}:
            counts["invalid_duplex"] += 1
        if len(channel.name) > 16:
            counts["name_too_long"] += 1
        for warning in channel.warnings:
            counts[warning.split(":", 1)[0]] += 1
    return dict(counts)


def print_validation(counts: dict[str, int]) -> None:
    if not counts:
        print("Validering: inga varningar.")
        return
    print("Validering/varningar:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
