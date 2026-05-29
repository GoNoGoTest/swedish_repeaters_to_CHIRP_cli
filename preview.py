"""Console preview formatting."""

from __future__ import annotations

from models import InputInspection, NormalizedChannel


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
    print(f"\nPreview ({min(limit, len(channels))} av {len(channels)} kanaler):")
    print(f"{'#':>3} {'Name':<16} {'Freq':>10} {'Dup':>3} {'Off':>7} {'Tone':>7} {'Ort':<22} Kommentar")
    print("-" * 88)
    for index, channel in enumerate(channels[:limit], start=1):
        tone = channel.ctcss_text() or ("1750" if channel.needs_1750_hz else "")
        print(
            f"{index:>3} {channel.name:<16.16} {channel.frequency_text():>10} "
            f"{channel.duplex or '':>3} {channel.offset_text():>7} {tone:>7} "
            f"{channel.city:<22.22} {channel.comment}"
        )
    if len(channels) > limit:
        print(f"... {len(channels) - limit} fler rader")
