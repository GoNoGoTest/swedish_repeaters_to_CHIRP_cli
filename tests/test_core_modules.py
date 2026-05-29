from exporters.chirp import to_chirp_row
from filters import default_analog_fm_row_filter, normalize_row, normalize_rows
from importers.sk6ba import inspect_rows
from models import NormalizedChannel
from naming import generate_names, render_name
from sorting import sort_channels
from tones import parse_ctcss
from validation import validate_channels


def row(**overrides):
    base = {
        "id": "1",
        "type": "Repeater",
        "status": "QRV",
        "mode": "FM",
        "band": "2m",
        "district": "6",
        "network": "SK6BA",
        "call": "SK6ABC",
        "city": "Borås",
        "channel": "RV48",
        "output": "145.600",
        "tx_shift": "-0.6",
        "access": "77.0",
        "lat": "57.72",
        "lng": "12.94",
        "locator": "JO67AQ",
    }
    base.update(overrides)
    return base


def channel(**overrides):
    defaults = dict(
        source_id="1",
        type="Repeater",
        status="QRV",
        mode="FM",
        band="2m",
        district="6",
        network="SK6BA",
        city="Borås",
        channel="RV48",
        call="SK6ABC",
        frequency_mhz=145.6,
        duplex="-",
        offset_mhz=0.6,
    )
    defaults.update(overrides)
    return NormalizedChannel(**defaults)


def test_2m_repeater_negative_shift_and_ctcss_normalizes_for_chirp():
    ch = normalize_row(row(tx_shift="-0.6", access="77.0"))

    assert ch is not None
    assert ch.frequency_mhz == 145.6
    assert ch.duplex == "-"
    assert ch.offset_mhz == 0.6
    assert ch.ctcss_hz == 77.0
    assert to_chirp_row(ch, 1)["Tone"] == "Tone"


def test_70cm_repeater_positive_shift_normalizes_plus_offset():
    ch = normalize_row(row(band="70cm", output="434.750", tx_shift="1.6", access=""))

    assert ch is not None
    assert ch.duplex == "+"
    assert ch.offset_mhz == 1.6
    assert ch.ctcss_hz is None


def test_simplex_hotspot_has_no_duplex_or_offset():
    ch = normalize_row(row(type="Hotspot", band="70cm", output="434.550", tx_shift="0", access=""))

    assert ch is not None
    assert ch.duplex == ""
    assert ch.offset_text() == "0"
    assert ch.type == "Hotspot"


def test_link_and_hotspot_are_in_default_filter():
    assert default_analog_fm_row_filter(row(type="Link")) is True
    assert default_analog_fm_row_filter(row(type="Hotspot")) is True


def test_beacon_is_filtered_out_by_default():
    assert default_analog_fm_row_filter(row(type="Beacon")) is False


def test_access_only_1750_sets_burst_without_ctcss():
    ctcss, needs_1750, warnings = parse_ctcss("1750")

    assert ctcss is None
    assert needs_1750 is True
    assert warnings == []


def test_access_1750_and_ctcss_sets_both():
    ctcss, needs_1750, warnings = parse_ctcss("1750 / 77.0")

    assert ctcss == 77.0
    assert needs_1750 is True
    assert warnings == []


def test_access_accepts_decimal_point_and_decimal_comma():
    assert parse_ctcss("77.0")[:2] == (77.0, False)
    assert parse_ctcss("77,0")[:2] == (77.0, False)


def test_fm_dmr_is_included_when_mode_contains_fm():
    assert default_analog_fm_row_filter(row(mode="FM / DMR")) is True


def test_digital_only_mode_is_excluded_from_default_analog_filter():
    assert default_analog_fm_row_filter(row(mode="DMR")) is False


def test_missing_or_invalid_output_is_warned_by_inspection_and_skipped_by_normalizer():
    rows = [row(id="missing", output=""), row(id="invalid", output="not-a-frequency")]
    inspection = inspect_rows(rows, list(rows[0]))

    assert normalize_rows(rows) == []
    assert inspection.warning_counts["missing_output"] == 1
    assert inspection.warning_counts["invalid_output"] == 1


def test_unclear_tx_shift_adds_warning_and_falls_back_to_simplex():
    ch = normalize_row(row(tx_shift="oklar"))

    assert ch is not None
    assert ch.duplex == ""
    assert "invalid_tx_shift" in ch.warnings
    assert validate_channels([ch])["invalid_tx_shift"] == 1


def test_missing_coordinates_during_geosort_warns_but_does_not_crash():
    ch = normalize_row(row(lat="", lng=""))

    sorted_channels = sort_channels([ch], geographic_key="latlon")

    assert sorted_channels == [ch]
    assert "missing_coordinates" in ch.warnings


def test_clipped_name_collisions_get_deterministic_suffixes():
    first = channel(source_id="1", city="LångortsnamnSomKolliderar", call="SK6AAA", frequency_mhz=145.6)
    second = channel(source_id="2", city="LångortsnamnSomKolliderar", call="SK6BBB", frequency_mhz=145.7)

    generate_names([first, second], template="{city}", max_len=10)
    names_once = (first.name, second.name)
    generate_names([first, second], template="{city}", max_len=10)

    assert names_once == (first.name, second.name)
    assert first.name != second.name
    assert len(first.name) == len(second.name) == 10
    assert "-" in first.name and "-" in second.name


def test_swedish_characters_are_transliterated_when_ascii_names_are_requested():
    ch = channel(city="ÅmålÄlmhultÖrebro")

    generate_names([ch], template="{city}", transliterate_swedish=True)

    assert ch.name == "AmalAlmhultOrebr"  # clipped to CHIRP's 16 character default


def test_long_comment_and_callsign_export_without_none_nan_or_empty_junk_parts():
    ch = normalize_row(row(network=None, call=float("nan"), channel="", locator="", access="1750"))

    assert ch is not None
    exported = to_chirp_row(ch, 1)
    assert exported["Comment"] == "1750 Hz"
    assert "None" not in exported["Comment"]
    assert "nan" not in exported["Comment"].casefold()
    assert "||" not in exported["Comment"]


def test_empty_city_field_uses_name_fallbacks():
    assert render_name(channel(city="", call="SK6ABC", channel="RV48"), "{city}") == "SK6ABC"
    assert render_name(channel(city="", call="", channel="RV48"), "{city}") == "RV48"
    assert render_name(channel(city="", call="", channel=""), "{city}") == "NONAME"
