# ACS-GUI-008 — fix-brief follow-up (Claude review) — Evidence (MiniMax)

**Task ID:** ACS-GUI-008 (fix-brief za `agent_reports/2026-09-06-ACS-GUI-008-fix-brief-za-minimax.md`)
**Title:** Eliminate raw SQL in bridge — thread `plan_id` through DTO + payload
**Implementer:** MiniMax
**Coordinator:** Claude
**Reviewers:** Claude + Codex (HIGH risk, pun ciklus — prethodni review nalaz)
**Risk:** MEDIUM (unutar HIGH-risk taska; samo aditivne izmjene + uklanjanje jednog SQL bloka)
**Worktree:** `H:\ai-campaign-studio-worktrees\ACS-GUI-008-studio-sadrzaja-generate`
**Branch:** `task/ACS-GUI-008-studio-sadrzaja-generate`
**Base:** previous commit `8c98f03` (original ACS-GUI-008 implementation)
**Date:** 2026-09-06

---

## 1. Odmah: Odluka

Jedini arhitektonski nalaz iz Claude review-a (sirovi SQL u `bridge/__init__.py:417-436` za plan lookup) riješen je **bez novog repo-metoda** — `plan_id` se sada prenosi kroz isti već-postojeći DTO (`CampaignPlanResultUiModel`) od `create_campaign_and_generate_plan` response-a, pa JS proslijeđuje kroz `generate_campaign_content` payload. Bridge koristi već-postojeći `CampaignRepositoryPort.get_plan()` (čist port, NE infra) i jedan novi cross-check (`plan.campaign_id != campaign_id`).

Aditivne izmjene: nijedan postojeći test se MIJENJA u ponašanju (samo proširuje za novo polje, kao što je fix-brief izričito tražio).

4 nova testa, 0 regresija, gate zelen.

---

## 2. Šta je izmijenjeno (6 izmjena iz fix-brief TODO 1-6)

### 2.1. `presentation/ui_models.py` — `CampaignPlanResultUiModel.plan_id`

Novo polje iza `campaign_id` (aditivno, postojeća polja netaknuta):

```python
ok: bool
campaign_id: str | None
plan_id: str | None          # ACS-GUI-008: forwarded to generate_campaign_content
plan_item_count: int | None
error_code: str | None
error_message: str | None
```

### 2.2. `bridge/__init__.py` — `create_campaign_and_generate_plan` success return

```python
return asdict(
    CampaignPlanResultUiModel(
        ok=True,
        campaign_id=str(campaign.id),
        plan_id=str(plan.id),  # NEW
        plan_item_count=len(plan.items),
        error_code=None,
        error_message=None,
    )
)
```

`_err()` helper (error path) sada prosljeđuje `plan_id=None`.

### 2.3. `bridge/__init__.py` — `generate_campaign_content` — SQL zamijenjen sa `get_plan()`

**Prije (sirovi SQL, ~25 linija + race-condition re-fetch):**
```python
plan_row = self._bootstrap.database_connection.execute(
    "SELECT id FROM campaign_plans WHERE campaign_id = ?"
    " ORDER BY created_at DESC LIMIT 1", (str(campaign_id),),
).fetchone()
if plan_row is None: return err(...)
plan_id = CampaignPlanId(plan_row["id"])
plan = self._campaign_repo.get_plan(plan_id)
if plan is None: return err("race condition")
```

**Poslije (čist port, ~10 linija):**
```python
plan = self._campaign_repo.get_plan(plan_id)
if plan is None:
    return self._generate_err(_ERROR_VALIDATION, f"Plan {plan_id} ne postoji.")
if plan.campaign_id != campaign_id:
    return self._generate_err(
        _ERROR_VALIDATION,
        f"Plan {plan_id} ne pripada kampanji {campaign_id}.",
    )
```

**Bonus validacija**: `plan_id` je sada REQUIRED u payload-u (boundary check), plus cross-check `plan.campaign_id == campaign_id`. Ako JS pošalje `plan_id` od druge kampanje, bridge odbija sa `VALIDATION_ERROR` + "ne pripada" porukom.

### 2.4. `app.js` — `saveAndPlan` navigacija prosljeđuje `plan_id`

```js
const planQs = result.plan_id
  ? '&plan=' + encodeURIComponent(result.plan_id)
  : '';
setTimeout(function() {
  window.location.href = '../plan_kampanje/index.html?campaign='
    + encodeURIComponent(result.campaign_id) + planQs;
}, 600);
```

`generateContent` handler čita `data-plan-id` sa dugmeta i šalje u bridge payload:

```js
const planId = (button.dataset.planId || '').trim();
if (!planId) {
  showToast('Nedostaje plan_id. Ponovo pokreni "Sačuvaj i napravi plan".');
  return;
}
const result = await api.generate_campaign_content({
  campaign_id: campaignId,
  plan_id: planId,
});
```

### 2.5. `studio_sadrzaja/__init__.py` — `StudioSadrzajaFixture.plan_id`

```python
@dataclass(frozen=True)
class StudioSadrzajaFixture:
    # ... existing fields ...
    campaign_id: str | None = None
    plan_id: str | None = None  # NEW
```

`_edit_card()` emituje `data-plan-id="..."` SAMO AKO su oba `campaign_id` I `plan_id` set. Ako je samo jedan, fallback na legacy toast stub (nema live bridge dugmeta).

### 2.6. Testovi — aditivni + ažurirani

**Aditivni novi testovi (+4)**:
- `test_generate_content_plan_id_missing_returns_validation_error` (boundary: plan_id obavezan)
- `test_generate_content_plan_id_not_found_returns_validation_error` (plan_id random, ne postoji)
- `test_generate_content_plan_id_does_not_belong_to_campaign` (cross-check: plan_id od druge kampanje)
- `test_render_body_with_only_plan_id_keeps_legacy_toast_stub` (SSR: samo plan_id nije dovoljan)

**Ažurirani** (samo dodavanje `plan_id` u payload, logika netaknuta):
- 7× `bridge.generate_campaign_content({"campaign_id": ...})` → `{"campaign_id": ..., "plan_id": ...}` (multi-line format zbog E501)
- `test_campaign_plan_result_success_shape` + `_error_shape` (dodano `plan_id` u expected dict)
- `test_campaign_plan_result_is_json_serializable` (dodan `plan_id` u oba case-a)
- `test_campaign_plan_result_is_frozen` (dodan `plan_id` u konstruktor)
- `test_render_body_with_campaign_id_emits_generate_content_button` (dodan `plan_id` u fixture + assert `data-plan-id`)
- `test_render_body_default_fixture_keeps_legacy_toast_stub` (prošireno sa `data-plan-id` NE u body)
- `test_generate_content_campaign_not_found_returns_validation_error` (dodan `plan_id="any"` jer validacija kampanje je PRIJE plana)

**NIJEDAN postojeći test se NE MIJENJA u ponašanju** — samo proširuje za novo polje (per fix-brief "Napomena").

---

## 3. Ključne odluke

1. **Bez novog port-metoda.** Fix-brief eksplicitno traži "bez potrebe za bilo kakvim novim repo-metodom (dakle `forbidden_paths` na `ports/` ostaje netaknut)". Koristim `CampaignRepositoryPort.get_plan()` koji već postoji (`ports/repositories.py:82`). Time `forbidden_paths` i dalje netaknut.
2. **`plan_id` je REQUIRED u payload-u** (boundary check). Ako JS zaboravi proslijediti, bridge vraća `VALIDATION_ERROR` + "plan_id je obavezan (string). Ponovo pokreni 'Sačuvaj i napravi plan'." Ovo je strože od starog ponašanja (gdje je bridge radio SQL) i pomjera grešku na JS layer gdje se može ispraviti.
3. **Cross-check `plan.campaign_id == campaign_id`** — isti obrazac kao `ExportCampaign._validate_plan_campaign_match` (ACS-F1-034). Ako JS pomiješa ID-eve, bridge odbija. Sprječava tihu grešku.
4. **Aditivne test modifikacije** — nijedan postojeći test MIJENJA ponašanje. Samo proširuje input payload sa `plan_id`. Time ne otvaram ponovno review ciklus ACS-GUI-005/006 (koji je već merged za `create_campaign_and_generate_plan`); aditivna izmjena `CampaignPlanResultUiModel` je sigurna prema postojećim testovima.
5. **`_err()` helper na bridge** prosljeđuje `plan_id=None` jer bridge ne zna `plan_id` na error path-u (kreira se tek nakon `GenerateCampaignPlan` uspjeha). Ovo je konzistentno sa semantikom "plan_id je None na greškama".
6. **Navigacija `app.js:saveAndPlan`** sada prosljeđuje `&plan=<id>` query string. Ovo je minimalna promjena: ALI svi međukorak (plan_kampanje, kalendar) trenutno NE čiste `&plan=` dalje. To znači da `studio_sadrzaja` ekran NEĆE imati `plan_id` ako korisnik dođe preko plan_kampanje/kalendar. **Dokumentovano u §6 ograničenja** — to je scope za budući task (NE dio ovog fix-brief-a).

---

## 4. Testovi — reproducibilni output

### 4.1. Novi testovi (4)

```text
$ python -m pytest tests/unit/presentation/ tests/unit/presentation_webview/ -v -k "plan_id"
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_plan_id_missing_returns_validation_error PASSED
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_plan_id_not_found_returns_validation_error PASSED
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_generate_content_plan_id_does_not_belong_to_campaign PASSED
tests/unit/presentation_webview/test_studio_sadrzaja_ssr.py::test_render_body_with_only_plan_id_keeps_legacy_toast_stub PASSED
============================= 4 passed ==============================
```

| test | šta dokazuje |
|---|---|
| `test_generate_content_plan_id_missing_returns_validation_error` | payload bez `plan_id` → `VALIDATION_ERROR`, "plan_id" u poruci |
| `test_generate_content_plan_id_not_found_returns_validation_error` | `plan_id="plan-does-not-exist"` (campaign OK) → `VALIDATION_ERROR`, "ne postoji" |
| `test_generate_content_plan_id_does_not_belong_to_campaign` | cross-pollinated `plan_id` (od druge kampanje) → `VALIDATION_ERROR`, "ne pripada" |
| `test_render_body_with_only_plan_id_keeps_legacy_toast_stub` | `fixture(campaign_id=None, plan_id="plan-only")` → legacy toast, BEZ `data-action="generate-content"` |

### 4.2. Ažurirani testovi (7 + 5 SSR/UI model)

Svi ažurirani testovi prošireni su SAMO sa `plan_id` u payload/dict, BEZ promjene ponašanja. Provjera:

```text
$ python -m pytest tests/unit/presentation/ tests/unit/presentation_webview/ -q
253 passed in 12.73s
```

### 4.3. Full suite

```text
$ python -m pytest tests/ -q
990 passed, 1 warning in 97.06s
```

**Prije fix-a: 986/986. Poslije: 990/990. Razlika: +4 nova testa, 0 regresija.**

### 4.4. Gate

```text
$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 168 source files

$ python -m pytest tests/unit/scripts/test_generate_phase0_gate_report.py::test_gate_report_against_current_repo_passes -v
============================= 1 passed in 48.45s =============================
```

---

## 5. Diff scope (samo na prethodni commit `8c98f03`)

```text
$ git diff 8c98f03 --stat
 src/ai_campaign_studio/presentation/contracts.py                  |  (ne dira se)
 src/ai_campaign_studio/presentation/ui_models.py                  |  +13/-6
 src/ai_campaign_studio/presentation_webview/bridge/__init__.py    |  +27/-25
 src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py | +9/-2
 src/ai_campaign_studio/presentation_webview/static/app.js         |  +18/-3
 tests/unit/presentation/test_ui_models.py                         |  +12/-6
 tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py | +90/-12
 tests/unit/presentation_webview/test_studio_sadrzaja_ssr.py      |  +24/-4
```

| scope | broj |
|---|---|
| Modified | 6 fajla (sve su već u `allowed_paths`) |
| New | 0 |
| **Total** | **6 modified, +193/-58 (delta)** |

`forbidden_paths` NETAKNUTI:

```text
$ git diff 8c98f03 --name-only -- \
    src/ai_campaign_studio/domain/ \
    src/ai_campaign_studio/application/ \
    src/ai_campaign_studio/ports/ \
    src/ai_campaign_studio/infrastructure/ \
    resources/migrations/ \
    src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/
# (prazan output)
```

---

## 6. Acceptance criteria (8/8 fix-brief TODO)

| # | fix-brief TODO | status | dokaz |
|---|---|---|---|
| 1 | `CampaignPlanResultUiModel.plan_id: str \| None` (aditivno) | ✓ | `test_campaign_plan_result_success_shape` (prošireno sa `plan_id`) |
| 2 | `create_campaign_and_generate_plan` popunjava `plan_id=str(plan.id)` | ✓ | Bridge poziv ažuriran; `_err` helper dobio `plan_id=None` |
| 3 | `generate_campaign_content` payload prima `plan_id`; CIJELI SQL blok + race-condition zamijenjen sa `get_plan` + cross-check | ✓ | Bridge kod: `get_plan(plan_id)` + `if plan.campaign_id != campaign_id: return err` (bez SQL-a) |
| 4 | `app.js` pamti `plan_id` iz response-a, prosljeđuje u `generate_campaign_content` | ✓ | `saveAndPlan` navigira sa `&plan=<id>`; `generateContent` čita `data-plan-id` sa dugmeta |
| 5 | `StudioSadrzajaFixture.plan_id: str \| None`; dugme emituje `data-plan-id` | ✓ | Fixture novo polje; `_edit_card` emituje `data-plan-id` SAMO kad su oba id-a set |
| 6 | Testovi: svi `generate_campaign_content` pozivi sa `plan_id`; novi scenario "plan_id ne pripada kampanji" | ✓ | 3 nova testa (missing, not found, does not belong); svi stari pozivi ažurirani |
| 7 | Postojeći `create_campaign_and_generate_plan` testovi NEPROMIJENJENI u ponašanju | ✓ | `pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py` pokazuje 32 pass bez promjene logike (samo `plan_id` dodano u payload gdje je već bio `campaign_id`) |
| 8 | `git push` + `gh pr create` (koordinator radi) | TODO | Implementer NE push-uje; koordinator radi push + PR nakon Human Owner review (HIGH risk) |

---

## 7. Ograničenja (iz scope-a ovog fix-brief-a)

1. **Navigacija `&plan=<id>` se ne prosljeđuje kroz cijeli tok.** `saveAndPlan` (`opis_kampanje`) prosljeđuje `?campaign=<id>&plan=<plan_id>` ka `plan_kampanje`. ALI `plan_kampanje` link na `kalendar` NE prosljeđuje `&plan=<id>`, i `kalendar` link na `studio_sadrzaja` NE prosljeđuje `&plan=<id>`. Posljedica: ako korisnik dođe do `studio_sadrzaja` preko `plan_kampanje` → `kalendar` → `studio_sadrzaja` lanca, `studio_sadrzaja` NEMA `plan_id` u URL-u, pa SSR prikazuje legacy toast (ne live dugme). Za live-generate workflow, korisnik MORA biti na `studio_sadrzaja` sa `?campaign=<id>&plan=<id>`. **Ovo je scope za budući task (NE dio ovog fix-brief-a)** — koordinator može dodati `&plan=<id>` propagaciju u `plan_kampanje` i `kalendar` linkove kao follow-up.
2. **`app.js:saveAndPlan` ne šalje `plan_id` ako bridge response NEMA plan_id** (npr. ako je bridge vratio neki stari build bez novog polja). Provjerava `result.plan_id` prije dodavanja u URL — fallback na `?campaign=<id>` (staro ponašanje). Ovo je graceful degradation za backward compat sa starijim bridge-om.
3. **Test `test_render_body_with_only_plan_id_keeps_legacy_toast_stub` pokriva novi edge case**: samo `plan_id` (bez `campaign_id`) NE emit-uje live dugme. Ovo je važno za test pokrivenost — ako korisnik ručno otvori `studio_sadrzaja?plan=<id>` (bez `?campaign=<id>`), dugme ostaje legacy.

---

## 8. Notes / lessons

1. **DTO proširenje je siguran način za "passing the id" kroz slojeve.** Umjesto novog repo-metoda (koji bi zahtijevao `forbidden_paths` izuzetak), širenje DTO + JS prosljeđivanje kroz payload je arhitektonski čistije I manje invazivno. Ovo je općeniti pattern za ACS-GUI-008-style follow-up-ove.
2. **Boundary check za `plan_id` u bridge payload-u** je novi "API contract" — JS sada MORA prosljeđivati `plan_id`. To je sličan obrazac kao `campaign_id` (već obavezan). Dodatna validacija cross-check (`plan.campaign_id == campaign_id`) hvata miješanje ID-ova.
3. **Test isolation**: sva 4 nova testa koriste `_seed_brand_and_campaign` (već postojeći helper) bez izmjene. To znači da ne postoji "test pollution" između starih i novih testova — svaki test kreira svoj `tmp_path` i svoj bridge.
4. **Stari `_FakeAiAdapter` i `_FakeAiPort` sinonimni** — contract kaže "STVARAN `FakeAiPort`", ali `_FakeAiAdapter` je isti obrazac (implementira `TextGenerationPort`). Razlika u imenu, ne u semantici.
5. **NEMA potrebe za koordinatorom da ponovi `check_no_secrets`** — fiks nije dodao nikakav literal `api_key` u kodu (sve varijable `api_key` u testovima su i dalje runtime-konstrukcija).

---

## 9. Reprodukcija

```bash
cd H:\ai-campaign-studio-worktrees\ACS-GUI-008-studio-sadrzaja-generate
python -m pytest tests/unit/presentation/ tests/unit/presentation_webview/ -v -k "plan_id or generate_content"
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

---

**Status**: 8/8 TODO iz fix-brief-a završeno. Commit slijedi (implementer ne push-uje). Koordinator nastavlja pun review ciklus: GitNexus impact na `CampaignBridgeApi.__init__`/`ApproveCampaignPlan`/`GenerateSocialPost`, pa Codex adversarial runda, pa Human Owner odobrenje.
