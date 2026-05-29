"""Filtering and normalization from SK6BA rows to channels."""

from __future__ import annotations

from importers.sk6ba import parse_decimal
from models import NormalizedChannel
from tones import parse_ctcss

DEFAULT_TYPES = {"Repeater", "Link", "Hotspot"}


def default_analog_fm_row_filter(row: dict[str, str]) -> bool:
    return (
        row.get("status", "").strip().upper() == "QRV"
        and row.get("type", "").strip() in DEFAULT_TYPES
        and "FM" in row.get("mode", "").upper()
    )


def normalize_rows(rows: list[dict[str, str]], include_warnings: bool = True) -> list[NormalizedChannel]:
    channels: list[NormalizedChannel] = []
    for row in rows:
        channel = normalize_row(row)
        if channel is not None:
            channels.append(channel)
    return channels


def normalize_row(row: dict[str, str]) -> NormalizedChannel | None:
    warnings: list[str] = []
    output = parse_decimal(row.get("output"))
    if output is None:
        return None

    shift = parse_decimal(row.get("tx_shift")) or 0.0
    if shift > 0:
        duplex = "+"
    elif shift < 0:
        duplex = "-"
    else:
        duplex = ""

    ctcss, needs_1750, tone_warnings = parse_ctcss(row.get("access", ""))
    warnings.extend(tone_warnings)
    lat = parse_decimal(row.get("lat"))
    lng = parse_decimal(row.get("lng"))
    if row.get("lat") and lat is None:
        warnings.append("invalid_lat")
    if row.get("lng") and lng is None:
        warnings.append("invalid_lng")

    comment_parts = [
        part for part in [
            row.get("network", ""),
            f"{row.get('call', '')} {row.get('channel', '')}".strip(),
            f"locator {row.get('locator', '')}" if row.get("locator") else "",
            "1750 Hz" if needs_1750 else "",
        ] if part
    ]

    return NormalizedChannel(
        source_id=row.get("id", ""),
        type=row.get("type", ""),
        status=row.get("status", ""),
        mode=row.get("mode", ""),
        band=row.get("band", ""),
        district=row.get("district", ""),
        network=row.get("network", ""),
        city=row.get("city", ""),
        channel=row.get("channel", ""),
        call=row.get("call", ""),
        frequency_mhz=output,
        duplex=duplex,
        offset_mhz=abs(shift),
        ctcss_hz=ctcss,
        needs_1750_hz=needs_1750,
        latitude=lat,
        longitude=lng,
        locator=row.get("locator", ""),
        comment=" | ".join(comment_parts),
        warnings=warnings,
    )
