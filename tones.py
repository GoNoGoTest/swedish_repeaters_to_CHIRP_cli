"""Tone parsing helpers."""

from __future__ import annotations

import re
from typing import Optional

VALID_CTCSS = {
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5, 94.8,
    97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3, 131.8,
    136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 165.5, 167.9, 171.3,
    173.8, 177.3, 179.9, 183.5, 186.2, 189.9, 192.8, 196.6, 199.5, 203.5,
    206.5, 210.7, 218.1, 225.7, 229.1, 233.6, 241.8, 250.3, 254.1,
}


def parse_ctcss(access: str) -> tuple[Optional[float], bool, list[str]]:
    """Return (CTCSS Hz, 1750 Hz flag, warnings) from an SK6BA access field."""
    value = (access or "").strip().replace(",", ".")
    warnings: list[str] = []
    if not value:
        return None, False, warnings

    lower = value.lower()
    has_1750 = "1750" in lower
    numbers = [float(m.group(1)) for m in re.finditer(r"(?<!\d)(\d{2,3}(?:\.\d)?)(?!\d)", value)]
    ctcss = next((n for n in numbers if 60.0 <= n <= 260.0 and abs(n - 175.0) > 0.01), None)
    if ctcss is not None:
        ctcss = round(ctcss, 1)
        if ctcss not in VALID_CTCSS:
            warnings.append(f"unusual_ctcss:{ctcss:g}")
    elif numbers and not has_1750:
        warnings.append(f"unparsed_access:{access}")
    elif not numbers and not has_1750:
        warnings.append(f"unparsed_access:{access}")
    return ctcss, has_1750, warnings
