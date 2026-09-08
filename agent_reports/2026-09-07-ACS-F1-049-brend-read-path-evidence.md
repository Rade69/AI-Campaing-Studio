# ACS-F1-049 — implementer evidence (Crush)

Task: Brend ekran čita stvaran brand/snapshot/approved facts iz baze (drugi read-path ekran, ACS-F1-046 obrazac).
Branch: `task/ACS-F1-049-brend-read-path` (worktree `../ACS-F1-049-brend-read-path`, base `640f018`).
Status: implementacija + testovi gotovi. Čeka review (Claude → Codex adversarial → Human Owner odobrenje).

## Šta je urađeno (10 fajlova, +448/-4)

**Bridge** (`bridge/__init__.py`):
- Nova `@_with_call_resources` metoda `get_brand_overview(raw_payload: dict | None = None)` — poziva `_ensure_brand()` (postojeći), pa `get_brand` + `get_snapshot` + `list_snapshot_facts`, filtrira preko `is_fact_usable`, vraća `BrandOverviewResultUiModel` (brand_name, primary_audience, voice=formality+tone, facts).
- `_brand_err` (dedicated DTO shape) + `_LIFECYCLE_ERROR_MAPPERS`/`_LIFECYCLE_ERROR_MESSAGES` entry `"get_brand_overview"`.
- Import `is_fact_usable` (iz `domain.facts.policies` — import, ne izmena).

**Presentation**: `contracts.py` + `ui_models.py` — `get_brand_overview` potpis + `BrandFactUiModel`/`BrandOverviewResultUiModel`.

**Frontend**:
- `brend/__init__.py` — ekran-specifični markeri `data-brend-name`/`data-brend-audience`/`data-brend-voice`/`data-brend-facts` (SSR i dalje fixture-driven, offline fallback netaknut).
- `app.js` — `loadBrandOverview()` sa ekran-specifičnim markerom (`if(!nameEl) return;`), `escapeHtml` na voice/facts, `textContent` na name/audience (inherentno XSS-safe), immediate fast path + `pywebviewready` fallback (BF-1/BF-2 obrasci iz ACS-F1-046 primenjeni OD PRVE VERZIJE).

**Odluka dokumentovana**: `description` (opis brenda) NIJE u DTO — `BrandSnapshot` nema brand-description polje; `brand-voice`/`brand-resources` paneli ostaju fixture-only (domain nema editor/resurse). Ne izmišljam podatke.

## Testovi (stvarno pokrenuto u worktree)

```text
pytest (bridge + contracts + ui_models + brend_ssr + static_pages) -> 145 passed
pytest -q (ceo suite)                                                -> 1124 passed, 1 failed*
ruff check (9 fajlova)                                               -> All checks passed
mypy (4 source fajla)                                                -> Success
node --check app.js                                                 -> OK
```

Ključni dokazi:
- `test_get_brand_overview_returns_real_brand_and_facts` — 3 fakt-a (fact-location/implants/team) tačno iz brightsmile.json.
- `test_get_brand_overview_filters_non_approved_facts` — SUPERSEDED fakt (linkovan na snapshot) se NE pojavljuje.
- `test_get_brand_overview_lifecycle_failure_returns_safe_exact_dto` — tačan key-set + bez leak-a u log/rezultat.
- `test_render_body_emits_brand_hydration_markers` + `test_app_js_has_brand_hydration_with_escape_and_lifecycle` + `test_write_all_pages_brend_carries_hydration_markers`.

`*` — `test_gate_report_against_current_repo_passes` je **flaky/pre-existing**, NE vezan za ovaj task: pada SAMO kad se pokreće unutar celog suite-a (rekurzivni subprocess `pytest -q` pokreće 1123 testova dok spoljašnji suite još radi); izolovano prolazi (7 passed), a `ACS_GATE_REPORT_RUNNING=1 python -m pytest -q` daje 1123 passed / 2 skipped. Nije uzrokovan brend izmenama.

## GitNexus

- Index up-to-date (`640f018`).
- `CampaignBridgeApi` upstream → LOW (1 — samo `__main__.py` import). Izmena je čisto aditivna (novi read metod), nema promena u repo sloju (`get_brand`/`get_snapshot`/`list_snapshot_facts` su VEĆ postojale i netaknute).
