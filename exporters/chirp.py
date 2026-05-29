"""CHIRP CSV exporter."""

from __future__ import annotations

import csv
from pathlib import Path

from models import NormalizedChannel

CHIRP_COLUMNS = [
    "Location", "Name", "Frequency", "Duplex", "Offset", "Tone", "rToneFreq",
    "cToneFreq", "DtcsCode", "DtcsPolarity", "Mode", "TStep", "Skip", "Comment",
]


def export_chirp_csv(channels: list[NormalizedChannel], path: str | Path, start_location: int = 1) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHIRP_COLUMNS)
        writer.writeheader()
        for location, channel in enumerate(channels, start=start_location):
            writer.writerow(to_chirp_row(channel, location))


def to_chirp_row(channel: NormalizedChannel, location: int) -> dict[str, str | int]:
    tone = channel.chirp_tone or ("Tone" if channel.ctcss_hz is not None else "")
    ctcss = channel.ctcss_text() if channel.ctcss_hz is not None else "88.5"
    rtone_freq = channel.chirp_rtone_freq or ctcss
    ctone_freq = channel.chirp_ctone_freq or ctcss
    comment = channel.comment
    if channel.warnings:
        comment = (comment + " | " if comment else "") + ";".join(channel.warnings)
    return {
        "Location": location,
        "Name": channel.name,
        "Frequency": f"{channel.frequency_mhz:.6f}",
        "Duplex": channel.duplex,
        "Offset": f"{abs(channel.offset_mhz):.6f}" if channel.duplex else "0.000000",
        "Tone": tone,
        "rToneFreq": rtone_freq,
        "cToneFreq": ctone_freq,
        "DtcsCode": channel.chirp_dtcs_code or "023",
        "DtcsPolarity": channel.chirp_dtcs_polarity or "NN",
        "Mode": channel.chirp_mode or channel.mode or "FM",
        "TStep": channel.chirp_tstep or "5.00",
        "Skip": channel.chirp_skip,
        "Comment": comment,
    }
