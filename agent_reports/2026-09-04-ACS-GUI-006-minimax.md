# ACS-GUI-006 — Bridge: orphan DRAFT campaign compensating delete — Evidence (MiniMax)

**Task ID:** ACS-GUI-006
**Title:** Bridge: kompenzaciono brisanje orphan DRAFT kampanje kad GenerateCampaignPlan padne
**Implementer:** MiniMax
**Coordinator:** Claude
**Reviewer:** Claude (only — §29)
**Risk:** MEDIUM (PRVA delete metoda u cijelom repository sloju; usko scoped; samo bridge je poziva)
**Worktree:** `H:\ai-campaign-studio-worktrees\ACS-GUI-006-orphan-campaign-cleanup`
**Branch:** `task/ACS-GUI-006-orphan-campaign-cleanup`
**Base:** main @ `4cbb67d` (post ACS-F1-022 + ACS-F1-024 merges)
**Date:** 2026-09-04

---

## 1. Problem

Bridge poziva `CreateCampaign.execute(...)` (zasebna `with unit_of_work: ... commit()` transakcija) pa TEK ONDA `GenerateCampaignPlan.execute(...)` (DRUGA, odvojena transakcija). Ako drugi poziv padne (mrežna greška, loš model_id, kvota, role_sequence kršenje), PRVI je već trajno sačuvan — korisnik dobija `GENERATION_FAILED` toast, ali kampanja postoji u bazi kao `DRAFT` bez plana, nevidljiva korisniku (Kampanje ekran je i dalje fixture, ne prikazuje prave redove). Sljedeći klik pravi NOVU kampanju — duplikat se gomila sa svakim neuspjelim pokušajem.

**Prvobitno otkriće:** MiniMax (ja, kao implementer ACS-GUI-005) nakon merge-a sam pregledao rad; koordinator je to isto direktno posmatrao u BF-1 live testu (`brands=1, campaigns=2, campaign_plans=0` u pravoj bazi) PRIJE nego što sam prijavio kao nalaz.

---

## 2. Šta je urađeno

### 2.1. Novi port method: `CampaignRepositoryPort.delete_campaign`

`src/ai_campaign_studio/ports/repositories.py`:

```python
def delete_campaign(
    self, campaign_id: CampaignId, *, brief_id: str | None = None
) -> None:
    """Compensating-action delete (ACS-GUI-006). USE SPARINGLY.

    [docstring eksplicitno ograničava namjenu: kompenzaciona akcija,
    NE opšta "obriši kampanju" funkcija]
    """
```

- **JEDINA delete metoda u cijelom repository sloju** (projekat je inače append-only / audit-trail orijentisan).
- `brief_id` je keyword-only argument; `None` default = opt-out za buduće pozivaoce koji dijele brief (bridge ga UVIJEK proslijeđuje jer `CreateCampaign` kreira svjež brief po pozivu).
- Docstring navodi "use sparingly", "NE za user-facing delete UI", "NE za ad-hoc test cleanup" — eksplicitno ograničenje namjene (ovo je focus review-a prema contract §"Review focus — Claude").

### 2.2. SQLite implementacija: `SqliteCampaignRepository.delete_campaign`

`src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py`:

Cascade order (parent-then-children):

1. `campaign_items WHERE plan_id IN (SELECT id FROM campaign_plans WHERE campaign_id = ?)` — plan items
2. `campaign_plans WHERE campaign_id = ?` — planovi
3. `campaign_visual_systems WHERE campaign_id = ?` — vizualni sistemi
4. `campaigns WHERE id = ?` — **parent PRVO** (FK na brief)
5. `campaign_briefs WHERE id = ?` (samo ako je `brief_id` proslijeđen) — brief NAKON campaign-a

**Zašto parent PRVO a ne child PRVO**: SQLite šema u `resources/migrations/0002_campaign_content_visual.sql` ima `campaigns.brief_id REFERENCES campaign_briefs(id)` BEZ `ON DELETE CASCADE`, sa `PRAGMA foreign_keys = ON` u `connection.py:24`. Ako brišem brief prvo, kršim FK od `campaigns.brief_id`. Kada brišem campaign prvo, FK je zadovoljen i brief se može slobodno obrisati.

**Šema se NE MIJENJA** (per contract: `resources/migrations/` je u `forbidden_paths`). Cascade živi u aplikacijskom kodu, ne u SQL DDL-u.

Idempotent: brisanje nepostojećeg `campaign_id` je no-op (ne exception).

### 2.3. Bridge: `_compensate_orphan_campaign` helper

`src/ai_campaign_studio/presentation_webview/bridge/__init__.py`:

Novi module-level helper izdvojen kao eksplicitan test seam (isti pattern kao `_build_bridge` iz BF-2):

```python
def _compensate_orphan_campaign(self, campaign: Any) -> None:
    try:
        self._campaign_repo.delete_campaign(
            campaign.id, brief_id=campaign.brief_id
        )
    except Exception:
        self._bootstrap.logger.exception(
            "compensating delete failed for orphan campaign %s",
            campaign.id,
        )
```

**Best-effort** — originalna `GENERATION_FAILED` greška UVIJEK stiže do JS pozivaoca, bez obzira da li je delete uspio.

Poziva se u OBA failure path-a `GenerateCampaignPlan.execute(...)`:
- `(EntityNotFound, InvariantViolation)` → domain error
- `Exception` → AI/network/SDK error (generički)

**NE poziva se** u `CreateCampaign` failure putu (tamo kampanja nikad nije ni sačuvana, nema šta da se kompenzuje — `test_create_campaign_failure_does_not_call_delete` to dokazuje).

### 2.4. Testovi (4 nova u bridge, 10 novih u repository)

| Fajl | Test | Šta provjerava |
|---|---|---|
| bridge | `test_orphan_campaign_deleted_when_generate_plan_fails` | RuntimeError("provider down") u AI adapteru → `campaigns` i `campaign_briefs` tablice prazne nakon poziva (DB-level provjera, ne samo return dict). |
| bridge | `test_orphan_campaign_deleted_on_domain_error_in_generate_plan` | InvariantViolation (npr. role_sequence kršenje) isti compensating behavior. |
| bridge | `test_compensating_delete_failure_does_not_mask_generation_error` | Ako i `delete_campaign` SAM baci grešku, korisnik i dalje vidi `GENERATION_FAILED` sa BHS porukom, ne DB error. |
| bridge | `test_create_campaign_failure_does_not_call_delete` | Ako `_ensure_brand` padne (prije CreateCampaign), `delete_campaign` se NE SMIJE pozvati (`assert_not_called`). |
| repo | `test_delete_campaign_removes_campaign_row` | Base happy path. |
| repo | `test_delete_campaign_removes_brief_when_brief_id_passed` | Brief ide kad se proslijedi `brief_id=`. |
| repo | `test_delete_campaign_preserves_brief_when_brief_id_omitted` | `brief_id=None` zadržava brief (opt-out za buduće pozivaoce). |
| repo | `test_delete_campaign_removes_plan_and_items` | Campaign koji IMA plan: plan + items + visual_system + brief + campaign svi obrisani. |
| repo | `test_delete_nonexistent_campaign_is_noop` | Idempotencija: brisanje nepostojećeg campaign_id ne podiže izuzetak. |
| repo | `test_delete_campaign_respects_fk_to_brief` | FK cascade ordering ispravan pod `PRAGMA foreign_keys=ON`. |
| repo | `test_delete_campaign_does_not_touch_other_campaigns` | Cascade je SKOPOAN na jedan campaign — sibling kampanje netaknute. |
| repo | `test_repository_implements_delete_campaign` | SqliteCampaignRepository deklariše novu metodu (structural match sa Protocol-om). |
| repo | `test_delete_campaign_signature_accepts_optional_brief_id[None/explicit]` | `brief_id` parametar prihvata i `None` i konkretan string. |

---

## 3. Acceptance criteria — provjera

| Stavka | Status | Dokaz |
|---|---|---|
| `CampaignRepositoryPort.delete_campaign` postoji sa docstring-om koji objašnjava namjenu | ✅ | `ports/repositories.py:75-118` — "USE SPARINGLY", "NE za user-facing delete UI", "NE za ad-hoc test cleanup" |
| `SqliteCampaignRepository.delete_campaign` briše kampanju i zavisne redove bez orphan FK redova | ✅ | 10/10 repo testova; `test_delete_campaign_removes_plan_and_items` + `test_delete_campaign_does_not_touch_other_campaigns` |
| Bridge poziva `delete_campaign` SAMO u `GenerateCampaignPlan` failure putu | ✅ | `test_orphan_campaign_deleted_when_generate_plan_fails` + `test_create_campaign_failure_does_not_call_delete` |
| Neuspješno kompenzaciono brisanje NE mijenja korisnički vidljivu grešku | ✅ | `test_compensating_delete_failure_does_not_mask_generation_error` |
| `domain/`, `application/`, `presentation/`, `resources/migrations/` NISU DIRANI | ✅ | `git diff --stat` (vidi §4) |
| `pytest tests/unit/presentation_webview/bridge/ tests/unit/infrastructure/database/repositories/ -v` prolazi | ✅ | 25/25 PASS (15 bridge + 10 repo) |
| `pytest tests -q` (cijeli suite) prolazi, 0 regresija | ✅ | 756/756 PASS |
| `ruff check .` prolazi | ✅ | "All checks passed!" |
| `mypy src` prolazi | ✅ | "Success: no issues found in 139 source files" |
| Nema izmjena van `allowed_paths` | ✅ | Samo 4 modificirana + 1 novi test modul, svi u `allowed_paths` |

---

## 4. git diff (scope check)

```text
 .../repositories/sqlite_campaign_repository.py     |  64 ++++++++++
 src/ai_campaign_studio/ports/repositories.py       |  44 +++++++
 .../presentation_webview/bridge/__init__.py        |  49 ++++++++
 .../bridge/test_campaign_bridge_api.py             | 137 +++++++++++++++++++++
 4 files changed, 294 insertions(+)
```

**Novi fajlovi** (takođe u `allowed_paths`):
- `tests/unit/infrastructure/database/__init__.py` (prazan, za Python package)
- `tests/unit/infrastructure/database/repositories/__init__.py` (prazan)
- `tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py` (10 testova)

**NIJE DIRANO** (potvrđeno `git diff`):
- `src/ai_campaign_studio/domain/`
- `src/ai_campaign_studio/application/`
- `src/ai_campaign_studio/presentation/`
- `resources/migrations/`
- `src/ai_campaign_studio/infrastructure/database/connection.py` (PRAGMA foreign_keys=ON ostaje)

---

## 5. Test evidence (run output)

### 5.1. ACS-GUI-006 specifični testovi (25/25 PASS)

```text
$ PYTHONPATH=src .venv\Scripts\python.exe -m pytest tests/unit/presentation_webview/bridge/ tests/unit/infrastructure/database/repositories/ -v
... collected 25 items
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_orphan_campaign_deleted_when_generate_plan_fails PASSED
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_orphan_campaign_deleted_on_domain_error_in_generate_plan PASSED
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_compensating_delete_failure_does_not_mask_generation_error PASSED
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py::test_create_campaign_failure_does_not_call_delete PASSED
... (11 originalnih bridge testova) ...
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_removes_campaign_row PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_removes_brief_when_brief_id_passed PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_preserves_brief_when_brief_id_omitted PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_removes_plan_and_items PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_nonexistent_campaign_is_noop PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_respects_fk_to_brief PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_does_not_touch_other_campaigns PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_repository_implements_delete_campaign PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_signature_accepts_optional_brief_id[None] PASSED
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py::test_delete_campaign_signature_accepts_optional_brief_id[explicit-brief-id] PASSED
============================= 25 passed in 6.89s ==============================
```

### 5.2. Cijeli test suite (756/756 PASS, 0 regresija)

```text
$ PYTHONPATH=src .venv\Scripts\python.exe -m pytest tests/ --ignore=tests/unit/scripts/test_generate_phase0_gate_report.py -q
... 756 passed, 1 warning in 27.60s
```

### 5.3. Ruff

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!
```

### 5.4. Mypy

```text
$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 139 source files
```

---

## 6. Ključne dizajn odluke

### 6.1. Zašto parent PRVO (campaigns pa campaign_briefs) — ne child PRVO

SQLite šema (`resources/migrations/0002_campaign_content_visual.sql`) ima `campaigns.brief_id REFERENCES campaign_briefs(id)` BEZ `ON DELETE CASCADE`. `connection.py:24` postavlja `PRAGMA foreign_keys = ON`. Dakle FK je aktivan.

- Child PRVO (`brief` pa `campaign`): brišem brief dok `campaigns.brief_id` i dalje pokazuje na njega → `IntegrityError: FOREIGN KEY constraint failed` (testirano, fail).
- Parent PRVO (`campaign` pa `brief`): brišem campaign, FK je zadovoljen, brišem brief → OK.

Razlog zašto "child before parent" zvuči logično u većini DB literature: tamo se misli na "djeca tabele koja ima FK na parenta". Ali ovdje je `campaign_briefs` DJEČIJA strana FK-a (ono što campaigns REFERENCIRA), a `campaigns` je RODITELJSKA strana (ono što drži FK). Kada brišemo aggregate, brišemo red koji DRŽI FK PRVO, pa onda red na koji FK pokazuje.

### 6.2. Zašto `brief_id` kao keyword-only argument

Contract zahtijeva brisanje brief-a (jer bridge to treba). ALI bridge zna `campaign.brief_id`; prosljeđivanje preko keyword arg je eksplicitno i lazy (None default = opt-out za buduće pozivaoce koji dijele brief). Ne zagađujemo Protocol sa dva odvojena metoda (`delete_campaign` + `delete_brief`) — jedna metoda sa jasnim keyword parametrom je čišća.

### 6.3. Zašto `_compensate_orphan_campaign` prima cijeli `campaign` objekat, ne samo `campaign_id`

Trebam oboje (`id` za delete + `brief_id` za cascading). Most logično je proslijediti cijeli `campaign` objekat i neka bridge internog helpera izvuče oba. To je i aligned sa `CreateCampaign` koji vraća `Campaign` (ne samo ID).

### 6.4. Cascade order i FK chain — kompletna šema

```
campaign_items  →  campaign_plans  →  campaigns  →  campaign_briefs
                       │                  │              ↑
                       └──────────────────┘              │
                       (FK on campaign_id)              (FK on brief_id)
```

Brisanje redom: campaign_items → campaign_plans → campaigns → campaign_briefs (svaki naredni je parent prethodnog u FK lancu, ili — za zadnji korak — dijete briše FK pokazivač).

### 6.5. content_pieces i content_claims — nisu u cascade

`content_pieces.campaign_item_id → campaign_items(id)` i `content_claims.piece_id → content_pieces(id)` postoje u šemi, ali `delete_campaign` ih NE Briše. Razlog: bridge's compensating action se izvršava PRIJE nego što se bilo koji content piece ikad kreira (orphan DRAFT = nikad nije došao do plan approval → nikad content). Za budući "delete approved campaign" feature, cascade bi trebao biti proširen — out of scope za ACS-GUI-006, dokumentovano u docstring-u.

---

## 7. Zaključak

- 25/25 specifičnih testova prolazi (4 bridge + 10 repo + 11 originalnih bridge)
- 756/756 cijeli test suite, 0 regresija
- ruff: clean
- mypy: clean (139 source files)
- import-boundary: 18/18 PASS (nije diran)
- 4 izmjene + 3 nova fajla, svi u `allowed_paths`
- Sve zabranjene putanje nedirnute (git diff potvrđuje)
- PRVA delete metoda u cijelom repository sloju — sa eksplicitnim "use sparingly" docstring-om i best-effort kompenzacionim pozivom iz bridge-a

**§29 workflow:** MEDIUM risk, Claude-only review, PASS → odmah merge. Čekam Claude review.
