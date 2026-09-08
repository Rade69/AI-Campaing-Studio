---
task_id: ACS-F1-050
phase: "P1.5-G6 — Analytics Read Models (Faza 1 v1.5 §21)"
title: "Agregacijski read modeli: CampaignPerformanceSummary / ContentPerformanceSummary / PlatformPerformanceSummary"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-08
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/domain/performance/
  - src/ai_campaign_studio/application/performance/
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_performance_repository.py
  - tests/unit/domain/performance/
  - tests/unit/application/performance/
  - tests/unit/ports/test_repositories.py
  - tests/unit/infrastructure/database/repositories/test_sqlite_performance_repository.py
  - tests/integration/database/repositories/test_sqlite_performance_repository.py
forbidden_paths:
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - resources/migrations/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/campaign/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Prvi task koji MIJENJA potpis `PerformanceRepositoryPort`-a (dodaje
    novu metodu -- port sam sebe najavljuje kao mjesto gdje će
    "query-by-related-entity" metode doći za G3/G4/G5/G6 caller-e).
    OBAVEZNO `gitnexus_impact PerformanceRepositoryPort --direction
    upstream` PRIJE izmjene (potvrditi da nijedan postojeći caller ne
    implementira Protocol na način koji bi nova metoda pokvarila --
    `Protocol` je structural typing, pa svaki postojeći fake/mock u
    testovima koji "implementira" ovaj port možda treba dopunu).
---

# Kontekst

P1.5-G1 (domain), G2 (persistence), G3 (CSV import), G4 (matching), G5
(metric calculation, ACS-F1-048) su svi zatvoreni. `DistributionInstance`
nosi `campaign_id`/`campaign_item_id`/`content_piece_id`/`platform_code`
direktno; `PerformanceSnapshot` je vezan za `DistributionInstance`
(NE direktno za `ContentPiece` -- Faza 0.7 §4 kritično pravilo).
`calculate_derived_metrics` (G5, `domain/performance/calculator.py`)
je čista funkcija koja pretvara JEDAN `CanonicalMetricSet` u JEDAN
`DerivedMetricSet`.

`PerformanceRepositoryPort`-ov VLASTITI docstring (`ports/repositories.py`)
već najavljuje ovaj task: "Query-by-related-entity methods (e.g. 'all
snapshots for one distribution instance') are added later, when a real
caller (P1.5-G3/G4/G5/G6) asks for them." **G6 je taj caller.**

Faza 1 v1.5 §21 traži TAČNO tri read modela:

```text
CampaignPerformanceSummary
ContentPerformanceSummary
PlatformPerformanceSummary
```

"Ne praviti još kompleksan BI warehouse" -- minimalna agregacija, ne
dashboard, ne vremenske serije, ne filter-UI (to je G7).

# Otvoreno pitanje — istražiti/odlučiti PRIJE koda (kao G5-ova valuta)

**Agregacija preko VIŠE `PerformanceSnapshot`-ova za isti
`DistributionInstance`** (npr. dnevni CSV importi tokom mjesec dana)
nema postojeći presedan u kodu. Implementer MORA odlučiti i
DOKUMENTOVATI JEDAN dosljedan pristup, npr.:

1. **Najnoviji snapshot po periodu** (uzeti `PerformanceSnapshot` sa
   najnovijim `observed_at` po `DistributionInstance`, ignorisati
   starije) -- jednostavnije, ali gubi "ukupno" (npr. ukupna potrošnja
   preko cijele kampanje).
2. **Sabrati raw metrike preko svih snapshot-ova** za taj
   `DistributionInstance`, PA tek onda pozvati
   `calculate_derived_metrics` na zbir -- daje "ukupno za cijeli
   period", ali zahtijeva da periodi snapshot-ova NE preklapaju (ako
   preklapaju, dupliranje). Ako implementer bira ovo, mora eksplicitno
   navesti da li/kako provjerava preklapanje perioda (`MetricPeriod`).
3. Nešto treće, argumentovano.

Ovo NIJE isto pitanje kao G5-ova valuta (koje je bilo "ne postoji
polje uopšte") -- ovdje POLJE postoji (`CanonicalMetricSet`), pitanje
je AGREGACIONA SEMANTIKA. Implementer bira PRISTUP #2 (sabiranje) OSIM
AKO ne pronađe jak razlog za #1 -- "ukupno za kampanju" je ono što plan
§21 traži ("Campaign**Performance**Summary", ne "Campaign Latest
Snapshot"), ali MORA eksplicitno dokumentovati odabir i eventualnu
"preklapanje perioda" napomenu u evidence-u, ne prećutno pretpostaviti.

**Currency napomena (nastavak F1-048 nalaza):** F1-048 je odgodio
"currency consistency" edge-case za G6 jer je to PRAVO mjesto gdje se
VIŠE snapshot-ova agregira (mix valuta postaje stvaran rizik tek ovdje).
`CanonicalMetricSet`/`PerformanceSnapshot` I DALJE nemaju currency
polje (potvrđeno u F1-048). Implementer NE dodaje currency polje u
ovom tasku (to bi bila domain izmjena van scope-a) -- ako agregacija
sabira `spend`/`revenue` preko snapshot-ova bez currency koncepta, to
je POSTOJEĆI, već-poznat gap, ne nova greška. Prijaviti u evidence-u
kao potvrdu da je gap I DALJE otvoren i da ostaje za budući task (ne
G6 sam scope) ako se ikad realno pojave multi-currency izvori.

# Objective

## 1. Nova repo metoda: `list_performance_snapshots_by_distribution_instance`

Dodati na `PerformanceRepositoryPort` (ports/repositories.py):

```python
def list_performance_snapshots_by_distribution_instance(
    self, distribution_instance_id: DistributionInstanceId
) -> tuple[PerformanceSnapshot, ...]: ...
```

Implementirati u `SqlitePerformanceRepository`
(`infrastructure/database/repositories/sqlite_performance_repository.py`)
-- isti obrazac kao postojeći `list_performance_import_rows`
(`SELECT * FROM performance_snapshots WHERE distribution_instance_id = ?
ORDER BY observed_at`). NEMA nove migracije -- tabela već postoji.

**GitNexus impact provjera OBAVEZNA prije ove izmjene** (vidi
frontmatter `gitnexus` napomenu) -- `PerformanceRepositoryPort` je
`@runtime_checkable Protocol`, pa provjeriti da li postoje in-memory
fake/test-double implementacije koje bi trebale dopunu (grep za
"PerformanceRepositoryPort" u testovima).

## 2. Read modeli

(domain ili application sloj — implementer bira lokaciju unutar
`allowed_paths`, dokumentuje zašto):

```python
@dataclass(frozen=True)
class CampaignPerformanceSummary:
    campaign_id: CampaignId
    derived: DerivedMetricSet
    raw: CanonicalMetricSet  # agregirani zbir (vidi otvoreno pitanje)
    distribution_instance_count: int

@dataclass(frozen=True)
class ContentPerformanceSummary:
    content_piece_id: PostId
    derived: DerivedMetricSet
    raw: CanonicalMetricSet
    distribution_instance_count: int

@dataclass(frozen=True)
class PlatformPerformanceSummary:
    platform_code: str
    derived: DerivedMetricSet
    raw: CanonicalMetricSet
    distribution_instance_count: int
```

Implementer prilagođava tačna polja ako ima jak razlog (npr. dodati
`snapshot_count` odvojeno od `distribution_instance_count`), ali MORA
zadržati `derived: DerivedMetricSet` (G5 rezultat) kao source of truth
za izvedene metrike -- ne računati CTR/CPC/itd. ponovo van
`calculate_derived_metrics`.

## 3. Agregacijska funkcija (application/performance/, novi fajl)

Npr. `build_campaign_performance_summary.py` (i po analogiji za
content/platform, ili jedna parametrizovana funkcija -- implementer
bira strukturu, ali prati POSTOJEĆI stil iz
`match_performance_import_batch.py`: čista funkcija/use-case klasa,
prima repo port kao zavisnost, NE zna za SQLite/bridge).

Tok: `campaign_id` -> `list_distribution_instances_by_campaign`
(POSTOJI) -> za svaki instance ->
`list_performance_snapshots_by_distribution_instance` (NOVO, #1 gore)
-> agregirati raw metrike (otvoreno pitanje pristup #2) ->
`calculate_derived_metrics` (POSTOJI, G5) -> `CampaignPerformanceSummary`.

Nula `DistributionInstance`/nula `PerformanceSnapshot` -> summary sa
svim `None`/`0` vrijednostima, NE izuzetak.

# Implementation steps

1. Istražiti i dokumentovati agregacionu semantiku (Otvoreno pitanje
   sekcija) PRIJE koda.
2. GitNexus impact na `PerformanceRepositoryPort` PRIJE izmjene porta.
3. Nova port metoda + SQLite implementacija + testovi (prazna lista,
   jedan snapshot, više snapshot-ova, `ORDER BY observed_at`
   provjeren).
4. Tri read model dataclasse + testovi (frozen, polja).
5. Agregacijska funkcija(e) + testovi: nula instanci, jedan instance/
   jedan snapshot, više instanci/snapshot-ova, provjera da `derived`
   polje STVARNO dolazi iz `calculate_derived_metrics` (ne
   duplirana logika).
6. Puni gate.

# Acceptance

- [ ] Nova port metoda postoji, ista `tuple[..., ...]` konvencija kao
      ostale list-metode, `ORDER BY observed_at` (ili dokumentovan
      drugi red).
- [ ] SQLite implementacija testirana (prazno/jedan/više).
- [ ] Tri read model dataclasse postoje, frozen.
- [ ] Agregacijska funkcija koristi `calculate_derived_metrics` (G5)
      kao JEDINI izvor izvedenih metrika -- nema duple formule.
- [ ] Agregaciona semantika (sabiranje vs najnoviji) eksplicitno
      dokumentovana u evidence-u, sa obrazloženjem.
- [ ] Currency-gap nalaz iz F1-048 eksplicitno potvrđen kao I DALJE
      otvoren (ne prećutno zaboravljen, ne riješen mimo scope-a).
- [ ] Nula instanci/snapshot-ova -> summary bez izuzetka.
- [ ] `presentation/`, `presentation_webview/`, `domain/content/`,
      `domain/campaign/`, `application/posts/`, `application/campaign/`,
      `resources/migrations/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/domain/performance/
      tests/unit/application/performance/ tests/unit/ports/
      tests/unit/infrastructure/database/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/domain/performance/ tests/unit/application/performance/ tests/unit/ports/ tests/unit/infrastructure/database/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-050-analytics-read-models
gh pr create --base main --title "ACS-F1-050: P1.5-G6 Analytics Read Models"
gh pr checks
```

# Review focus — Claude + Codex (adversarial)

- **Port izmjena**: `PerformanceRepositoryPort` je `@runtime_checkable
  Protocol` -- provjeriti da nijedan postojeći test-double/fake ne
  postane structurally invalid, i da GitNexus impact nije propušten.
- Agregaciona semantika je stvarno dosljedna (sabiranje ILI najnoviji,
  ne miješano po metrici bez razloga) i dokumentovana.
- `calculate_derived_metrics` je JEDINI izvor izvedenih metrika --
  adversarial: potražiti bilo koju ručno pisanu formulu (`/`, `*`)
  van tog poziva u novom kodu.
- Currency-gap potvrda (ne tiho zaboravljena, ne tiho riješena).
- Prazna/nula-instanci putanja stvarno testirana, ne pretpostavljena.

# Rollback

HIGH risk -- prva izmjena `PerformanceRepositoryPort` potpisa (Protocol
extension), dotiče infrastructure sloj. Iako je aditivno (nova metoda,
ne mijenja postojeće), Protocol structural typing + GitNexus upstream
provjera zahtijevaju pun adversarial ciklus, ne §29.

# Coordination

Paralelno sa ACS-F1-051 (Početna dashboard read path) --
`allowed_paths` potpuno disjoint (`domain/performance/` +
`application/performance/` + `ports/repositories.py` +
`infrastructure/database/repositories/sqlite_performance_repository.py`
vs `presentation_webview/screens/pocetna/` + `bridge/__init__.py` +
`app.js` + `presentation/`), sigurno za paralelan rad. NE
paralelizovati sa BILO KOJIM drugim taskom koji dira
`ports/repositories.py` ili `sqlite_performance_repository.py`.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-050-analytics-read-models
Branch:   task/ACS-F1-050-analytics-read-models
Base:     main @ fb1d79e
```
