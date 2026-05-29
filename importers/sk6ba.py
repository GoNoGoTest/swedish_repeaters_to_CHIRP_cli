"""Importer for local SK6BA/Marks semicolon CSV exports."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from models import InputInspection

INSPECT_COLUMNS = ["type", "status", "mode", "band", "district", "network"]


def read_csv(path: str | Path) -> tuple[list[dict[str, str]], InputInspection]:
    """Read a UTF-8/BOM CSV and return rows plus inspection metadata."""
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(handle, dialect=dialect)
        rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]

    inspection = inspect_rows(rows, reader.fieldnames or [])
    return rows, inspection


def parse_decimal(value: Any) -> float | None:
    """Parse decimal values with either comma or point separators."""
    text = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not text or text == '""':
        return None
    try:
        return float(text)
    except ValueError:
        return None


def inspect_rows(rows: list[dict[str, str]], columns: list[str]) -> InputInspection:
    unique = {}
    for column in INSPECT_COLUMNS:
        unique[column] = sorted({row.get(column, "") for row in rows}, key=lambda s: (s == "", s.lower()))

    warning_counts = {
        "missing_output": sum(1 for row in rows if not row.get("output")),
        "invalid_output": sum(1 for row in rows if row.get("output") and parse_decimal(row.get("output")) is None),
        "missing_status": sum(1 for row in rows if not row.get("status")),
        "missing_mode": sum(1 for row in rows if not row.get("mode")),
        "missing_coordinates": sum(1 for row in rows if not row.get("lat") or not row.get("lng")),
        "unknown_columns": max(0, len([c for c in columns if c not in EXPECTED_COLUMNS])),
    }
    return InputInspection(len(rows), columns, unique, warning_counts)


EXPECTED_COLUMNS = {
    "id", "updated", "type", "band", "mode", "network", "network_id", "district",
    "call", "city", "channel", "output", "tx_shift", "access", "status", "lat",
    "lng", "locator", "masl", "magl", "watt_pep", "dir", "ant", "backup",
}
