"""Interactive CLI for converting SK6BA/Marks repeater CSV to CHIRP CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

from exporters.chirp import export_chirp_csv
from filters import default_analog_fm_row_filter, normalize_rows
from importers.sk6ba import read_csv
from naming import DEFAULT_TEMPLATE, generate_names
from preview import format_inspection, print_preview
from sorting import sort_channels
from validation import print_validation, validate_channels

DEFAULT_INPUT = "Example_input_Marks amatörradioklubb export - repeaters.csv"
DEFAULT_OUTPUT = "chirp_export.csv"


def prompt(text: str, default: str) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{text}{suffix}: ").strip()
    return answer or default


def numbered_menu(title: str, options: list[tuple[str, str]], default_index: int = 1) -> str:
    print(f"\n{title}")
    for index, (label, _value) in enumerate(options, start=1):
        default_mark = " (default)" if index == default_index else ""
        print(f"  {index}. {label}{default_mark}")
    raw = prompt("Välj nummer", str(default_index))
    try:
        choice = int(raw)
        if 1 <= choice <= len(options):
            return options[choice - 1][1]
    except ValueError:
        pass
    print("Ogiltigt val, använder default.")
    return options[default_index - 1][1]


def run_pipeline(input_path: str, output_path: str, name_template: str, geo_sort: str, preview_limit: int, assume_yes: bool) -> int:
    rows, inspection = read_csv(input_path)
    print(format_inspection(inspection))

    filtered = [row for row in rows if default_analog_fm_row_filter(row)]
    channels = normalize_rows(filtered)
    channels = sort_channels(channels, geographic_key=geo_sort)
    generate_names(channels, name_template)
    print_validation(validate_channels(channels))
    print_preview(channels, limit=preview_limit)

    if not channels:
        print("Inga kanaler att exportera.")
        return 2

    if not assume_yes:
        confirm = prompt(f"Exportera {len(channels)} kanaler till {output_path}? (j/N)", "N")
        if confirm.lower() not in {"j", "ja", "y", "yes"}:
            print("Avbrutet före export.")
            return 1

    export_chirp_csv(channels, output_path)
    print(f"Skrev CHIRP CSV: {output_path}")
    return 0


def interactive() -> int:
    mode = numbered_menu(
        "Läge",
        [("Snabbt läge", "quick"), ("Avancerat läge", "advanced")],
        default_index=1,
    )
    input_path = prompt("SK6BA/Marks CSV-fil", DEFAULT_INPUT)
    output_path = prompt("CHIRP output CSV", DEFAULT_OUTPUT)

    if mode == "quick":
        return run_pipeline(input_path, output_path, DEFAULT_TEMPLATE, "none", 20, assume_yes=False)

    template = prompt("Namntemplate tokens {type} {network} {band} {district} {city} {channel} {call}", DEFAULT_TEMPLATE)
    geo_sort = numbered_menu(
        "Geografisk sorteringsnyckel",
        [("Ingen", "none"), ("Locator", "locator"), ("Latitud/longitud", "latlon")],
        default_index=1,
    )
    preview_limit = int(prompt("Antal preview-rader", "30"))
    return run_pipeline(input_path, output_path, template, geo_sort, preview_limit, assume_yes=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Konvertera SK6BA/Marks repeater CSV till CHIRP CSV.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Lokal SK6BA/Marks CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="CHIRP CSV som ska skrivas")
    parser.add_argument("--name-template", default=DEFAULT_TEMPLATE, help="Namntemplate med tokens")
    parser.add_argument("--geo-sort", choices=["none", "locator", "latlon"], default="none", help="Valfri geografisk sorteringsnyckel")
    parser.add_argument("--preview", type=int, default=20, help="Antal preview-rader")
    parser.add_argument("--yes", action="store_true", help="Exportera utan interaktiv bekräftelse")
    parser.add_argument("--interactive", action="store_true", help="Tvinga interaktivt snabb/avancerat läge")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.interactive:
        return interactive()
    if any(flag in __import__('sys').argv for flag in ["--input", "--output", "--name-template", "--geo-sort", "--preview", "--yes"]):
        return run_pipeline(args.input, args.output, args.name_template, args.geo_sort, args.preview, args.yes)
    return interactive()


if __name__ == "__main__":
    raise SystemExit(main())
