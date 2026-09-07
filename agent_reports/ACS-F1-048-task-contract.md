---
task_id: ACS-F1-048
phase: "P1.5-G5 — Metric Calculation (Faza 1 v1.5 §20)"
title: "Deterministički kalkulator izvedenih metrika (CTR/CPC/CPM/CPA/ROAS/Conversion Rate)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-07
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/domain/performance/metrics.py
  - src/ai_campaign_studio/domain/performance/calculator.py
  - src/ai_campaign_studio/domain/performance/__init__.py
  - tests/unit/domain/performance/test_metrics.py
  - tests/unit/domain/performance/test_calculator.py
forbidden_paths:
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Novi fajl (`calculator.py`), nema postojećih pozivalaca da se
    provjeri impact -- GitNexus upstream provjera je preventivna
    (potvrditi da ništa VEĆ ne postoji pod istim imenom / da se ne
    duplira postojeća logika).
---

# Kontekst

Faza 1 v1.5 §20 (`AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md`,
sekcija "20. P1.5-G5 — Metric Calculation"). P1.5-G3 (CSV import,
ACS-F1-042/043) i P1.5-G4 (matching, ACS-F1-044) su zatvoreni --
`PerformanceImportRow`/`DistributionInstance` sad postoje i mogu se
povezati. `CanonicalMetricSet` (`domain/performance/metrics.py`) NOSI
9 sirovih, opcionih metrika (reach/impressions/engagements/clicks/
conversions/spend/revenue/video_views/watch_time_seconds) i NJEN
VLASTITI docstring eksplicitno kaže: "Value validation ... is
deliberately NOT here; that is P1.5-G5 Metric Calculator's job."

Ovaj task NE dodaje persistenciju niti GUI -- to su G6 (Analytics Read
Models) i G7 (Minimal UI), zasebni budući taskovi. G5 je ČISTO
domain-layer: jedna deterministička funkcija koja uzima sirove metrike
i vraća izvedene, bez repo/bridge zavisnosti -- isti "domain-only, bez
persistencije" obrazac kao P1.5-G1 (`ACS-F1-037`).

# Objective

## 1. `DerivedMetricSet` — novi frozen dataclass u `metrics.py`

Šest izvedenih metrika, SVE opcione (`float | None`):

```python
@dataclass(frozen=True)
class DerivedMetricSet:
    ctr: float | None = None               # clicks / impressions
    cpc: float | None = None               # spend / clicks
    cpm: float | None = None               # spend / impressions * 1000
    cpa: float | None = None               # spend / conversions
    roas: float | None = None              # revenue / spend
    conversion_rate: float | None = None   # conversions / clicks
```

Implementer bira tačna imena polja ako postoji jači razlog za drugačiji
oblik (npr. da li vratiti postotak kao `0.034` ili `3.4` -- MORA biti
dokumentovano i KONZISTENTNO, jedan izbor za sve postotne metrike:
CTR i Conversion Rate).

## 2. `calculate_derived_metrics(metrics: CanonicalMetricSet) -> DerivedMetricSet`

Nova čista funkcija u novom `domain/performance/calculator.py`. Za
SVAKU izvedenu metriku, primijeniti PRAVILO (implementer ovo primjenjuje
dosljedno na svih 6, ne izmišlja različitu logiku po metrici):

- Ako je BILO KOJI potreban ulaz `None` (nedostaje) -> rezultat `None`
  (ne 0, ne izuzetak -- "nemamo podatak" nije isto što i "podatak je
  nula").
  ako je BROJILAC (npr. `clicks` za CTR) `None`, ILI imenilac (npr.
  `impressions` za CTR) `None`, `DerivedMetricSet.ctr` je `None`.
- Ako je IMENILAC POSTOJI ali je NULA (npr. `impressions=0`) -> rezultat
  `None` (dijeljenje sa nulom se NIKAD ne dešava, ne baca se
  `ZeroDivisionError`, ne vraća se `inf`/`nan`).
- Ako je BILO KOJI ulaz NEGATIVAN -> implementer ODLUČUJE i
  DOKUMENTUJE jedan dosljedan pristup (preporuka: tretirati kao
  nevalidan ulaz -> rezultat `None` za svaku metriku koja tu vrijednost
  koristi, NE baciti izuzetak -- jedan loš red iz CSV importa ne smije
  srušiti cijeli batch izračun; ovo je isti "fail soft po redu" obrazac
  kao `PlanPostLayout`/`ExportCampaign`-ov partial-failure). Ako
  implementer smatra da bi `InvariantViolation` bio ispravniji izbor,
  navesti obrazloženje u evidence-u -- koordinator odlučuje na review-u.
- Normalan slučaj (svi potrebni ulazi postoje, imenilac > 0) ->
  standardna formula, `float`.

## 3. Currency-konzistentnost napomena (OTVORENO PITANJE -- istražiti PRIJE koda)

Faza 1 v1.5 §20 eksplicitno traži "currency consistency" kao obavezan
edge-case test. **Provjereno: `CanonicalMetricSet`/`PerformanceSnapshot`
NEMAJU nijedno polje za valutu nigdje u domain sloju.** Prije pisanja
testa za ovo, implementer MORA:

1. Provjeriti da li valuta postoji NEGDJE drugdje u sistemu (npr. na
   nivou kampanje/brenda/provider config) -- ako NE postoji nigdje,
   ovo je STVARAN domain gap, ne nešto što G5 sam može popraviti u
   svom uskom scope-u (dodavanje `currency` polja na
   `CanonicalMetricSet` bi bila DOMAIN izmjena van "čist kalkulator"
   scope-a ovog taska).
2. Ako gap postoji: prijaviti kao `OUT_OF_SCOPE_FINDING` u evidence-u
   (ne tiho preskočiti zahtjev, ne sam dodati polje bez odobrenja) --
   koordinator odlučuje da li G5 dobija malo prošireni scope (dodati
   `currency: str | None` na `CanonicalMetricSet`, čisto aditivno) ili
   se currency-provjera odgađa za G6 (gdje se agregira PREKO snapshot-a
   i mix valuta postaje stvaran rizik).
3. G5-ov OWN kalkulator (jedan `CanonicalMetricSet` -> jedan
   `DerivedMetricSet`) nema PRIRODNO mjesto za "mix valuta" grešku --
   to je pitanje AGREGACIJE preko više snapshot-a, što je G6-ov posao.
   Implementer treba argumentovano zaključiti da li ovaj edge-case
   uopšte pripada G5-u ili je pogrešno naveden u planu za ovaj gate, i
   navesti taj zaključak eksplicitno u evidence-u.

# Implementation steps

1. Istražiti currency pitanje (Objective #3) PRIJE pisanja koda,
   prijaviti nalaz.
2. `DerivedMetricSet` dataclass + testovi (frozen, sva polja opciona).
3. `calculate_derived_metrics` + testovi za SVIH 6 metrika x svaki
   obavezan edge-case iz plana:
   - zero impressions (pogađa CTR, CPM)
   - zero clicks (pogađa CPC, Conversion Rate)
   - zero conversions (pogađa CPA)
   - zero spend (pogađa CPC, CPM, ROAS)
   - missing values (svaka kombinacija None ulaza)
   - negative/invalid ulazi (dosljedan tretman, dokumentovan)
   - normalan slučaj (sve prisutno, sve pozitivno) -- tačne vrijednosti
     provjerene ručnim računom u testu, ne samo "nije None"
4. Puni gate.

# Acceptance

- [ ] `DerivedMetricSet` postoji, frozen, 6 opcionih `float` polja.
- [ ] `calculate_derived_metrics` čista funkcija, bez repo/bridge
      zavisnosti, bez side-effect-a.
- [ ] Nijedno dijeljenje sa nulom ne baca `ZeroDivisionError` niti
      vraća `inf`/`nan` -- uvijek `None`.
- [ ] Nedostajući ulaz (bilo koji potreban za tu metriku) -> `None`,
      ne izuzetak.
- [ ] Negativni/nevalidni ulazi tretirani dosljedno i dokumentovano
      (fail-soft preporučeno, ali implementer može argumentovati
      alternativu).
- [ ] Currency-pitanje istraženo i EKSPLICITNO prijavljeno u evidence-u
      (nalaz ili zaključak "ne pripada G5", ne tiho izostavljeno).
- [ ] `domain/performance/entities.py`, `enums.py`,
      `application/`, `ports/`, `infrastructure/`,
      `presentation_webview/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/domain/performance/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/domain/performance/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-048-metric-calculator
gh pr create --base main --title "ACS-F1-048: P1.5-G5 Metric Calculation"
gh pr checks
```

# Review focus — Claude (MEDIUM, §29)

- Svaka od 6 formula ručno provjerena protiv plana (CTR=clicks/
  impressions, CPC=spend/clicks, CPM=spend/impressions*1000,
  CPA=spend/conversions, ROAS=revenue/spend,
  Conversion Rate=conversions/clicks).
- Adversarial: pokušati NaN/Inf kroz float edge-case (npr.
  `float('inf')` kao sirov ulaz) -- da li kalkulator to hvata ili
  propušta dalje.
- Currency nalaz stvarno istražen, ne pretpostavljen.

# Rollback

MEDIUM risk -- nova, izolovana domain funkcija, nula postojećih
pozivalaca, nula persistencije/GUI uticaja. Claude-only review →
odmah merge po §29 ako PASS.

# Coordination

Paralelno sa ACS-F1-049 (Brend read-path) -- `allowed_paths` potpuno
disjoint (domain/performance/ vs presentation_webview/screens/brend/ +
bridge/app.js), sigurno za paralelan rad. NE paralelizovati sa BILO
KOJIM drugim taskom koji dira `presentation_webview/static/app.js`
(lekcija iz GUI-009/F1-046/F1-047 3-way merge sudara ranije danas).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-048-metric-calculator
Branch:   task/ACS-F1-048-metric-calculator
Base:     main @ cc84778
```
