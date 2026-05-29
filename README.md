# swedish_repeaters_to_CHIRP_cli

Första Python-version av en CLI som läser lokal SK6BA/Marks-export och skapar en CHIRP-kompatibel CSV för analoga FM-kanaler.

## Modulstruktur

- `main.py` – interaktivt snabb-/avancerat läge samt argumentbaserad körning.
- `importers/sk6ba.py` – CSV-läsning, BOM/UTF-8, separatoridentifiering och inputinspektion.
- `models.py` – `InputInspection` och `NormalizedChannel`.
- `filters.py` – defaultfilter för analog FM och normalisering.
- `tones.py` – CTCSS/1750 Hz-tolkning.
- `naming.py` – tokenbaserad namngenerering och deterministisk kollisionshantering.
- `sorting.py` – sortering efter distrikt, valfri geografisk nyckel, typ, ort och frekvens.
- `exporters/chirp.py` – CHIRP CSV-export.
- `preview.py` – inputinspektion och preview-tabell.
- `validation.py` – enkel validering/varningsräkning.

## Exempel

Interaktivt läge med numrerade menyer och Enter-defaults:

```bash
python3 main.py --interactive
```

Icke-interaktiv körning mot exempelfilen:

```bash
python3 main.py \
  --input "Example_input_Marks amatörradioklubb export - repeaters.csv" \
  --output chirp_export.csv \
  --yes
```

Avancerade val via argument:

```bash
python3 main.py \
  --input "Example_input_Marks amatörradioklubb export - repeaters.csv" \
  --output chirp_export.csv \
  --name-template "{district}{city}" \
  --geo-sort locator \
  --preview 30 \
  --yes
```

Namntemplate stöder tokens: `{type}`, `{network}`, `{band}`, `{district}`, `{city}`, `{channel}`, `{call}`. Namn klipps till 16 tecken för CHIRP och kollisioner får deterministiska suffix.

## Defaultfilter

Defaultprofilen exporterar analog FM där:

- `status=QRV`
- `type` är `Repeater`, `Link` eller `Hotspot`
- `mode` innehåller `FM`

## CHIRP-kolumner

Exporten innehåller minst:

`Location`, `Name`, `Frequency`, `Duplex`, `Offset`, `Tone`, `rToneFreq`, `cToneFreq`, `DtcsCode`, `DtcsPolarity`, `Mode`, `TStep`, `Skip`, `Comment`.
