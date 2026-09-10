---
task: ACS-S2-014 — S2-G6 Pipeline Orchestration
author: minimax (privremeni koordinator, Claude na pauzi zbog limita tokena)
date: 2026-09-10
purpose: Coordinator re-review summary sent to Codex for fresh adversarial re-review (round 3)
review_target: task/ACS-S2-014-ingestion-pipeline @ f2c1d92 (after rebase on origin/main @ 09650ce)
previous_verdict: REJECT (round 2, R2-BF-1 + R2-BF-2 — see agent_reports/2026-09-10-ACS-S2-014-review-codex-r2.md)
status: coordinator-independent-verification PASS on round-3 fix, awaiting Codex round 3
---

# ACS-S2-014 — Coordinator re-review summary (round 3) for Codex

## Verdict so far

Pi's fix-round 3 commit `f2c1d92` addresses R2-BF-1 from the
previous Codex review by choosing **option A** (refetch/recovery,
not inline base64). The R2-BF-2 (PR scope contamination) finding
was already addressed by my earlier `git reset --hard c54dcb9
&& git cherry-pick 9104893 && git push --force-with-lease` cycle
(see "Pre-existing rebase state" below). R2-BF-1 has been
independently verified by the coordinator via mutation test.

## Pre-existing rebase state (informs this review)

When Codex round 2 was published, branch was at HEAD `9104893`,
which still contained two Claude-authored workflow commits
(`5444dac` handoff + `a548b89` CURRENT_STATE duplicate). I dropped
both via `git reset --hard c54dcb9` (Pi's BF-1..BF-5 fix) +
`git cherry-pick 9104893` (my round-2 re-review summary) +
`git push --force-with-lease`, producing a clean chain. R2-BF-2
should be considered **already-resolved** by that force-push; the
chain on `origin/main..HEAD` does not contain those two commits.
Please re-verify on the new HEAD that this finding no longer
applies.

## Scope (post-rebase on `origin/main` @ `09650ce`)

```text
16 files changed, 2553 insertions(+), 9 deletions(-)
```

Breakdown of `origin/main..HEAD` after `git rebase origin/main`
(clean rebase, 5 commits, no conflicts):

- `src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py`
  (+655 lines net) — R2-BF-1 fix: removed `raw_content_ref=base64...`,
  added requeue block (FETCHED → PENDING with `missing_raw_body_refetch`)
  at the start of `_fetch`, removed `b64decode` fallback from
  `_extract_snapshot`, removed `import base64`
- `tests/integration/application/ingestion/test_ingest_pipeline.py`
  (+706) — 2 new reproducer tests for R2-BF-1
- `tests/unit/application/ingestion/test_ingest_brand_sources.py`
  (+64) — unit test for "no inline base64" pattern (source check)
- `tests/integration/application/ingestion/test_real_adapter_pipeline.py`
  (+136, new, unchanged from round 2) — BF-5 fixture test
- `tests/unit/infrastructure/web_ingestion/test_url_classifier.py`
  (+58, unchanged from round 2) — URL classifier unit tests
- `src/ai_campaign_studio/application/ingestion/dependencies.py`
  (+59) — unchanged from round 2
- `src/ai_campaign_studio/application/ingestion/__init__.py`
  (+18) — exports
- `src/ai_campaign_studio/infrastructure/web_ingestion/url_classifier.py`
  (+171, new) — unchanged from round 2
- `src/ai_campaign_studio/infrastructure/web_ingestion/__init__.py`
  (+4) — unchanged
- `agent_reports/2026-09-10-ACS-S2-014-pi.md` (+237) — original evidence
- `agent_reports/2026-09-10-ACS-S2-014-fix-round2-evidence.md` (+59) — round-2 evidence
- `agent_reports/2026-09-10-ACS-S2-014-fix-round3-evidence.md` (+87) — round-3 evidence
- `agent_reports/2026-09-10-ACS-S2-014-review-codex-r2.md` (+126) — round-2 review (workflow artifact)
- `agent_reports/2026-09-10-ACS-S2-014-coordinator-re-review.md` (+182) — round-2 coordinator summary (workflow artifact)
- empty test `__init__.py` files

## R2-BF-1 fix summary (per Codex round 2)

| Aspect | Detail |
|--------|--------|
| **Fix location** | `ingest_brand_sources.py:325-349` (requeue block) + `:397-405` (`SourceSnapshot` constructor call without `raw_content_ref`) + removal of `import base64` (line 17) |
| **Pattern** | On `_fetch` start, any `CrawlTarget` in `state=FETCHED` with `snapshot_id is not None` is moved back to `PENDING` with `last_error="missing_raw_body_refetch"`. The claim loop below refetches them. `save_source_snapshot` upserts on the deterministic `id`. |
| **`raw_content_ref` state** | Always `None` for any snapshot produced by this use-case (the field is a `str \| None` reference per the `SourceSnapshot` contract; not used as inline payload). |
| **`b64decode` fallback** | Removed from `_extract_snapshot`. Missing in-memory body is a defensive no-op (logs `extract_missing_raw_body`, returns `()`). |
| **`_compute_run_stats`** | Semantic unchanged. Comment added documenting that `fetched_pages` counts unique URLs with `snapshot_id is not None` in `DONE` state. |

## Local verification (coordinator independent)

### Static checks

```text
$ python -m ruff check .
All checks passed!  EXIT=0

$ python -m mypy src
Success: no issues found in 211 source files  EXIT=0
```

### Targeted test suite (G6 + classifier)

```text
$ python -m pytest --tb=line -q \
    tests/integration/application/ingestion/test_ingest_pipeline.py
14 passed in 7.13s   EXIT=0
```

Round-2 was 12 passed; round-3 added 2 reproducer tests
(`test_refetch_path_recovers_body_on_resume` and
`test_raw_content_ref_is_never_inline_body` / similar), now 14.

### Mutation test (R2-BF-1, requeue block)

I independently verified R2-BF-1 by reverting the requeue block
(removing the `for stale in self._repository.list_crawl_targets_by_run(run_id):`
loop) and running `test_refetch_path_recovers_body_on_resume`.

| Mutation | Location | Test | Symptom on mutation | After restore |
|----------|----------|------|---------------------|---------------|
| Removed requeue block (replaced with `pass`) | `ingest_brand_sources.py:334-349` (R2-BF-1 requeue) | `test_refetch_path_recovers_body_on_resume` | `AssertionError: assert 1 > 1` on `len(fetcher.calls)`, plus `WARNING extract_missing_raw_body` — IDENTICAL to Codex R2 repro | 14 passed, `git diff` empty |

Pi documented two more mutations in `fix-round3-evidence.md`:
(a) restoring `raw_content_ref=base64.b64encode(...)` breaks
`test_raw_content_ref_is_never_inline_body`, and
(b) restoring `b64decode` fallback breaks the source-check unit
test. I did not run these myself but they are consistent with
the pattern.

## Original findings — status (per Codex round 2)

- **BF-1 functional recovery**: CLOSED (round 2 confirmed).
  Re-verify on new HEAD that the cancel/hard-kill reproducer
  still passes after the requeue-based refetch path replaced the
  inline-base64 path.
- **BF-2 cancellation checks**: CLOSED (round 2 confirmed).
- **BF-3 MIME detection**: CLOSED (round 2 confirmed).
- **BF-4 visual extraction**: CLOSED (round 2 confirmed).
- **BF-5 real integration**: CLOSED (round 2 confirmed).
- **R2-BF-1 contract breach**: address by current round-3 fix
  (option A: refetch/recovery).
- **R2-BF-2 PR scope contamination**: pre-existing force-push
  resolved it; please re-verify on the new HEAD.

## Specific re-review focus points for Codex (round 3)

1. **Confirm `raw_content_ref` is never inline payload**:
   - `grep -n "base64\|b64encode\|b64decode" src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py` should return zero matches.
   - `grep -n "raw_content_ref" src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py` should return only references to the `SourceSnapshot` field, no assignment with `=` on the right-hand side containing actual data.
2. **Confirm requeue logic correctness**:
   - At `_fetch` start, the `for stale in self._repository.list_crawl_targets_by_run(run_id):` loop moves any `FETCHED` target with `snapshot_id is not None` back to `PENDING`. Verify that the order is: (a) requeue happens BEFORE the main `while True` claim loop, (b) the requeue uses `update_crawl_target_state(target.id, PENDING, last_error=...)`, (c) `recover_expired_leases` is unaffected.
3. **Confirm idempotence**: requeue + refetch on a run with no leftover FETCHED targets should be a no-op (no extra claim, no duplicate fetch).
4. **Confirm `_extract_snapshot` no longer reads `raw_content_ref`**:
   - The `if content is None and snapshot.raw_content_ref:` block at `:443` should be either removed or guarded by a type/scheme check. Per Pi's evidence, it was replaced with a no-op (defensive `return ()` on missing body).
5. **Confirm `_compute_run_stats` semantic unchanged**:
   - Stats for the cancel/hard-kill reproducer should match round-2 values: `snapshots=2, chunks=4, candidates=4, stats fetched_pages=2 / extracted_chunks=4 / built_candidates=4 / failed_pages=0`.
6. **Confirm new reproducer tests are present and pass**:
   - `test_raw_content_ref_is_never_inline_body` (or similarly named)
   - `test_refetch_path_recovers_body_on_resume`
   - `test_ingest_brand_sources_never_inlines_base64_body` (source check)
7. **Confirm R2-BF-2 re-verify**: re-run `git diff --stat origin/main..HEAD` and confirm `.agent/CURRENT_STATE.md` and `agent_reports/2026-09-10-coordinator-handoff-to-minimax-2.md` are NOT in the diff.

## What was NOT changed (preserved from G3/G2 review)

- `recover_expired_leases` / `claim_next_crawl_target` (G2
  atomic claim/recovery) — not touched
- `HttpFetcher` / `UrlSafetyPolicy` SSRF code — not touched
- 1:1 chunk→candidate mapping (BUILD_FACTS) — not touched
- S2-G7a — not touched, no new dependency
- `_checkpoint` ordering (F1 fix) — not touched; DISCOVER
  checkpoint still AFTER `_discover()`
- Repository/port method signatures — unchanged; no new
  persistence/port method added
- `SourceSnapshot` contract — field remains `str | None`,
  semantics unchanged (reference, not payload)
- `application/ingestion/__init__.py` export list — no new
  public symbol added

## Decision request

If your re-review finds no new blocking findings (or only minor
issues the coordinator can address in a follow-up commit),
recommend **PASS** and the coordinator will:

1. `gh pr merge --squash` (no `--delete-branch`, worktree holds
   the branch) — but ONLY after Human Owner explicit approval
   (HIGH task, not §29).
2. Post-merge cycle: `git pull`, `npx gitnexus analyze`,
   `CURRENT_STATE.md` prepend, CI verification.
3. Begin S2-G7b Task Contract (HIGH, bridge + GUI ekran, last
   blocking task before "unesi URL → vidi rezultat" demo).

If you find new blocking findings, please write the fix brief
directly to `agent_reports/2026-09-10-ACS-S2-014-review-codex-r3.md`
(in this worktree) per the project's "fix-brief in agent_reports,
not scratchpad" convention.
