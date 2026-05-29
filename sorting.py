"""Sorting helpers."""

from __future__ import annotations

from models import NormalizedChannel


def sort_channels(channels: list[NormalizedChannel], geographic_key: str = "none") -> list[NormalizedChannel]:
    def geo(channel: NormalizedChannel):
        if geographic_key == "locator":
            return channel.locator or ""
        if geographic_key == "latlon":
            if (channel.latitude is None or channel.longitude is None) and "missing_coordinates" not in channel.warnings:
                channel.warnings.append("missing_coordinates")
            return (channel.latitude if channel.latitude is not None else 999.0, channel.longitude if channel.longitude is not None else 999.0)
        return ""

    return sorted(
        channels,
        key=lambda ch: (
            district_key(ch.district),
            geo(ch),
            type_key(ch.type),
            ch.city.casefold(),
            ch.frequency_mhz,
        ),
    )


def district_key(value: str):
    return (0, int(value)) if value.isdigit() else (1, value.casefold())


def type_key(value: str) -> int:
    order = {"Repeater": 0, "Link": 1, "Hotspot": 2}
    return order.get(value, 99)
