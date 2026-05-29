"""Importer and selection helpers for optional static channel packs."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from models import NormalizedChannel
from sorting import sort_channels

CHANNELPACK_COLUMNS = [
    "pack_id", "source_id", "enabled_default", "service", "band", "category", "tags",
    "type", "label", "channel", "name_hint", "rx_frequency", "tx_frequency", "duplex",
    "offset", "mode", "tstep", "tone", "rtone_freq", "ctone_freq", "dtcs_code",
    "dtcs_polarity", "skip", "tx_allowed", "rx_only", "license_note", "comment",
    "source", "source_url", "inferred_from_range",
]

BOOL_COLUMNS = {"enabled_default", "tx_allowed", "rx_only", "inferred_from_range"}
BOOL_DEFAULTS = {
    "enabled_default": False,
    "tx_allowed": True,
    "rx_only": False,
    "inferred_from_range": False,
}
TEXT_DEFAULTS = {column: "" for column in CHANNELPACK_COLUMNS if column not in BOOL_COLUMNS}

TRUE_VALUES = {"true", "1", "yes", "y", "ja", "j"}
FALSE_VALUES = {"false", "0", "no", "n", "nej"}


@dataclass(frozen=True)
class ChannelPackRow:
    pack_id: str
    source_id: str
    enabled_default: bool
    service: str
    band: str
    category: str
    tags: list[str]
    type: str
    label: str
    channel: str
    name_hint: str
    rx_frequency: float
    tx_frequency: float | None
    duplex: str
    offset: float
    mode: str
    tstep: str
    tone: str
    rtone_freq: str
    ctone_freq: str
    dtcs_code: str
    dtcs_polarity: str
    skip: str
    tx_allowed: bool
    rx_only: bool
    license_note: str
    comment: str
    source: str
    source_url: str
    inferred_from_range: bool


@dataclass(frozen=True)
class ChannelPack:
    path: Path
    pack_id: str
    rows: list[ChannelPackRow]
    warnings: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.pack_id or self.path.stem


@dataclass(frozen=True)
class ChannelPackSummary:
    total_rows: int
    services: Counter[str]
    bands: Counter[str]
    categories: Counter[str]
    tags: Counter[str]


class ChannelPackError(ValueError):
    """Raised when a channel-pack CSV contains invalid critical values."""


def find_channelpack_files(directory: str | Path = "channelpacks") -> list[Path]:
    path = Path(directory)
    if not path.exists():
        return []
    return sorted(candidate for candidate in path.glob("*.csv") if candidate.is_file())


def load_channelpacks(directory: str | Path = "channelpacks") -> list[ChannelPack]:
    return [read_channelpack(path) for path in find_channelpack_files(directory)]


def read_channelpack(path: str | Path) -> ChannelPack:
    csv_path = Path(path)
    warnings: list[str] = []
    rows: list[ChannelPackRow] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return ChannelPack(csv_path, csv_path.stem, [], ["empty_csv"])
        missing = [column for column in CHANNELPACK_COLUMNS if column not in reader.fieldnames]
        non_critical_missing = [column for column in missing if column not in {"source_id", "rx_frequency"}]
        if non_critical_missing:
            warnings.append("missing_columns:" + ",".join(non_critical_missing))
        critical_missing = [column for column in missing if column in {"source_id", "rx_frequency"}]
        if critical_missing:
            raise ChannelPackError(f"{csv_path}: saknar kritiska kolumner: {', '.join(critical_missing)}")

        for line_number, raw_row in enumerate(reader, start=2):
            row = _with_defaults(raw_row)
            try:
                rows.append(parse_channelpack_row(row, csv_path, line_number))
            except ChannelPackError:
                raise
            except ValueError as exc:
                warnings.append(f"line_{line_number}:{exc}")

    pack_id = next((row.pack_id for row in rows if row.pack_id), csv_path.stem)
    return ChannelPack(csv_path, pack_id, rows, warnings)


def _with_defaults(raw_row: dict[str, str | None]) -> dict[str, str]:
    row: dict[str, str] = {}
    for column in CHANNELPACK_COLUMNS:
        default = str(BOOL_DEFAULTS[column]).lower() if column in BOOL_DEFAULTS else TEXT_DEFAULTS[column]
        value = raw_row.get(column, default)
        row[column] = clean(value) if value is not None else default
    return row


def parse_channelpack_row(row: dict[str, str], path: Path | None = None, line_number: int | None = None) -> ChannelPackRow:
    context = ""
    if path is not None:
        context = str(path)
        if line_number is not None:
            context += f":{line_number}"
        context += ": "

    bools = {column: parse_bool(row.get(column, ""), column, context) for column in BOOL_COLUMNS}
    rx_frequency = parse_float(row.get("rx_frequency"))
    if rx_frequency is None:
        raise ValueError("invalid_rx_frequency")
    tx_frequency = parse_float(row.get("tx_frequency"))
    offset = parse_float(row.get("offset")) or 0.0

    return ChannelPackRow(
        pack_id=clean(row.get("pack_id")),
        source_id=clean(row.get("source_id")),
        enabled_default=bools["enabled_default"],
        service=clean(row.get("service")),
        band=clean(row.get("band")),
        category=clean(row.get("category")),
        tags=split_tags(row.get("tags", "")),
        type=clean(row.get("type")) or "Static",
        label=clean(row.get("label")),
        channel=clean(row.get("channel")),
        name_hint=clean(row.get("name_hint")),
        rx_frequency=rx_frequency,
        tx_frequency=tx_frequency,
        duplex=clean(row.get("duplex")),
        offset=offset,
        mode=clean(row.get("mode")) or "FM",
        tstep=clean(row.get("tstep")) or "5.00",
        tone=clean(row.get("tone")),
        rtone_freq=clean(row.get("rtone_freq")),
        ctone_freq=clean(row.get("ctone_freq")),
        dtcs_code=clean(row.get("dtcs_code")) or "023",
        dtcs_polarity=clean(row.get("dtcs_polarity")) or "NN",
        skip=clean(row.get("skip")),
        tx_allowed=bools["tx_allowed"],
        rx_only=bools["rx_only"],
        license_note=clean(row.get("license_note")),
        comment=clean(row.get("comment")),
        source=clean(row.get("source")),
        source_url=clean(row.get("source_url")),
        inferred_from_range=bools["inferred_from_range"],
    )


def parse_bool(value: str | None, column: str, context: str = "") -> bool:
    text = clean(value).casefold()
    if text == "":
        return BOOL_DEFAULTS[column]
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ChannelPackError(f"{context}ogiltigt boolean-värde för {column}: {value!r}")


def parse_float(value: str | None) -> float | None:
    text = clean(value).replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def split_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split("|") if tag.strip()]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def summarize_channelpack_rows(rows: Iterable[ChannelPackRow]) -> ChannelPackSummary:
    materialized = list(rows)
    return ChannelPackSummary(
        total_rows=len(materialized),
        services=Counter(row.service for row in materialized if row.service),
        bands=Counter(row.band for row in materialized if row.band),
        categories=Counter(row.category for row in materialized if row.category),
        tags=Counter(tag for row in materialized for tag in row.tags),
    )


def filter_channelpack_rows(
    rows: Iterable[ChannelPackRow],
    *,
    enabled_default_only: bool = False,
    bands: set[str] | None = None,
    categories: set[str] | None = None,
    tags: set[str] | None = None,
) -> list[ChannelPackRow]:
    selected: list[ChannelPackRow] = []
    for row in rows:
        if enabled_default_only and not row.enabled_default:
            continue
        if bands and row.band not in bands:
            continue
        if categories and row.category not in categories:
            continue
        if tags and not (set(row.tags) & tags):
            continue
        selected.append(row)
    return selected


def rows_to_channels(rows: Iterable[ChannelPackRow]) -> list[NormalizedChannel]:
    return [row_to_channel(row) for row in rows]


def row_to_channel(row: ChannelPackRow) -> NormalizedChannel:
    name = row.name_hint or row.label or row.channel or row.source_id
    comment_parts = [row.comment, row.license_note, row.source]
    return NormalizedChannel(
        source_id=row.source_id,
        type=row.type,
        status="QRV",
        mode=row.mode,
        band=row.band,
        district="",
        network=row.service,
        city="",
        channel=row.channel or row.label,
        call="",
        frequency_mhz=row.rx_frequency,
        duplex=row.duplex,
        offset_mhz=abs(row.offset),
        comment=" | ".join(part for part in comment_parts if part),
        name=name,
        chirp_tone=row.tone,
        chirp_rtone_freq=row.rtone_freq,
        chirp_ctone_freq=row.ctone_freq,
        chirp_dtcs_code=row.dtcs_code,
        chirp_dtcs_polarity=row.dtcs_polarity,
        chirp_mode=row.mode,
        chirp_tstep=row.tstep,
        chirp_skip=row.skip,
    )


def merge_channels(
    imported_channels: list[NormalizedChannel],
    pack_channels: list[NormalizedChannel],
    placement: str,
    duplicate_policy: str = "keep_all",
) -> list[NormalizedChannel]:
    deduped_pack_channels = apply_duplicate_policy(imported_channels, pack_channels, duplicate_policy)
    if placement == "beginning":
        return [*deduped_pack_channels, *imported_channels]
    if placement == "end":
        return [*imported_channels, *deduped_pack_channels]
    if placement == "same_sorting":
        return sort_channels([*imported_channels, *deduped_pack_channels])
    raise ValueError(f"Okänd placering: {placement}")


def apply_duplicate_policy(
    imported_channels: list[NormalizedChannel],
    pack_channels: list[NormalizedChannel],
    duplicate_policy: str,
) -> list[NormalizedChannel]:
    if duplicate_policy == "keep_all":
        return list(pack_channels)
    if duplicate_policy == "skip_pack_duplicates":
        imported_keys = {duplicate_key(channel) for channel in imported_channels}
        return [channel for channel in pack_channels if duplicate_key(channel) not in imported_keys]
    raise ValueError(f"Okänd dubblettpolicy: {duplicate_policy}")


def duplicate_key(channel: NormalizedChannel) -> tuple[float, str, str]:
    return (round(channel.frequency_mhz, 6), channel.duplex, f"{abs(channel.offset_mhz):.6f}")
