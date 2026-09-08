# ACS-F1-051 — implementer evidence (Crush)

Task: Početna (Dashboard) ekran čita stvarne KPI/nedavne kampanje iz baze (treći read-path ekran).
Branch: `task/ACS-F1-051-pocetna-read-path` (worktree `../ACS-F1-051-pocetna-read-path`, base `941ae97`).
Status: implementacija + testovi gotovi. Čeka review (Claude → Codex adversarial → Human Owner odobrenje).

## Šta je urađeno (10 fajlova, +605/-8)

**Bridge** (`bridge/__init__.py`):
- Nova `@_with_call_resources` metoda `get_dashboard_overview(raw_payload=None)` — reuse-uje postojeće `list_campaigns()`/`get_brief()`/`list_campaign_content()` (bez novih repo metoda, bez dupliranja poslovne logike). Vraća 4 KPI brojača + `recent_campaigns` (top 5, newest first).
- `_dashboard_err` (dedicated DTO shape) + `_LIFECYCLE_ERROR_MAPPERS`/`_LIFECYCLE_ERROR_MESSAGES` entry.

**Presentation**: `contracts.py` + `ui_models.py` — `get_dashboard_overview` potpis + `DashboardOverviewResultUiModel`/`DashboardRecentCampaignUiModel`.

**Frontend**:
- `pocetna/__init__.py` — `data-pocetna-kpi-value="active|planned|drafts|approved"` + `data-pocetna-recent` markeri (SSR i dalje fixture-driven).
- `app.js` — `loadDashboardOverview()` sa ekran-specifičnim markerom + `escapeHtml` na recent name/status + `textContent` na KPI brojeve + `pywebviewready`/fast path.

## Odluke (eksplicitno dokumentovane, ne prećutne)

1. **"Aktivna kampanja" = `Campaign.status != EXPORTED`.** `CampaignStatus` nema ARCHIVED/CANCELLED; `EXPORTED` je jedini terminalni status. Brojač je `active = len([c for c in campaigns if c.status is not EXPORTED])`.
2. **`activity` (Zadnje aktivnosti) ostaje fixture-only.** Ne postoji domain "activity log" koncept; rekonstruisanje iz `created_at` bi bilo izmišljanje. SSR panel netaknut.

## Testovi (stvarno pokrenuto u worktree)

```text
pytest (bridge + contracts + ui_models + pocetna_ssr + static_pages) -> 154 passed
pytest -q (ceo suite)                                                -> 1159 passed, 0 failed
ruff check (9 fajlova)                                               -> All checks passed
mypy (4 source fajla)                                                -> Success
node --check app.js                                                 -> OK
```

Ključni dokazi:
- `test_get_dashboard_overview_empty_db_returns_zeroes` — prazna baza → nula, ne greška.
- `test_get_dashboard_overview_returns_campaign_and_content_counts` — 1 kampanja + 3 pieces (PLANNED/DRAFT/APPROVED) → tačni brojači.
- `test_get_dashboard_overview_exported_campaign_not_active` — EXPORTED kampanja se ne broji kao aktivna (dokazuje definiciju), ali ostaje u recent listi.
- `test_get_dashboard_overview_lifecycle_failure_returns_exact_dto` — tačan key-set + bez leak-a.
- `test_app_js_dashboard_hydration_lifecycle_isolation_and_xss` — **izvršni Node/VM DOM test** (lifecycle + izolacija + XSS).

## Mutation dokaz (obavezno po kontraktu, nezavisno reprodukovano)

- Bezuslovan `loadDashboardOverview()` → test PADA (`readyListeners: 0`, `lateKpiActive: false`).
- Generički `h3` umesto `[data-pocetna-recent]` → test PADA (`statusEscaped: false` i dr.).

Oba vraćena; test zelen na ispravnom kodu.

## GitNexus

- Index up-to-date. `CampaignBridgeApi` upstream → LOW (1 — samo `__main__.py` import). Izmena čisto aditivna (novi read metod, bez novih repo metoda).
