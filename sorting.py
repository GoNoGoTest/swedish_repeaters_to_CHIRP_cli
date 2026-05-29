"""Sorting helpers."""

from __future__ import annotations

from models import NormalizedChannel


def sort_channels(channels: list[NormalizedChannel], geographic_key: str = "none") -> list[NormalizedChannel]:
    def geo(channel: NormalizedChannel):
        if geographic_key == "locator":
            return safe_text(channel, "locator")
        if geographic_key == "latlon":
            latitude = getattr(channel, "latitude", None)
            longitude = getattr(channel, "longitude", None)
            warnings = getattr(channel, "warnings", None)
            if (latitude is None or longitude is None) and isinstance(warnings, list) and "missing_coordinates" not in warnings:
                warnings.append("missing_coordinates")
            return (latitude if latitude is not None else 999.0, longitude if longitude is not None else 999.0)
        return ""

    return sorted(
        channels,
        key=lambda ch: (
            district_key(safe_text(ch, "district")),
            geo(ch),
            type_key(safe_text(ch, "type")),
            safe_text(ch, "city").casefold(),
            getattr(ch, "frequency_mhz", 0.0) or 0.0,
        ),
    )


def safe_text(channel: NormalizedChannel, attribute: str) -> str:
    return str(getattr(channel, attribute, "") or "")


def district_key(value: str):
    return (0, int(value)) if value.isdigit() else (1, value.casefold())


def type_key(value: str) -> int:
    order = {"Repeater": 0, "Link": 1, "Hotspot": 2, "Static": 3}
    return order.get(value, 99)
