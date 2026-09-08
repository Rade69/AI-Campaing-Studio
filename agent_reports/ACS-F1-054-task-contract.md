---
task_id: ACS-F1-054
phase: "P1.5-G7b (revidiran) — Content Performance tabela u Pregled i izvoz (Faza 1 v1.5 §22)"
title: "Pregled i izvoz ekran prikazuje performance po pojedinom content piece-u"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-08
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_pregled_izvoz_ssr.py
  - tests/unit/presentation_webview/test_static_pages_generator.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/brend/
  - src/ai_campaign_studio/presentation_webview/screens/plan_kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/kalendar/
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/
  - src/ai_campaign_studio/presentation_webview/screens/pocetna/
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Peti GUI read-path presedan nakon Kampanje/Brend/Početna/Campaign
    Performance (ACS-F1-046/049/051/053). Provjeriti da
    `build_content_performance_summary` (ACS-F1-050) i
    `list_campaign_content` (postojeći) i dalje imaju iste potpise
    poslije bilo kakvih međuvremenih izmjena.
---

# Kontekst

Faza 1 v1.5 §22 traži "ContentPiece → Performance section" kao dio
P1.5-G7 Minimal UI. **Originalni plan je pretpostavljao da postoji
per-content-piece ekran** (npr. novi tab u Studio sadržaja) — istraga
prije ovog kontrakta je otkrila da to NE POSTOJI: Studio sadržaja je i
dalje potpuno fixture-driven mockup ("Stavka 1/6" hardkodovano), nema
`content_piece_id` ni u URL-u ni u `app.js`-u, jedini runtime identiteti
koji teku kroz app su `campaign_id`/`plan_id`. Dodavanje pravog
per-item routing-a na Studio sadržaja bi bio mnogo veći, zaseban posao
van scope-a G7 (Human Owner odluka 2026-09-08: NE raditi to sada).

**Revidiran G7b**: umjesto novog ekrana/taba, content-piece-level
performance se prikazuje kao TABELA unutar VEĆ POSTOJEĆE "Učinak
kampanje" kartice u "Pregled i izvoz" ekranu (ACS-F1-053, G7a) —
koristi SAMO postojeći `campaign_id` identitet koji ekran već ima
preko `?campaign=`. Nema potrebe za novim runtime identitetom.

`build_content_performance_summary(repo, content_piece_id) ->
ContentPerformanceSummary` (ACS-F1-050) VEĆ POSTOJI.
`ContentRepositoryPort.list_campaign_content(campaign_id) ->
tuple[ContentPiece, ...]` VEĆ POSTOJI (`self._content_repo`, korišten
od `generate_campaign_content`). Tok: `campaign_id` →
`list_campaign_content` → za SVAKI `ContentPiece`,
`build_content_performance_summary(performance_repo, piece.id)` →
tabela redova.

**BF-1/BF-2/XSS klase nalaza MORAJU biti primijenjene OD PRVE VERZIJE,
uključujući OBAVEZAN izvršni Node/VM test sa dvostrukim
`pywebviewready` emit-om od početka** (F1-051 BF-1 standard, F1-053
ga je već ponovio bez podsjetnika — nastaviti tu praksu):

1. `loadX()`: immediate fast path + jednokratni
   `window.addEventListener('pywebviewready', loadX, {once:true})`.
2. Ekran-specifičan marker (`data-content-perf-*` ili slično).
3. **Node/VM test mora emitovati `pywebviewready` DVAPUT i dokazati
   exactly-once API poziv**, ne string-presence.
4. Sadržaj u redovima (npr. content piece headline/naslov) dolazi iz
   korisnički/AI-generisanog teksta -- XSS-escape obavezan (isti rizik
   kao Kampanje/Brend liste).

**Napomena (Codex-ova neblokirajuća napomena iz F1-053)**: reuse već
parsiranu `?campaign=` vrijednost iz postojećeg boot IIFE-a umjesto da
se `URLSearchParams(location.search).get('campaign')` ponovo poziva u
novom IIFE-u -- F1-053 je ovo propustio (neblokirajuće tamo, ali OVDJE
implementer treba PRIMIJENITI ispravku, ne ponoviti istu devijaciju
treći put).

# Objective

## 1. Nova READ js_api metoda: `get_campaign_content_performance(raw_payload: dict) -> dict`

Isti obrazac kao `get_campaign_performance` (payload nosi
`campaign_id: str`). Validacija: dict + `campaign_id` str non-empty;
nepostojeća kampanja → `VALIDATION_ERROR`.

Tok:
```python
pieces = self._content_repo.list_campaign_content(campaign_id)
rows = [
    ContentPerformanceRowUiModel(
        content_piece_id=str(piece.id),
        label=<platform_code/format_code + headline ako payload postoji>,
        derived=<mapiran build_content_performance_summary(...).derived>,
    )
    for piece in pieces
]
```

Nula content piece-ova (kampanja bez generisanog sadržaja) → `ok=True`
sa praznom listom, NE greška. Piece bez `payload` (još negenerisan) →
implementer bira razuman fallback label (npr.
`f"{platform_code}/{format_code}"` bez headline-a), NE prazan string.

`derived` po redu dolazi ISKLJUČIVO iz
`build_content_performance_summary` (G6/G5 lanac) — nema ručnih
formula. Implementer bira razuman podskup `DerivedMetricSet` polja za
tabelu (npr. CTR + CPC dovoljno za MVP red, ne mora svih 6 -- puna
kartica već postoji na campaign nivou iz G7a) i dokumentuje izbor.

## 2. `pregled_izvoz/__init__.py` -- render + hidratacija

Nova tabela ISPOD postojeće G7a "Učinak kampanje" kartice (isti red
ili novi red -- implementer procjenjuje layout, isti kao G7a). SSR
fixture prikazuje 2-3 placeholder reda ("Nema podataka" ako fixture
prazna). Ekran-specifičan `data-content-perf-*` marker na tabeli/
redovima.

`app.js` dobija `loadContentPerformance()` (ili integrisano u
POSTOJEĆI `loadCampaignPerformance()` IIFE iz G7a -- implementer bira,
ali ako se odvoji u novi IIFE, MORA reuse-ovati već parsiran
`campaign_id`, ne ponovo parsirati `location.search`).

## 3. `presentation/contracts.py` + `ui_models.py`

`PresentationFacade` dobija `get_campaign_content_performance` potpis.
Nov `ContentPerformanceRowUiModel` + rezultat model (implementer bira
tačna imena, prati `*ResultUiModel` obrazac).

# Implementation steps

1. Bridge metoda (Objective #1) + testovi: nepostojeća kampanja
   (VALIDATION_ERROR), kampanja bez content piece-ova (prazna lista),
   kampanja sa >=2 piece-a različitih performance stanja (jedan sa
   podacima, jedan bez -- tačne vrijednosti po redu, isti seed-stil
   kao G6/G7a testovi), piece bez payload-a (fallback label), no
   secret/path/exception leak.
2. `contracts.py`/`ui_models.py` dopuna + testovi.
3. `pregled_izvoz/__init__.py` render + `app.js` povezivanje --
   `pywebviewready` + ekran-specifičan marker OD POČETKA + **OBAVEZAN
   izvršni Node/VM test sa dvostrukim emit-om** + XSS-escape test
   (payload u content piece headline-u) + test da SSR offline fallback
   i dalje radi + PRIMIJENJEN reuse postojećeg `campaign_id`
   (ne ponovljen parsing -- Codex F1-053 napomena).
4. Integration test: STVARNA baza, >=2 content piece-a, tabela sa
   tačnim redovima.

# Acceptance

- [ ] `get_campaign_content_performance` postoji, vraća TAČNE redove
      za kampanju SA content piece-ovima, praznu listu za kampanju
      BEZ njih (ok=True u oba), `VALIDATION_ERROR` za nepostojeću
      kampanju.
- [ ] Svaki red `derived` dolazi ISKLJUČIVO iz
      `build_content_performance_summary` -- nema duplih formula.
- [ ] Nijedan secret/path/exception tekst ne curi.
- [ ] `app.js` koristi `pywebviewready` + immediate fast path +
      ekran-specifičan marker OD PRVE VERZIJE.
- [ ] **Izvršni Node/VM DOM test postoji OD PRVE VERZIJE**, dvostruki
      emit, exactly-once dokaz (F1-051/053 standard).
- [ ] XSS-escape na content piece label/headline stvarno testiran.
- [ ] `campaign_id` REUSE-OVAN iz postojećeg parsing-a, ne ponovljen
      (Codex F1-053 napomena primijenjena, ne ponovljena).
- [ ] SSR (`render_body()`) i dalje radi OFFLINE sa fixture prikazom.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`, svi
      ostali screens/ folderi NISU DIRANI.
- [ ] `python -m pytest tests/unit/presentation_webview/
      tests/unit/presentation/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `node --check src/ai_campaign_studio/presentation_webview/static/app.js`
      prolazi.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src
node --check src/ai_campaign_studio/presentation_webview/static/app.js

git push -u origin task/ACS-F1-054-content-performance-table
gh pr create --base main --title "ACS-F1-054: Content Performance tabela u Pregled i izvoz"
gh pr checks
```

# Review focus — Claude + Codex (adversarial)

- **Izvršni test dokazuje exactly-once lifecycle** (dvostruki emit) --
  prvi provjereni item.
- Cross-screen izolacija (nula DOM izmjena/API poziva na ekranu bez
  `data-content-perf-*` markera).
- `derived` dolazi iz G6 lanca, nema ručne formule.
- XSS escape na label/headline stvarno testiran.
- `campaign_id` je STVARNO reuse-ovan (ne ponovljen parsing) --
  provjeriti da implementer nije ponovio istu devijaciju treći put.
- Prazna/nepostojeća kampanja putanje stvarno testirane.

# Rollback

HIGH risk -- peti read-path presedan, GUI lifecycle klasa grešaka.
Pun review ciklus obavezan.

# Coordination

**NE paralelizovati** sa G7c (Import Performance UI) niti bilo kojim
drugim taskom koji dira `presentation_webview/static/app.js`/
`bridge/__init__.py` (ista lekcija kao GUI-009/F1-046/F1-047 3-way
sudar). Sekvencijalno: G7b (ovaj task) → G7c → P1.5-G8 (Integration
acceptance).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-054-content-performance-table
Branch:   task/ACS-F1-054-content-performance-table
Base:     main @ 853ce8d
```
