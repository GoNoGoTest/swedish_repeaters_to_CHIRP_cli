"""Filtering and normalization from SK6BA rows to channels."""

from __future__ import annotations

import math
from typing import Any

from importers.sk6ba import parse_decimal
from models import NormalizedChannel
from tones import parse_ctcss

DEFAULT_TYPES = {"Repeater", "Link", "Hotspot"}


def clean_text(value: Any) -> str:
    """Return a safe string for CSV values without placeholder junk."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"none", "nan"} else text


def default_analog_fm_row_filter(row: dict[str, str]) -> bool:
    return (
        clean_text(row.get("status")).upper() == "QRV"
        and clean_text(row.get("type")) in DEFAULT_TYPES
        and "FM" in clean_text(row.get("mode")).upper()
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

    raw_shift = clean_text(row.get("tx_shift"))
    shift = parse_decimal(raw_shift)
    if shift is None:
        if raw_shift:
            warnings.append("invalid_tx_shift")
        shift = 0.0

    if shift > 0:
        duplex = "+"
    elif shift < 0:
        duplex = "-"
    else:
        duplex = ""

    ctcss, needs_1750, tone_warnings = parse_ctcss(clean_text(row.get("access")))
    warnings.extend(tone_warnings)
    lat_raw = clean_text(row.get("lat"))
    lng_raw = clean_text(row.get("lng"))
    lat = parse_decimal(lat_raw)
    lng = parse_decimal(lng_raw)
    if lat_raw and lat is None:
        warnings.append("invalid_lat")
    if lng_raw and lng is None:
        warnings.append("invalid_lng")

    network = clean_text(row.get("network"))
    call = clean_text(row.get("call"))
    channel_name = clean_text(row.get("channel"))
    locator = clean_text(row.get("locator"))

    comment_parts = [
        part for part in [
            network,
            f"{call} {channel_name}".strip(),
            f"locator {locator}" if locator else "",
            "1750 Hz" if needs_1750 else "",
        ] if part
    ]

    return NormalizedChannel(
        source_id=clean_text(row.get("id")),
        source_type="sk6ba",
        type=clean_text(row.get("type")),
        status=clean_text(row.get("status")),
        mode=clean_text(row.get("mode")),
        band=clean_text(row.get("band")),
        district=clean_text(row.get("district")),
        network=network,
        city=clean_text(row.get("city")),
        channel=channel_name,
        call=call,
        frequency_mhz=output,
        duplex=duplex,
        offset_mhz=abs(shift),
        ctcss_hz=ctcss,
        needs_1750_hz=needs_1750,
        latitude=lat,
        longitude=lng,
        locator=locator,
        comment=" | ".join(comment_parts),
        warnings=warnings,
    )
