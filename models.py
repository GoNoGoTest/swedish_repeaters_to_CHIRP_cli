"""Data models for SK6BA/Marks repeater conversion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class InputInspection:
    """Summary of an imported CSV file before filtering/normalization."""

    row_count: int
    columns: list[str]
    unique_values: dict[str, list[str]]
    warning_counts: dict[str, int]


@dataclass
class NormalizedChannel:
    """Normalized analogue channel ready for preview and CHIRP export."""

    source_id: str
    type: str
    status: str
    mode: str
    band: str
    district: str
    network: str
    city: str
    channel: str
    call: str
    frequency_mhz: float
    duplex: str
    offset_mhz: float
    ctcss_hz: Optional[float] = None
    needs_1750_hz: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    locator: str = ""
    comment: str = ""
    warnings: list[str] = field(default_factory=list)
    name: str = ""

    def frequency_text(self) -> str:
        return f"{self.frequency_mhz:.6f}".rstrip("0").rstrip(".")

    def offset_text(self) -> str:
        if self.duplex == "":
            return "0"
        return f"{abs(self.offset_mhz):.6f}".rstrip("0").rstrip(".")

    def ctcss_text(self) -> str:
        if self.ctcss_hz is None:
            return ""
        return f"{self.ctcss_hz:.1f}"
