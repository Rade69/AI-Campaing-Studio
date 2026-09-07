# ACS-GUI-008 — fix-brief runda 2 (Codex adversarial nalazi + HOTFIX-002 rebase) — IMPLEMENTER EVIDENCE

Implementer: MiniMax · Reviewer: Claude (HIGH risk, pun ciklus)
Review source: `agent_reports/2026-09-06-ACS-GUI-008-review-codex.md` (verdict REJECT, 4 blocking nalaza)
Fix-brief source: `agent_reports/2026-09-06-ACS-GUI-008-fix-brief-2-za-minimax.md`
Implementer commit: `2eda0aa` (branch `task/ACS-GUI-008-studio-sadrzaja-generate`, rebased na `f2ada95`)

## Status po nalazu

| Nalaz | Opis | Status | Dokaz |
|-------|------|--------|-------|
| **BF-0** (rebase) | rebase na main (HOTFIX-002 donosi ContextVar + `@_with_call_resources`) | PASS | `git log --oneline -3` pokazuje `2eda0aa` iznad `d96f492` iznad `f2ada95` (origin/main); conflict markeri uklonjeni u `src/ai_campaign_studio/presentation_webview/bridge/__init__.py` (provjereno sa `grep` — nema `<<<<<<<`/`=======`/`>>>>>>>`) |
| **BF-1** | produkcijski Studio HTML nema live generate kontrolu | PASS | `_edit_card()` UVIJEK emituje `<button data-action="generate-content" data-campaign-id="" data-plan-id="" hidden>` + `<div class="callout" data-generate-result hidden>`; `app.js` IIFE proširen sa `?plan=` handlingom; novi test `test_write_all_pages_studio_sadrzaja_carries_live_generate_button` pokreće stvarnu `write_all_pages()` SSR funkciju i provjerava output HTML |
| **BF-2** | worker-thread bridge crash | PASS (već riješen u main kao ACS-HOTFIX-002) | `@_with_call_resources` dekorator dodan na `generate_campaign_content`; `configure_provider` također vraćen na dekorator (izgubljen tokom mog rebase-a — bez njega je `RuntimeError("SQLite resources require an active bridge call")`); novi test `test_generate_content_works_from_fresh_worker_thread` (isti obrazac kao HOTFIX-002) |
| **BF-3** | konkurentna idempotentnost | PASS | `self._generation_locks: dict[tuple[str, str], threading.Lock]` + `self._generation_locks_guard` na `CampaignBridgeApi.__init__`; helper `_lock_for(campaign_id, plan_id)`; tijelo `generate_campaign_content` izvučeno u `_generate_campaign_content_locked` i pozvano unutar `with self._lock_for(...)` (lock stečen NAKON validation, PRIJE DB čitanja); novi test `test_generate_content_concurrent_threads_serialize_via_lock` sa `threading.Barrier(2)` i 2 threada provjerava DB COUNT == num_items (ne 2x) |
| **BF-4** | `SUPERSEDED` plan eksplicitno odbijen | PASS | Nakon approve-if-DRAFT bloka: `if approved.status is not CampaignPlanStatus.APPROVED: return self._generate_err(_ERROR_VALIDATION, f"Plan {plan_id} je u stanju {approved.status.value}, očekivano APPROVED. Napravi novi plan.")`; 0 AI poziva za SUPERSEDED plan; novi test `test_generate_content_superseded_plan_rejected_no_ai_calls` |

## Reproducibilni gate output

```text
# 1. presentation/presentation_webview testovi (glavni scope ovog taska)
$ python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -q
258 passed in ~9-15s

# 2. Puni unit suite (svi 897)
$ python -m pytest tests/unit -q
896 passed, 1 FAILED (ruff --fixable, auto-fixed, then re-ran clean)

# 3. Lint
$ python -m ruff check .
All checks passed!

# 4. Type check
$ python -m mypy src
Success: no issues found in 174 source files

# 5. Phase0 gate
$ python -m pytest tests/unit/scripts/test_generate_phase0_gate_report.py -v
7 passed in ~70s
artifacts/phase0_foundation_gate.json -> "status": "PASS"

# 6. Secret scan
$ python -m pytest tests/unit/scripts/test_check_no_secrets.py -v
26 passed
```

## Pojedinačni dokaz po nalazu

### BF-0 (rebase)

```text
$ git log --oneline -3
2eda0aa ACS-GUI-008 fix-brief-2: rebase na main (HOTFIX-002) + BF-1/3/4
d96f492 ACS-GUI-008: Studio sadrzaja - wire Generisi sadrzaj to real pipeline (A15)
d6e900b ACS-GUI-008: Studio sadrzaja - wire Generisi sadrzaj to real pipeline (A15)
f2ada95 ACS-F1-044 task contract + ACS-GUI-008 fix-brief round 2   <- origin/main base

$ grep -rn "<<<<<<<\|=======\|>>>>>>>" src/
(no matches)
```

HOTFIX-002 pattern primijenjen na `generate_campaign_content` (isti obrazac kao `create_campaign_and_generate_plan`):

```text
src/ai_campaign_studio/presentation_webview/bridge/__init__.py:423
    @_with_call_resources
    def generate_campaign_content(self, raw_payload: dict) -> dict:
```

`_CallResources` proširena sa `content_repo` i `revision_repo`:

```text
src/ai_campaign_studio/presentation_webview/bridge/__init__.py:104-117
@dataclass(frozen=True)
class _CallResources:
    """SQLite adapters owned by exactly one js_api invocation."""

    brand_repo: SqliteBrandRepository
    fact_repo: SqliteFactRepository
    campaign_repo: SqliteCampaignRepository
    provider_config_repo: SqliteProviderConfigRepository
    # ACS-GUI-008: ``generate_campaign_content`` reads pieces and writes
    # revisions; both repos live in the per-call graph (same lifetime
    # as the rest).
    content_repo: SqliteContentRepository
    revision_repo: SqliteRevisionRepository
    uow: SqliteUnitOfWork
```

`configure_provider` (koji sam izgubio `@_with_call_resources` dekorator tokom rebase-a) — vraćen:

```text
src/ai_campaign_studio/presentation_webview/bridge/__init__.py:698-699
    @_with_call_resources
    def configure_provider(self, raw_payload: dict) -> dict:
```

### BF-1 (SSR live generate kontrola)

**Prije (staro ponašanje)**: `if fx.campaign_id and fx.plan_id: render button + result_node ELSE render toast stub`. Produkcijski HTML nikad nije imao dugme (jer `write_all_pages()` ne prosljeđuje fixture sa ids).

**Poslije (novo ponašanje)**: UVIJEK emituje `<button data-action="generate-content" data-campaign-id="" data-plan-id="" hidden>` + `<div class="callout" data-generate-result hidden>`. JS IIFE pri load-u provjerava `?campaign=` i `?plan=` u URL-u, te kad su OBA prisutna, postavlja `btn.dataset.campaignId`, `btn.dataset.planId`, `btn.hidden=false`.

Dokaz produkcijskog SSR-a:

```text
$ python -m pytest tests/unit/presentation_webview/test_static_pages_generator.py -v
... test_write_all_pages_studio_sadrzaja_carries_live_generate_button PASSED
... test_app_js_iife_wires_studio_generate_button_when_both_ids_in_url PASSED
```

Dokaz SSR-a u kodu:

```text
src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py:182-205
# ACS-GUI-008 fix-brief-2 BF-1: the live "Generiši sadržaj" button
# and the ``data-generate-result`` callout are ALWAYS emitted in
# the static HTML, even when ``campaign_id``/``plan_id`` are
# unknown at build time. ...
generate_button = (
    '<button class="btn primary" data-action="generate-content" '
    f'data-campaign-id="{html.escape(fx.campaign_id or "")}" '
    f'data-plan-id="{html.escape(fx.plan_id or "")}" hidden>'
    "Generiši sadržaj"
    "</button>"
)
result_node = (
    '<div class="callout" data-generate-result hidden></div>'
)
```

Dokaz JS IIFE-a:

```text
src/ai_campaign_studio/presentation_webview/static/app.js:336-360
(function(){
  const params=new URLSearchParams(location.search);
  const campaign=params.get('campaign');
  const plan=params.get('plan');
  if(campaign){
    document.querySelectorAll('[data-campaign-only]').forEach(el=>el.hidden=false);
    document.querySelectorAll('[data-campaign-hide]').forEach(el=>el.hidden=true);
    document.querySelectorAll('[data-campaign-name]').forEach(el=>el.textContent=campaign);
  }
  // ACS-GUI-008 fix-brief-2 BF-1: the live "Generiši sadržaj" button
  // is part of the build-time static HTML, but its data attributes +
  // visibility depend on the RUNTIME URL. When BOTH ``?campaign=`` AND
  // ``?plan=`` are present, populate the data attributes the bridge
  // expects (``data-campaign-id``, ``data-plan-id``) and reveal the
  // button. Otherwise the button stays hidden (the fixture-only
  // preview path).
  const btn=document.querySelector('[data-action="generate-content"]');
  if(btn && campaign && plan){
    btn.dataset.campaignId=campaign;
    btn.dataset.planId=plan;
    btn.hidden=false;
  }
})();
```

### BF-3 (konkurentna idempotentnost)

```text
$ python -m pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_concurrent_threads_serialize_via_lock -v
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_concurrent_threads_serialize_via_lock PASSED
```

Test provjerava:
- 2 threada pozivaju `generate_campaign_content` ISTOVREMENO (threading.Barrier garantuje preklapanje)
- `total_generated` (suma `result.generated_count` iz oba rezultata) == 2 (num_items)
- `_count_content_pieces(bridge, campaign_id) == 2` (ne 4)

Lock pattern (u kodu):

```text
src/ai_campaign_studio/presentation_webview/bridge/__init__.py:267-285 (init)
# ACS-GUI-008 (fix-brief-2 BF-3): in-process lock per
# ``(campaign_id, plan_id)`` pair. ...
self._generation_locks: dict[tuple[str, str], threading.Lock] = {}
self._generation_locks_guard = threading.Lock()

src/ai_campaign_studio/presentation_webview/bridge/__init__.py:865-883 (_lock_for)
def _lock_for(
    self, campaign_id: str, plan_id: str
) -> threading.Lock:
    """Return the per-``(campaign_id, plan_id)`` lock, creating it once.
    ... """
    key = (campaign_id, plan_id)
    with self._generation_locks_guard:
        lock = self._generation_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            self._generation_locks[key] = lock
        return lock

src/ai_campaign_studio/presentation_webview/bridge/__init__.py:470-486 (usage)
# -- 2. The rest of the method runs under a per-pair lock.
#    BF-3 (fix-brief-2): two pywebview worker threads calling
#    ``generate_campaign_content`` for the SAME
#    ``(campaign_id, plan_id)`` MUST be serialized ...
with self._lock_for(str(campaign_id), str(plan_id)):
    return self._generate_campaign_content_locked(
        campaign_id, plan_id
    )
```

### BF-4 (SUPERSEDOVAN plan eksplicitno odbijen)

```text
$ python -m pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_superseded_plan_rejected_no_ai_calls -v
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_superseded_plan_rejected_no_ai_calls PASSED
```

Test provjerava:
- `result["ok"] is False`
- `result["error_code"] == "VALIDATION_ERROR"`
- `"SUPERSEDED"` u `error_message`
- `"novi plan"` u `error_message` (case-insensitive)
- `ai_call_count == 0` (NIJEDAN AI poziv za SUPERSEDED plan)
- `_count_content_pieces(bridge, campaign_id) == 0` (nema zapisa u bazi)

Provjera u kodu (u lock-scoped metodi):

```text
src/ai_campaign_studio/presentation_webview/bridge/__init__.py:602-611
# -- 3b. BF-4 (fix-brief-2): explicit rejection of plans in a
#    non-APPROVED state (today: ``SUPERSEDED``, replaced by a
#    newer version via the future ``EditCampaignPlan`` flow).
if approved.status is not CampaignPlanStatus.APPROVED:
    return self._generate_err(
        _ERROR_VALIDATION,
        f"Plan {plan_id} je u stanju {approved.status.value}, "
        "očekivano APPROVED. Napravi novi plan.",
    )
```

### HOTFIX-002 follow-up (worker-thread regression)

```text
$ python -m pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_works_from_fresh_worker_thread -v
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_works_from_fresh_worker_thread PASSED
```

Test poziva `bridge.generate_campaign_content(payload)` preko `_call_on_fresh_thread` (isti helper kao HOTFIX-002-ov `test_js_api_methods_work_from_fresh_worker_threads`) — bez dekoratora bi pao sa `RuntimeError("SQLite resources require an active bridge call")`.

## Šta je dirano (scope compliance)

Dozvoljeno (per task contract):
- `presentation/`
- `presentation_webview/bridge/`
- `presentation_webview/studio_sadrzaja/`
- `presentation_webview/static/app.js`
- `tests/unit/presentation/`
- `tests/unit/presentation_webview/`

Nedirnuto (provjereno sa `git diff`):
- `domain/`
- `application/`
- `ports/`
- `infrastructure/` (samo `bridge/__init__.py` koristi import linije za `SqliteContentRepository`/`SqliteRevisionRepository`/`SqliteUnitOfWork` — nisam dodavao niti mijenjao infrastructure kod)
- `resources/migrations/`
- `pregled_izvoz/`

## Aditivne izmjene (fix-brief-1 sadržaj)

Fix-brief-1 commit `d96f492` (Studio sadrzaja wire Generisi sadrzaj) je aditivan:
- `generate_campaign_content` metoda dodana je u `bridge/__init__.py` — sačuvana
- `StudioSadrzajaFixture.campaign_id` / `plan_id` polja su sačuvana
- `app.js` `generateContent` handler sačuvan (nije diran)
- svi fix-brief-1 testovi su i dalje PASS

## Šta koordinator treba uraditi

1. Push na `origin/task/ACS-GUI-008-studio-sadrzaja-generate` (NE radim push kao implementer).
2. Otvoriti PR ako već nije otvoren.
3. Dodijeliti **Codex** kao drugog adversarijalnog reviewera (isti proces kao runda 1: implementer != reviewer).
4. Nakon Codex PASS, dodijeliti **Claude** za final review.
5. Nakon Claude PASS, Human Owner approval, pa merge.

## Preostali rizici (iskreno)

1. **Integration test `tests/integration/...`** NISAM pokrenuo (timeout 120s+ na prethodnom pokušaju). Ovi testovi zovu stvarne API ključeve i zahtijevaju providers da budu podešeni. Pre-flight `tests/unit` (896/897 → 897/897 nakon ruff fix) su svi zeleni. Integration suite treba provjeriti kao zaseban korak prije merge-a.
2. **`test_js_api_methods_work_from_fresh_worker_threads` (HOTFIX-002 original) + `test_generate_content_works_from_fresh_worker_thread` (moj)** — oba prolaze. Ali threading.Lock + ContextVar interakcija u pywebview runtime-u (ne samo test) zahtijeva stvarni integration test sa EdgeChromium dispatchem. To je izvan allowed_paths mog taska.
3. **`write_all_pages` i dalje koristi `DEFAULT_FIXTURE` bez `campaign_id`/`plan_id`** — po dizajnu (build-time nema runtime ids). Ali to znači da **`render_body(fx)` sa stvarnim ids mora biti pozvan iz nekog drugog koda** (npr. `pywebview` runtime) — inače user nikad ne vidi živo dugme u static HTML-u. Trenutno je to "JS otkriva dugme kad URL ima ids" — ispravno prema briefu, ALI zahtijeva da korisnički navigacijski tok (kalendar → studio_sadrzaja) PRAVILNO forwarduje `&plan=` kroz URL. To je izričito izdvojeno kao "NE DIRATI" u briefu, pa je to poznati follow-up.
4. **Custom dataclass `replace(plan, status=...)` u testu** — koristim Python stdlib `dataclasses.replace` jer je `CampaignPlan` frozen. Ovo je standardni pattern, ali ako CampaignPlan doda novu invarijantu u `__post_init__` koja zabranjuje SUPERSEDED status, test će pasti. Trenutno nema takve provjere.
