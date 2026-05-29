"""CHIRP CSV exporter."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

from models import NormalizedChannel

CHIRP_COLUMNS = [
    "Location",
    "Name",
    "Frequency",
    "Duplex",
    "Offset",
    "Tone",
    "rToneFreq",
    "cToneFreq",
    "DtcsCode",
    "DtcsPolarity",
    "Mode",
    "TStep",
    "Skip",
    "Comment",
]
RX_ONLY_POLICIES = {"duplex_off", "mark_rx_only", "skip", "stop"}
RxOnlyPolicy = Literal["duplex_off", "mark_rx_only", "skip", "stop"]


def export_chirp_csv(
    channels: list[NormalizedChannel],
    path: str | Path,
    start_location: int = 1,
    *,
    rx_only_policy: RxOnlyPolicy | None = None,
) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHIRP_COLUMNS)
        writer.writeheader()
        location = start_location
        for channel in channels:
            row = to_chirp_row(channel, location, rx_only_policy=rx_only_policy)
            if row is None:
                continue
            writer.writerow(row)
            location += 1


def to_chirp_row(
    channel: NormalizedChannel,
    location: int,
    *,
    rx_only_policy: RxOnlyPolicy | None = None,
) -> dict[str, str | int] | None:
    if channel.rx_only or channel.tx_allowed is False:
        if rx_only_policy is None or rx_only_policy == "stop":
            raise ValueError(
                f"RX-only kanal kräver policy före export: {channel.source_type}:{channel.source_id}"
            )
        if rx_only_policy not in RX_ONLY_POLICIES:
            raise ValueError(f"Okänd RX-only-policy: {rx_only_policy}")
        if rx_only_policy == "skip":
            return None

    tone = channel.chirp_tone or ("Tone" if channel.ctcss_hz is not None else "")
    ctcss = channel.ctcss_text() if channel.ctcss_hz is not None else "88.5"
    rtone_freq = channel.chirp_rtone_freq or ctcss
    ctone_freq = channel.chirp_ctone_freq or ctcss
    duplex = channel.duplex
    offset = chirp_offset(channel)
    skip = channel.skip or channel.chirp_skip
    comment = export_comment(channel)

    if channel.rx_only or channel.tx_allowed is False:
        if rx_only_policy == "duplex_off":
            duplex = "off"
            offset = "0.000000"
            comment = append_comment(comment, "RX-only")
        elif rx_only_policy == "mark_rx_only":
            skip = skip or "S"
            comment = append_comment(comment, "RX-only")

    return {
        "Location": location,
        "Name": channel.name,
        "Frequency": f"{channel.frequency_mhz:.6f}",
        "Duplex": duplex,
        "Offset": offset,
        "Tone": tone,
        "rToneFreq": rtone_freq,
        "cToneFreq": ctone_freq,
        "DtcsCode": channel.chirp_dtcs_code or "023",
        "DtcsPolarity": channel.chirp_dtcs_polarity or "NN",
        "Mode": channel.mode or channel.chirp_mode or "FM",
        "TStep": channel.tstep or channel.chirp_tstep or "5.00",
        "Skip": skip,
        "Comment": comment,
    }


def chirp_offset(channel: NormalizedChannel) -> str:
    if channel.duplex == "split":
        tx_frequency = channel.tx_frequency_mhz or channel.frequency_mhz
        return f"{tx_frequency:.6f}"
    if channel.duplex:
        return f"{abs(channel.offset_mhz):.6f}"
    return "0.000000"


def export_comment(channel: NormalizedChannel) -> str:
    comment = channel.comment
    if channel.license_note and channel.license_note not in comment:
        comment = append_comment(comment, channel.license_note)
    if channel.warnings:
        comment = append_comment(comment, ";".join(channel.warnings))
    return comment


def append_comment(comment: str, addition: str) -> str:
    return (comment + " | " if comment else "") + addition
