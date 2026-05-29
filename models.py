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
    chirp_tone: str = ""
    chirp_rtone_freq: str = ""
    chirp_ctone_freq: str = ""
    chirp_dtcs_code: str = "023"
    chirp_dtcs_polarity: str = "NN"
    chirp_mode: str = "FM"
    chirp_tstep: str = "5.00"
    chirp_skip: str = ""
    source_type: str = "sk6ba"
    pack_id: str = ""
    service: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    label: str = ""
    name_hint: str = ""
    tx_frequency_mhz: Optional[float] = None
    tstep: str = "5.00"
    skip: str = ""
    tx_allowed: bool = True
    rx_only: bool = False
    license_note: str = ""
    source: str = ""
    source_url: str = ""
    inferred_from_range: bool = False
    enabled_default: bool | None = None
    manually_selected: bool | None = None

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
