---
task_id: ACS-F1-012
phase: Faza-1
title: "A12 (dio 1) — Claim linter + final ContentStatus derivation"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-02
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - src/ai_campaign_studio/application/posts/derive_content_status.py
  - src/ai_campaign_studio/application/posts/generate_social_post.py
  - resources/claim_rules/default_v1.yaml
  - tests/unit/application/posts/test_claim_linter.py
  - tests/unit/application/posts/test_derive_content_status.py
  - tests/unit/application/posts/test_generate_social_post.py
  - tests/integration/application/posts/test_generate_social_post_integration.py
forbidden_paths:
  - src/ai_campaign_studio/application/posts/select_allowed_facts.py
  - src/ai_campaign_studio/application/posts/claim_validator.py
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/brands/
  - src/ai_campaign_studio/application/schemas/
  - src/ai_campaign_studio/application/mappers/
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: ce4eb5b
  index_status: fresh (analyze re-run 2026-09-02 post ACS-F1-011 merge)
  targets:
    - symbol: "GenerateSocialPost (application/posts/generate_social_post.py) — modifying its interim status logic"
      upstream_risk: LOW
      upstream_count: 0
      downstream_notes: "Zero upstream importers besides its own test files (not yet wired into bootstrap/GUI/CLI) — safe to change its internal status-derivation step. The public execute() signature does not change."
      affected_processes: []
    - symbol: "new claim_linter.py / derive_content_status.py"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "New files, zero existing importers besides the generate_social_post.py rewire in this same task."
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

**A12 iz plana je podijeljen na dva taska**, isti princip kao A9→(ACS-F1-010+011): plan sekcije
36 ("Claim linter") i 37 ("Derivacija Content statusa") su tijesno povezane sa već-mergovanim A11
kodom (`GenerateSocialPost`, `claim_validator.py`) i ne zavise ni od čega novog — **ovaj task**
(ACS-F1-012, "A12 dio 1"). Sekcija 38 ("Content revisions", `revise_content_piece.py`) je
samostalan use-case koji ponovo koristi ovaj linter ali ne blokira ništa drugo — ide u poseban
budući kontrakt (ACS-F1-013, nije još napisan), da ovaj task ostane fokusiran i MEDIUM.

**Šta ACS-F1-011 (već mergovano) namjerno NIJE uradio** (dokumentovano u tom kontraktu): Fact-ID
validator (plan sekcija 35) je implementiran, ali PUNI linter (prohibited termini, numeric pattern
detekcija — sekcija 36) nije, i `ContentPiece.status` je ostajao na interim vrijednosti
(`NEEDS_REVIEW` ili `GENERATING`) — NIKAD `DRAFT`, jer je `DRAFT` rezervisan za sekcija-37 ishod
"nema upozorenja" koji zahtijeva puni linter. **Ovaj task zatvara tu prazninu.**

**Zašto `ClaimStatus.PROHIBITED` do sad nije korišten**: enum član postoji od ACS-F1-002
(`domain/content/enums.py`), ali A11 ga nije koristio jer Fact-ID validator (sekcija 35) samo
odlučuje `VERIFIED_BY_FACT`/`UNSUPPORTED`/`NON_FACTUAL`. `PROHIBITED` je isključivo lintera posao
(sekcija 36) — ovaj task ga prvi put stvarno postavlja.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md
  sekcija 36 "Claim linter", sekcija 37 "Derivacija Content statusa"
  (NE sekcija 38 "Content revisions" — to je van scope-a ovog taska)
```

Pročitati postojeći kod (ne pogađati potpise):

```text
src/ai_campaign_studio/application/posts/claim_validator.py (ACS-F1-011 — Fact-ID validator,
  STIL primjer, ne diraj ga)
src/ai_campaign_studio/application/posts/generate_social_post.py (ACS-F1-011 — TAČNO mjesto
  gdje trenutna interim status logika živi, redovi oko "Interim status" komentara)
src/ai_campaign_studio/domain/content/claims.py (ContentClaim — već ima reason_codes polje)
src/ai_campaign_studio/domain/content/enums.py (ClaimStatus — PROHIBITED već postoji;
  ContentStatus — DRAFT/NEEDS_REVIEW već postoje)
resources/prompts/post_generation/v1.yaml (kontekst — ne diraj, samo referenca)
```

# Objective

1. `resources/claim_rules/default_v1.yaml` — rule config (prohibited termini + numeric pattern
   definicije), data-driven (NE hardkodirati liste u Python-u).
2. `application/posts/claim_linter.py` — `lint_claim()`, primjenjuje pravila na SVAKI claim
   (bilo kog tipa) i može ESKALIRATI status.
3. `application/posts/derive_content_status.py` — `derive_content_status()`, čista funkcija koja
   iz claimova (POSLIJE lintera) računa finalni `ContentStatus`.
4. Prežicati `generate_social_post.py`: pozvati linter na svaki claim POSLIJE
   `validate_claim()`, pa `derive_content_status()` umjesto stare interim logike.

# Implementation steps

## `resources/claim_rules/default_v1.yaml`

```yaml
prohibited_terms:
  - najbolji
  - vodeći
  - garantujemo
  - "100%"
  - bez rizika
  - potpuno sigurno
  - najjeftiniji
  - jedini
  - certifikovan
currency_symbols: ["KM", "BAM", "EUR", "€", "RSD"]
```

Implementer bira tačan YAML shape (dokumentovati), ali MORA sadržati barem ova dva ključa sa
tačno ovim početnim vrijednostima (plan sekcija 36 lista) — "Industry/brand restrictions se
dodaju u isti evaluation pass" znači fajl mora biti lako proširiv (dodaj string u listu), ne da
zahtijeva kod izmjenu za novi termin.

## `claim_linter.py`

```python
@dataclass(frozen=True)
class ClaimRules:
    prohibited_terms: tuple[str, ...]
    currency_symbols: tuple[str, ...]

def load_claim_rules(path: Path) -> ClaimRules: ...

def lint_claim(claim: ContentClaim, rules: ClaimRules) -> ContentClaim: ...
```

`lint_claim` primjenjuje na SVAKI claim, bez obzira na trenutni status (čak i
`VERIFIED_BY_FACT` — fact-backed claim i dalje može sadržati riskantan jezik):

1. **Prohibited/risky termini**: case-insensitive substring provjera `claim.text` protiv
   `rules.prohibited_terms`. Ako nađe bilo koji → `status = ClaimStatus.PROHIBITED`, dodaj
   `"prohibited-claim"` u `reason_codes` (PROHIBITED nadjačava bilo koji prethodni status —
   fact-backed ILI ne, riskantan jezik je i dalje riskantan).
2. **Numeric pattern signal** (SAMO ako claim NIJE već `PROHIBITED` iz koraka 1, i SAMO za
   claimove čiji trenutni status NIJE `VERIFIED_BY_FACT`
   — fact-backed numeric claim je već prošao pravu provjeru u ACS-F1-011, ne treba dupli signal):
   detektuj cijenu (broj + `rules.currency_symbols` član, bilo koji redoslijed) →
   `"unsupported-price"`; postotak (`\d+\s*%`) → `"unsupported-percent"`; trajanje (broj +
   dana/sedmica/mjeseci/godina/minuta/sati, BHS + EN varijante) → `"unsupported-duration"`; datum
   (jednostavan `\d{1,2}\.\d{1,2}\.\d{2,4}` ili slično, ne mora biti savršeno — plan eksplicitno
   kaže "ne mora savršeno razumjeti semantiku") → `"unsupported-date"`; bilo koji drugi goli broj
   → `"unsupported-number"`. Prvi pattern koji se poklopi pobjeđuje (provjeri redoslijedom:
   price, percent, duration, date, generic number). Ako nađe → `status =
   ClaimStatus.UNSUPPORTED`, dodaj odgovarajući reason code (uz postojeće reason_codes, ne
   zamijeni ih).
3. Ako ništa od gore — claim se vraća NEPROMIJENJEN (isti status, isti reason_codes).

## `derive_content_status.py`

```python
def derive_content_status(claims: tuple[ContentClaim, ...]) -> ContentStatus:
    if any(c.status is ClaimStatus.PROHIBITED for c in claims):
        return ContentStatus.NEEDS_REVIEW
    if any(c.status is ClaimStatus.UNSUPPORTED for c in claims):
        return ContentStatus.NEEDS_REVIEW
    return ContentStatus.DRAFT
```

Tačno plan sekcija 37: "Ne auto-approve post" — `DRAFT` je najviše što ova funkcija ikad vrati,
nikad `APPROVED`. Approve je eksplicitna buduća akcija (van scope-a).

## `generate_social_post.py` — rewiring

Pronaći trenutni blok:

```python
claims = tuple(
    validate_claim(claim, allowed, self._fact_repo) for claim in output.claims
)
status = (
    ContentStatus.NEEDS_REVIEW
    if any(claim.status is ClaimStatus.UNSUPPORTED for claim in claims)
    else ContentStatus.GENERATING
)
```

Zamijeniti sa:

```python
validated = (
    validate_claim(claim, allowed, self._fact_repo) for claim in output.claims
)
rules = load_claim_rules(_CLAIM_RULES_PATH)  # implementer bira gdje/kako konstantu drži
claims = tuple(lint_claim(claim, rules) for claim in validated)
status = derive_content_status(claims)
```

`GenerateSocialPost.__init__` potpis se NE mijenja (linter pravila se učitavaju iz resursa, ne
injektuju kao port — isti nivo kao `resources/prompts/` učitan direktno preko
`YamlPromptRepository.from_bundled_resources()` pattern-a u ACS-F1-008, implementer može
replicirati sličan `from_bundled_resources()` helper na `ClaimRules` ili jednostavno hardkodirati
putanju relativno na fajl — dokumentovati izbor).

# Acceptance

- [ ] Claim sa prohibited terminom (npr. "Mi smo najbolji izbor") → `PROHIBITED`, bez obzira da li
      je prethodno bio `VERIFIED_BY_FACT`/`UNSUPPORTED`/`NON_FACTUAL` (test za sve tri startne
      vrijednosti).
- [ ] Numeric claim (cijena/postotak/trajanje/datum/goli broj) koji NIJE `VERIFIED_BY_FACT` →
      `UNSUPPORTED` sa odgovarajućim reason code-om (test po pattern tipu, 5 testova).
- [ ] `VERIFIED_BY_FACT` claim sa brojem u tekstu → OSTAJE `VERIFIED_BY_FACT` (ne triggera
      lažno "unsupported-number" na već fact-backed claim — eksplicitan test).
- [ ] Claim bez prohibited termina i bez numeric pattern-a → nepromijenjen (test).
- [ ] `derive_content_status`: prazan claims tuple → `DRAFT` (nema šta da izazove NEEDS_REVIEW).
- [ ] `derive_content_status`: bilo koji `PROHIBITED` → `NEEDS_REVIEW` (test).
- [ ] `derive_content_status`: bilo koji `UNSUPPORTED` (bez `PROHIBITED`) → `NEEDS_REVIEW` (test).
- [ ] `derive_content_status`: svi `VERIFIED_BY_FACT`/`NON_FACTUAL`, nema warninga → `DRAFT`
      (test).
- [ ] `derive_content_status` NIKAD ne vraća `APPROVED`/`GENERATING` — samo `DRAFT`/`NEEDS_REVIEW`
      (implicitno kroz tipizaciju + testove, provjeri da nema slučajnog trećeg ishoda).
- [ ] `GenerateSocialPost` rewiring: postojeći ACS-F1-011 testovi (`test_generate_social_post.py`,
      `test_generate_social_post_integration.py`) MORAJU biti ažurirani gdje očekuju
      `GENERATING` — sad će dobiti `DRAFT` (happy path bez warninga) — implementer ažurira
      assertions, NE briše testove.
- [ ] `resources/claim_rules/default_v1.yaml` sadrži tačno početnu listu prohibited termina iz
      plan sekcije 36 i `currency_symbols` iz iste sekcije.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/application/posts tests/integration/application/posts -v
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `PROHIBITED` nadjačava svaki prethodni claim status (uključujući `VERIFIED_BY_FACT`) — provjeri
  da fact-backed claim sa riskantnim jezikom stvarno postane `PROHIBITED`, ne ostane
  `VERIFIED_BY_FACT`;
- numeric-pattern signal se NE primjenjuje na već `VERIFIED_BY_FACT` claimove (izbjeći lažne
  pozitive na legitimno fact-backed brojeve);
- `derive_content_status` je čista funkcija (nema side-effect-a, nema repository/AI poziva) —
  lako testabilna u izolaciji;
- `generate_social_post.py` diff je fokusiran na status-derivation blok — provjeri da ostatak
  use-case-a (loading, AIRequest building, persistence) nije slučajno promijenjen;
- postojeći ACS-F1-011 testovi su ažurirani (ne izbrisani/oslabljeni) da odražavaju novi `DRAFT`
  ishod na happy path-u — pročitaj diff tih fajlova pažljivo, ovo je mjesto gdje bi implementer
  mogao "popraviti" test brisanjem provjere umjesto stvarnim popravkom.

# Rollback

MEDIUM risk — izolovana logika unutar već-postojećeg, izolovanog `application/posts/` paketa.
Fix na istoj branch bez proširenja scope-a. STOP i vrati na puni ciklus samo ako se pokaže da
treba dirati `domain/content/enums.py`/`claims.py` (trenutno nije potrebno — `PROHIBITED` već
postoji).

# Coordination

Nezavisan od svega trenutno otvorenog. **Ne implementira sekciju 38** (Content revisions,
`revise_content_piece.py`) — to je budući ACS-F1-013, van scope-a ovog taska, ne dodavati ga
"dok si već tu".

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-012-claim-linter-status
Branch:   task/ACS-F1-012-claim-linter-status
Base:     main @ ce4eb5b
```
