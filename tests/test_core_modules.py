import pytest

from exporters.chirp import to_chirp_row
from filters import default_analog_fm_row_filter, normalize_row, normalize_rows
from importers.channelpacks import (
    ChannelPackError,
    filter_channelpack_rows,
    load_channelpacks,
    merge_channels,
    parse_channelpack_row,
    rows_to_channels,
    split_tags,
)
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
    ch = normalize_row(
        row(type="Hotspot", band="70cm", output="434.550", tx_shift="0", access="")
    )

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
    first = channel(
        source_id="1",
        city="LångortsnamnSomKolliderar",
        call="SK6AAA",
        frequency_mhz=145.6,
    )
    second = channel(
        source_id="2",
        city="LångortsnamnSomKolliderar",
        call="SK6BBB",
        frequency_mhz=145.7,
    )

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
    ch = normalize_row(
        row(network=None, call=float("nan"), channel="", locator="", access="1750")
    )

    assert ch is not None
    exported = to_chirp_row(ch, 1)
    assert exported["Comment"] == "1750 Hz"
    assert "None" not in exported["Comment"]
    assert "nan" not in exported["Comment"].casefold()
    assert "||" not in exported["Comment"]


def test_empty_city_field_uses_name_fallbacks():
    assert (
        render_name(channel(city="", call="SK6ABC", channel="RV48"), "{city}")
        == "SK6ABC"
    )
    assert render_name(channel(city="", call="", channel="RV48"), "{city}") == "RV48"
    assert render_name(channel(city="", call="", channel=""), "{city}") == "NONAME"


def channelpack_row(**overrides):
    base = {
        "pack_id": "test_pack",
        "source_id": "aprs",
        "enabled_default": "true",
        "service": "amateur",
        "band": "2m",
        "category": "aprs",
        "tags": "packet|aprs",
        "type": "Static",
        "label": "APRS",
        "channel": "",
        "name_hint": "APRS",
        "rx_frequency": "144.800000",
        "tx_frequency": "144.800000",
        "duplex": "",
        "offset": "0.000000",
        "mode": "NFM",
        "tstep": "5.0",
        "tone": "",
        "rtone_freq": "",
        "ctone_freq": "",
        "dtcs_code": "",
        "dtcs_polarity": "",
        "skip": "",
        "tx_allowed": "true",
        "rx_only": "false",
        "license_note": "Cert krävs",
        "comment": "APRS simplex",
        "source": "bandplan",
        "source_url": "https://example.test",
        "inferred_from_range": "false",
    }
    base.update(overrides)
    return base


def test_channelpack_tags_are_split_on_pipe():
    assert split_tags("packet|aprs | data") == ["packet", "aprs", "data"]


def test_channelpack_bool_values_are_strict():
    with pytest.raises(ChannelPackError):
        parse_channelpack_row(channelpack_row(enabled_default="maybe"))


def test_channelpack_missing_noncritical_columns_get_defaults():
    row = channelpack_row()
    del row["mode"]
    parsed = parse_channelpack_row(row)

    assert parsed.mode == "FM"
    assert parsed.enabled_default is True


def test_channelpack_rows_convert_to_chirp_export_fields():
    parsed = parse_channelpack_row(
        channelpack_row(mode="NFM", tstep="12.5", dtcs_code="047", dtcs_polarity="RN")
    )
    ch = rows_to_channels([parsed])[0]
    exported = to_chirp_row(ch, 1)

    assert ch.name == "APRS"
    assert exported["Mode"] == "NFM"
    assert exported["TStep"] == "12.5"
    assert exported["DtcsCode"] == "047"
    assert exported["DtcsPolarity"] == "RN"


def test_sk6ba_rows_have_explicit_source_type():
    ch = normalize_row(row())

    assert ch is not None
    assert ch.source_type == "sk6ba"


def test_channelpack_rows_map_metadata_without_sk6ba_repeater_logic():
    parsed = parse_channelpack_row(
        channelpack_row(
            source_id="packet-1",
            tags="packet|aprs",
            tx_frequency="145.500000",
            offset="-0.600000",
            tone="Tone",
            rtone_freq="77.0",
            tx_allowed="false",
            rx_only="true",
            inferred_from_range="true",
        )
    )
    ch = rows_to_channels([parsed])[0]

    assert ch.source_type == "channel_pack"
    assert ch.source_id == "packet-1"
    assert ch.pack_id == "test_pack"
    assert ch.service == "amateur"
    assert ch.category == "aprs"
    assert ch.tags == ["packet", "aprs"]
    assert ch.label == "APRS"
    assert ch.name_hint == "APRS"
    assert ch.tx_frequency_mhz == 145.5
    assert ch.tstep == "5.0"
    assert ch.tx_allowed is False
    assert ch.rx_only is True
    assert ch.license_note == "Cert krävs"
    assert ch.source == "bandplan"
    assert ch.source_url == "https://example.test"
    assert ch.inferred_from_range is True
    assert ch.ctcss_hz is None
    assert ch.warnings == []
    assert ch.offset_mhz == 0.6


def test_filter_channelpack_rows_supports_default_band_category_and_tags():
    aprs = parse_channelpack_row(channelpack_row())
    voice = parse_channelpack_row(
        channelpack_row(
            source_id="voice",
            enabled_default="false",
            category="voice",
            tags="fm_simplex",
        )
    )

    assert filter_channelpack_rows([aprs, voice], enabled_default_only=True) == [aprs]
    assert filter_channelpack_rows(
        [aprs, voice], bands={"2m"}, categories={"aprs"}, tags={"packet"}
    ) == [aprs]


def test_merge_channelpacks_supports_beginning_end_and_same_sorting():
    repeater = channel(source_id="r", district="6", city="Borås", frequency_mhz=145.6)
    static = rows_to_channels([parse_channelpack_row(channelpack_row())])[0]

    assert merge_channels([repeater], [static], "beginning") == [static, repeater]
    assert merge_channels([repeater], [static], "end") == [repeater, static]
    assert merge_channels([repeater], [static], "same_sorting") == [repeater, static]


def test_load_channelpacks_finds_repository_csv_files():
    packs = load_channelpacks("channelpacks")

    assert len(packs) >= 2
    assert sum(len(pack.rows) for pack in packs) > 0


def test_sort_channels_handles_static_rows_without_location_metadata():
    static = type("StaticOnly", (), {"type": "Static", "frequency_mhz": 144.8})()

    assert sort_channels([static]) == [static]


def test_channelpack_name_tokens_and_fallbacks_avoid_empty_separators():
    ch = channel(
        source_type="channel_pack",
        source_id="src1",
        service="amateur",
        category="",
        district="",
        label="Label",
        channel="CH1",
        name_hint="Hint",
        type="Static",
        band="2m",
        city="",
        call="",
    )

    assert render_name(ch, "{service}-{category}-{name_hint}") == "amateur-Hint"
    assert render_name(ch, "{district}/{city}/{category}") == "Hint"


def test_chirp_export_rx_only_policies_and_split_fields():
    ch = channel(
        source_type="channel_pack",
        source_id="rx",
        frequency_mhz=145.5,
        tx_frequency_mhz=144.9,
        duplex="split",
        rx_only=True,
        tx_allowed=False,
        mode="NFM",
        tstep="12.5",
        skip="P",
        license_note="RX only enligt bandplan",
        comment="Lyssna",
    )

    with pytest.raises(ValueError):
        to_chirp_row(ch, 1)

    marked = to_chirp_row(ch, 1, rx_only_policy="mark_rx_only")
    assert marked is not None
    assert marked["Duplex"] == "split"
    assert marked["Offset"] == "144.900000"
    assert marked["Mode"] == "NFM"
    assert marked["TStep"] == "12.5"
    assert marked["Skip"] == "P"
    assert marked["Comment"] == "Lyssna | RX only enligt bandplan | RX-only"

    disabled = to_chirp_row(ch, 1, rx_only_policy="duplex_off")
    assert disabled is not None
    assert disabled["Duplex"] == "off"
    assert disabled["Offset"] == "0.000000"
    assert to_chirp_row(ch, 1, rx_only_policy="skip") is None


def test_validation_finds_channelpack_issues_and_frequency_duplicates():
    from validation import (
        find_frequency_duplicates,
        validate_channelpack_header,
        validate_channelpack_raw_rows,
    )

    repeater = channel(source_id="sk", frequency_mhz=145.5)
    pack = channel(
        source_type="channel_pack",
        source_id="pack1",
        pack_id="",
        frequency_mhz=145.5,
        label="",
        channel="",
        name_hint="",
        rx_only=True,
    )
    other_pack = channel(
        source_type="channel_pack",
        source_id="pack2",
        pack_id="pack",
        frequency_mhz=145.5,
        label="L",
        name_hint="N",
    )

    counts = validate_channels([repeater, pack, other_pack])
    assert counts["missing_pack_id"] == 1
    assert counts["missing_label"] == 1
    assert counts["missing_channel"] == 1
    assert counts["missing_name_hint"] == 1
    assert counts["rx_only_without_policy"] == 1
    assert counts["frequency_duplicate"] == 1
    assert counts["frequency_duplicate_sk6ba_channel_pack"] == 1
    assert counts["frequency_duplicate_channel_pack"] == 1

    duplicates = find_frequency_duplicates([repeater, pack, other_pack])
    assert duplicates[0]["frequency"] == 145.5
    assert duplicates[0]["source_types"] == ["channel_pack", "sk6ba"]
    assert duplicates[0]["source_ids"] == ["sk", "pack1", "pack2"]

    assert (
        validate_channelpack_header(["pack_id", "source_id"])["missing_header_column"]
        > 1
    )
    raw_counts = validate_channelpack_raw_rows(
        [
            {
                "pack_id": "",
                "source_id": "dup",
                "rx_frequency": "bad",
                "enabled_default": "maybe",
            },
            {"pack_id": "p", "source_id": "dup", "rx_frequency": "145.5"},
        ]
    )
    assert raw_counts["duplicate_source_id"] == 1
    assert raw_counts["missing_or_invalid_rx_frequency"] == 1
    assert raw_counts["invalid_boolean_enabled_default"] == 1
