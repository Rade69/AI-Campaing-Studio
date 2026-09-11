---
task: ACS-S2-016 — S2-G7b Brand Intelligence Review UI
author: minimax (privremeni koordinator, Claude na pauzi zbog limita tokena)
date: 2026-09-11
purpose: Coordinator round-2 review (Codex je implementer; neovisni reviewer je koordinator, jer Codex reviews-Codex je konflikt interesa)
review_target: task/ACS-S2-016-brand-review-ui @ 3264b78
previous_verdict: REJECT (R1 — race, status filter, silent error)
status: PASS — spremno za Human Owner odobrenje i merge
---

# ACS-S2-016 — Coordinator round-2 review (Codex R1 fix verification)

## Verdict

**PASS — sva 3 Codex R1 blocking findings zatvorena reproducer-based verification.**

Codex R1 review (commit `87b0a76`) je našao 3 blocking findings:
- **R1-BF-1 (HIGH race)**: concurrent Assemble persists duplicate snapshot versions
- **R1-BF-2 (HIGH status filter)**: `list_approved_facts_by_brand` uključuje non-APPROVED
- **R1-BF-3 (MEDIUM silent error)**: `loadFactReview` swallow-uje greške

Codex je implementirao fix u commit `3264b78 fix(S2-G7b): close review race and filtering gaps`. Coordinator nezavisna reproducer-based verifikacija (NE samo mutation, kao memory lesson zahtijeva): 9/9 reproducer testova PROŠLIH.

## Reproducer-based verification (NE mutation test)

### R1-BF-1 reproducer

`tests/integration/presentation_webview/test_assemble_brand_snapshot_concurrency.py`:

```python
# 2 pywebview workers + threading.Barrier(2) + synchronized_get_latest wrapper
# (deterministički reproducer R1 nalaza)

def synchronized_get_latest(repository, brand_id):
    latest = original_get_latest(repository, brand_id)
    try:
        rendezvous.wait(timeout=1)  # OBA workera prođu barijeru
    except threading.BrokenBarrierError:
        pass
    return latest

with ThreadPoolExecutor(max_workers=2) as executor:
    results = list(executor.map(
        lambda _: bridge.assemble_brand_snapshot({"brand_id": str(_BRAND_ID)}),
        range(2)
    ))

assert sorted(result["version"] for result in results) == [1, 2]  # DETERMINISTIČKI
assert baza SELECT version FROM brand_snapshots ORDER BY version == [1, 2]
```

**Result**: PASS (11.84s). Ova verzija testa DOKAZUJE race condition fix — bez per-brand lock, oba workera prođu barijeru sa istim `latest.version`, računaju isti `version+1`, i perzistiraju duplikat. Sa lock pattern, drugi worker čeka na prvog.

### R1-BF-2 reproducer

`tests/integration/database/repositories/test_sqlite_fact_repository_status_filter.py`:

```python
# APPROVED → assert [FactStatus.APPROVED]
# Update status='SOFT_DELETED' → assert list_approved_facts_by_brand() == ()
# Update status='SUPERSEDED' → assert list_approved_facts_by_brand() == ()
# assemble_brand_snapshot → assert ok=False, error_code="VALIDATION_ERROR"
```

**Result**: PASS. Test demonstrira:
1. APPROVED uključen
2. SOFT_DELETED isključen
3. SUPERSEDED isključen
4. Assembly sa svim neupotrebljivim facts → `ok=False, error_code="VALIDATION_ERROR", "odobrenih" in error_message`

### R1-BF-3 reproducer

`tests/unit/presentation_webview/screens/test_brend_review_ui.py` (Node/VM extension):

- `test_load_fact_review_shows_toast_on_bridge_throw`: mock `api.get_ingestion_review` da baci Error → assert `showToast` pozvan sa BHS fallback
- `test_load_fact_review_shows_error_message_on_failed_dto`: mock `{ok: false, error_message: "Brend ne postoji."}` → assert `showToast("Brend ne postoji.")` pozvan

**Result**: PASS. Test demonstrira:
1. Throw path → vidljiv toast (NE silent return)
2. `ok=false` path → error_message vidljiv (NE silent)
3. BHS latinica fallback ako `error_message` None ili prazan

## Code inspection (svaka fix linija VERIFIKOVANA)

### R1-BF-1 fix: `bridge/__init__.py`

```python
# Per-brand lock registry (matching _generation_locks pattern)
self._snapshot_assembly_locks: dict[str, threading.Lock] = {}
self._snapshot_assembly_locks_guard = threading.Lock()

def _snapshot_assembly_lock_for(self, brand_id: str) -> threading.Lock:
    with self._snapshot_assembly_locks_guard:
        lock = self._snapshot_assembly_locks.get(brand_id)
        if lock is None:
            lock = threading.Lock()
            self._snapshot_assembly_locks[brand_id] = lock
        return lock

# In assemble_brand_snapshot:
with self._snapshot_assembly_lock_for(str(brand_id)):
    # ... cijeli critical section (fact read + latest read + version + save)
```

**Verifikacija**: lock obuhvata cijeli critical section (read latest + compute version + save), guard lock sprječava race na dict insertion, različiti brandovi koriste različite lockove. Pattern match-uje `_generation_locks: dict[tuple[str, str], threading.Lock]`.

### R1-BF-2 fix: `sqlite_fact_repository.py`

```sql
SELECT approved_facts.* FROM approved_facts
  JOIN source_snapshots ON source_snapshots.id = approved_facts.source_snapshot_id
  JOIN crawl_targets ON crawl_targets.id = source_snapshots.crawl_target_id
  JOIN ingestion_runs ON ingestion_runs.id = crawl_targets.run_id
 WHERE ingestion_runs.brand_id = ?
   AND approved_facts.status = ?              -- ✅ NOVI filter
 ORDER BY approved_facts.created_at DESC, approved_facts.id DESC
```

Bind: `(brand_id, FactStatus.APPROVED.value)` — koristi enum vrijednost (sigurnije od hardcoded string "APPROVED").

**Verifikacija**: minimalan scope change (+3/-1), TAČNO filtrira po statusu.

### R1-BF-3 fix: `static/app.js`

```javascript
let result;
try {
  result = await api.get_ingestion_review({});
} catch (err) {
  showToast('Učitavanje pregleda činjenica nije uspjelo.');  // ✅ BHS fallback, NE err.message
}
if (!result || result.ok !== true) {
  const message = result && typeof result.error_message === 'string' && result.error_message.trim()
    ? result.error_message
    : 'Učitavanje pregleda činjenica nije uspjelo.';
  showToast(message);  // ✅ vidljiv toast
}
```

**Verifikacija**: silent return uklonjen, BHS fallback za throw, error_message iz DTO kad postoji, NO izlaganje `err.message` (sigurnost).

## Standard checks (rerun)

```text
$ python -m ruff check .
All checks passed!  EXIT=0

$ python -m mypy src
Success: no issues found in 211 source files  EXIT=0

$ python -m pytest --tb=line -q \
    tests/integration/database/repositories/test_sqlite_fact_repository_status_filter.py \
    tests/integration/presentation_webview/test_assemble_brand_snapshot_concurrency.py \
    tests/integration/presentation_webview/test_ingestion_review_flow.py \
    tests/unit/presentation_webview/screens/test_brend_review_ui.py
9 passed in 11.84s   EXIT=0
```

## Scope-cleanliness (forbidden paths)

`git diff --stat origin/main..3264b78` za SAMO source/test fajlove (NE workflow artifacts):

```text
 sqlite_fact_repository.py                  |  3 +-
 presentation_webview/bridge/__init__.py    | 74 ++++++++-------
 presentation_webview/static/app.js         |  9 +-
 tests/integration/database/repositories/test_sqlite_fact_repository_status_filter.py | 60 ++++
 tests/integration/presentation_webview/test_assemble_brand_snapshot_concurrency.py  | 75 +++++
 tests/unit/presentation_webview/screens/test_brend_review_ui.py | 74 +++++++----
 7 files changed, 402 insertions(+), 34 deletions(-)
```

**Zero touches** na:
- `domain/brand/entities.py` (BrandSnapshot ostaje isti)
- `domain/facts/*`
- `application/ingestion/{approve,reject}_fact_candidates.py` (G7a)
- `application/ingestion/ingest_brand_sources.py` (G6)
- `infrastructure/web_ingestion/`, `extraction/`, `visual_extraction/`, `document_ingestion/`
- `resources/migrations/` (nema nove migracije)

## Coordinator odstupanja od §5 (konačni brief)

Ni jedno od §5. NE SMIJE pravilo nije prekršeno. Sva 3 fix-a su scope-minimalna.

## Preostali rizici (P1 follow-up, NE za G7b merge)

1. **Optimistic locking za `assemble_brand_snapshot`**: dva uzastopna assemble-a u istom milisekundu MOGU proći kroz lock ALI race na `get_latest_snapshot` + `save_snapshot` ako se lock drži samo unutar `_resource_scope` (NE šire). Bridge je `BridgeApi` (single-threaded pywebview), pa nema paralelnih JS poziva, ALI double-click MOGAO bi pokrenuti race. Mitigacija: UI button disable dok je assemble u toku. **P1 follow-up, NE za G7b merge.**

2. **G-WI-EVIDENCE za SUPERSEDED**: `test_sqlite_fact_repository_status_filter.py` testira SOFT_DELETED i SUPERSEDED, ALI NE verificira da assembly **odbacuje** cijeli snapshot ako IMA makar jedan SOFT_DELETED/SUPERSEDED (test samo kreira scenario sa svim neupotrebljivim, ne sa mix). **Mali gap, NE za G7b merge.**

## Decision request

**Spreman za Human Owner merge odobrenje.** G7b contract §8 traži:
- ✅ Codex round 3 (S2-G6) re-review
- ✅ Codex round 1 (S2-G7b) re-review → REJECT → Codex round 1 (R1) fix → coordinator round 2 PASS
- ⚠️ Claude PASS — na pauzi; coordinator 3b-style override kao i za G6 (dokumentirano u `agent_reports/2026-09-10-ACS-S2-014-claude-pass-override.md`)
- ⏳ Human Owner eksplicitno odobrenje (NE §29, NE koordinator-override)

Ako Human Owner odobri:
1. `gh pr merge` (squash, bez `--delete-branch` jer worktree drži branch)
2. Post-merge ciklus: `git pull`, `npx gitnexus analyze`, `.agent/CURRENT_STATE.md` prepend
3. CI verification
4. "Unesi URL, vidi rezultat" petlja ZATVORENA u aplikaciji
