# → ZA CODEX — ACS-GUI-009 adversarial review

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-07

Drugi export-tier HIGH-risk bridge task nakon ACS-GUI-008 (koje je
prošlo kroz tri runde prije PASS-a). Ovaj put: prvi GUI poziv
`GenerateVisualSystem`/`PlanPostLayout`/`ExportCampaign`.

## Šta pregledati

```text
agent_reports/ACS-GUI-009-task-contract.md (originalni kontrakt)
agent_reports/ACS-GUI-009-addendum-post-hotfix002.md (kako se pomirilo sa GUI-008/HOTFIX-002)
agent_reports/2026-09-07-ACS-GUI-009-export-v2-evidence.md
PR: https://github.com/Rade69/AI-Campaing-Studio/pull/9 (commit ebfb50e, CI zeleno)

src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  (nova export_campaign_package metoda, ~180 linija; _CallResources +
  visual_repo/performance_repo; _LIFECYCLE_ERROR_MAPPERS dobio treći
  unos; nov self._visual_system_by_plan in-process dict)
src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/__init__.py
src/ai_campaign_studio/presentation_webview/static/app.js
  (approve-gate UI-only handler + exportCampaign handler + IIFE prošireno)
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  (7 novih export testova)
tests/unit/presentation_webview/test_static_pages_generator.py
  (write_all_pages test za pregled_izvoz)
```

## Šta sam ja već nezavisno provjerio

- Diff scope tačno 10 fajlova + evidence, `domain/`/`application/`/
  `ports/`/`infrastructure/`/`resources/migrations/`/`studio_sadrzaja/`
  netaknuti.
- **Mutation-testirao status-provjeru** (plan mora biti APPROVED) --
  privremeno uklonio, potvrdio da test STVARNO padne (stiže do
  `NO_PROVIDER_CONFIGURED` umjesto `VALIDATION_ERROR`, dokazuje da bi
  export nastavio za DRAFT/SUPERSEDED plan), vratio.
- Pročitao `test_export_campaign_package_happy_path_writes_zip_and_is_idempotent`
  direktno -- STVARNO otvara ZIP sa diska, provjerava PNG magic bytes,
  `manifest.json`, DIREKTAN SQL COUNT na `distribution_instances` (2) i
  `campaign_visual_systems` (1, NAKON DVA export poziva -- idempotentnost
  dokazana SQL-om, ne pretpostavkom).
- GitNexus impact (glavni checkout, PRIJE merge-a): `ExportCampaign`
  LOW (1 postojeći importer, `__init__.py`), `GenerateVisualSystem` LOW
  (0 postojećih pozivalaca). Očekivano -- ovo je PRVI GUI poziv.
- 1065/1065 test, ruff/mypy čisti, CI zeleno na PR #9 za tačan commit
  `ebfb50e`.
- BF-1 ekvivalent (uvijek-emitovano dugme + `write_all_pages()` test)
  primijenjen isto kao GUI-008.

## Posebno fokusiraj (tvoj posao)

- **Konkurentnost oko `_visual_system_by_plan` dict-a**: implementer je
  SVJESNO odlučio da NE stavi puni per-campaign lock (kao BF-3 za
  `generate_campaign_content`) jer je duplirani `CampaignVisualSystem`
  "osirotjeli red, ne dupliran izvezeni sadržaj". Slažeš li se da je
  ovo dovoljno, ili postoji scenario gdje TO ipak korumpira export
  (npr. dva konkurentna poziva, svaki sa SVOJIM `visual_system_id`,
  oba prosljeđena u `PlanPostLayout`/`ExportCampaign` -- da li bi to
  moglo ostaviti `LayoutSpec` redove koji pokazuju na POGREŠAN/obrisan
  vizuelni sistem, ili je to i dalje bezopasno)?
  - `_get_cached_visual_system`-ova ČITANJE ne koristi
    `_visual_system_by_plan_guard` (samo PISANJE ga koristi) -- da li
    to predstavlja stvaran problem pod GIL-om ili je bezopasno kao
    "belt-and-braces" (isti stil kao GUI-008 review komentar)?
- **Da li `ExportCampaign`-ov ponovljeni poziv (svaki export = novi
  `DistributionInstance` red po piece-u, ACS-F1-039 dizajn) uzrokuje
  stvaran problem kod konkurentnog/uzastopnog dvoklika ovdje** -- ili
  je to već prihvaćeno ponašanje iz ranijeg review-a (svaki export je
  "nov distribution event")? Vrijedi provjeriti da li GUI kontekst
  mijenja tu procjenu (korisnik može slučajno duplo kliknuti brže nego
  što bi CLI/test scenario ikad uradio).
- Da li `plan.campaign_id != campaign_id` cross-check (isti obrazac
  kao GUI-008) STVARNO pokriven testom sa DVIJE prave kampanje, ne
  samo pretpostavljen?
- Secret safety na svim error putevima (isti standard kao GUI-008 BF-5
  -- provjeri da `_export_err` STVARNO ima ispravan
  `ExportCampaignResultUiModel` oblik na resource-lifecycle failure
  putanji, ne samo na domain-error putanji).

## Kad završiš

Standardan format (verdict/scope/acceptance/architecture/security/tests
YAML header + narativ). Ako PASS/PASS_WITH_NOTES, ide na Human Owner
odobrenje (HIGH risk).
