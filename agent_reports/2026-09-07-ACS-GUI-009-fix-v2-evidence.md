# ACS-GUI-009 (v2) — fix evidence (Crush, poslije Codex REJECT)

Fix-brief: `agent_reports/2026-09-07-ACS-GUI-009-fix-brief-za-crush.md`.
Branch: `task/ACS-GUI-009-pregled-izvoz-export-v2` (worktree `../ACS-GUI-009-pregled-izvoz-export-v2`).
Status: sva 3 blocking nalaza (BF-1/BF-2/BF-3) popravljena + testovi zeleni. Čeka Codex re-review.

## Fix 1 — BF-1 (secret-in-log)

`_resolve_ai_adapter` (`bridge/__init__.py`): `logger.exception(...)` → `logger.error("...%s (%s)", provider_code, type(exc).__name__)` — bez traceback-a/`str(exc)`, isti obrazac kao `configure_provider` (ACS-GUI-007 BF-3).

**Mutation-dokazano** (privremeno vratio `logger.exception`, pokrenuo test): test PADA sa sentinelom `sk-SECRET-SENTINEL-GUI009` u `caplog.text`; vraćen `logger.error` → test prolazi. Test nije lažan.

## Fix 2 — BF-2 (concurrent ZIP korupcija)

Cijela export sekvenca (get/create visual system → layout loop → `ExportCampaign.execute`) sada je unutar JEDNOG `with self._lock_for(str(campaign_id), str(plan_id)):` — isti lock koji `generate_campaign_content` već koristi. Lock takođe čini visual-system idempotentnost atomičnom (TOCTOU eliminisan).

Test `test_export_campaign_package_concurrent_same_plan_produces_one_valid_zip`: `threading.Barrier(2)`, dva worker threada na stvarni `export_campaign_package` za isti `(campaign_id, plan_id)`; assert `ZipFile(...).testzip() is None` (validan) + `COUNT(*) campaign_visual_systems == 1` (nedupliran).

## Fix 3 — BF-3 (test gaps + helper bug)

- **3a** — `_seed_brand_and_campaign` dobio `plan_id_suffix: str = "1"`; `id=f"plan-{plan_id_suffix}"` i `CampaignItemId(f"item-{plan_id_suffix}-{i+1}")`. Default pozivi i dalje prolaze (nijedan test ne asertuje item-id literal). Novi test `test_export_campaign_package_plan_from_other_campaign_returns_validation_error` seeduje DVA nezavisna campaign/plan para (`suffix="1"`/`"2"`) i assertuje `VALIDATION_ERROR` + "ne pripada kampanji".
- **3b** — novi test `test_export_campaign_package_lifecycle_failure_returns_exact_dto_keys`: patch `create_connection` → `RuntimeError`; assert tačan key-set `{ok, campaign_id, zip_path, exported_count, skipped_count, error_code, error_message}` + `ok=False`, `zip_path=None`, `exported_count=None`, `skipped_count=None`.

## Verifikacija (stvarno pokrenuto u worktree)

```text
pytest tests/.../test_campaign_bridge_api.py     -> 60 passed
pytest -q (ceo suite)                             -> 1069 passed, 0 failed
ruff check (bridge + test)                        -> All checks passed
mypy (bridge)                                     -> Success
```

## OUT_OF_SCOPE napomena (ne dirano, za budući review)

`bridge/__init__.py` linije ~412 (`create_campaign_and_generate_plan`) i ~706 (`generate_campaign_content`) imaju ISTI `logger.exception("adapter factory failed for %s", provider_code)` bez type-only zaštite. To je postojeći kod iz ACS-GUI-005/008 (van scope-a ovog fix-briefa koji je pokrio SAMO `_resolve_ai_adapter`). Istovjetan secret-in-log rizik postoji tamo; preporučujem zaseban mali hardening task.
