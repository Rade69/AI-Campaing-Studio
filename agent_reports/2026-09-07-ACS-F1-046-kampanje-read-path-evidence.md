# ACS-F1-046 — implementer evidence (Crush)

Task: Kampanje lista čita stvarne kampanje iz baze (prvi READ js_api metod).
Addendum: `agent_reports/ACS-F1-046-addendum-scope-decision.md` (odobreno proširenje scope-a).
Branch: `task/ACS-F1-046-kampanje-read-path` (worktree `../ACS-F1-046-kampanje-read-path`, base `94cd2db`).
Status: implementacija + testovi gotovi. Čeka review (Claude → Codex adversarial → Human Owner odobrenje).

## OUT_OF_SCOPE_FINDING (rešen)

`list_campaigns` je bio neizvodljiv bez novih repo metoda. Koordinator odobrio 3
aditivne metode + isključio `updated_at` (polje ne postoji nigdje u sistemu). Sve
po addendum-u.

## Šta je urađeno (14 fajlova, +562/-0)

**Repo sloj (odobreno proširenje):**
1. `CampaignRepositoryPort.list_campaigns()` + SQLite impl — `SELECT * FROM campaigns ORDER BY created_at DESC`, prazna tabela → `()`.
2. `CampaignRepositoryPort.get_latest_plan_for_campaign(campaign_id)` + impl — `ORDER BY version DESC LIMIT 1` + isti item-loading kao `get_plan`.
3. `BrandRepositoryPort.get_brand(brand_id)` + impl — `SELECT * FROM brands WHERE id = ?`.

**Bridge:**
- Nova `@_with_call_resources` metoda `list_campaigns(raw_payload: dict | None = None)` — vraća `ListCampaignsResultUiModel` sa `CampaignSummaryUiModel` redovima (id, name=brief.offer, status=CampaignStatus.value, plan_item_count, brand=brand.name, created_at ISO). Prazna baza → `ok=True, campaigns=()`.
- `_LIFECYCLE_ERROR_MAPPERS`/`_LIFECYCLE_ERROR_MESSAGES` + `_list_err` (dedicated DTO shape).

**Presentation:**
- `contracts.py` + `ui_models.py` — `list_campaigns` potpis + `CampaignSummaryUiModel`/`ListCampaignsResultUiModel`.

**Frontend:**
- `app.js` — `escapeHtml` + `loadCampaigns()` (poziva se pri load-u), zamjenjuje `table.table` stvarnim redovima, XSS-escape svake interpolirane vrijednosti, prazna lista → poruka, offline fallback (bez bridge-a → fixture ostaje).

`render_body()` u `kampanje/__init__.py` NIJE diran (ostaje fixture-driven SSR fallback).

## Testovi (stvarno pokrenuto u worktree)

```text
pytest (repo + ports + brand integration)  -> 24 passed
pytest (bridge + contracts + ui_models + kampanje_ssr) -> 97 passed
pytest -q (ceo suite)                       -> 1069 passed, 0 failed
ruff check (13 fajlova)                     -> All checks passed
mypy (6 source fajlova)                     -> Success
```

Ključni dokazi:
- `test_list_campaigns_returns_seeded_campaign_with_plan` — plan_item_count=3 tačan, name=brief.offer, brand ime stvarno pročitano.
- `test_list_campaigns_campaign_without_plan_has_zero_items` — 0 bez plana.
- `test_list_campaigns_returns_newest_first` — `created_at DESC`.
- `test_list_campaigns_works_from_fresh_worker_thread` — `_with_call_resources` thread-safety.
- `test_app_js_has_escape_html_and_load_campaigns` — XSS escape (sva 5 opasna znaka) + call-sites.
- `test_get_brand_round_trip` / `test_get_unknown_brand_returns_none` — brand null-safety.

## GitNexus

- Index up-to-date (`94cd2db`).
- `CampaignRepositoryPort` / `BrandRepositoryPort` upstream → risk "HIGH" **samo zbog broja importer-a (19)**; izmjena je ČISTO ADITIVNA (3 nove metode, nijedan postojeći potpis nepromijenjen), potvrđeno 1069/1069 bez regresije.
- `detect-changes` NIJE pokrenut (uncommitted diff u worktree; radi se nakon commit-a — workflow §6).

## Napomene

- `get_brand` test je dodat u `tests/integration/.../test_sqlite_brand_repository.py` (postojeći fajl) umjesto u addendum-om naveden `tests/unit/.../test_sqlite_brand_repository.py` koji NE postoji — integration je prirodno mjesto (tu su svi brand repo testovi).
- `campaigns` je `tuple` u Python `dict` (konzistentno sa `content_piece_ids`), a JSON serializacija (pywebview) ga pretvara u list — JS dobija `[]`.
- Brand ime iz fixture-a je `"BrightSmile Dental"` (ne `"BrightSmile"`) — test asertuje `"BrightSmile" in brand`, ne tačan string.
