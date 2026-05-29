"""Flexible deterministic channel naming."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from models import NormalizedChannel

DEFAULT_TEMPLATE = "{district}{city}"
MAX_CHIRP_NAME = 16
TOKEN_RE = re.compile(r"\{(type|network|band|district|city|channel|call)\}")


def generate_names(channels: list[NormalizedChannel], template: str = DEFAULT_TEMPLATE, max_len: int = MAX_CHIRP_NAME) -> None:
    base_names = [clip_name(render_name(ch, template), max_len) for ch in channels]
    groups: dict[str, list[int]] = defaultdict(list)
    for index, base in enumerate(base_names):
        groups[base].append(index)

    for base, indexes in groups.items():
        if len(indexes) == 1:
            channels[indexes[0]].name = base
            continue
        used: set[str] = set()
        for index in indexes:
            suffix = deterministic_suffix(channels[index])
            prefix_len = max(1, max_len - len(suffix) - 1)
            candidate = f"{base[:prefix_len]}-{suffix}"
            bump = 1
            while candidate in used:
                alt = f"{suffix[:-1]}{bump % 10}" if len(suffix) > 1 else str(bump % 10)
                candidate = f"{base[:max(1, max_len - len(alt) - 1)]}-{alt}"
                bump += 1
            used.add(candidate)
            channels[index].name = candidate


def render_name(channel: NormalizedChannel, template: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return str(getattr(channel, match.group(1), "") or "")

    rendered = TOKEN_RE.sub(repl, template)
    return sanitize_name(rendered or channel.call or channel.city or f"CH{channel.source_id}")


def sanitize_name(value: str) -> str:
    value = re.sub(r"\s+", "", value.strip())
    value = re.sub(r"[^A-Za-z0-9ÅÄÖåäö_/-]", "", value)
    return value or "CHAN"


def clip_name(value: str, max_len: int) -> str:
    return value[:max_len]


def deterministic_suffix(channel: NormalizedChannel, length: int = 3) -> str:
    key = "|".join([channel.source_id, channel.call, channel.channel, f"{channel.frequency_mhz:.6f}"])
    return hashlib.blake2s(key.encode("utf-8"), digest_size=4).hexdigest().upper()[:length]
