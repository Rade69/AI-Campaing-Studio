# ACS-GUI-009 (v2) — implementer evidence (Crush)

Task: Pregled i izvoz — stvaran vizuelni sistem + layout + render + ZIP export.
Addendum: `agent_reports/ACS-GUI-009-addendum-post-hotfix002.md`.
Branch: `task/ACS-GUI-009-pregled-izvoz-export-v2` (worktree `../ACS-GUI-009-pregled-izvoz-export-v2`, base `057386e`).
Status: implementacija + testovi gotovi. Čeka review (Claude → Codex adversarial → Human Owner odobrenje).

## Šta je urađeno

1. `bridge/__init__.py` — nova `@_with_call_resources` metoda
   `export_campaign_package(raw_payload)` koja prima `{campaign_id, plan_id}`
   (addendum §3 — `plan_id` direktno u payload-u, NE preko `campaign-routes.json`),
   pa: (a) validira + učitava kampanju/plan i eksplicitno odbija ne-APPROVED plan
   (uključujući `SUPERSEDED`, BF-4 ekvivalent, 0 AI poziva), (b) idempotentno
   kreira `CampaignVisualSystem` preko in-process `self._visual_system_by_plan`
   mape (addendum §4 — NEMA JSON cache), (c) generiše `LayoutSpec` po piece-u sa
   partial-failure tolerancijom, (d) poziva `ExportCampaign` sa TAČNIH 7 portova
   (uključujući `performance_repo`) i vraća `zip_path`/`exported_count`/
   `skipped_count`.
   - `_CallResources` proširen sa `visual_repo` + `performance_repo` + property
     getter-i (addendum §5).
   - `_LIFECYCLE_ERROR_MAPPERS`/`_LIFECYCLE_ERROR_MESSAGES` dobili
     `"export_campaign_package": "_export_err"` (addendum §6).
   - Dodat `_export_err` (dedicated `ExportCampaignResultUiModel` shape).
   - Dodat `_resolve_ai_adapter` (ponovno koristi `_resolve_provider` +
     `build_text_generation_adapter`).

2. `presentation/contracts.py` + `presentation/ui_models.py` — dodat
   `export_campaign_package` u `PresentationFacade` + novi
   `ExportCampaignResultUiModel` (addendum §3, isti obrazac kao GUI-008).

3. `screens/pregled_izvoz/__init__.py` — "Izvezi ZIP paket" je sada
   `data-action="export-campaign"` i UVIJEK emitovan (`hidden` + `disabled`,
   prazni `data-campaign-id`/`data-plan-id`); "Odobri kampanju" je
   `data-action="approve-gate"` (UI-only gate, bez backend poziva).

4. `static/app.js` — dodati `approve-gate`/`export-campaign` handler-i +
   `exportCampaign` funkcija + proširen boot IIFE da otkrije export dugme kad su
   oba `?campaign=`/`?plan=` prisutna (addendum §7, isti obrazac kao
   `generate-content`).

## Testovi

- `tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py` — 7 novih
  testova (boundary validation, missing ids, unknown campaign, plan-not-APPROVED,
  no-provider, happy path + idempotentnost + ZIP na disku, partial layout
  failure → skipped_count=1).
- `tests/unit/presentation_webview/test_pregled_izvoz_ssr.py` — 2 testa ažurirana
  (approve-gate + export-campaign, ne više toast stub).
- `tests/unit/presentation_webview/test_static_pages_generator.py` — 1 novi test
  `test_write_all_pages_pregled_izvoz_carries_live_export_button` (addendum §7).
- `tests/unit/presentation/test_contracts.py` + `test_ui_models.py` — dopune.

Rezultati (stvarno pokrenuto, worktree):

```text
pytest tests/.../test_campaign_bridge_api.py -k export  -> 7 passed
pytest (ssr + contracts + ui_models + static_pages)     -> 51 passed
pytest -q (ceo suite)                                    -> 1065 passed, 0 failed
ruff check (9 izmenjenih fajlova)                        -> All checks passed
mypy (4 source fajla)                                    -> Success
```

## GitNexus

- Index up-to-date (`057386e`).
- Impact (iz glavnog checkout-a, jer je index vezan tamo):
  - `ExportCampaign` upstream → LOW, 1 (samo `__init__.py` import).
  - `GenerateVisualSystem` upstream → LOW, 0.
  - `PlanPostLayout` upstream → LOW, 0.
- `detect-changes` NIJE pokrenut: radi se tek nakon commit-a (uncommitted diff u
  worktree-u nije vidljiv indexu vezanom za glavni checkout). Korak za
  koordinatora poslije commit-a (workflow §6 + CURRENT_STATE "Trajna napomena").

## Scope napomena

`tests/unit/presentation_webview/test_static_pages_generator.py` NIJE u
originalnom `allowed_paths` task contracta, ali je DODAT jer addendum §7
eksplicitno traži write_all_pages test "isti obrazac kao
`test_write_all_pages_studio_sadrzaja_carries_live_generate_button`", a taj test
živi samo u tom fajlu. Nema izmena van ova 10 fajla; `domain/`, `application/`,
`ports/`, `infrastructure/`, `resources/migrations/`, `studio_sadrzaja/` netaknuti.

## Nepotvrđeno

- Nisam pokretao stvarnu pywebview aplikaciju (nema live end-to-end GUI
  verifikacije; bridge testovi su integration-style sa stvarnom SQLite + fake AI +
  pravim `PillowRenderer`/`ZipExportWriter`).
