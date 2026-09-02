# → ZA PI — ACS-F1-012 brief

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-02

## Status — spreman, ništa ne blokira

Za razliku od ACS-F1-011, ovaj task **nije BLOCKED** — sve od čega zavisi (`ClaimStatus.PROHIBITED`,
`ContentStatus.DRAFT`/`NEEDS_REVIEW`, `ContentClaim.reason_codes`) već postoji na `main`. Možeš
krenuti odmah.

## Gdje je pun kontrakt

`agent_reports/ACS-F1-012-task-contract.md` — pročitaj ga cijelog.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-012-claim-linter-status
Branch:   task/ACS-F1-012-claim-linter-status
Base:     main @ ce4eb5b
```

## Ukratko šta radiš

Ovo je "A12 dio 1" — plan sekcije 36 (Claim linter) + 37 (Derivacija Content statusa). Sekcija 38
(Content revisions) je NAMJERNO isključena, ide u budući ACS-F1-013 — ne dodavati je "dok si već
tu".

Ti sam si u ACS-F1-011 ostavio `ContentPiece.status` na interim vrijednosti (`GENERATING` ili
`NEEDS_REVIEW`, nikad `DRAFT`) upravo zato što je puni linter tada nedostajao. Sad ga praviš:

1. **`resources/claim_rules/default_v1.yaml`** — data-driven lista prohibited termina +
   currency simboli (tačne početne vrijednosti su u kontraktu).
2. **`claim_linter.py`** — `lint_claim(claim, rules)`: prohibited termin u `claim.text` →
   `PROHIBITED` (nadjačava ČAK I `VERIFIED_BY_FACT` — riskantan jezik je riskantan bez obzira na
   fact backing). Numeric pattern (cijena/postotak/trajanje/datum/goli broj) u tekstu claim-a koji
   NIJE već `VERIFIED_BY_FACT` → `UNSUPPORTED` sa odgovarajućim reason code-om.
3. **`derive_content_status.py`** — čista funkcija: bilo koji `PROHIBITED`/`UNSUPPORTED` claim →
   `NEEDS_REVIEW`, inače `DRAFT`. Nikad `APPROVED` (ne auto-approve-uje se).
4. **Prežicati `generate_social_post.py`** (tvoj vlastiti fajl iz ACS-F1-011) — pozvati linter
   na svaki claim POSLIJE `validate_claim()`, pa `derive_content_status()` umjesto stare interim
   logike.

## Pažnja — najlakše mjesto da se nešto zeza

Tvoji POSTOJEĆI ACS-F1-011 testovi (`test_generate_social_post.py`,
`test_generate_social_post_integration.py`) očekuju `GENERATING` na happy path-u. Nakon
rewiring-a, happy path (bez prohibited/numeric problema) će vratiti `DRAFT`. **Ažuriraj te
assertion-e da odražavaju novi, ispravan ishod — ne brisati/oslabljivati testove da "prođu".** Ovo
je tačno mjesto koje ću najpažljivije pregledati.

## Van scope-a

- `select_allowed_facts.py`/`claim_validator.py` (tvoj ACS-F1-011 kod) — ne diraj, samo pozivaj.
- `revise_content_piece.py` (sekcija 38) — budući task.
- Bilo šta u `domain/` — sve što ti treba (`PROHIBITED`, `DRAFT`, `reason_codes`) već postoji.
