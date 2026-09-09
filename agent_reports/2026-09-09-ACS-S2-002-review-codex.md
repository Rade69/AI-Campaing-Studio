---
verdict: REJECT
scope: REJECT
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - "BF-1: lease_until može isteći dok claim čeka SQLite write lock"
  - "BF-2: domain/ingestion/__init__.py nije u allowed_paths"
---

# ACS-S2-002 — Codex adversarial review PR #25

CILJ: review HEAD 7848c5e, konkurentni claim i snapshot/COALESCE fix.
URAĐENO: REJECT. Snapshot fix je dobar; claim race i scope nisu.
NE DIRATI: snapshot FK/JOIN i COALESCE. SLJEDEĆE: fix pa re-review.

## BF-1 — HIGH

`sqlite_ingestion_repository.py:299` računa `lease_until` prije
`BEGIN IMMEDIATE` na liniji 300. Live repro držao je konkurentni writer
lock pa pozvao claim s duration=1. Claim je commitovao, ali vratio lease
star -0.429769 s; neposredni recovery vratio je 1 i red učinio PENDING.
Drugi worker tada može claimovati isti URL dok ga prvi obrađuje.

Fix: računati rok tek nakon sticanja write locka; dodati test koji drži
lock duže od lease trajanja i potvrđuje važeći lease po povratku. Validirati
pozitivno trajanje. Kontrola s 8 threadova/1 targetom bez dodatnog zastoja
dala je tačno jedan claim, pa je problem specifično vrijeme pod contentionom.

## BF-2 — MEDIUM

Contract dopušta ingestion entities.py/enums.py, ali ne ingestion/__init__.py;
PR ga ipak mijenja. Koordinator mora eksplicitno odobriti scope ili ukloniti
izmjenu jer acceptance traži nula fajlova van allowed_paths.

## Potvrđeno

- Upgrade 0000-0008→0009: `[9]`, zatim `[]`; snapshot kolona/FK postoje.
- Snapshot JOIN uklanja cross-run same-URL leak; COALESCE čuva postojeći ID.
- UNIQUE/ON CONFLICT i recovery `< now`/NULL boundary rade.
- Focused: 32 passed; architecture: 18 passed.
- Full: 1262 passed, 1 skipped, 1 warning.
- Ruff, mypy (183 files), secret scan i diff-check prolaze.
- CI SUCCESS; PR OPEN i MERGEABLE/CLEAN na identičnom HEAD-u.

GitNexus main indeks 7a0337f je svjež. IngestionRepositoryPort impact HIGH:
22 stavke/18 direktnih importa. Worktree detect-changes binding nije radio;
kompenzacija: puni diff/caller sweep i live probe.

Reviewer nije mergeao niti pushao.
