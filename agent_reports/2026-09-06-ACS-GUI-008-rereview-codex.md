---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: PASS
gitnexus_impact: PASS
blocking_findings:
  - BF-5
---

# ACS-GUI-008 — Codex rereview, runda 2

## CILJ

Svježe provjeriti commit `897bd5c` na PR-u #4 nakon HOTFIX-002 rebasea i fix runde za originalne BF-1/BF-3/BF-4 nalaze. Review ne mijenja implementaciju.

## URAĐENO

`REJECT`: originalna četiri nalaza su funkcionalno zatvorena, ali je pronađen novi blocking mismatch na infrastrukturnoj failure putanji nove `generate_campaign_content` metode. Normalni, konkurentni, `SUPERSEDED`, direktni-URL i worker-thread tokovi prolaze.

## PROVJERENO

- Tačan PR HEAD: `897bd5cbb967b78e08508bc12e371b02bb8e1064`; PR #4 je `OPEN`, `MERGEABLE/CLEAN`, CI `test` je `SUCCESS` za isti commit.
- Branch je iza trenutnog `main` samo za jedan documentation/re-review-request commit (`62f9add`); merge-base je `f2ada95`. Nema novije produkcijske promjene koju bi task propustio.
- Diff prema `main` dira samo ugovorene presentation/bridge/UI/test fajlove te projektne evidence izvještaje. Domain, Application, Ports, Infrastructure implementacije, migracije i `pregled_izvoz` nisu dirani.
- BF-1: produkcijski `write_all_pages()` HTML uvijek sadrži skriveno live dugme i result node. Stvarni `app.js` izvršen je u izoliranom Node DOM harnessu:

```text
?campaign=C&plan=P -> hidden=false, campaignId=C, planId=P
?campaign=C        -> hidden=true
?plan=P            -> hidden=true
bez parametara     -> hidden=true
```

- BF-2/HOTFIX follow-up: `generate_campaign_content` ima `@_with_call_resources`; fresh-worker-thread test prolazi.
- BF-3: per-pair lock se uzima nakon boundary validacije i prije prvog DB čitanja; `_generate_campaign_content_locked()` ne otpušta ga unutar read–generate–write sekvence. Konkurentni barrier test prolazi i baza ostaje na dvije, ne četiri stavke.
- BF-4: `SUPERSEDED` se odbija prije provider factoryja/generatora; test potvrđuje `VALIDATION_ERROR`, nula AI poziva i nula zapisa.
- Round-robin, parcijalni uspjeh, sekvencijalni retry/idempotency i secret-safe exception mapiranja iz prve runde ostaju pokriveni postojećim testovima i pregledanim kodom.

## GITNEXUS / IMPACT

Indeks glavnog checkouta je svjež na `62f9add`. Svježi upstream impact:

- `CampaignBridgeApi`: 1 direktni importer (`presentation_webview/__main__.py`), LOW;
- `ApproveCampaignPlan`: 1 postojeći produkcijski caller (`run_system_b.py`), LOW;
- `GenerateSocialPost`: 1 postojeći produkcijski caller (`run_system_b.py`), LOW.

Koordinatorov task-commit `detect_changes` dokaz navodi HIGH zbog bridge diffa i linijskih pomaka; ručnim diff/caller pregledom nisu potvrđeni neočekivani caller-i ili boundary promjene. Poznati worktree-binding problem sprječava ponavljanje task-level `detect-changes` direktno iz linked worktreea, ali svježi simbol-impact i stvarni branch diff potvrđuju očekivani surface.

## BLOCKING FINDINGS

### BF-5 — [medium] Resource-lifecycle greška vraća pogrešan DTO za novu js_api metodu

**Requirement:** `generate_campaign_content` mora na svakoj failure putanji vratiti `GenerateContentResultUiModel` oblik: `ok`, `campaign_id`, `generated_count`, `failed_count`, `content_piece_ids`, `error_code`, `error_message`.

**Evidence:** `_with_call_resources` u `bridge/__init__.py:121-147` hvata grešku nastalu prije/poslije tijela dekorirane metode. Posebno prepoznaje samo `configure_provider`; sve ostale metode šalje kroz `self._err()`, koji je namijenjen `CampaignPlanResultUiModel`. Nova generate metoda ima vlastiti `_generate_err()` na `bridge/__init__.py:1128-1148`, ali ga dekorator nikad ne bira.

Live reprodukcija nakon konstrukcije izoliranog bridgea i `create_connection -> OSError("disk unavailable")` vratila je:

```text
{
  'ok': False,
  'campaign_id': None,
  'plan_id': None,
  'plan_item_count': None,
  'error_code': 'INTERNAL_ERROR',
  'error_message': 'Interna greška — pogledajte log aplikacije.'
}
```

Stvarni ključevi su `campaign_id,error_code,error_message,ok,plan_id,plan_item_count`; obavezni `generated_count,failed_count,content_piece_ids` nedostaju. Postojeći connection-failure test (`test_campaign_bridge_api.py:240-258`) pokriva samo `configure_provider` i `create_campaign_and_generate_plan`, pa regresiju za treću dekoriranu metodu ne vidi.

**Failure path:** nedostupna/oštećena/zaključana baza ili greška pri zatvaranju konekcije nastaje u `_resource_scope()` izvan vlastitog try/error mapiranja `generate_campaign_content`; dekorator vraća DTO druge operacije.

**Impact:** `js_api` ne baca iznimku i trenutni JS uspije prikazati generičnu poruku, ali javni Presentation contract mijenja oblik rezultata upravo na realnoj infrastrukturnoj grešci. Typed/budući caller koji čita generate brojače dobiva nedostajuća polja. To direktno krši acceptance i dedicated DTO invariant.

**Minimalna korekcija:** učiniti lifecycle error mapiranje operacijski tipiziranim (npr. dekoratoru predati odgovarajući error mapper ili eksplicitno mapirati `generate_campaign_content` na `_generate_err`) i proširiti permanentni connection-failure test da potvrdi tačan skup ključeva nove metode i odsustvo exception/secret leaka.

## STANDARDNA VERIFIKACIJA

```text
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -q
263 passed in 16.42s

python -m pytest \
  ...::test_generate_content_works_from_fresh_worker_thread \
  ...::test_generate_content_concurrent_threads_serialize_via_lock \
  ...::test_generate_content_superseded_plan_rejected_no_ai_calls -q
3 passed in 1.75s

python -m pytest -q
1042 passed, 1 warning in 130.24s

python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 174 source files

python scripts/check_no_secrets.py
NO CONFIRMED SECRET IN TRACKED FILES
```

`git diff --check main...HEAD` je čist. Worktree je čist i prati origin task branch.

## ADVERSARIALNA PROVJERA

- Izvršen stvarni JS bootstrap s oba/jednim/nijednim query parametrom; BF-1 radi kako brief traži.
- Prisiljen je kvar per-call SQLite connection factoryja; time je potvrđen BF-5 na kodu koji test suite ne pokriva.
- Pregledan je cijeli lock scope, ne samo `_lock_for`; nema otpuštanja/reacquire rupe.
- Svježe izvršeni worker, concurrent i `SUPERSEDED` testovi prolaze.
- Pravi EdgeChromium prozor nije automatski otvoren u reviewu. To nije novi blocker: acceptance eksplicitno koristi permanentni `threading.Thread` model, a instalirani pywebview dispatch model je već potvrđen u HOTFIX-002. Ostaje koristan manual smoke test prije releasea.

## NE DIRATI U FIX RUNDI

- BF-1 URL/UI wiring, generation lock i `SUPERSEDED` kontrolu toka — svježe su potvrđeni.
- Domain/Application/Ports/Infrastructure implementacije, migracije, `pregled_izvoz` i prirodni Plan/Kalendar → Studio navigation follow-up.
- Ne širiti fix na poslovnu logiku; BF-5 je lokalna bridge error-mapper/test korekcija.

## SLJEDEĆE

MiniMax radi jedan uski fix za BF-5 unutar `bridge/__init__.py` i `test_campaign_bridge_api.py`, zatim pokreće connection-failure regression, presentation suite, puni suite, Ruff, mypy i secret scan. Nakon novog commita Codex provjerava samo BF-5 diff/repro; ako prođe, task može na Human Owner odobrenje. PR #4 ne mergeati na `897bd5c`.
