# → ZA PI — FLOW-1001 brief

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-03

## Status — spreman, ništa ne blokira

Sve od čega zavisi već postoji na `main` (schema, prompt, repository port + SQLite adapter — samo
ih niko još nije koristio). Možeš krenuti odmah.

## Gdje je pun kontrakt

`agent_reports/FLOW-1001-task-contract.md` — pročitaj ga cijelog, ovaj brief je samo skraćeni
pregled. Ovaj kontrakt je gušći od prosjeka (dosta dizajn odluka unaprijed riješeno) — vrijedi
pročitati u cjelosti prije koda.

```text
Worktree: ../ai-campaign-studio-worktrees/FLOW-1001-content-revisions
Branch:   task/FLOW-1001-content-revisions
Base:     main @ 5118970
```

## Ukratko šta radiš

Plan sekcija 38 — poslednji preostali komad A12 grupe (linter/status derivacija su tvoj
ACS-F1-012, već gotovo). Već postoji SVE osim domain home-a za revision tipove i samog use-case-a:

- `application/schemas/revision_output.py` — `RevisionOutput`, partial-update preko
  `changed_fields` (Pydantic `model_fields_set`), NE diraj.
- `resources/prompts/revision/v1.yaml` — prompt već postoji.
- `RevisionRepositoryPort`/`SqliteRevisionRepository` — potpuno gotovi, **niko ih još nije
  koristio** — ti si prvi.

Dva nova komada:

1. **`RevisionType` enum** — dodaj u `domain/content/revisions.py`, ISPOD postojećeg
   `RevisionOrigin` (svih 10 vrijednosti su u kontraktu, kopiraj tačno).
2. **`ReviseContentPiece`** use-case — `execute(content_piece_id, revision_type, instruction)`.
   Puna 19-koračna specifikacija je u kontraktu; ukratko: učitaj post → provjeri ima li
   `payload` → odbij `NEW_VISUAL_DIRECTION` odmah → AI poziv sa "immutable fields" u prompt
   kontekstu → `RevisionOutput.changed_fields` MORA biti podskup dozvoljene mape za taj
   `revision_type` (kontrakt ima tačnu mapu, koristi je bukvalno) → primijeni samo ta polja na
   payload → ponovo lintuj POSTOJEĆE claims (`lint_claim`, ne regeneriši ih) →
   `derive_content_status` → **ALI ako je stari status bio `APPROVED`, finalni status je UVIJEK
   `NEEDS_REVIEW`** (doslovno piše u `ContentPiece` docstring-u, pročitaj ga) → napravi
   `Revision` zapis (`version` = redni broj preko `list_entity_revisions`) → atomic persist
   (`save_revision` + `save_content_piece`).

## Najvažnije — dvije namjerne granice

- **`NEW_VISUAL_DIRECTION`** — `RevisionOutput` NEMA `visual_direction` polje. Odbij odmah sa
  jasnom greškom, BEZ AI poziva. Ne izmišljaj zaobilazno rješenje, ne diraj schema fajl.
- **Claims se NE regenerišu** — `RevisionOutput` nema `claims` polje. Samo ponovo pusti postojeće
  claims kroz `lint_claim` (reuse iz `claim_linter.py`), ne pravi nove.

## Pažnja — najlakše mjesto da se nešto zeza

- Partial-field provjera (`changed_fields` mora biti podskup dozvoljene mape) mora STVARNO
  odbaciti prekoračenje, ne tiho primijeniti djelimično — testiraj slučaj gdje model "pokuša"
  promijeniti polje van dozvoljenog opsega za dati tip.
- APPROVED→NEEDS_REVIEW invarijanta mora raditi ČAK i kad revidiran sadržaj prođe linter bez
  ijednog upozorenja (tj. ne smije "prirodno" ostati DRAFT samo zato što je čist).

## Van scope-a

`generate_social_post.py`/`claim_validator.py`/`claim_linter.py`/`derive_content_status.py`/
`select_allowed_facts.py` — koristi ih (import), ne mijenjaj.
