"""Validation helpers for normalized channels and channel-pack CSV data."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from models import NormalizedChannel

KNOWN_MODES = {"", "FM", "NFM", "AM", "NAM", "DV", "DMR", "WFM"}
VALID_DUPLEX = {"", "+", "-", "split", "off"}
VALID_RX_ONLY_POLICIES = {"duplex_off", "mark_rx_only", "skip", "stop"}
VALID_SPLIT_POLICIES = {"export", "skip", "stop"}
VALID_BOOLEAN_TEXT = {
    "",
    "true",
    "1",
    "yes",
    "y",
    "ja",
    "j",
    "false",
    "0",
    "no",
    "n",
    "nej",
}


def validate_channels(
    channels: list[NormalizedChannel],
    *,
    rx_only_policy: str | None = None,
    split_policy: str | None = None,
    export_supports_split: bool = True,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    source_ids: Counter[str] = Counter(
        channel.source_id
        for channel in channels
        if channel.source_type == "channel_pack" and channel.source_id
    )

    for channel in channels:
        if not channel.name:
            counts["missing_name"] += 1
        if not render_final_name_exists(channel):
            counts["empty_final_name"] += 1
        if channel.source_type == "channel_pack":
            validate_channelpack_channel(
                channel, counts, rx_only_policy, split_policy, export_supports_split
            )
        if not (0 < channel.frequency_mhz < 10000):
            counts["invalid_frequency"] += 1
        if channel.duplex not in VALID_DUPLEX:
            counts["invalid_duplex"] += 1
        if len(channel.name) > 16:
            counts["name_too_long"] += 1
        if (
            channel.source_type != "channel_pack"
            and channel.mode.upper() not in KNOWN_MODES
        ):
            counts["unknown_mode"] += 1
        for warning in channel.warnings:
            counts[warning.split(":", 1)[0]] += 1

    counts["duplicate_source_id"] += sum(
        count - 1 for count in source_ids.values() if count > 1
    )
    duplicate_groups = find_frequency_duplicates(channels)
    sk6ba_channel_pack_duplicates = [
        group
        for group in duplicate_groups
        if {item["source_type"] for item in group["channels"]}
        >= {"sk6ba", "channel_pack"}
    ]
    channel_pack_duplicates = [
        group
        for group in duplicate_groups
        if sum(1 for item in group["channels"] if item["source_type"] == "channel_pack")
        > 1
    ]
    relevant_duplicate_frequencies = {
        group["frequency"]
        for group in [*sk6ba_channel_pack_duplicates, *channel_pack_duplicates]
    }
    counts["frequency_duplicate"] += len(relevant_duplicate_frequencies)
    counts["frequency_duplicate_sk6ba_channel_pack"] += len(
        sk6ba_channel_pack_duplicates
    )
    counts["frequency_duplicate_channel_pack"] += len(channel_pack_duplicates)
    return {key: value for key, value in counts.items() if value}


def render_final_name_exists(channel: NormalizedChannel) -> bool:
    return bool(
        (
            channel.name
            or channel.name_hint
            or channel.channel
            or channel.label
            or channel.call
            or channel.city
            or channel.source_id
        ).strip()
    )


def validate_channelpack_channel(
    channel: NormalizedChannel,
    counts: Counter[str],
    rx_only_policy: str | None,
    split_policy: str | None,
    export_supports_split: bool,
) -> None:
    if not channel.pack_id:
        counts["missing_pack_id"] += 1
    if not channel.source_id:
        counts["missing_source_id"] += 1
    if not (0 < channel.frequency_mhz < 10000):
        counts["missing_or_invalid_rx_frequency"] += 1
    if not channel.label:
        counts["missing_label"] += 1
    if not channel.channel:
        counts["missing_channel"] += 1
    if not channel.name_hint:
        counts["missing_name_hint"] += 1
    if channel.mode.upper() not in KNOWN_MODES:
        counts["unknown_mode"] += 1
    if not isinstance(channel.tx_allowed, bool):
        counts["invalid_boolean_tx_allowed"] += 1
    if not isinstance(channel.rx_only, bool):
        counts["invalid_boolean_rx_only"] += 1
    if not isinstance(channel.inferred_from_range, bool):
        counts["invalid_boolean_inferred_from_range"] += 1
    if (
        channel.rx_only or channel.tx_allowed is False
    ) and rx_only_policy not in VALID_RX_ONLY_POLICIES:
        counts["rx_only_without_policy"] += 1
    if channel.duplex == "split" and (
        not export_supports_split or split_policy not in VALID_SPLIT_POLICIES
    ):
        counts["split_without_export_support_or_policy"] += 1


def validate_channelpack_header(fieldnames: Sequence[str] | None) -> dict[str, int]:
    """Return warning/error counts for a channel-pack CSV header."""
    from importers.channelpacks import CHANNELPACK_COLUMNS

    counts: Counter[str] = Counter()
    if not fieldnames:
        return {"missing_header": 1}
    seen = set(fieldnames)
    missing = [column for column in CHANNELPACK_COLUMNS if column not in seen]
    unknown = [column for column in fieldnames if column not in CHANNELPACK_COLUMNS]
    if missing:
        counts["missing_header_column"] = len(missing)
    if unknown:
        counts["unknown_header_column"] = len(unknown)
    return dict(counts)


def validate_channelpack_raw_rows(
    rows: Iterable[dict[str, Any]], fieldnames: Sequence[str] | None = None
) -> dict[str, int]:
    """Validate raw channel-pack rows before normalization/parsing."""
    counts: Counter[str] = Counter(
        validate_channelpack_header(fieldnames) if fieldnames is not None else {}
    )
    source_ids: Counter[str] = Counter()
    for row in rows:
        source_id = clean(row.get("source_id"))
        source_ids[source_id] += 1
        if not clean(row.get("pack_id")):
            counts["missing_pack_id"] += 1
        if not source_id:
            counts["missing_source_id"] += 1
        rx_text = clean(row.get("rx_frequency"))
        if parse_float(rx_text) is None:
            counts["missing_or_invalid_rx_frequency"] += 1
        for column in ("label", "channel", "name_hint"):
            if not clean(row.get(column)):
                counts[f"missing_{column}"] += 1
        mode = clean(row.get("mode")) or "FM"
        if mode.upper() not in KNOWN_MODES:
            counts["unknown_mode"] += 1
        for column in (
            "enabled_default",
            "tx_allowed",
            "rx_only",
            "inferred_from_range",
        ):
            if clean(row.get(column)).casefold() not in VALID_BOOLEAN_TEXT:
                counts["invalid_boolean"] += 1
                counts[f"invalid_boolean_{column}"] += 1
    counts["duplicate_source_id"] += sum(
        count - 1 for value, count in source_ids.items() if value and count > 1
    )
    return {key: value for key, value in counts.items() if value}


def find_frequency_duplicates(
    channels: Iterable[NormalizedChannel],
) -> list[dict[str, Any]]:
    """Return duplicate RX-frequency groups with source types and source ids."""
    grouped: dict[float, list[NormalizedChannel]] = defaultdict(list)
    for channel in channels:
        grouped[round(channel.frequency_mhz, 6)].append(channel)

    duplicates: list[dict[str, Any]] = []
    for frequency, group in sorted(grouped.items()):
        if len(group) < 2:
            continue
        duplicates.append(
            {
                "frequency": frequency,
                "source_types": sorted({channel.source_type for channel in group}),
                "source_ids": [channel.source_id for channel in group],
                "channels": [
                    {
                        "source_type": channel.source_type,
                        "source_id": channel.source_id,
                        "name": channel.name,
                        "pack_id": channel.pack_id,
                    }
                    for channel in group
                ],
            }
        )
    return duplicates


def parse_float(value: str | None) -> float | None:
    text = clean(value).replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if 0 < number < 10000 else None


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def print_validation(counts: dict[str, int]) -> None:
    if not counts:
        print("Validering: inga varningar.")
        return
    print("Validering/varningar:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
