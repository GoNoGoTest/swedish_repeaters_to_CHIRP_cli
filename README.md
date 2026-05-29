# swedish_repeaters_to_CHIRP_cli

`swedish_repeaters_to_CHIRP_cli` är ett litet Python-verktyg som läser en lokal repeaterexport från SK6BA/Marks amatörradioklubb och skapar en CHIRP-kompatibel CSV för analoga FM-kanaler. Målet är att snabbt få in svenska repeatrar, länkar och hotspots i CHIRP:s normala minneskanalflöde utan att handredigera varje rad.

## Avgränsning

Det här projektet gör **endast** en generell CHIRP CSV-export från SK6BA/Marks-exporten.

Det skapar inte och försöker inte ersätta:

- radiofiler eller färdiga radioimages för en specifik radio,
- Nicsure-, Radtel- eller RT-880-specifika exporter,
- DMR-, D-Star- eller C4FM-codepluggar,
- CHIRP:s vanliga arbetsflöde för att läsa från radio, importera CSV, kontrollera minnen och skriva tillbaka till radio.

Använd därför alltid CHIRP enligt programmets normala rekommendationer för just din radio.

## Installation

Projektet använder bara Python-standardbiblioteket och kräver inga externa paket.

1. Klona eller ladda ned projektet.
2. Lägg SK6BA/Marks-exporten som CSV i projektmappen, eller ange sökväg med `--input`.
3. Kör med Python 3:

```bash
python main.py
```

På system där Python 3 heter `python3` kan du i stället köra:

```bash
python3 main.py
```

## Körning

### Interaktivt läge

Om du kör utan argument startar verktyget interaktivt:

```bash
python main.py
```

Du kan även tvinga interaktivt läge:

```bash
python main.py --interactive
```

### Snabbt läge

Snabbt läge använder standardvalen:

- standardfilnamn för input och output om du trycker Enter,
- namntemplate `{district}{city}`,
- ingen geografisk sorteringsnyckel,
- preview med 20 rader,
- bekräftelse innan CSV-filen skrivs.

Det här är läget att börja med om du bara vill skapa en CHIRP CSV och kontrollera resultatet i previewn.

### Avancerat läge

Avancerat läge låter dig välja:

- namntemplate med tokens,
- geografisk sortering: ingen, locator eller latitud/longitud,
- hur många preview-rader som ska visas.

Exempel med avancerade argument utan interaktiv bekräftelse:

```bash
python main.py \
  --input "Example_input_Marks amatörradioklubb export - repeaters.csv" \
  --output chirp_export.csv \
  --name-template "{district}{city}" \
  --geo-sort locator \
  --preview 30 \
  --yes
```

### Icke-interaktiv körning

För script eller upprepade körningar kan du ange input, output och `--yes` direkt:

```bash
python main.py \
  --input "Example_input_Marks amatörradioklubb export - repeaters.csv" \
  --output chirp_export.csv \
  --yes
```

## Input från SK6BA/Marks

Importen läser lokal CSV med UTF-8/BOM-stöd och försöker automatiskt känna igen semikolon eller komma som separator. Decimalvärden kan anges med punkt eller komma, till exempel `145.600` eller `145,600`.

Verktyget förväntar sig SK6BA/Marks-liknande kolumner, bland annat:

- `type`, `status`, `mode`, `band`, `district`, `network`,
- `call`, `city`, `channel`, `output`, `tx_shift`, `access`,
- `lat`, `lng`, `locator`.

Okända kolumner stoppas inte, men räknas i varningsrapporten som `unknown_columns`.

## Defaultfilter

Defaultprofilen exporterar bara rader som matchar alla dessa villkor:

- `status` är `QRV`,
- `type` är `Repeater`, `Link` eller `Hotspot`,
- `mode` innehåller `FM`.

Rader som inte matchar filtreras bort innan normalisering, preview och export.

## CHIRP-export

CSV-filen skrivs med CHIRP-kolumnerna:

`Location`, `Name`, `Frequency`, `Duplex`, `Offset`, `Tone`, `rToneFreq`, `cToneFreq`, `DtcsCode`, `DtcsPolarity`, `Mode`, `TStep`, `Skip`, `Comment`.

### `output` blir CHIRP `Frequency`

Inputkolumnen `output` tolkas som repeaterns eller kanalens utfrekvens i MHz och skrivs till CHIRP-kolumnen `Frequency` med sex decimaler.

Exempel:

- `output=145.600` blir `Frequency=145.600000`.
- `output=434,750` blir `Frequency=434.750000`.

Om `output` saknas eller inte kan tolkas som decimalvärde exporteras inte raden.

### `tx_shift` blir CHIRP `Duplex` och `Offset`

Inputkolumnen `tx_shift` tolkas som sändarskift i MHz:

- positivt värde ger `Duplex=+`,
- negativt värde ger `Duplex=-`,
- tomt, noll eller ogiltigt värde ger simplex, alltså tom `Duplex` och `Offset=0.000000`.

`Offset` skrivs alltid som absolutbeloppet av skiftet med sex decimaler.

Exempel:

- `tx_shift=-0.600` blir `Duplex=-` och `Offset=0.600000`.
- `tx_shift=1.600` blir `Duplex=+` och `Offset=1.600000`.

Om `tx_shift` finns men inte kan tolkas får kanalen varningen `invalid_tx_shift`.

### CTCSS och 1750 Hz

Inputkolumnen `access` används för att hitta CTCSS-toner och eventuell 1750 Hz-öppning.

- CTCSS-värden mellan 60,0 och 260,0 Hz tolkas och avrundas till en decimal.
- Komma och punkt fungerar som decimaltecken.
- Kända standardtoner exporteras som `Tone=Tone`, `rToneFreq=<ton>` och `cToneFreq=<ton>`.
- Om ingen CTCSS hittas lämnas `Tone` tom. CHIRP-kolumnerna `rToneFreq` och `cToneFreq` får då standardvärdet `88.5`, men används inte eftersom `Tone` är tom.
- Om `access` innehåller `1750` läggs `1750 Hz` i kommentaren. Det blir ingen särskild CHIRP-toninställning, eftersom 1750 Hz normalt hanteras som manuell anrops-/burstton i radion.
- En CTCSS-ton som inte finns i den inbyggda standardlistan exporteras ändå, men får varningen `unusual_ctcss`.
- Oklara accessfält som inte går att tolka får varningen `unparsed_access`.

## Kanalnamn

Kanalnamn byggs med en namntemplate. Standard är:

```text
{district}{city}
```

Följande tokens stöds:

- `{type}`
- `{network}`
- `{band}`
- `{district}`
- `{city}`
- `{channel}`
- `{call}`

För `{city}` används fallback i ordningen `city`, `call`, `channel`, `NONAME`.

Efter att namnet har renderats:

1. tas whitespace bort,
2. otillåtna tecken tas bort,
3. namnet klipps till CHIRP-längden 16 tecken,
4. kollisioner hanteras deterministiskt med suffix baserat på kanalens id, anropssignal, kanal och frekvens.

Som standard behåller CLI-läget svenska tecken `ÅÄÖåäö` om de finns i källan. Namngeneratorn har även stöd för translitterering av svenska tecken till `A`, `A`, `O`, `a`, `a`, `o` när den används programmässigt med translitterering aktiverad.

Om två kanaler får samma klippta basnamn läggs ett stabilt suffix till, till exempel:

```text
SKaraborgABC
SKaraborg-1A2
```

Suffixet är deterministiskt, så samma input bör ge samma namn vid nästa körning.

## Preview och varningsrapport

Varje körning skriver först en inputinspektion, sedan validering/varningar och därefter en preview.

### Inputinspektion

Inputinspektionen visar:

- antal lästa rader,
- hittade kolumner,
- unika värden för viktiga filterkolumner,
- varningsräkningar från råfilen.

Vanliga råvarningar:

- `missing_output` – rader där `output` saknas,
- `invalid_output` – rader där `output` inte kan tolkas som decimal,
- `missing_status` – rader utan status,
- `missing_mode` – rader utan mode,
- `missing_coordinates` – rader där `lat` eller `lng` saknas,
- `unknown_columns` – kolumner som inte finns i den förväntade SK6BA/Marks-strukturen.

### Validering/varningar

Valideringen gäller de kanaler som återstår efter defaultfiltret och normaliseringen. Om allt ser bra ut visas:

```text
Validering: inga varningar.
```

Annars visas antal per varning, till exempel `invalid_tx_shift`, `invalid_lat`, `invalid_lng`, `unusual_ctcss` eller `unparsed_access`.

### Preview

Preview-tabellen visar ett urval av de kanaler som kommer att exporteras:

- `Name` – CHIRP-kanalnamnet efter namngenerering,
- `Freq` – utfrekvensen från `output`,
- `Dup` – `+`, `-` eller tomt duplexfält,
- `Off` – offset i MHz,
- `Tone` – CTCSS-ton eller `1750` om endast 1750 Hz hittades,
- `Ort` – ort från input,
- `Kommentar` – nät, anropssignal/kanal, locator, 1750 Hz och eventuella kanalvarningar.

Previewn är en kontrollvy. Det är fortfarande CSV-filen som ska importeras i CHIRP.

## Import i CHIRP

Ett säkert grundflöde i CHIRP är normalt:

1. Starta CHIRP.
2. Läs först från din radio och spara en backup av originalfilen.
3. Öppna den radiofil eller image som ska uppdateras.
4. Importera CSV-filen som skapats av verktyget via CHIRP:s importfunktion för CSV.
5. Kontrollera minneskanalerna i CHIRP, särskilt frekvens, duplex, offset och toner.
6. Justera eventuella radio- eller modellberoende inställningar manuellt.
7. Skriv till radion enligt CHIRP:s normala arbetsflöde för din modell.

Verktyget skapar alltså bara importunderlaget. CHIRP ansvarar för radioformatet och kommunikationen med radion.

## Felsökning

### Saknade kolumner

Om previewn blir tom eller varningsrapporten ser konstig ut, kontrollera att inputfilen verkligen är en SK6BA/Marks-export och att kolumnnamnen motsvarar de förväntade namnen. Särskilt viktiga kolumner är `status`, `type`, `mode`, `output`, `tx_shift` och `access`.

`unknown_columns` betyder inte automatiskt fel, men kan tyda på att exportformatet har ändrats.

### Okända decimalformat

Decimaler med punkt och komma stöds, men andra format kan misslyckas. Exempel på stödda värden:

- `145.600`
- `145,600`
- `-0.600`
- `-0,600`

Undvik enheter, extra text eller ovanliga tusentalsseparatorer i numeriska fält.

### Saknad outputfrekvens

Rader utan tolkbar `output` kan inte bli CHIRP-kanaler och hoppas över. Kontrollera `missing_output` och `invalid_output` i inputinspektionen om antalet exporterade kanaler är lägre än väntat.

### Oklara toner

Om `access` innehåller fri text eller ett tonformat som inte känns igen kan du få `unparsed_access`. Kontrollera då repeaterinformationen manuellt och justera tonen i CHIRP efter import om det behövs.

`unusual_ctcss` betyder att ett numeriskt CTCSS-värde hittades men inte finns i den inbyggda standardlistan. Värdet exporteras ändå, men bör kontrolleras.

### Inga kanaler exporteras

Om körningen slutar med `Inga kanaler att exportera.` beror det oftast på något av följande:

- inga rader matchar defaultfiltret `QRV` + `Repeater`/`Link`/`Hotspot` + `FM`,
- `output` saknas eller har fel format på matchande rader,
- inputfilen har andra kolumnnamn än förväntat.

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
