"""Console preview formatting."""

from __future__ import annotations

from models import InputInspection, NormalizedChannel
from validation import find_frequency_duplicates


def format_inspection(inspection: InputInspection) -> str:
    lines = [
        f"Rader: {inspection.row_count}",
        f"Kolumner ({len(inspection.columns)}): {', '.join(inspection.columns)}",
        "Unika värden:",
    ]
    for key, values in inspection.unique_values.items():
        shown = ", ".join(v or "<tom>" for v in values[:20])
        if len(values) > 20:
            shown += f", ... (+{len(values) - 20})"
        lines.append(f"  {key}: {shown}")
    lines.append("Varningsräkningar:")
    for key, count in inspection.warning_counts.items():
        lines.append(f"  {key}: {count}")
    return "\n".join(lines)


def print_preview(channels: list[NormalizedChannel], limit: int = 20) -> None:
    duplicates = duplicate_source_ids_by_frequency(channels)
    name_collisions = collision_names(channels)
    print(f"\nPreview ({min(limit, len(channels))} av {len(channels)} kanaler):")
    print(
        f"{'#':>3} {'Src':<4} {'Name':<16} {'Freq':>10} {'Dup':>5} {'Off/Tx':>10} "
        f"{'Mode':<4} {'Step':>6} {'Skip':<4} Metadata / Kommentar"
    )
    print("-" * 132)
    for index, channel in enumerate(channels[:limit], start=1):
        marker = source_marker(channel)
        meta = channel_metadata(channel)
        warnings = preview_warnings(channel, duplicates, name_collisions)
        details = " | ".join(
            part for part in [meta, channel.comment, "; ".join(warnings)] if part
        )
        print(
            f"{index:>3} {marker:<4} {channel.name:<16.16} {channel.frequency_text():>10} "
            f"{channel.duplex or '':>5} {offset_or_tx(channel):>10} {channel.mode:<4.4} "
            f"{(channel.tstep or channel.chirp_tstep):>6.6} {(channel.skip or channel.chirp_skip):<4.4} {details}"
        )
    if len(channels) > limit:
        print(f"... {len(channels) - limit} fler rader")
    print_preview_warnings(channels, duplicates, name_collisions)


def source_marker(channel: NormalizedChannel) -> str:
    if channel.source_type == "channel_pack":
        return "[CP]"
    if channel.network == "SK6BA" or channel.source_type == "sk6ba":
        return "[SK]"
    if "mark" in channel.network.casefold():
        return "[MA]"
    return "[--]"


def channel_metadata(channel: NormalizedChannel) -> str:
    values = [
        f"source_type={channel.source_type}",
        f"source_id={channel.source_id}",
        f"pack_id={channel.pack_id}" if channel.pack_id else "",
        f"service={channel.service}" if channel.service else "",
        f"category={channel.category}" if channel.category else "",
        f"tags={','.join(channel.tags)}" if channel.tags else "",
        f"label={channel.label}" if channel.label else "",
        f"channel={channel.channel}" if channel.channel else "",
        f"tx_allowed={str(channel.tx_allowed).lower()}",
        f"rx_only={str(channel.rx_only).lower()}",
        f"license_note={channel.license_note}" if channel.license_note else "",
        f"inferred_from_range={str(channel.inferred_from_range).lower()}",
        selection_metadata(channel),
    ]
    return " ".join(value for value in values if value)


def selection_metadata(channel: NormalizedChannel) -> str:
    selected_by = getattr(channel, "selected_by", "")
    enabled_default = getattr(channel, "enabled_default", None)
    manually_selected = getattr(channel, "manually_selected", None)
    values = []
    if enabled_default is not None:
        values.append(f"enabled_default={str(enabled_default).lower()}")
    if manually_selected is not None:
        values.append(f"manually_selected={str(manually_selected).lower()}")
    if selected_by:
        values.append(f"selected_by={selected_by}")
    return " ".join(values)


def offset_or_tx(channel: NormalizedChannel) -> str:
    if channel.duplex == "split" and channel.tx_frequency_mhz is not None:
        return f"{channel.tx_frequency_mhz:.6f}".rstrip("0").rstrip(".")
    return channel.offset_text()


def duplicate_source_ids_by_frequency(
    channels: list[NormalizedChannel],
) -> dict[float, set[str]]:
    return {
        group["frequency"]: set(group["source_ids"])
        for group in find_frequency_duplicates(channels)
    }


def collision_names(channels: list[NormalizedChannel]) -> set[str]:
    counts: dict[str, int] = {}
    for channel in channels:
        counts[channel.name] = counts.get(channel.name, 0) + 1
    return {name for name, count in counts.items() if name and count > 1}


def preview_warnings(
    channel: NormalizedChannel,
    duplicates: dict[float, set[str]],
    name_collisions: set[str],
) -> list[str]:
    warnings = []
    if channel.name in name_collisions:
        warnings.append("NAMNKOLLISION")
    if round(channel.frequency_mhz, 6) in duplicates:
        warnings.append("FREKVENSDUBBLETT")
    if channel.rx_only or channel.tx_allowed is False:
        warnings.append("RX-ONLY")
    if channel.inferred_from_range:
        warnings.append("inferred_from_range=true")
    return warnings


def print_preview_warnings(
    channels: list[NormalizedChannel],
    duplicates: dict[float, set[str]],
    name_collisions: set[str],
) -> None:
    rx_only_count = sum(
        1 for channel in channels if channel.rx_only or channel.tx_allowed is False
    )
    inferred_count = sum(1 for channel in channels if channel.inferred_from_range)
    if not (duplicates or name_collisions or rx_only_count or inferred_count):
        return
    print("\nPreview-varningar:")
    for name in sorted(name_collisions):
        print(f"  Namnkollision: {name}")
    for frequency, source_ids in sorted(duplicates.items()):
        print(f"  Frekvensdubblett {frequency:.6f}: {', '.join(sorted(source_ids))}")
    if rx_only_count:
        print(f"  RX-only-varningar: {rx_only_count}")
    if inferred_count:
        print(f"  inferred_from_range=true: {inferred_count}")
