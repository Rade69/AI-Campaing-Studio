---
task_id: ACS-F1-042
phase: P1.5-G3 dio 1 -- CSV Import (Faza 1 v1.5 §18, Faza 0.7 §12-14)
title: "CSV performance import: kolona-mapping + row parsing/validation engine (čist, bez I/O, bez matching-a)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies: [ACS-F1-038]
allowed_paths:
  - src/ai_campaign_studio/application/performance/
  - resources/performance_import/
  - tests/unit/application/performance/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - resources/migrations/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/visual/
  - src/ai_campaign_studio/application/rendering/
  - src/ai_campaign_studio/application/export/
  - src/ai_campaign_studio/application/evaluation/
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Potpuno nov, izolovan podpaket (`application/performance/`) sa
    nula postojećih pozivalaca -- ništa u repou danas uvozi ovaj
    modul. Čista logika, bez I/O (ni fajl, ni baza, ni mreža), bez
    DistributionInstance matching-a (to je dio 2 / G4). GitNexus
    impact nije potreban.
---

# Kontekst

Ovo je **PRVI od najmanje dva dijela** za P1.5-G3 CSV Import (Faza 1
v1.5 §18: `ImportPerformanceCsv` / `PreviewPerformanceMapping` /
`ConfirmPerformanceImport`), po istom obrascu kao ranije podijeljeni
taskovi (A13 dio 1/2/2b, Slice 1.5 G1→G2→G3 za DistributionInstance
samo).

**Zašto podjela.** Pun G3 obuhvata: (a) parsiranje CSV fajla i
prepoznavanje kolona, (b) validaciju redova, (c) matching uvezenih
redova na `DistributionInstance` (traži baza pristup + odluku o
prioritetu ključeva), (d) tri use-case-a orkestrisana oko toga, (e)
novu perzistenciju (`PerformanceImportRow` tabela). Raditi sve
odjednom bi bio prevelik, teško pregledljiv task. Ovaj dio (dio 1) je
NAMJERNO ograničen na čist, testabilan engine BEZ ikakvog I/O (nema
otvaranja fajla, nema baze) -- isti princip kao P1.5-G1 (čist domain
prije P1.5-G2 perzistencije).

**Scope odluka koju review MORA potvrditi (nije trivijalna, spec je
tanak).** Faza 1 v1.5 §18 kaže samo: korisnik mora vidjeti
`matched`/`unmatched`/`ambiguous`/`invalid`, ništa se ne smije tiho
izgubiti. Faza 0.7 §14 (Matching) je EKSPLICITNO odvojen odjeljak
(P1.5-G4, sljedeći gate, ne ovaj) sa prioritetom `external_content_id →
analytics_match_key → stable IDs → manual`. Ovaj kontrakt tumači
podjelu ovako:

- **Kolona-mapping** (ovaj dio 1): da li je CSV header uspješno
  prepoznat kao poznato kanonsko polje (`matched`), da li header
  odgovara VIŠE kanonskih polja odjednom (`ambiguous`), ili da li
  ostane neprepoznat (`unmatched`). Ovo su POLJA, ne redovi sadržaja.
- **Row validacija** (ovaj dio 1): da li mapirani red ima sve
  OBAVEZNE vrijednosti i da li su tipski ispravne (`invalid` ako ne).
- **Matching na `DistributionInstance`** (NIJE ovaj dio -- dio 2 /
  G4): traži pristup bazi i odluku o prioritetu ključeva, van scope-a
  ove čiste faze.

Dio 1 dakle NE proizvodi `matched`/`unmatched`/`ambiguous` u smislu
"da li red odgovara postojećem sadržaju" -- to dolazi u dio 2. Dio 1
proizvodi mapping-status PO KOLONI (`matched`/`ambiguous`/`unmatched`
kanonsko polje) i validity PO REDU (`valid`/`invalid`). Ovo je
namjerna, dokumentovana interpretacija -- reviewer treba eksplicitno
potvrditi da ima smisla prije nego što dio 2 (koji dodaje pravi
DistributionInstance matching) krene.

**Referenca korisnikovog `deklarant_pro` projekta** (dat kao primjer
2026-09-05): `COLUMN_MAP` dict koji mapira kanonsko polje → listu
mogućih naziva header-a (case-insensitive, višejezično), i
`ImportResult.validate() -> (ok, errors, warnings)` obrazac (parsiranje
odvojeno od validacije). Ovaj task prati isti duh, ALI pravila idu u
YAML resurs (`resources/performance_import/`), ne hardkodovana u
Python-u -- isti obrazac kao `claim_linter.py` +
`resources/claim_rules/default_v1.yaml` (A12 dio 1).

**CSV-only, ne CSV+Excel.** Faza 0.7 §12 pominje "CSV / Excel" kao
opcije, ne oboje odmah. Excel (.xlsx) zahtijeva novu eksternu
zavisnost (`openpyxl` ili slično) koju stdlib nema; CSV ne zahtijeva
NIŠTA (stdlib `csv` modul). Ovaj task je **CSV-only preko stdlib
`csv`**, bez ijedne nove zavisnosti. Excel podrška je eksplicitno
ODGOĐENA -- dodaje se kasnije kao nov format-parser, bez potrebe da
se ovaj engine redizajnira (mapping/validation logika radi na već
pročitanim `dict[str, str]` redovima, ne na sirovim bajtovima fajla,
pa je format file-parsing sloj potpuno odvojen i zamjenjiv).

# Objective

## 1. `resources/performance_import/column_aliases_v1.yaml`

Data-driven mapping kanonsko polje → lista alias header naziva
(case-insensitive poređenje, EN + BHS termini). Kanonska polja:

```text
platform_code
external_content_id
analytics_match_key
period_start
period_end
reach
impressions
engagements
clicks
conversions
spend
revenue
video_views
watch_time_seconds
```

(devet metrika + platform_code/external_content_id/analytics_match_key
+ period_start/period_end -- period_start/period_end su OBAVEZNI za
`MetricPeriod`, ostala metrička polja su OPCIONA pojedinačno, ali BAR
JEDNA metrika mora biti prisutna po redu da red ima smisla -- ako
implementer nađe da spec (Faza 0.7 §5/§6, `CanonicalMetricSet`) kaže
drugačije, prati POSTOJEĆI `CanonicalMetricSet`/`MetricPeriod` domain
model kao izvor istine, ne ovaj popis).

Format YAML: slično `resources/claim_rules/default_v1.yaml` -- top-level
`version: "1"` + dict `column_aliases: {canonical_field: [alias, ...]}`.

## 2. `application/performance/column_mapping.py`

- `load_column_aliases(path: Path | None = None) -> ColumnAliasRules`
  (default path -- isti obrazac kao `claim_linter.py`'s YAML loading;
  vraća i `version` string za `mapping_version`).
- `@dataclass(frozen=True) class ColumnMatch`: `canonical_field: str`,
  `header: str | None` (None ako unmatched), `status: Literal["matched",
  "ambiguous", "unmatched"]`, `candidates: tuple[str, ...]` (za
  ambiguous -- koji header-i su svi odgovarali).
- `map_columns(headers: tuple[str, ...], rules: ColumnAliasRules) ->
  tuple[ColumnMatch, ...]` -- za SVAKO kanonsko polje iz pravila,
  jedan `ColumnMatch`. Deterministički (isti headers -> isti redoslijed
  i rezultat).
- Ambiguous pravilo (implementer definiše precizno, dokumentovati u
  docstring-u): npr. ako VIŠE header-a iz CSV-a odgovara ISTOM
  kanonskom polju (dva header-a oba aliasi za "spend").

## 3. `application/performance/row_parsing.py`

- `@dataclass(frozen=True) class ParsedRow`: `row_number: int`
  (1-based, header red = red 0), `raw_values: dict[str, str]`
  (nepromijenjene originalne vrijednosti, ključ = originalni header
  tekst -- ništa se ne gubi), `mapped_values: dict[str, str]`
  (kanonsko_polje -> string vrijednost, samo za MATCHED kolone),
  `errors: tuple[str, ...]` (prazno = validan red).
- `parse_rows(raw_rows: tuple[dict[str, str], ...], column_matches:
  tuple[ColumnMatch, ...]) -> tuple[ParsedRow, ...]` -- čista funkcija,
  NE otvara fajl (poziva se sa VEĆ pročitanim redovima, npr. iz
  `csv.DictReader`).
- Validacija po redu: `period_start`/`period_end` moraju parsirati kao
  ISO datum (ili format koji implementer odabere i DOKUMENTUJE --
  konzistentno sa `MetricPeriod.__post_init__` iz `domain/performance/
  metrics.py`, koji zahtijeva `end >= start`); bar jedna numerička
  metrika mora biti prisutna i parsirati kao broj (negativan broj =
  invalid -- metrike ne mogu biti negativne, provjeriti da li
  `CanonicalMetricSet` to već implicira). Svaka greška ide kao
  čitljiva poruka u `errors` (npr. `"period_end (2026-13-40) is not a
  valid date"`), red ostaje u rezultatu (NIKAD se tiho ne izbacuje --
  poziva se ConfirmPerformanceImport dio 2 da odluči šta s invalid
  redovima, ovaj engine samo javlja).

# Implementation steps

1. `resources/performance_import/column_aliases_v1.yaml` (Objective #1).
2. `application/performance/column_mapping.py` (Objective #2) + testovi:
   sve-matched slučaj, ambiguous slučaj (dva headera isto polje),
   unmatched slučaj (header koji ne odgovara ničemu -- NE smije se
   tretirati kao greška, samo ignorisati kao "extra column", pošto CSV
   može imati kolone koje aplikacija ne koristi), case-insensitivity
   dokaz (header "SPEND" i "spend" oba rade), BHS alias dokaz (bar
   jedan bosanski/srpski/hrvatski termin po metrici gdje ima smisla,
   npr. "trošak"/"potrošnja" za spend, "prikazi"/"impresije" za
   impressions -- implementer bira razumne termine).
3. `application/performance/row_parsing.py` (Objective #3) + testovi:
   validan red, red sa nedostajućom obaveznom vrijednosti, red sa
   tekstom umjesto broja, red sa nevalidnim datumom, red gdje
   `period_end < period_start`, red sa NEGATIVNOM metrikom (ako
   `CanonicalMetricSet` to zabranjuje), red koji ima SAMO extra/nepoznate
   kolone (nijedna mapirana metrika) -- treba biti invalid sa jasnom
   porukom, ne tiho prazan red.
4. Dokaz da je `mapped_values` iz `ParsedRow` DOVOLJAN da se kasnije (u
   dio 2, koji ovaj task NE implementira) konstruiše
   `CanonicalMetricSet`/`MetricPeriod` -- napisati bar jedan test koji
   RUČNO konstruiše `CanonicalMetricSet(**relevant subset)` iz
   `parsed_row.mapped_values` da dokaže da su nazivi/tipovi kompatibilni
   (ne treba pravi use-case, samo dokaz o shape-kompatibilnosti).

# Acceptance

- [ ] `column_aliases_v1.yaml` postoji, sadrži sve nabrojana kanonska
      polja sa razumnim EN+BHS aliasima.
- [ ] `map_columns` vraća `matched`/`ambiguous`/`unmatched` po
      kanonskom polju, deterministički, case-insensitive.
- [ ] `parse_rows` vraća `ParsedRow` po redu sa `errors` (prazno =
      valid) -- NIJEDAN red se ne izbacuje tiho, čak ni invalid.
- [ ] `raw_values` čuva SVE originalne vrijednosti (nema gubitka
      podataka čak i za nemapirane kolone).
- [ ] Nema I/O u ovom kodu (nema `open()`, nema baze) -- čiste funkcije
      nad već-pročitanim podacima.
- [ ] Nema nove eksterne zavisnosti (samo stdlib + postojeći `PyYAML`).
- [ ] `python -m pytest tests/unit/application/performance/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a** (push grane sam po sebi NE pokreće
      CI -- `ci.yml` sluša samo `push:[main]`/`pull_request:[main]`,
      obavezno otvoriti PR).

# Verification

```bash
python -m pytest tests/unit/application/performance/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-042-csv-column-mapping
gh pr create --base main --title "ACS-F1-042: CSV column-mapping + row parsing engine"
gh pr checks
```

# Review focus -- Claude

- Ambiguous-kolona pravilo je STVARNO testirano (dva header-a → isto
  polje → `ambiguous`, ne tiho uzeti prvi).
- Invalid-red slučajevi STVARNO pokrivaju sve navedene kategorije
  (nedostajuće polje, tekst umjesto broja, loš datum, `end < start`,
  negativna metrika, samo-extra-kolone red) -- ne samo jedan sretan
  test.
- `raw_values` STVARNO nema gubitka -- test koji provjerava da
  nemapirana/extra kolona i dalje postoji u `raw_values`.
- Scope granica (kolona/red validacija OVDJE, DistributionInstance
  matching NIJE OVDJE) je ISPOŠTOVANA -- nema nikakvog poziva ka
  repozitorijumu ili domain entity-ju van `application/performance/`.
- YAML pravila su STVARNO data-driven (izmjena YAML-a mijenja
  ponašanje bez izmjene Python koda -- test dokaz, isti standard kao
  `claim_linter.py`).

# Rollback

MEDIUM risk (nov podsistem, ali potpuno izolovan -- nula postojećih
pozivalaca, nula I/O). Lako se revertuje ili prepravlja bez uticaja na
ostatak sistema.

# Coordination

Zavisi od ACS-F1-038 (mergovano, `CanonicalMetricSet`/`MetricPeriod`
postoje). **Blokira dio 2** (persistencija + tri use-case-a +
DistributionInstance matching) -- taj kontrakt se piše NAKON što ovaj
prođe review, po istom "napiši sljedeći dio kad prethodni prođe"
obrascu kao A13.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-042-csv-column-mapping
Branch:   task/ACS-F1-042-csv-column-mapping
Base:     main @ 83b4845
```
