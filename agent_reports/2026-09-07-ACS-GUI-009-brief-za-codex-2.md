# → ZA CODEX — ACS-GUI-009 (v2) re-review (PR #9, poslije BF-1/2/3 fixa)

PR #9: https://github.com/Rade69/AI-Campaing-Studio/pull/9
Branch: `task/ACS-GUI-009-pregled-izvoz-export-v2` (rebase-ovan na main
kroz ACS-F1-045/046/047, HEAD `a0eb87a`).
Implementer: Crush. Fix evidence:
`agent_reports/2026-09-07-ACS-GUI-009-fix-v2-evidence.md`.

Odnosi se na tvoj REJECT:
`agent_reports/2026-09-07-ACS-GUI-009-review-codex.md` (BF-1, BF-2, BF-3).

## Šta je popravljeno (nezavisno provjereno prije ovog handoff-a)

- **BF-1** (secret-in-log): `_resolve_ai_adapter`-ov `except Exception:`
  oko `build_text_generation_adapter(...)` sad koristi `logger.error(
  "adapter factory failed for %s (%s)", provider_code,
  type(exc).__name__)` umjesto `logger.exception(...)` -- bez
  traceback-a, bez `str(exc)`. Mutation-testirao SAM ovo (privremeno
  vratio `logger.exception`, pokrenuo `test_export_adapter_factory_failure_does_not_log_secret`
  sa sentinelom `sk-SECRET-SENTINEL-GUI009` -- test PUKAO, sentinel u
  `caplog.text`; vraćen fix -- test prošao).
- **BF-2** (concurrent ZIP korupcija): cijela `export_campaign_package`
  sekvenca (get/create visual system → layout petlja →
  `ExportCampaign.execute`) je sad unutar JEDNOG
  `with self._lock_for(str(campaign_id), str(plan_id)):`, isti lock
  koji `generate_campaign_content` koristi. Mutation-testirao SAM ovo
  (vraćen stari kod bez lock-a, `test_export_campaign_package_concurrent_same_plan_produces_one_valid_zip`
  PUKAO 5/5 pokušaja; vraćen fix -- prošao 5/5).
- **BF-3**: `_seed_brand_and_campaign` proširen (`plan_id`/
  `item_id_prefix` parametri, backward-compatible defaults) da omogući
  DVA genuinely nezavisna campaign/plan para u istoj bazi. Novi testovi:
  cross-campaign plan rejection (`VALIDATION_ERROR`, "ne pripada
  kampanji") i tačan DTO key-set na `create_connection` lifecycle
  failure (`ok=False, zip_path=None`, ostala polja `None`, TAČNO 7
  ključeva).

## Napomena o rebase-u (veliki, ručno riješen konflikt)

Branch je bio baziran na main-u OD PRIJE ACS-F1-045/046/047 (sva tri su
u međuvremenu merge-ovana). Rebase je proizveo veliki konflikt u
`bridge/__init__.py` (nove `get_job_status`/`cancel_job`/
`_LIFECYCLE_ERROR_MAPPERS` iz F1-047 vs. novi `export_campaign_package`
iz GUI-009 -- oba dodaju metode na istom mjestu) i u
`test_campaign_bridge_api.py` (F1-047-ovi novi testovi vs. GUI-009-ovi
novi testovi, plus DVIJE različite verzije `_seed_brand_and_campaign`-a
sa različitim parametar-imenima -- `plan_id`/`item_id_prefix` iz F1-047
protiv `plan_id_suffix` iz Crush-ovog GUI-009 fixa). Riješio sam ručno:
zadržao F1-047-ov parametar-oblik (već korišten od postojećih F1-047
testova), preveo Crush-ov novi cross-campaign test na taj oblik.
Provjerio brojem test funkcija prije/poslije (56+7=63, tačno) i punim
test/ruff/mypy run-om PRIJE push-a.

## Verifikacija (moja, nakon rebase-a)

```text
python -m pytest -q          -> 1087 passed
python -m ruff check .       -> All checks passed!
python -m mypy src           -> Success: no issues found in 175 source files
```

CI na PR #9: zeleno.

## OUT_OF_SCOPE napomena (Crush-ova, potvrđena)

`create_campaign_and_generate_plan` (linija ~417) i
`generate_campaign_content` (linija ~810) imaju ISTI
`logger.exception("adapter factory failed for %s", provider_code)`
secret-in-log obrazac -- postojeći kod iz GUI-005/008, van scope-a
ovog fix-briefa koji je pokrio SAMO `_resolve_ai_adapter`. Potvrdio
sam da su oba mjesta zaista nedirana. Preporuka: zaseban mali
hardening task za ova dva mjesta.

## Tvoj fokus za ovu rundu

- Ponovo provjeri BF-1/BF-2/BF-3 fix-eve (kod, ne samo evidence).
- Ponovo provjeri da rebase nije unio regresiju u dijeljenom kodu
  (`_LIFECYCLE_ERROR_MAPPERS`, `_seed_brand_and_campaign`,
  `get_job_status`/`cancel_job` iz F1-047 i dalje rade zajedno sa
  `export_campaign_package`).
- Standardna adversarial provjera: secret sentinel, concurrent export,
  cross-campaign ownership, lifecycle DTO shape.

Kad završiš, javi rezultat -- koordinator prenosi Human Owner-u za
odobrenje prije merge-a (HIGH risk, pun ciklus).
