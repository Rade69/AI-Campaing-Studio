# ACS-GUI-009 (v2) — fix-brief za Crush (poslije Codex REJECT)

Odnosi se na: `H:\ai-campaign-studio-worktrees\ACS-GUI-009-pregled-izvoz-export-v2\agent_reports\2026-09-07-ACS-GUI-009-review-codex.md`
(verdict REJECT, 3 blocking findings). Coordinator (Claude) je SVA TRI nalaza
nezavisno reprodukovao PRIJE pisanja ovog briefa — vidi "Nezavisna
verifikacija" ispod. Ovo je jedini fix-brief za v2 rundu (nije nastavak
ranijeg fix-brief-1 — v1→v2 prelaz je bio pokriven addendumom, ne
fix-briefom).

PR #9 se NE MERGE-uje dok Codex ne ponovi review i ne da PASS. Ovo je HIGH task
— pun ciklus (implementer → Claude → Codex → Human Owner) i dalje važi.

## Nezavisna verifikacija (coordinator, prije ovog briefa)

- **BF-1**: reprodukovano direktnim pozivom `_resolve_ai_adapter()` sa
  mock-ovanim `_resolve_provider` (vraća sentinel API ključ
  `sk-SECRET-SENTINEL-GUI009`) i `build_text_generation_adapter` koji baca
  `RuntimeError("adapter rejected credential=" + api_key)`. Rezultat:
  `secret_in_result=False`, `secret_in_logs=True` — traceback sa sentinel
  ključem doslovno završava u application logu preko `logger.exception(...)`.
- **BF-2**: pročitan `zip_exporter.py` — potvrđeno `ZipFile(out, mode="w")`
  direktno otvara `output_path` bez atomic temp+rename. Pročitan
  `export_campaign_package` (linije 897-973 u trenutnom stanju) — potvrđeno da
  NEMA `with self._lock_for(...)` niti bilo kog drugog lock-a oko koraka
  3-5 (visual system → layout loop → `ExportCampaign.execute`); jedini lock
  (`_visual_system_by_plan_guard`) štiti SAMO jednu dict mutaciju. Vlastita
  reprodukcija: 2 threada, `threading.Barrier`, oba pozivaju stvaran
  `ZipExportWriter().write_zip()` na ISTU putanju → **7/30 korumpiranih ZIP
  arhiva** (isti red veličine kao Codex-ovih 9/50).
- **BF-3**: pročitan `_seed_brand_and_campaign` helper — potvrđeno
  `plan = CampaignPlan(id="plan-1", ...)` i `CampaignItemId(f"item-{i+1}")` su
  HARDKODIRANI literali, nezavisni od `campaign.id`. Dva poziva helpera
  proizvode dva RAZLIČITA `campaign.id`, ali ISTI `plan-1`/`item-1...` — drugi
  `save_plan` poziv piše/rebinda isti plan-id, pa naivan "pozovi helper dva
  puta" test NE testira dva nezavisna plana, testira isti plan-red prepisan
  drugi put.

Sva tri nalaza su potvrđena kao stvarna, ne false-positive. Prelazimo na fix.

## Fix 1 — BF-1: ukloniti secret-in-log rizik

**Lokacija**: `bridge/__init__.py`, `_resolve_ai_adapter`, `except Exception:`
grana oko poziva `build_text_generation_adapter(provider_code, api_key)`.

**Šta promijeniti**: zamijeniti

```python
except Exception:
    self._bootstrap.logger.exception(
        "adapter factory failed for %s", provider_code
    )
```

sa type-only, no-traceback logovanjem — isti obrazac kao `configure_provider`
(ACS-GUI-007 BF-3 fix):

```python
except Exception as exc:
    self._bootstrap.logger.error(
        "adapter factory failed for %s (%s)",
        provider_code,
        type(exc).__name__,
    )
```

NE koristiti `logger.exception` niti proslijediti `exc`/`str(exc)` u poruku —
oba mogu sadržati credential tekst koji SDK ubaci u exception message.
`provider_code` je siguran (nije secret).

**Test** (novi, u `test_campaign_bridge_api.py`): `caplog`-baziran sentinel
test — mock `_resolve_provider` da vrati sentinel ključ, mock
`build_text_generation_adapter` da baci `RuntimeError` SA sentinel ključem u
poruci, pozvati `export_campaign_package` (ili direktno `_resolve_ai_adapter`
ako je lakše testabilno), assert da sentinel NIJE nigdje u `caplog.text`, i da
JE u rezultatu prisutan generic `error_code` bez secret sadržaja.

## Fix 2 — BF-2: serializovati cijelu export sekvencu

**Lokacija**: `export_campaign_package`, koraci 3-5 (linije ~897-973).

**Šta promijeniti**: cijela sekvenca (get/create visual system → layout loop →
`ExportCampaign.execute`) mora biti unutar JEDNOG lock-a keyed po
`(campaign_id, plan_id)`, isti `_lock_for` koji `generate_campaign_content`
već koristi (linija 557: `with self._lock_for(str(campaign_id),
str(plan_id)):`). Obrazac:

```python
with self._lock_for(str(campaign_id), str(plan_id)):
    # postojeći koraci 3, 4, 5 (visual system, layout loop, ExportCampaign)
```

Ovo AUTOMATSKI zamjenjuje potrebu za `_visual_system_by_plan_guard` u ovoj
putanji (širi lock ga obuhvata) — `_visual_system_by_plan_guard` NE brisati
ako ga koristi neki drugi caller, ali provjeriti da li je poslije ovog fixa i
dalje potreban bilo gdje drugo.

NE mijenjati semantiku "svaki export je novi `DistributionInstance`
događaj" — lock samo serializuje, ne deduplicira uzastopne pozive.
NE uvoditi DB-backed lock niti mijenjati `ExportCampaign`/`ZipExportWriter`
potpise (forbidden per Codex "NE DIRATI").

**Test** (novi): deterministički dva-worker-thread test sa
`threading.Barrier`, pozivajući STVARNI `export_campaign_package` (ne samo
`ZipExportWriter` izolovano) dva puta konkurentno za ISTI
`(campaign_id, plan_id)` (koristeći `_seed_brand_and_campaign` +
`_approve_plan` iz postojećeg test helpera). Assert: tačno JEDAN validan ZIP
na disku (`zipfile.ZipFile(...).testzip() is None`), i NIJE kreiran duplirani
`CampaignVisualSystem` red (broj redova u `visual_systems` tabeli za taj plan
== 1).

## Fix 3 — BF-3: dvije nove regresijske putanje + helper fix

**3a. Cross-campaign ownership test** — koristiti `_seed_brand_and_campaign`
DVA PUTA, ali sa eksplicitno različitim `item_topic_prefix` NIJE dovoljno jer
`plan-1`/`item-1...` ostaju isti. Prije pisanja testa, prvo popraviti helper:

Helper fix — dodati opcioni parametar (npr. `plan_id_suffix: str = "1"`) i
koristiti ga u `id="plan-1"` → `id=f"plan-{plan_id_suffix}"` i
`CampaignItemId(f"item-{plan_id_suffix}-{i+1}")`, TAKO DA postojeći pozivi
(default `plan_id_suffix="1"`) ostanu bit-for-bit isti kao danas (ne kvariti
postojeće testove) ali novi pozivi mogu tražiti `plan_id_suffix="2"` za
genuinely nezavisan drugi campaign/plan par.

Novi test: seed campaign A (plan-1) i campaign B (plan-2) sa
`plan_id_suffix="2"`; pozvati `export_campaign_package({"campaign_id":
A, "plan_id": <plan B's id>})`; assert `ok=False`,
`error_code=_ERROR_VALIDATION`, poruka sadrži "ne pripada kampanji".

**3b. Export lifecycle-failure DTO test** — mock/patch da `create_connection`
(ili ekvivalentna tačka unutar `ExportCampaign`/repo sloja koju export
putanja koristi) baci exception TOKOM `export_campaign_package` poziva (ne
tokom `generate_campaign_content` — postojeći lifecycle testovi pokrivaju
samo configure/create/generate-content, NE export). Assert da vraćeni dict
ima TAČNO ovaj key-set (ni više ni manje):
`campaign_id, error_code, error_message, exported_count, ok, skipped_count,
zip_path` — i da nijedna vrijednost ne sadrži path/traceback/secret tekst
mimo onoga što je već dozvoljeno (`zip_path` je dozvoljen kao path per
postojeći docstring, ali samo na `ok=True` grani — na `ok=False` grani
`zip_path` treba biti `None`, potvrditi stvarno ponašanje i testirati ga
eksplicitno).

## Šta NE dirati (Codex-ovo ograničenje, i dalje važi)

- `domain/`, `application/`, `ports/`, `infrastructure/` (osim
  `zip_exporter.py` AKO fix 2 to zahtijeva — trenutni plan NE zahtijeva
  izmjenu tog fajla, lock je dovoljan na bridge nivou), migracije.
- Semantika "svaki export = nova `DistributionInstance`".
- Nema DB-backed visual-system lookup/schema promjena.
- `approve-gate` ostaje UI-only.

## Verifikacija prije re-review-a

```bash
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Sve mora proći, 0 regresija u postojećim testovima (uključujući postojeće
pozive `_seed_brand_and_campaign` bez novog parametra — moraju ostati
identični). Poslije zelenog run-a, tražiti Codex rereview PR #9-a. HIGH task
ne ide na Human Owner approval dok Codex ne da PASS na sva tri nalaza.
