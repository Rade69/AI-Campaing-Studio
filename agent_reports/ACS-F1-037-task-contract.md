---
task_id: ACS-F1-037
phase: Slice 1.5 — P1.5-G1 Performance Domain (Faza 1 v1.5 §15-16)
title: "Performance domain modeli: DistributionInstance, PerformanceSnapshot, PerformanceImportBatch, CanonicalMetricSet, MetricPeriod, PerformanceSource (domain-only, bez perzistencije)"
risk: LOW
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: [ACS-F1-036]
allowed_paths:
  - src/ai_campaign_studio/domain/performance/__init__.py
  - src/ai_campaign_studio/domain/performance/enums.py
  - src/ai_campaign_studio/domain/performance/metrics.py
  - src/ai_campaign_studio/domain/performance/entities.py
  - src/ai_campaign_studio/domain/common/ids.py
  - tests/unit/domain/performance/test_enums.py
  - tests/unit/domain/performance/test_metrics.py
  - tests/unit/domain/performance/test_entities.py
forbidden_paths:
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/domain/visual/
  - src/ai_campaign_studio/domain/analytics/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/application/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Per `.agent/TASK_ROUTING.md` sekcija "Performance / Analytics task"
    — GitNexus je OBAVEZAN za SVAKI Slice 1.5 task, bez izuzetka. Ovo
    je čisto NOVI kod (nov `domain/performance/` paket, nema izmjene
    postojećih fajlova osim tri aditivne linije u `domain/common/ids.py`)
    — nula postojećih pozivalaca do sad, pa je impact provjera
    formalnost, ali se i dalje pokreće (koordinator prije merge-a,
    GitNexus MCP dostupan, indeks stale — re-index prije provjere).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: e970697
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

**P1.5-G1** (Faza 1 v1.5 §16) — prvi pravi Slice 1.5 gate. Ovo je ČISTO
domain-nivo task: definisati POJMOVE (Python dataclass/enum definicije,
bez SQL-a, bez fajlova, bez mreže) koje će P1.5-G2 (Persistence, sljedeći
task — migracija `0004_performance_foundation.sql`, tabele
`distribution_instances`/`performance_snapshots`/`performance_import_batches`/
`performance_import_rows`) tek onda dati mjesto u bazi.

`ACS-F1-036` (mergovano) je već zaključao `analytics_match_key` — ovaj
task ga NE dira, samo definiše entitete koji će GA KASNIJE koristiti
(P1.5-G3/G4, budući taskovi) za matching.

**Modeli tačno po Faza 0.7 §3, §5, §6, §13 i Faza 1 v1.5 §16** (nijedan
izmišljen, nijedan izostavljen):

- `DistributionInstance` (Faza 0.7 §3) — "konkretan sadržaj, u konkretnoj
  verziji, poslat/objavljen na konkretnom kanalu/platformi/formatu."
- `PerformanceSnapshot` (Faza 0.7 §5) — metrika u jednom periodu, VEZANA
  za `DistributionInstance` (NE direktno za `ContentPiece` — kritično
  pravilo, Faza 0.7 §4: "Ako korisnik nakon objave promijeni caption, ne
  smijemo pripisati stare rezultate novoj verziji sadržaja").
- `PerformanceImportBatch` (Faza 0.7 §13) — jedan uvoz podataka
  (CSV/API/ručan), sa brojem redova/uparenih/neuparenih — "Svaki import
  mora biti provjerljiv. Ne raditi silent matching bez evidence."
- `CanonicalMetricSet` — grupisanih 9 platform-neutralnih metrika (Faza
  0.7 §6: "COMMON CANONICAL METRICS" — `reach, impressions, engagements,
  clicks, conversions, spend, revenue, video_views, watch_time_seconds`),
  SVE opciona (ne podržavaju sve platforme iste metrike).
- `MetricPeriod` — period_start/period_end kao jedan value object (umjesto
  dva razdvojena polja na `PerformanceSnapshot`).
- `PerformanceSource` — enum za ODAKLE dolaze PERFORMANCE PODACI
  (`CSV_IMPORT`, `MANUAL`, `API`) — **NAMJERNO ODVOJEN enum od
  `DistributionSource`** (ODAKLE dolazi sama DISTRIBUCIJA sadržaja —
  `EXPORT`, `MANUAL`, `CSV_IMPORT`, `API`, Faza 0.7 §3). Ova dva enuma
  dijele DIO vokabulara (`MANUAL`/`CSV_IMPORT`/`API`) ali NISU isti tip
  — `DistributionSource` ima i `EXPORT` (sadržaj IZLAZI iz sistema),
  što nema smisla za performance podatke (metrika UVIJEK ULAZI, nikad
  "izlazi preko exporta"). Implementer NE smije ih spojiti u jedan enum.

**Namjerno IZOSTAVLJENO iz ovog taska** (eksplicitno zabranjeno per Faza
1 v1.5 §7 i §16 "Ne implementirati provider API adaptere"):
`PerformanceSourcePort`, bilo koji konkretan adapter
(Meta/TikTok/LinkedIn/CSV), migracija/perzistencija (P1.5-G2), metric
calculator (P1.5-G5), CSV import use-case (P1.5-G3).

**Poznata manja nedosljednost između planskih dokumenata** (NIJE greška
ovog taska, samo transparentno zabilježena): plan §19 "P1.5-G3 CSV
Import" spominje 4 kategorije ("matched, unmatched, ambiguous, invalid")
ali Faza 0.7 §13 model `PerformanceImportBatch` ima SAMO
`matched_count`/`unmatched_count` (2 polja). Ovaj task implementira
TAČNO ono što Faza 0.7 §13 doslovno navodi (2 polja) — dodatna
"ambiguous"/"invalid" granularnost je pitanje za P1.5-G3 (implementer
TOG budućeg taska odlučuje da li proširiti model ili agregirati ih u
`unmatched_count`).

# Objective

## 1. `domain/common/ids.py` — tri nova ID tipa (aditivno)

```python
DistributionInstanceId = NewType("DistributionInstanceId", str)
PerformanceSnapshotId = NewType("PerformanceSnapshotId", str)
PerformanceImportBatchId = NewType("PerformanceImportBatchId", str)
```

Isti stil, isto mjesto (odmah nakon postojećih ID tipova), NULA izmjena
postojećih linija.

## 2. `domain/performance/enums.py`

```python
class DistributionSource(StrEnum):
    EXPORT = "EXPORT"
    MANUAL = "MANUAL"
    CSV_IMPORT = "CSV_IMPORT"
    API = "API"

class PerformanceSource(StrEnum):
    CSV_IMPORT = "CSV_IMPORT"
    MANUAL = "MANUAL"
    API = "API"
```

## 3. `domain/performance/metrics.py`

```python
@dataclass(frozen=True)
class CanonicalMetricSet:
    """9 platform-neutralnih metrika (Faza 0.7 §6). SVE opciona — ne
    podržavaju sve platforme/izvori iste metrike. Validacija vrijednosti
    (npr. negativni brojevi) NIJE ovdje — to je P1.5-G5 Metric
    Calculator posao (namjerno, per Faza 1 v1.5 §20)."""
    reach: int | None = None
    impressions: int | None = None
    engagements: int | None = None
    clicks: int | None = None
    conversions: int | None = None
    spend: float | None = None
    revenue: float | None = None
    video_views: int | None = None
    watch_time_seconds: float | None = None


@dataclass(frozen=True)
class MetricPeriod:
    """Period izvještavanja. ``end`` ne smije prethoditi ``start`` — ovo
    JESTE pravi domain invarijant (definicija perioda, ne poslovna
    politika koja bi se mogla promijeniti), zato se provjerava u
    ``__post_init__`` (isti nivo stroгosti kao ostali domain invarijanti
    u projektu)."""
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise InvariantViolation(
                f"MetricPeriod.end ({self.end}) cannot precede"
                f" MetricPeriod.start ({self.start})"
            )
```

## 4. `domain/performance/entities.py`

```python
@dataclass(frozen=True)
class DistributionInstance:
    """Konkretan sadržaj, u konkretnoj verziji, na konkretnom
    kanalu/platformi/formatu (Faza 0.7 §3)."""
    id: DistributionInstanceId
    campaign_id: CampaignId
    campaign_item_id: CampaignItemId
    content_piece_id: PostId
    content_revision_id: RevisionId
    channel_code: str
    platform_code: str
    format_code: str
    distribution_source: DistributionSource
    created_at: datetime
    external_account_id: str | None = None
    external_content_id: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Metrika u jednom periodu, VEZANA za DistributionInstance (NE
    direktno za ContentPiece — Faza 0.7 §4 kritično pravilo)."""
    id: PerformanceSnapshotId
    distribution_instance_id: DistributionInstanceId
    period: MetricPeriod
    observed_at: datetime
    source: PerformanceSource
    metrics: CanonicalMetricSet
    source_batch_id: PerformanceImportBatchId | None = None
    raw_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PerformanceImportBatch:
    """Jedan uvoz podataka — mora biti provjerljiv (Faza 0.7 §13)."""
    id: PerformanceImportBatchId
    source: PerformanceSource
    imported_at: datetime
    row_count: int
    matched_count: int
    unmatched_count: int
    mapping_version: str
    source_file_name: str | None = None
    platform_code: str | None = None
    raw_source_snapshot_ref: str | None = None
```

`raw_metrics: dict[str, Any] = field(default_factory=dict)` — isti
obrazac kao `AIRequest.metadata` (`ports/ai.py`) — mutable default polje
na frozen dataclass-i je standardan, već korišten obrazac u ovom
projektu (frozen sprečava REASSIGNMENT atributa, ne mutaciju
vrijednosti unutar njega).

# Implementation steps

1. `domain/common/ids.py` — tri nove linije po Objective #1.
2. `domain/performance/enums.py` po Objective #2.
3. `domain/performance/metrics.py` po Objective #3.
4. `domain/performance/entities.py` po Objective #4.
5. Testovi:
   - `test_enums.py`: `DistributionSource` ima TAČNO 4 vrijednosti,
     `PerformanceSource` ima TAČNO 3, `DistributionSource` i
     `PerformanceSource` su RAZLIČITI tipovi (ne isti enum aliasovan
     dvaput) — eksplicitan test da `DistributionSource is not
     PerformanceSource` i da `PerformanceSource` NEMA `EXPORT` vrijednost.
   - `test_metrics.py`: `CanonicalMetricSet` konstruisan bez ijednog
     argumenta → sva polja `None` (SVE opciona, dokaz); konstruisan sa
     par vrijednosti → tačno drže vrijednost. `MetricPeriod` sa
     `end >= start` → radi; `end < start` → `InvariantViolation` (test
     GRANICE: `end == start` MORA proći, to nije "prije").
   - `test_entities.py`: sve tri entity klase su frozen (pokušaj
     izmjene atributa nakon konstrukcije → `FrozenInstanceError` ili
     ekvivalentno — isti obrazac kao postojeći `test_models_are_dataclasses`
     stil testova u projektu); `DistributionInstance`/`PerformanceSnapshot`
     konstruisani BEZ opcionih polja → opciona polja su `None`/prazan
     dict; `PerformanceSnapshot.raw_metrics` default je STVARNO prazan
     dict PO INSTANCI (dvije odvojene instance NE dijele isti mutable
     dict objekat — klasičan "mutable default" test, dokazati sa
     `is not` provjerom između dvije instance).

# Acceptance

- [ ] `domain/performance/` paket postoji sa `enums.py`/`metrics.py`/
      `entities.py`, sve tri klase entiteta + `CanonicalMetricSet` +
      `MetricPeriod` + oba enuma tačno po planom navedenim poljima
      (nijedno polje izmišljeno, nijedno izostavljeno od onoga što Faza
      0.7 §3/§5/§6/§13 navodi).
- [ ] `DistributionSource` i `PerformanceSource` su DVA RAZLIČITA enum
      tipa (test dokaz), NE jedan podijeljen enum.
- [ ] `MetricPeriod` odbija `end < start` (`InvariantViolation`),
      prihvata `end == start`.
- [ ] `CanonicalMetricSet` konstruisan bez argumenata → sve `None`.
- [ ] `PerformanceSnapshot.raw_metrics` mutable-default bug NE postoji
      (dvije instance imaju odvojene dict objekte).
- [ ] Sve tri entity dataclass-e su `frozen=True` (test dokaz).
- [ ] Nema `ports/`, `infrastructure/`, `application/`, `resources/migrations/`
      izmjena — ovo je ČISTO domain paket, nula I/O.
- [ ] Nema izmjena u `domain/campaign/`, `domain/content/`,
      `domain/visual/`, `domain/analytics/` (postojeći domain moduli
      NETAKNUTI).
- [ ] `domain/common/ids.py` ima TAČNO tri nove linije, nula izmjena
      postojećih.
- [ ] `python -m pytest tests/unit/domain/performance/ -v` prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema nove eksterne zavisnosti.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/domain/performance/ -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Polja SVAKOG modela provjerena red-po-red protiv Faza 0.7 §3/§5/§6/§13
  (ne nagađati, ne dodavati "korisna" polja koja plan ne traži — ovo je
  namjerno usko skopiran task);
- `DistributionSource`/`PerformanceSource` STVARNO odvojeni tipovi, ne
  jedan enum sa dva imena;
- `MetricPeriod.__post_init__` invarijant je ISPRAVNO strog (`<`, ne
  `<=` — `end == start` mora biti dozvoljen, jednodnevni period je
  validan);
- `raw_metrics` mutable-default zamka STVARNO testirana (klasična
  Python greška — `field(default_factory=dict)`, NIKAD `= {}` direktno
  u potpisu);
- nijedan fajl van `domain/performance/` + tri aditivne linije u
  `ids.py` nije diran — ovo je čist, izolovan, nula-rizik dodatak.

# Rollback

LOW risk — potpuno nov, izolovan domain paket, nula postojećih
pozivalaca, nula I/O, nula postojeće-koda izmjene osim tri aditivne
linije. Fix na istoj branch bez proširenja scope-a. §29: Claude-only
review, PASS → odmah merge.

# Coordination

Zavisi od ACS-F1-036 (mergovano, `analytics_match_key` već postoji) —
UNBLOCKED. Sljedeći korak: **P1.5-G2 Persistence** (Faza 1 v1.5 §17 —
nova migracija `0004_performance_foundation.sql`, tabele
`distribution_instances`/`performance_snapshots`/
`performance_import_batches`/`performance_import_rows`, plus
`DistributionRepositoryPort`/`PerformanceRepositoryPort` portovi i
SQLite implementacije — ovaj task NE piše persistenciju, samo pojmove
koje će P1.5-G2 dati mjesto u bazi).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-037-performance-domain
Branch:   task/ACS-F1-037-performance-domain
Base:     main @ e970697
```
